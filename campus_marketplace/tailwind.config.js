/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "shop/templates/**/*.html",
  ],
  safelist: [
    
  ],
 
  theme: {
    extend: {},
  },
  plugins: [
    require('@tailwindcss/line-clamp'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
  ],
}

