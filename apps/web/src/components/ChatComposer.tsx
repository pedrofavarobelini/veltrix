type ChatComposerProps = {
  value: string;
  loading: boolean;
  placeholder: string;
  onChange: (value: string) => void;
  onSend: () => void;
};

export function ChatComposer({ value, loading, placeholder, onChange, onSend }: ChatComposerProps) {
  return (
    <footer className="chat-composer">
      <button className="composer-icon-button" type="button" aria-label="Anexar arquivo" disabled>
        +
      </button>

      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        disabled={loading}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onSend();
          }
        }}
      />

      <button className="send-button" type="button" onClick={onSend} disabled={loading}>
        {loading ? "..." : "➤"}
      </button>
    </footer>
  );
}
