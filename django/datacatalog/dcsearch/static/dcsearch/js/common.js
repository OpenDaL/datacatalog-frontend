// Open/close hamburger menu
const menu = document.querySelector('nav');
const header = document.querySelector('header');
const hmbrgr = document.querySelector('#hamburger');
const headerElement = document.querySelector('#onboarding, #page-header');

// Set an in memory image to track if webp image can be loaded
const memImg = document.createElement('img');

window.onload = (event) => {
  const headerStyle = window.getComputedStyle(headerElement, false);
  var curImageUrl = headerStyle.backgroundImage.slice(5,-2);
  memImg.src = curImageUrl;
}

memImg.addEventListener('error', (ev) => {
    // curImageUrl can be used, since error can only occur after 'onload' event
    fallBackImage = curImageUrl.replace('.webp', '.jpg');
    headerElement.style.backgroundImage = `url("${fallBackImage}")`;
})

// Open hamburger menu on click
hmbrgr.addEventListener('click', function(e) {
    menu.classList.toggle('open-menu');
    header.classList.toggle('open-menu');
    hmbrgr.classList.toggle('open-menu');
    e.stopPropagation();
})

// Discontinuation Notice
var infoButton = document.querySelector('#discontinuation-info-link');
var discPopup = document.querySelector('#discontinuation-overlay');
var closeButton = document.querySelector('#discontinuation-overlay .popup .close');

const shouldHideMessage = document.cookie.includes('hideDiscontinuationMessage');
if (!shouldHideMessage) {
  // Show the popup
  discPopup.classList.toggle('visible');
}

function hideDiscontinuationMessage(e) {
  const tgt = e.target;
  if (tgt != infoButton && tgt != discPopup && tgt != closeButton) {
    return;
  }
  document.cookie = `hideDiscontinuationMessage=true; SameSite=Strict; path=/`;
  discPopup.classList.toggle('visible');
  e.stopPropagation();
}


infoButton.addEventListener('click', hideDiscontinuationMessage);
closeButton.addEventListener('click', hideDiscontinuationMessage);
discPopup.addEventListener('click', hideDiscontinuationMessage);
