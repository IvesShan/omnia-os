/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'deep-black': '#050505',
        'brand-orange': '#ff8a00',
        'void-teal': '#00151a',
        'neon-cyan': '#00ffff',
      },
      fontFamily: {
        'rajdhani': ['Rajdhani', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
