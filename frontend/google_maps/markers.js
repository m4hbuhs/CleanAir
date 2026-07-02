class MarkerManager {
    constructor(map, popupManager) {
        this.map = map;
        this.popupManager = popupManager;
        this.stationMarkers = [];
        this.reportMarkers = [];
        this.alertMarkers = [];
        this.reportClusterer = null;
    }

    createPinElement(background, glyphColor, text) {
        const pin = new google.maps.marker.PinElement({
            background: background,
            glyphColor: glyphColor,
            borderColor: "#ffffff",
        });
        if (text) pin.glyph = text;
        return pin.element;
    }

    renderStations(stations) {
        stations.forEach(st => {
            const color = utils.getAQIColor(st.aqi);
            const marker = new google.maps.marker.AdvancedMarkerElement({
                map: document.getElementById('layer-official').checked ? this.map : null,
                position: { lat: st.lat, lng: st.lng },
                content: this.createPinElement(color, "#000", "S"),
                title: st.name
            });
            marker.addListener("click", () => this.popupManager.showStation(st, marker));
            this.stationMarkers.push(marker);
        });
    }

    renderReports(reports) {
        reports.forEach(r => {
            let iconText = "🏭";
            if (r.type.includes("Dust")) iconText = "💨";
            if (r.type.includes("Garbage") || r.type.includes("Waste")) iconText = "🗑️";
            if (r.type.includes("Vehicle")) iconText = "🚗";
            
            const marker = new google.maps.marker.AdvancedMarkerElement({
                map: null, // Let clusterer handle it
                position: { lat: r.lat, lng: r.lng },
                content: this.createPinElement("#2196F3", "#fff", iconText),
                title: r.type
            });
            marker.addListener("click", () => this.popupManager.showReport(r, marker));
            this.reportMarkers.push(marker);
        });
        
        if (window.markerClusterer) {
            this.reportClusterer = new markerClusterer.MarkerClusterer({
                map: document.getElementById('layer-reports').checked ? this.map : null,
                markers: this.reportMarkers
            });
        }
    }

    renderAlerts(alerts) {
        alerts.forEach(a => {
            const color = a.status === "Pending" ? "#F44336" : "#FF9800";
            const marker = new google.maps.marker.AdvancedMarkerElement({
                map: document.getElementById('layer-alerts').checked ? this.map : null,
                position: { lat: a.lat, lng: a.lng },
                content: this.createPinElement(color, "#fff", "🚨"),
                title: "Alert: " + a.type
            });
            marker.addListener("click", () => this.popupManager.showAlert(a, marker));
            this.alertMarkers.push(marker);
        });
    }

    toggleStations(visible) {
        this.stationMarkers.forEach(m => m.map = visible ? this.map : null);
    }

    toggleReports(visible) {
        if (this.reportClusterer) {
            visible ? this.reportClusterer.setMap(this.map) : this.reportClusterer.setMap(null);
        } else {
            this.reportMarkers.forEach(m => m.map = visible ? this.map : null);
        }
    }
    
    toggleAlerts(visible) {
        this.alertMarkers.forEach(m => m.map = visible ? this.map : null);
    }
}
