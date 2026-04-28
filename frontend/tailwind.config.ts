import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17211f",
        mist: "#eef3f1",
        spruce: "#1f5d50",
        copper: "#b5673f",
        citrine: "#d7a928",
        skyglass: "#dcebf2",
      },
      boxShadow: {
        soft: "0 12px 36px rgba(23, 33, 31, 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;
