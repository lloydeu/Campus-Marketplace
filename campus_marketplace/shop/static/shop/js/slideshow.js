let currentSlide = 0;
const slides = document.querySelectorAll('.slide');
const slideBtns = document.querySelectorAll('.slide-btn');

function showSlide(n) {
  slides.forEach(slide => slide.classList.remove('opacity-100'));
  slides.forEach(slide => slide.classList.add('opacity-0'));
  slideBtns.forEach(btn => btn.classList.remove('opacity-100'));
  slideBtns.forEach(btn => btn.classList.add('opacity-50'));
  
  slides[n].classList.remove('opacity-0');
  slides[n].classList.add('opacity-100');
  slideBtns[n].classList.remove('opacity-50');
  slideBtns[n].classList.add('opacity-100');
}

function nextSlide() {
  currentSlide = (currentSlide + 1) % slides.length;
  showSlide(currentSlide);
}

function prevSlide() {
  currentSlide = (currentSlide - 1 + slides.length) % slides.length;
  showSlide(currentSlide);
}

slideBtns.forEach((btn, index) => {
  btn.addEventListener('click', () => {
    currentSlide = index;
    showSlide(currentSlide);
  });
});

document.getElementById('nextSlide').addEventListener('click', nextSlide);
document.getElementById('prevSlide').addEventListener('click', prevSlide);

setInterval(nextSlide, 5000);