/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        pitch: {
          DEFAULT: "#0d3820",
          dark: "#092614",
          light: "#14532d",
        },
        navy: {
          DEFAULT: "#0b1220",
          panel: "#101c33",
          card: "#0f172a",
        },
        gold: {
          DEFAULT: "#ffd23f",
          dim: "#ba9a2e",
        },
        ink: {
          primary: "#f5f7fa",
          secondary: "#9fb0c9",
          muted: "#6b7f9c",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        body: ["var(--font-body)", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      backgroundImage: {
        "stadium-gradient":
          "linear-gradient(160deg, #0b1220 0%, #101c33 55%, #0b1220 100%)",
        "pitch-gradient":
          "radial-gradient(ellipse at center, #14532d 0%, #0d3820 100%)",
      },
    },
  },
  plugins: [],
};
