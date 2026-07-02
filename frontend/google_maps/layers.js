class LayerManager {
    constructor(map, managers) {
        this.map = map;
        this.managers = managers; // { markerManager, heatmapManager, hotspotManager }
        this.bindEvents();
    }

    bindEvents() {
        document.getElementById('layer-official').addEventListener('change', (e) => {
            if (this.managers.markerManager) this.managers.markerManager.toggleStations(e.target.checked);
        });
        document.getElementById('layer-estimated').addEventListener('change', (e) => {
            if (this.managers.heatmapManager) this.managers.heatmapManager.toggle(e.target.checked);
        });
        document.getElementById('layer-reports').addEventListener('change', (e) => {
            if (this.managers.markerManager) this.managers.markerManager.toggleReports(e.target.checked);
        });
        document.getElementById('layer-hotspots').addEventListener('change', (e) => {
            if (this.managers.hotspotManager) this.managers.hotspotManager.toggle(e.target.checked);
        });
        document.getElementById('layer-alerts').addEventListener('change', (e) => {
            if (this.managers.markerManager) this.managers.markerManager.toggleAlerts(e.target.checked);
        });
    }
}
