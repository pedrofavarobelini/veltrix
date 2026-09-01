import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

const TITLE_ID = "settings-drawer-title";

type SettingsDrawerProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  /** Conteúdo injetado pelo pai — o drawer não conhece regra de domínio. */
  children: ReactNode;
};

/**
 * Casca acessível do painel lateral de configurações.
 *
 * É um componente de APRESENTAÇÃO: não sabe o que são providers, modelos ou
 * autorização. Cuida apenas de abrir, fechar, overlay, Escape e foco. Quem
 * conhece o domínio é o que vem em `children` (o ProviderSettingsPanel).
 */
export function SettingsDrawer({ open, title, onClose, children }: SettingsDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  // Escape fecha. O listener só existe enquanto o drawer está aberto, e a
  // função de retorno do efeito garante a remoção — sem listener órfão.
  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // Foco inicial previsível no botão fechar e devolução do foco a quem abriu.
  useEffect(() => {
    if (!open) {
      return;
    }

    const previouslyFocused = document.activeElement as HTMLElement | null;

    closeButtonRef.current?.focus();

    return () => previouslyFocused?.focus();
  }, [open]);

  // Renderização condicional: fechado não existe no DOM, então nada dentro dele
  // pode receber foco por Tab nem ser lido por leitor de tela.
  if (!open) {
    return null;
  }

  return (
    <div className="settings-layer">
      <div className="settings-overlay" onClick={onClose} aria-hidden="true" />

      <aside
        className="settings-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={TITLE_ID}
      >
        <header className="settings-drawer-header">
          <h2 id={TITLE_ID}>{title}</h2>
          <button
            ref={closeButtonRef}
            className="drawer-close"
            type="button"
            onClick={onClose}
            aria-label="Fechar configurações"
          >
            ✕
          </button>
        </header>

        <div className="settings-drawer-body">{children}</div>
      </aside>
    </div>
  );
}
