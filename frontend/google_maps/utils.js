const utils = {
    getAQIColor: (aqi) => {
        if (aqi <= 50) return "#00e400";
        if (aqi <= 100) return "#ffff00";
        if (aqi <= 200) return "#ff7e00";
        if (aqi <= 300) return "#ff0000";
        if (aqi <= 400) return "#8f3f97";
        return "#7e0023";
    },
    
    // Finds the closest point in the grid for mock click behavior
    findClosestAQI: (lat, lng, grid) => {
        if (!grid || grid.length === 0) return null;
        let minDistance = Infinity;
        let closest = grid[0];
        grid.forEach(cell => {
            const centerLat = (cell.bounds.north + cell.bounds.south) / 2;
            const centerLng = (cell.bounds.east + cell.bounds.west) / 2;
            const dLat = centerLat - lat;
            const dLng = centerLng - lng;
            const dist = dLat*dLat + dLng*dLng;
            if (dist < minDistance) {
                minDistance = dist;
                closest = cell;
            }
        });
        return closest;
    }
};
