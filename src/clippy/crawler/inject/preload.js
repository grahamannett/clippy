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

function _transmitData(flag, ...args) {
  console.log(CATCH_FLAG, flag, ...args)
}

function _fail(...args) {
  const FLAG = "FAIL"
  _transmitData(FLAT, ...args)
}

function _debug(...args) {
  const FLAG = "DEBUG"
  _transmitData(FLAG, ...args)
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
    _transmitData(INPUT_TYPE, window.scrollX, window.scrollY)
  }
}

var makeTrackInput = function (INPUT_TYPE) {
  return function (inputEvent) {
    // for tracking, trying to decide how to get text event and associated element
    var elementId = inputEvent.target.id
    var element = document.getElementById(elementId)
    if (element != null) {
      checkIfScrolled()
      _transmitData(
        INPUT_TYPE,
        inputEvent.target.value,
        // there is also element.offsetHeight, element.offsetWidth
        element.offsetLeft,
        element.offsetTop
      )
    } else {
      // console.log(CATCH_FLAG, FAIL_FLAG, INPUT_TYPE, inputEvent.target.value)
      _fail(INPUT_TYPE, inputEvent.target.value)
    }
  }
}

var trackClick = function (inputEvent) {
  const INPUT_TYPE = "Click"
  // there are like 10 different options on this inputEvent and not sure which i should use:
  // pageX,pageY, clientX, clientY, offsetX, offsetY, x, y, screenX, screenY
  const clickX = inputEvent.x
  const clickY = inputEvent.y

  const selectorVal = playwright.selector(inputEvent.target)
  const pythonLocator = playwright.generateLocator(inputEvent.target, "python")

  const boundingBox = {
    ...inputEvent.target.getBoundingClientRect().toJSON(),
    scrollX: window.scrollX,
    scrollY: window.scrollY,
  }

  checkIfScrolled()
  _transmitData(
    INPUT_TYPE,
    clickX,
    clickY,
    selectorVal,
    pythonLocator,
    JSON.stringify(boundingBox)
  )
}

var trackEnter = function (inputEvent) {
  const INPUT_TYPE = "Enter"
  if (inputEvent.code === "Enter") {
    _transmitData(INPUT_TYPE, inputEvent.code)
  }
}

// this has so many x,y values, not sure which to use...
// probably deltaX and deltaY but maybe should use pageX, pageY
// dont use this, theres too many events it will probably cause issues for playwright
var trackWheelEventAll = function (inputEvent) {
  const INPUT_TYPE = "Wheel"
  _transmitData(INPUT_TYPE, inputEvent.deltaX, inputEvent.deltaY)
}

function trackWheel(data) {
  const INPUT_TYPE = "Wheel"
  _transmitData(INPUT_TYPE, trackInfo.wheel.deltaX, trackInfo.wheel.deltaY)
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
window.addEventListener("input", makeTrackInput("Input"))
window.addEventListener("click", trackClick)
// window.addEventListener("keydown", trackEnter)
document.addEventListener("keydown", trackEnter)

// need debounce for these events
// document.addEventListener(
//   "wheel",
//   debounceEvent(trackWheel, 500, trackInfo.wheel, ["deltaX", "deltaY"])
// )
