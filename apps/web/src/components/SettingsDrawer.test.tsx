import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SettingsDrawer } from "./SettingsDrawer";

describe("drawer de configurações", () => {
  it("fechado não existe no DOM, então nada dentro dele recebe foco", () => {
    render(
      <SettingsDrawer open={false} title="Configurações" onClose={vi.fn()}>
        <button type="button">Interno</button>
      </SettingsDrawer>,
    );

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByRole("button", { name: "Interno" })).toBeNull();
  });

  it("aberto é um diálogo modal rotulado pelo título", () => {
    render(
      <SettingsDrawer open title="Configurações" onClose={vi.fn()}>
        <p>conteúdo</p>
      </SettingsDrawer>,
    );

    const dialog = screen.getByRole("dialog");

    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName("Configurações");
  });

  it("Escape fecha", () => {
    const onClose = vi.fn();

    render(
      <SettingsDrawer open title="Configurações" onClose={onClose}>
        <p>conteúdo</p>
      </SettingsDrawer>,
    );

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("clicar no overlay fecha", () => {
    const onClose = vi.fn();

    const { container } = render(
      <SettingsDrawer open title="Configurações" onClose={onClose}>
        <p>conteúdo</p>
      </SettingsDrawer>,
    );

    fireEvent.click(container.querySelector(".settings-overlay") as HTMLElement);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("o botão fechar aciona o fechamento", () => {
    const onClose = vi.fn();

    render(
      <SettingsDrawer open title="Configurações" onClose={onClose}>
        <p>conteúdo</p>
      </SettingsDrawer>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Fechar configurações" }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("move o foco para o botão fechar ao abrir", () => {
    render(
      <SettingsDrawer open title="Configurações" onClose={vi.fn()}>
        <p>conteúdo</p>
      </SettingsDrawer>,
    );

    expect(screen.getByRole("button", { name: "Fechar configurações" })).toHaveFocus();
  });

  it("devolve o foco a quem abriu, ao fechar", () => {
    const trigger = document.createElement("button");
    document.body.appendChild(trigger);
    trigger.focus();

    const { rerender } = render(
      <SettingsDrawer open title="Configurações" onClose={vi.fn()}>
        <p>conteúdo</p>
      </SettingsDrawer>,
    );

    rerender(
      <SettingsDrawer open={false} title="Configurações" onClose={vi.fn()}>
        <p>conteúdo</p>
      </SettingsDrawer>,
    );

    expect(trigger).toHaveFocus();

    trigger.remove();
  });

  it("não reage a Escape quando está fechado", () => {
    const onClose = vi.fn();

    render(
      <SettingsDrawer open={false} title="Configurações" onClose={onClose}>
        <p>conteúdo</p>
      </SettingsDrawer>,
    );

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).not.toHaveBeenCalled();
  });
});
