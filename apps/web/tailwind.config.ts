import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        tobacco: {
          50: "#fdf8f0",
          100: "#f9edda",
          200: "#f2d8ae",
          300: "#e8bd7a",
          400: "#dc9e44",
          500: "#c87e28",
          600: "#a8621e",
          700: "#86491a",
          800: "#6e3b1b",
          900: "#5c3219",
        },
      },
    },
  },
  plugins: [],
};

export default config;
