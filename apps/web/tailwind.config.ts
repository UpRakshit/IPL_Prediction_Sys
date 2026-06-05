import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#15201d",
        muted: "#60706a",
        line: "#dce4df",
        pitch: "#eef5f0",
        brand: {
          50: "#eaf8f0",
          100: "#d5f0e0",
          500: "#159566",
          700: "#0a6845",
          900: "#10392f",
        },
      },
      boxShadow: {
        panel: "0 12px 28px rgba(21, 32, 29, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
