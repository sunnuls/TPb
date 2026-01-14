/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        poker: {
          green: '#0E5233',
          felt: '#146B3A',
          gold: '#FFD700',
          chip: {
            red: '#DC143C',
            blue: '#1E90FF',
            green: '#32CD32',
            black: '#1a1a1a',
            white: '#F5F5F5',
          },
        },
      },
    },
  },
  plugins: [],
}

