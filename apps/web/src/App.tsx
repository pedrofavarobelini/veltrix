import { useEffect, useState } from "react";
import { ChatPage } from "./pages/ChatPage";
import { ObservabilityPage } from "./pages/ObservabilityPage";

export default function App() {
  const [route, setRoute] = useState(() => window.location.hash);

  useEffect(() => {
    const updateRoute = () => setRoute(window.location.hash);
    window.addEventListener("hashchange", updateRoute);
    return () => window.removeEventListener("hashchange", updateRoute);
  }, []);

  return route.startsWith("#/observability") ? <ObservabilityPage /> : <ChatPage />;
}
