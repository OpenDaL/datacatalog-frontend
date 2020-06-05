// Open/close hamburger menu
const menu = document.querySelector('nav');
const header = document.querySelector('header');
const hmbrgr = document.querySelector('#hamburger');
const headerElement = document.querySelector('#onboarding, #page-header');

// Set an in memory image to track if webp image can be loaded
const memImg = document.createElement('img');
const headerStyle = window.getComputedStyle(headerElement, false);
const curImageUrl = headerStyle.backgroundImage.slice(5,-2);
memImg.src = curImageUrl;

memImg.addEventListener('error', (ev) => {
    fallBackImage = curImageUrl.replace('.webp', '.jpg');
    headerElement.style.backgroundImage = `url("${fallBackImage}")`;
})

// Open hanburger menu on click
hmbrgr.addEventListener('click', function(e) {
    menu.classList.toggle('open-menu');
    header.classList.toggle('open-menu');
    hmbrgr.classList.toggle('open-menu');
    e.stopPropagation();
})
