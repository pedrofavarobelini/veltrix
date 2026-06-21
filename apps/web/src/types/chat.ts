export type ChatRole = "user" | "assistant";

export type FeedbackType = "like" | "dislike";

export type ChatMessageMeta = {
  provider: string;
  model: string;
  fallbackUsed: boolean;
  error?: string | null;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  meta?: ChatMessageMeta;
  feedback?: FeedbackType | null;
  isSystem?: boolean;
};
