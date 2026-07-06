import logging
from twilio.rest import Client
from backend.config import get_settings
from firebase_admin import firestore

logger = logging.getLogger(__name__)

def notify_subscribers(incident_record: dict):
    """
    Sends WhatsApp alerts to users subscribed to the district of the verified incident.
    """
    settings = get_settings()
    
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_whatsapp_number:
        logger.warning("Twilio credentials not configured. Skipping WhatsApp notification.")
        return
        
    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        
        district = incident_record.get("district", "Unknown")
        location = incident_record.get("street_name", incident_record.get("neighborhood", "Unknown"))
        
        message_body = f"Alert: Verified environmental hazard reported in your district ({district}) near {location}."
        
        # Query Firestore for subscribers in this district
        db = firestore.client()
        subscribers_ref = db.collection("subscribers").where("district", "==", district).stream()
        
        count = 0
        for sub in subscribers_ref:
            sub_data = sub.to_dict()
            phone_number = sub_data.get("phone_number")
            if phone_number:
                if not phone_number.startswith("whatsapp:"):
                    phone_number = f"whatsapp:{phone_number}"
                
                try:
                    client.messages.create(
                        body=message_body,
                        from_=settings.twilio_whatsapp_number,
                        to=phone_number
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to send WhatsApp to {phone_number}: {e}")
                    
        logger.info(f"Sent {count} WhatsApp notifications for incident at {location}.")
        
    except Exception as e:
        logger.error(f"Notification service failed: {e}", exc_info=True)
