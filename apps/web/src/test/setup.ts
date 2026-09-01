/**
 * Setup compartilhado da suíte frontend.
 *
 * Registra os matchers de DOM do jest-dom no `expect` do Vitest e limpa a
 * árvore renderizada entre testes, para que um componente montado em um teste
 * não seja encontrado por consulta do teste seguinte.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// O jsdom não implementa rolagem: `scrollIntoView` simplesmente não existe no
// protótipo do Element. É lacuna do AMBIENTE de teste, não do produto — o
// autoscroll do chat funciona no navegador — então basta um no-op para que o
// efeito não derrube a montagem do componente.
if (typeof Element !== "undefined" && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});
