import { defineConfig, globalIgnores } from "eslint/config";
import { nextIgnores } from "@rapid-template/config/eslint/ignores";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores(nextIgnores),
]);

export default eslintConfig;
