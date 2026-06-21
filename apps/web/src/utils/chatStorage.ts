import type { ChatMessage, FeedbackType } from "../types/chat";

export const CHAT_HISTORY_STORAGE_KEY = "pedrocore:v3:chat-history";
export const CHAT_HISTORY_LIMIT = 100;

function canUseLocalStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

export function createChatMessageId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function isValidMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== "object") {
    return false;
  }

  const item = value as Partial<ChatMessage>;

  return (
    typeof item.id === "string" &&
    (item.role === "user" || item.role === "assistant") &&
    typeof item.content === "string" &&
    typeof item.createdAt === "string"
  );
}

export function limitChatHistory(messages: ChatMessage[]) {
  if (messages.length <= CHAT_HISTORY_LIMIT) {
    return messages;
  }

  const systemMessages = messages.filter((item) => item.isSystem);
  const chatMessages = messages.filter((item) => !item.isSystem);
  const limitedChatMessages = chatMessages.slice(-CHAT_HISTORY_LIMIT);

  return [...systemMessages, ...limitedChatMessages];
}

export function loadChatHistory(defaultMessages: ChatMessage[]) {
  if (!canUseLocalStorage()) {
    return defaultMessages;
  }

  try {
    const rawHistory = window.localStorage.getItem(CHAT_HISTORY_STORAGE_KEY);

    if (!rawHistory) {
      return defaultMessages;
    }

    const parsedHistory = JSON.parse(rawHistory);

    if (!Array.isArray(parsedHistory)) {
      return defaultMessages;
    }

    const validMessages = parsedHistory.filter(isValidMessage);

    if (validMessages.length === 0) {
      return defaultMessages;
    }

    return limitChatHistory(validMessages);
  } catch {
    return defaultMessages;
  }
}

export function saveChatHistory(messages: ChatMessage[]) {
  if (!canUseLocalStorage()) {
    return;
  }

  try {
    window.localStorage.setItem(
      CHAT_HISTORY_STORAGE_KEY,
      JSON.stringify(limitChatHistory(messages)),
    );
  } catch {
    // localStorage pode falhar por quota, modo privado ou bloqueio do navegador.
  }
}

export function updateMessageFeedback(
  messages: ChatMessage[],
  messageId: string,
  feedback: FeedbackType,
) {
  return messages.map((item) => {
    if (item.id !== messageId || item.role !== "assistant" || item.isSystem) {
      return item;
    }

    return {
      ...item,
      feedback,
    };
  });
}
