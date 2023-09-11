// INFO: As I learn more about playwright, I am realizing that I would probably want to use
// expose_binding or expose_function in python from playwright rather than transmitting data over console.log
// console.log("CATCH: From preload.js")
const CATCH_FLAG = "CATCH"

const trackInfo = {
  wheel: {
    deltaX: 0,
    deltaY: 0,
  },
}

function _transmitData(flag, data) {
  console.log(CATCH_FLAG, flag, JSON.stringify(data))
}

function _fail(data) {
  const FLAG = "FAIL"
  _transmitData(FLAT, args)
}

function _debug(data) {
  const FLAG = "DEBUG"
  _transmitData(FLAG, data)
}

function elemPositionDocument(el) {
  let rect = el.getBoundingClientRect()

  return {
    left: rect.left + window.scrollX,
    right: rect.right + window.scrollX,
    top: rect.top + window.scrollY,
    bottom: rect.bottom + window.scrollY,
  }
}

// from https://stackoverflow.com/questions/42184322/javascript-get-element-unique-selector
function getSelector(elm) {
  if (elm.tagName === "BODY") return "BODY"
  const names = []
  while (elm.parentElement && elm.tagName !== "BODY") {
    if (elm.id) {
      names.unshift("#" + elm.getAttribute("id")) // getAttribute, because `elm.id` could also return a child element with name "id"
      break // Because ID should be unique, no more is needed. Remove the break, if you always want a full path.
    } else {
      let c = 1,
        e = elm
      for (; e.previousElementSibling; e = e.previousElementSibling, c++);
      names.unshift(elm.tagName + ":nth-child(" + c + ")")
    }
    elm = elm.parentElement
  }
  return names.join(">")
}

function checkIfScrolled() {
  const INPUT_TYPE = "Wheel"
  if (window.scrollX != 0 || window.scrollY != 0) {
    _transmitData(INPUT_TYPE, {
      delta_x: window.scrollX,
      delta_y: window.scrollY,
    })
  }
}

var makeTrackInput = function (INPUT_TYPE) {
  return function (inputEvent) {
    // for tracking, trying to decide how to get text event and associated element
    var elementId = inputEvent.target.id
    var element = document.getElementById(elementId)
    if (element != null) {
      checkIfScrolled()
      _transmitData(INPUT_TYPE, {
        value: inputEvent.target.value,
        // there is also element.offsetHeight, element.offsetWidth
        x: element.offsetLeft,
        y: element.offsetTop,
      })
    } else {
      _fail(INPUT_TYPE, { value: inputEvent.target.value })
    }
  }
}

var trackClick = function (inputEvent) {
  const INPUT_TYPE = "Click"
  // there are like 10 different options on this inputEvent and not sure which i should use:
  // pageX,pageY, clientX, clientY, offsetX, offsetY, x, y, screenX, screenY
  const x = inputEvent.x
  const y = inputEvent.y

  if (typeof playwright === "undefined") {
    selectorVal = getSelector(inputEvent.target)
    pythonLocator = "playwrightUndefined"
  } else {
    selectorVal = playwright.selector(inputEvent.target)
    pythonLocator = playwright.generateLocator(inputEvent.target, "python")
  }

  const boundingBox = {
    ...inputEvent.target.getBoundingClientRect().toJSON(),
    scroll_x: window.scrollX,
    scroll_y: window.scrollY,
  }

  checkIfScrolled()
  _transmitData(INPUT_TYPE, {
    x: x,
    y: y,
    selector: selectorVal,
    python_locator: pythonLocator,
    bounding_box: boundingBox,
  })
}

var trackEnter = function (inputEvent) {
  const INPUT_TYPE = "Enter"
  if (inputEvent.code === "Enter") {
    _transmitData(INPUT_TYPE, { value: inputEvent.code })
  }
}

// this has so many x,y values, not sure which to use...
// probably deltaX and deltaY but maybe should use pageX, pageY
// dont use this, theres too many events it will probably cause issues for playwright
var trackWheelEventAll = function (inputEvent) {
  const INPUT_TYPE = "Wheel"
  _transmitData(INPUT_TYPE, {
    delta_x: inputEvent.deltaX,
    delta_y: inputEvent.deltaY,
  })
}

function trackWheel(data) {
  const INPUT_TYPE = "Wheel"
  _transmitData(INPUT_TYPE, {
    delta_x: trackInfo.wheel.deltaX,
    delta_y: trackInfo.wheel.deltaY,
  })
}

function debounceEvent(func, delay, trackKey, keys) {
  let timerId
  return function (event) {
    clearTimeout(timerId)
    keys.forEach((key) => (trackKey[key] += event[key]))
    timerId = setTimeout(() => {
      func(event)
      keys.forEach((key) => (trackKey[key] = 0))
    }, delay)
  }
}

// use change over input because connecting input together seems like it could be problematic
// document.addEventListener("change", makeTrackInput("Change"))
// need {useCapture: true} to capture events before they may impact page
window.addEventListener("input", makeTrackInput("Input"), true)
window.addEventListener("click", trackClick, true)
document.addEventListener("keydown", trackEnter, true) // do this on document not window

// need debounce for these events
// document.addEventListener(
//   "wheel",
//   debounceEvent(trackWheel, 500, trackInfo.wheel, ["deltaX", "deltaY"])
// )
