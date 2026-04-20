// ESLint v9 flat config.
// Feature-slice boundaries enforced via eslint-plugin-boundaries.
//
// Rules:
// - Each source file belongs to an "element" (core, feature, page, lib, ui, types, app).
// - Feature files can only import from their own feature, lib, ui, types, core.
// - No feature can reach into another feature's internals.

import js from "@eslint/js";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import boundaries from "eslint-plugin-boundaries";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";

export default [
  {
    ignores: ["dist/**", "node_modules/**", "src/types/api.d.ts"],
  },
  // Config files run in Node. Keep them on a looser ruleset.
  {
    files: ["*.config.{ts,js,mjs,cjs}", "vite.config.ts", "tailwind.config.ts"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
      },
      globals: {
        ...globals.node,
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      "no-undef": "off",
    },
  },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        ecmaFeatures: { jsx: true },
      },
      globals: {
        ...globals.browser,
        ...globals.es2022,
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      boundaries,
    },
    settings: {
      "boundaries/elements": [
        { type: "core", pattern: "src/core/*" },
        { type: "feature", pattern: "src/features/*", capture: ["feature"] },
        { type: "page", pattern: "src/pages/*" },
        { type: "lib", pattern: "src/lib/*" },
        { type: "ui", pattern: "src/components/ui/*" },
        { type: "types", pattern: "src/types/*" },
        { type: "app", pattern: "src/{App,main}.{ts,tsx}" },
      ],
    },
    rules: {
      ...js.configs.recommended.rules,
      ...tsPlugin.configs.recommended.rules,
      // TypeScript handles undefined-identifier detection. Leaving ESLint's
      // no-undef on produces false positives for DOM types (RequestInit,
      // HTMLElement, etc.) and the `React` namespace under `jsx: react-jsx`.
      "no-undef": "off",
      // Empty-extending interfaces for prop types are a common React pattern.
      "@typescript-eslint/no-empty-object-type": "off",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "boundaries/element-types": [
        "error",
        {
          default: "disallow",
          rules: [
            { from: ["app"], allow: ["core", "page", "ui", "lib", "feature"] },
            {
              from: ["feature"],
              allow: [["feature", { feature: "${from.feature}" }], "ui", "lib", "types", "core"],
            },
            { from: ["page"], allow: ["feature", "ui", "lib", "core", "types"] },
            { from: ["core"], allow: ["lib", "types"] },
            { from: ["lib"], allow: ["lib", "types"] },
            { from: ["ui"], allow: ["lib", "types"] },
          ],
        },
      ],
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["../../../*"],
              message:
                "Deep relative imports discourage the feature-slice boundary. Use the @/ alias.",
            },
          ],
        },
      ],
    },
  },
];
