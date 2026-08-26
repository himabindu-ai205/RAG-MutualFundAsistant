export type ChatResponse = {
  intent: string;
  answer: string;
  source: string;
  last_updated_from_sources: string;
  disclaimer: string;
  request_id?: string;
};

export class ChatRequestError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "ChatRequestError";
    this.code = code;
  }
}

/** API origin without trailing slash. Empty → relative `/chat` (local Vite proxy or FastAPI static). */
export function apiBaseUrl(): string {
  let raw = (import.meta.env.VITE_API_BASE_URL || "").trim();
  if (!raw) {
    return "";
  }
  // Vercel env mistakes: host without scheme becomes a relative path and breaks fetch.
  if (!/^https?:\/\//i.test(raw)) {
    raw = `https://${raw}`;
  }
  return raw.replace(/\/+$/, "");
}

export function chatEndpoint(): string {
  const base = apiBaseUrl();
  return base ? `${base}/chat` : "/chat";
}

export function isPublicHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return false;
    }
    const host = parsed.hostname.toLowerCase();
    if (host === "localhost" || host.endsWith(".local")) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

export async function askQuestion(question: string): Promise<ChatResponse> {
  const response = await fetch(chatEndpoint(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    throw new ChatRequestError("chat_failed", "The assistant could not be reached.");
  }

  if (!response.ok) {
    const errorCode =
      data &&
      typeof data === "object" &&
      "error" in data &&
      typeof data.error === "string"
        ? data.error
        : "chat_failed";
    if (errorCode === "question_required") {
      throw new ChatRequestError("question_required", "Please type a factual question.");
    }
    throw new ChatRequestError("chat_failed", "The assistant could not answer right now.");
  }

  const payload = data as ChatResponse;
  if (
    typeof payload.answer !== "string" ||
    typeof payload.source !== "string" ||
    typeof payload.last_updated_from_sources !== "string"
  ) {
    throw new ChatRequestError("chat_failed", "The assistant returned an unexpected response.");
  }
  return payload;
}
