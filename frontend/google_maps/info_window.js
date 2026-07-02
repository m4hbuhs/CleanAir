class InfoWindowManager {
    constructor(map) {
        this.map = map;
        this.infoWindow = new google.maps.InfoWindow();
    }

    close() {
        this.infoWindow.close();
    }

    showStation(station, marker) {
        const content = `
            <div class="custom-popup">
                <h4>🏢 ${station.name}</h4>
                <p><strong>Official AQI:</strong> <span class="aqi-tag" style="background:${markerManager.getAQIColor(station.aqi)}">${station.aqi}</span></p>
                <p><strong>PM2.5:</strong> ${station.pm25} µg/m³</p>
                <p><strong>Last Updated:</strong> ${station.updated}</p>
                <p style="font-size:11px; color:#888; margin-top:8px;">(Official Data - Unmodified)</p>
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
                <p><strong>Time:</strong> ${alert.timestamp}</p>
            </div>
        `;
        this.infoWindow.setContent(content);
        this.infoWindow.open(this.map, marker);
    }

    showHotspot(hotspot, latLng) {
        const content = `
            <div class="custom-popup">
                <h4>🔥 Pollution Hotspot</h4>
                <p><strong>Primary Source:</strong> ${hotspot.dominant_type}</p>
                <p><strong>Reports:</strong> ${hotspot.report_count}</p>
                <p><strong>Avg Severity:</strong> ${hotspot.severity.toFixed(1)}/5</p>
                <p><strong>Estimated AQI:</strong> ${hotspot.estimated_aqi.toFixed(0)}</p>
            </div>
        `;
        this.infoWindow.setContent(content);
        this.infoWindow.setPosition(latLng);
        this.infoWindow.open(this.map);
    }

    showLoading(lat, lng) {
        const content = `
            <div class="custom-popup">
                <h4>🤖 AI Virtual Sensor</h4>
                <p>Calculating hyperlocal AQI...</p>
                <p style="font-size:11px; color:#aaa;">Fusing official, weather, and citizen data.</p>
            </div>
        `;
        this.infoWindow.setContent(content);
        this.infoWindow.setPosition({ lat, lng });
        this.infoWindow.open(this.map);
    }

    showResult(result) {
        // Build 24h forecast mini-chart HTML
        let forecastHtml = "";
        if (result.forecast && result.forecast.length > 0) {
            forecastHtml = `<div class="forecast-chart">`;
            // Take up to 12 points to fit in popup
            result.forecast.slice(0, 12).forEach(f => {
                const height = Math.min(100, Math.max(10, (f.aqi / 500) * 100));
                const color = markerManager.getAQIColor(f.aqi);
                forecastHtml += `<div class="forecast-bar" style="height:${height}%; background:${color};" title="Hour +${f.hour}: ${f.aqi.toFixed(0)}"></div>`;
            });
            forecastHtml += `</div><p style="font-size:10px; text-align:center; color:#aaa; margin:2px 0 0 0;">24h Forecast</p>`;
        }

        const content = `
            <div class="custom-popup">
                <h4>🤖 AI Estimated AQI</h4>
                <p style="font-size:24px; font-weight:bold; color:${markerManager.getAQIColor(result.aqi)}; margin:5px 0;">${result.aqi.toFixed(0)}</p>
                <p><strong>Confidence:</strong> ${result.confidence}%</p>
                <p><strong>Weather:</strong> ${result.weather}</p>
                ${forecastHtml}
                
                ${result.recommendation ? `
                <div class="recommendation-box">
                    <strong>Municipal Action:</strong><br/>
                    ${result.recommendation}
                </div>` : ''}
            </div>
        `;
        this.infoWindow.setContent(content);
    }
}
