type ErrorBannerProps = {
  message: string;
  retryDisabled: boolean;
  onRetry: () => void;
  onDismiss: () => void;
};

export function ErrorBanner({ message, retryDisabled, onRetry, onDismiss }: ErrorBannerProps) {
  return (
    <div className="error-banner" role="alert">
      <div>
        <strong>Não foi possível obter resposta agora.</strong>
        <p>{message}</p>
      </div>
      <div className="error-actions">
        <button type="button" onClick={onRetry} disabled={retryDisabled}>
          Tentar novamente
        </button>
        <button type="button" className="ghost-button" onClick={onDismiss}>
          Fechar
        </button>
      </div>
    </div>
  );
}
