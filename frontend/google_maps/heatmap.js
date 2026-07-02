class HeatmapManager {
    constructor(map) {
        this.map = map;
        this.fullGrid = [];       // Store all data
        this.activeRects = [];    // Store currently rendered rectangles
        this.isVisible = document.getElementById('layer-estimated').checked;
        
        // Listen to map bounds change to lazy render grid cells
        this.map.addListener("idle", () => this.lazyRender());
    }

    loadData(gridCells) {
        this.fullGrid = gridCells;
        this.lazyRender();
    }

    lazyRender() {
        if (!this.isVisible) return;
        
        const bounds = this.map.getBounds();
        if (!bounds) return;

        // Clear existing
        this.activeRects.forEach(r => r.setMap(null));
        this.activeRects = [];

        // Only draw rectangles that intersect the current viewport
        this.fullGrid.forEach(cell => {
            const cellBounds = new google.maps.LatLngBounds(
                { lat: cell.bounds.south, lng: cell.bounds.west },
                { lat: cell.bounds.north, lng: cell.bounds.east }
            );
            
            if (bounds.intersects(cellBounds)) {
                const color = utils.getAQIColor(cell.aqi);
                const rect = new google.maps.Rectangle({
                    bounds: cell.bounds,
                    fillColor: color,
                    fillOpacity: 0.35,
                    strokeWeight: 0,
                    map: this.map,
                    clickable: false // Let map handle clicks
                });
                this.activeRects.push(rect);
            }
        });
    }

    toggle(visible) {
        this.isVisible = visible;
        if (visible) {
            this.lazyRender();
        } else {
            this.activeRects.forEach(r => r.setMap(null));
            this.activeRects = [];
        }
    }
}
