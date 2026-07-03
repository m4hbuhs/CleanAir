class PopupManager {
    constructor(map) {
        this.map = map;
        this.infoWindow = new google.maps.InfoWindow();
    }

    showStation(station, marker) {
        const content = `
            <div class="custom-popup">
                <h4>🏢 ${station.name}</h4>
                <p><strong>Official AQI:</strong> <span class="aqi-tag" style="background:${utils.getAQIColor(station.aqi)}">${station.aqi}</span></p>
                <p><strong>PM2.5:</strong> ${station.pm25} µg/m³</p>
                <p><strong>Last Updated:</strong> ${station.updated}</p>
            </div>
        `;
        this.infoWindow.setContent(content);
        this.infoWindow.open(this.map, marker);
    }

    showReport(report, marker) {
        const content = `
            <div class="custom-popup">
                <h4>📸 Citizen Report</h4>
                <p><strong>Type:</strong> ${report.type}</p>
                <p><strong>Severity:</strong> ${report.severity}</p>
                <p><strong>Confidence:</strong> ${(report.confidence * 100).toFixed(1)}%</p>
                <p><strong>Time:</strong> ${report.timestamp}</p>
                <p style="margin-top:6px; font-style:italic;">"${report.description}"</p>
            </div>
        `;
        this.infoWindow.setContent(content);
        this.infoWindow.open(this.map, marker);
    }

    showAlert(alert, marker) {
        const content = `
            <div class="custom-popup">
                <h4>🚨 Municipal Alert</h4>
                <p><strong>Type:</strong> ${alert.type}</p>
                <p><strong>Trigger AQI:</strong> ${alert.aqi}</p>
                <p><strong>Status:</strong> ${alert.status}</p>
            </div>
        `;
        this.infoWindow.setContent(content);
        this.infoWindow.open(this.map, marker);
    }

    showHotspot(hotspot, latLng) {
        const content = `
            <div class="custom-popup">
                <h4>🔥 Pollution Hotspot</h4>
                <p><strong>Source:</strong> ${hotspot.dominant_type}</p>
                <p><strong>Reports:</strong> ${hotspot.report_count}</p>
                <p><strong>Estimated AQI:</strong> ${hotspot.estimated_aqi.toFixed(0)}</p>
            </div>
        `;
        this.infoWindow.setContent(content);
        this.infoWindow.setPosition(latLng);
        this.infoWindow.open(this.map);
    }

    showEstimatedClick(result, latLng) {
        const sat = result.satellite || { aod: 0.1, no2: 15, thermal_anomaly: false };
        const thermalBadge = sat.thermal_anomaly ? '<span style="color:red;font-weight:bold;">Detected 🔥</span>' : 'None';
        
        const content = `
            <div class="custom-popup" style="min-width: 200px;">
                <h4>🤖 AI Estimated AQI</h4>
                <p style="font-size:24px; font-weight:bold; color:${utils.getAQIColor(result.aqi)}; margin:5px 0;">${result.aqi.toFixed(0)}</p>
                <p><strong>Location:</strong> ${latLng.lat().toFixed(4)}, ${latLng.lng().toFixed(4)}</p>
                <div style="margin-top: 10px; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 6px; border: 1px solid #444;">
                    <h5 style="margin: 0 0 5px 0; color: #888; border-bottom: 1px solid #444; padding-bottom: 3px;">🛰️ GEE Confidence Breakdown</h5>
                    <p style="margin: 2px 0; font-size: 11px;"><strong>Aerosol (AOD):</strong> ${sat.aod.toFixed(2)}</p>
                    <p style="margin: 2px 0; font-size: 11px;"><strong>NO2 Density:</strong> ${sat.no2.toFixed(1)} µmol/m²</p>
                    <p style="margin: 2px 0; font-size: 11px;"><strong>Thermal Anomaly:</strong> ${thermalBadge}</p>
                </div>
            </div>
        `;
        this.infoWindow.setContent(content);
        this.infoWindow.setPosition(latLng);
        this.infoWindow.open(this.map);
    }
}
