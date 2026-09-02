import pedrocoreLogo from "../assets/pedrocore-logo-icon.png";

export function LoadingBubble() {
  return (
    <article className="message-row from-assistant loading-row">
      <img className="message-avatar brand-logo-image" src={pedrocoreLogo} alt="Veltrix" />
      <div className="message-bubble loading-bubble">
        <div className="message-heading">
          <strong>Veltrix</strong>
          <span>agora</span>
        </div>
        <p>Veltrix está pensando...</p>
        <div className="typing-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
    </article>
  );
}
