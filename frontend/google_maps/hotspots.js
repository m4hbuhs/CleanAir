class HotspotManager {
    constructor(map, popupManager) {
        this.map = map;
        this.popupManager = popupManager;
        this.circles = [];
    }

    loadData(hotspots) {
        this.clear();
        const isVisible = document.getElementById('layer-hotspots').checked;
        
        hotspots.forEach(h => {
            const color = h.severity >= 4 ? "#F44336" : "#FF9800";
            
            const circle = new google.maps.Circle({
                strokeColor: "#FFFFFF",
                strokeOpacity: 0.8,
                strokeWeight: 2,
                fillColor: color,
                fillOpacity: 0.35,
                map: isVisible ? this.map : null,
                center: { lat: h.lat, lng: h.lng },
                radius: h.radius
            });
            
            circle.addListener("click", (e) => {
                this.popupManager.showHotspot(h, e.latLng);
            });
            
            this.circles.push(circle);
        });
    }

    toggle(visible) {
        this.circles.forEach(c => c.setMap(visible ? this.map : null));
    }

    clear() {
        this.circles.forEach(c => c.setMap(null));
        this.circles = [];
    }
}
