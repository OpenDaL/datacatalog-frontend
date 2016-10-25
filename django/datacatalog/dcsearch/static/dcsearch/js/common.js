// Open/close hamburger menu
const menu = document.querySelector('nav');
const header = document.querySelector('header');
const hmbrgr = document.querySelector('#hamburger')

hmbrgr.addEventListener('click', function(e) {
    menu.classList.toggle('open-menu');
    header.classList.toggle('open-menu');
    hmbrgr.classList.toggle('open-menu');
    e.stopPropagation();
})
