/// <reference types="vitest" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// `defineConfig` vem de `vitest/config`, não de `vite`: é a mesma configuração
// do Vite acrescida do bloco `test`, o que evita um segundo arquivo de config
// que poderia divergir do build real.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    // Cada arquivo restaura mocks e stubs de ambiente sozinho: um teste que
    // finge build de produção não pode vazar esse estado para o seguinte.
    restoreMocks: true,
    unstubEnvs: true,
    unstubGlobals: true,
  },
});
