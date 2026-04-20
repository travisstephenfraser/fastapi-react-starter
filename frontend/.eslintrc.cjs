/**
 * ESLint — feature-slice boundaries enforced via eslint-plugin-boundaries.
 *
 * Rules:
 * - Each file belongs to an "element" (core, feature, page, lib, ui, types).
 * - `feature` files can only import from their own feature, lib, ui, types, core.
 * - No feature can reach into another feature's internals.
 */
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
  ],
  ignorePatterns: ["dist", ".eslintrc.cjs", "src/types/api.d.ts"],
  parser: "@typescript-eslint/parser",
  plugins: ["@typescript-eslint", "react-hooks", "react-refresh", "boundaries"],
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
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn",
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "boundaries/element-types": [
      "error",
      {
        default: "disallow",
        rules: [
          { from: "app", allow: ["core", "page", "ui", "lib", "feature"] },
          {
            from: "feature",
            allow: [
              ["feature", { feature: "${from.feature}" }], // same feature only
              "ui",
              "lib",
              "types",
              "core",
            ],
          },
          { from: "page", allow: ["feature", "ui", "lib", "core", "types"] },
          { from: "core", allow: ["lib", "types"] },
          { from: "lib", allow: ["lib", "types"] },
          { from: "ui", allow: ["lib", "types"] },
        ],
      },
    ],
    "no-restricted-imports": [
      "error",
      {
        patterns: [
          {
            group: ["../../../*"],
            message: "Deep relative imports discourage the feature-slice boundary. Use the @/ alias.",
          },
        ],
      },
    ],
  },
};
