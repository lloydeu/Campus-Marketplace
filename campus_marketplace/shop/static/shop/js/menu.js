
// Mobile menu toggle
const menuBtn = document.getElementById('menuBtn');
const mobileMenu = document.getElementById('mobileMenu');

menuBtn.addEventListener('click', () => {
mobileMenu.classList.toggle('hidden');
});

// Close menu when a link is clicked
const menuLinks = mobileMenu.querySelectorAll('a');
menuLinks.forEach(link => {
link.addEventListener('click', () => {
    mobileMenu.classList.add('hidden');
});
});
    