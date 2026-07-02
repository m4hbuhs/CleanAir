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
        const content = `
            <div class="custom-popup">
                <h4>🤖 AI Estimated AQI</h4>
                <p style="font-size:24px; font-weight:bold; color:${utils.getAQIColor(result.aqi)}; margin:5px 0;">${result.aqi.toFixed(0)}</p>
                <p><strong>Location:</strong> ${latLng.lat().toFixed(4)}, ${latLng.lng().toFixed(4)}</p>
                <p style="font-size:11px; color:#aaa;">(Locally interpolated from AI Grid)</p>
            </div>
        `;
        this.infoWindow.setContent(content);
        this.infoWindow.setPosition(latLng);
        this.infoWindow.open(this.map);
    }
}
