import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import jsxA11y from "eslint-plugin-jsx-a11y";

export default defineConfig([
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "coverage/**",
    "next-env.d.ts",
  ]),
  ...nextVitals,
  ...nextTs,
  {
    // eslint-config-next allaqachon jsx-a11y pluginini ro'yxatga oladi (subset qoidalar bilan);
    // bu blok to'liq recommended to'plamini yoqadi.
    files: ["**/*.{js,jsx,ts,tsx}"],
    rules: {
      ...jsxA11y.flatConfigs.recommended.rules,
    },
  },
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    rules: {
      // UI matnlari o'zbekcha apostrof bilan yoziladi ("bo'ladi") — qoida shovqinli, warn yetarli.
      "react/no-unescaped-entities": "warn",
      // React Compiler migratsiya lint'i: mavjud storage-sync patternlarni restrukturasiz tuzatib bo'lmaydi.
      "react-hooks/set-state-in-effect": "warn",
      // Run formalarida birlamchi inputga autofocus ataylab qo'yilgan.
      "jsx-a11y/no-autofocus": "warn",
    },
  },
]);
