/** @type {import('tailwindcss').Config} */
module.exports = {
  // Aquí se listan las rutas de todos los archivos que usan clases de Tailwind
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./*.{js,ts,jsx,tsx}", // Incluye archivos en la raíz como RAGFlashcardApp.jsx y main.jsx
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}