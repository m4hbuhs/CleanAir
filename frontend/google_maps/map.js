// Global map instance
let map = null;
let popupManager, markerManager, layerManager, heatmapManager, hotspotManager;

// Initialization callback from Google Maps API
window.initMap = async function() {
    // Custom dark theme styling
    const darkTheme = [
        { elementType: "geometry", stylers: [{ color: "#212121" }] },
        { elementType: "labels.icon", stylers: [{ visibility: "off" }] },
        { elementType: "labels.text.fill", stylers: [{ color: "#757575" }] },
        { elementType: "labels.text.stroke", stylers: [{ color: "#212121" }] },
        { featureType: "administrative", elementType: "geometry", stylers: [{ color: "#757575" }] },
        { featureType: "road", elementType: "geometry.fill", stylers: [{ color: "#2c2c2c" }] },
        { featureType: "road", elementType: "labels.text.fill", stylers: [{ color: "#8a8a8a" }] },
        { featureType: "water", elementType: "geometry", stylers: [{ color: "#000000" }] }
    ];

    map = new google.maps.Map(document.getElementById("map"), {
        center: { lat: 28.6139, lng: 77.2090 }, // New Delhi
        zoom: 12,
        styles: darkTheme,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        mapId: 'CLEANAIR_MAP_ID' // Required for AdvancedMarkers
    });

    // Initialize Managers
    popupManager = new PopupManager(map);
    markerManager = new MarkerManager(map, popupManager);
    heatmapManager = new HeatmapManager(map);
    hotspotManager = new HotspotManager(map, popupManager);
    
    layerManager = new LayerManager(map, {
        markerManager, 
        heatmapManager, 
        hotspotManager
    });

    // Setup Search Box
    const input = document.getElementById("search-box");
    const searchBox = new google.maps.places.SearchBox(input);
    
    searchBox.addListener("places_changed", () => {
        const places = searchBox.getPlaces();
        if (places.length == 0) return;
        
        const bounds = new google.maps.LatLngBounds();
        places.forEach((place) => {
            if (!place.geometry || !place.geometry.location) return;
            if (place.geometry.viewport) {
                bounds.union(place.geometry.viewport);
            } else {
                bounds.extend(place.geometry.location);
            }
        });
        map.fitBounds(bounds);
    });

    // Map Click: Calculate mock Virtual Sensor estimate based on grid data
    map.addListener("click", (e) => {
        const lat = e.latLng.lat();
        const lng = e.latLng.lng();
        const grid = window.MAP_DATA ? window.MAP_DATA.estimated_grid : null;
        
        const closestCell = utils.findClosestAQI(lat, lng, grid);
        if (closestCell) {
            popupManager.showEstimatedClick(closestCell, e.latLng);
        } else {
            // Fallback if grid is empty
            popupManager.showEstimatedClick({aqi: 50, confidence: 100}, e.latLng);
        }
    });

    // Load Initial Data
    if (window.MAP_DATA) {
        if (window.MAP_DATA.stations) markerManager.renderStations(window.MAP_DATA.stations);
        if (window.MAP_DATA.reports) markerManager.renderReports(window.MAP_DATA.reports);
        if (window.MAP_DATA.alerts) markerManager.renderAlerts(window.MAP_DATA.alerts);
        if (window.MAP_DATA.hotspots) hotspotManager.loadData(window.MAP_DATA.hotspots);
        if (window.MAP_DATA.estimated_grid) heatmapManager.loadData(window.MAP_DATA.estimated_grid);
    }
};
