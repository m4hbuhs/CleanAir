import logging
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Form, Response, HTTPException
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai
from firebase_admin import firestore

logger = logging.getLogger(__name__)
router = APIRouter()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

@router.post("/whatsapp-webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...)
):
    try:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")
            
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        system_instruction = (
            "You are the CleanAirApp Emergency Agent. "
            "Extract the environmental hazard (like fire, smoke, smog, dust) and location (street name, neighborhood) "
            "from the user's message. If a valid hazard is found, return exactly this format: "
            "HAZARD: [hazard]\nLOCATION: [location]. "
            "If no hazard is found, return 'NO_HAZARD'."
        )
        
        prompt = f"{system_instruction}\n\nUser Message: {Body}"
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        db = firestore.client()
        twiml_response = MessagingResponse()
        
        if text_response.startswith("HAZARD:"):
            # Parse the extracted info
            lines = text_response.split('\n')
            hazard = lines[0].replace("HAZARD: ", "").strip()
            location = lines[1].replace("LOCATION: ", "").strip() if len(lines) > 1 else "Unknown"
            
            incident_record = {
                "source": "whatsapp",
                "hazard": hazard,
                "location": location,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reporter": From,
                "verified": False, # Needs manual review
                "trust_score": 0.5
            }
            
            db.collection("incidents").add(incident_record)
            
            msg = f"Thank you. Your report of '{hazard}' at '{location}' has been recorded and an investigation team will be notified."
            twiml_response.message(msg)
        else:
            msg = "I'm the CleanAirApp Emergency Agent. Please describe the environmental hazard and your location."
            twiml_response.message(msg)
            
        return Response(content=str(twiml_response), media_type="application/xml")
        
    except Exception as e:
        logger.error(f"WhatsApp webhook failed: {e}")
        error_twiml = MessagingResponse()
        error_twiml.message("Sorry, our service is temporarily unavailable. Please try again later.")
        return Response(content=str(error_twiml), media_type="application/xml")
