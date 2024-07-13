const wsProtocol = window.clippyApp?.protocol || "ws" // ws or wss, not sure if wss will easily work
const wsHost = window.clippyApp?.host || "localhost"
const wsPort = window.clippyApp?.port || "8765"
const wsReconnectInterval = window.clippyApp?.reconnectInterval || 5000

function connectWebSocket() {
  const clippy_socket = new WebSocket(`${wsProtocol}://${wsHost}:${wsPort}`)

  clippy_socket.addEventListener("open", (event) => {})

  clippy_socket.addEventListener("close", (event) => {
    console.log(`clippy-injection disconnected from ws server, reconnecting in ${wsReconnectInterval / 1000}s`)
    setTimeout(connectWebSocket, wsReconnectInterval)
  })

  return clippy_socket
}

function sendEvent(eventType, eventData) {
  if (clippy_socket.readyState === WebSocket.OPEN) {
    const message = JSON.stringify({ type: eventType, data: eventData })
    clippy_socket.send(message)
  }
}

const clippy_socket = connectWebSocket()

window.addEventListener(
  "input",
  (inputEvent) => {
    var elementId = inputEvent.target.id
    var element = document.getElementById(elementId)
    if (element != null) {
      checkIfScrolled()
      sendEvent("input", {
        value: inputEvent.target.value,
        x: element.offsetLeft,
        y: element.offsetTop,
      })
    } else {
      // need to handle fail
    }
  },
  true
)

document.addEventListener(
  "keydown",
  (event) => {
    sendEvent("keydown", { key: event.key, code: event.code })
  },
  true
)

document.addEventListener("keyup", (event) => {
  sendEvent("keyup", { key: event.key, code: event.code })
})

document.addEventListener("mousemove", (event) => {
  sendEvent("mousemove", { x: event.clientX, y: event.clientY })
})

document.addEventListener("mousedown", (event) => {
  sendEvent("mousedown", { button: event.button, x: event.clientX, y: event.clientY })
})

document.addEventListener("mouseup", (event) => {
  sendEvent("mouseup", { button: event.button, x: event.clientX, y: event.clientY })
})

clippy_socket.addEventListener("error", (error) => {
  console.error("clippy-websocket error:", error)
})
