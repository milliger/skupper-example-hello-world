// Initialize the map
var map = L.map('map').setView([49.7079507, 7.6666393], 6); // Center on Munich with zoom level 13

// Add a tile layer
L.tileLayer('https://tile.openstreetmap.de/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 18
}).addTo(map);

// Initialize the marker variable (without adding it to the map yet)
var markers = {};

const planeIcon = L.icon({
    iconUrl: '/static/plane.svg',
    iconSize: [36, 36]
})

// Function to update the marker's position and add it to the map if it's the first event
function updateMarker(plane_id, latitude, longitude, heading) {
    var newLatLng = new L.LatLng(latitude, longitude);
    if (!markers[plane_id]) {
        // If the marker doesn't exist yet, create it and add it to the map
        const marker = L.marker(
            newLatLng, 
            {
                icon: planeIcon,
                rotationAngle: heading
            }
        ).addTo(map);
        markers[plane_id] = marker
    } else {
        // If the marker already exists, just update its position
        const marker = markers[plane_id]
        marker.setLatLng(newLatLng);
        marker.setRotationAngle(heading)
    }
}

new EventSource("/api/notifications").onmessage = event => {

    const data = JSON.parse(event.data)
    if (data.planes) {
        data.planes.forEach(plane => {
            updateMarker(plane.plane_id, parseFloat(plane.lat), parseFloat(plane.lon), parseFloat(plane.head))
        });
    } else {
        console.warn("Received event with missing planes:", data);
    }

    const div = document.createElement("div")
    div.className = "message"
    const time_div = document.createElement("div")
    time_div.className = "time"
    const data_pre = document.createElement("pre")
    data_pre.className = "data"
    time_div.innerHTML = `${new Date().toLocaleTimeString()} | ${data.origin}`
    data_pre.innerHTML = `${JSON.stringify(data.planes)}`

    div.appendChild(time_div)
    div.appendChild(data_pre)

    const messages = document.getElementById("messages")
    messages.insertBefore(div, messages.firstChild);
    if (messages.children.length > 20) {
        // remove the oldest message
        messages.removeChild(messages.lastChild);
    }

    const origin = document.getElementById("origin")
    origin.innerHTML = data.origin
};
