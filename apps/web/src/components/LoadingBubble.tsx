export function LoadingBubble() {
  return (
    <article className="message-row from-assistant loading-row">
      <div className="message-avatar">P</div>
      <div className="message-bubble loading-bubble">
        <div className="message-heading">
          <strong>PedroCore IA</strong>
          <span>agora</span>
        </div>
        <p>PedroCore está pensando...</p>
        <div className="typing-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </article>
  );
}
