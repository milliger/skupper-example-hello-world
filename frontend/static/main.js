new EventSource("/api/notifications").onmessage = event => {
    const p = document.createElement("p")
    p.innerHTML = `${new Date().toLocaleTimeString()}: ${event.data}`

    const messages = document.getElementById("messages")
    messages.insertBefore(p, messages.firstChild);

    console.log(event)
};
