export type Role = "user" | "assistant";

export type ChatMessage = { role: Role; content: string };

type StreamHandlers = {
  onDelta: (delta: string) => void;
  signal?: AbortSignal;
};

type StreamEvent = { delta?: string; error?: string } | "[DONE]";

type ErrorBody = { detail?: string };

/**
 * Turns an error response into something a user can act on. FastAPI answers
 * with `{detail}`, but a dead backend surfaces as the proxy's HTML page.
 */
async function readError(res: Response): Promise<string> {
  const text = await res.text().catch(() => "");
  try {
    const detail = (JSON.parse(text) as ErrorBody).detail;
    if (detail) return detail;
  } catch {
    // Not JSON: the proxy answered, which means the backend is unreachable.
    if (res.headers.get("content-type")?.includes("text/html") || res.status >= 500) {
      return `백엔드에 연결할 수 없습니다 (HTTP ${res.status}). FastAPI가 :8000에서 실행 중인지 확인하세요.`;
    }
  }
  return `요청 실패 (HTTP ${res.status})`;
}

/** POSTs to the FastAPI SSE endpoint and forwards text deltas as they arrive. */
export async function streamChat(
  messages: ChatMessage[],
  { onDelta, signal }: StreamHandlers,
): Promise<void> {
  const res = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(await readError(res));
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line; keep the trailing partial frame.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const raw = line.slice(5).trim();
      if (!raw) continue;

      const event: StreamEvent = raw === "[DONE]" ? raw : JSON.parse(raw);
      if (event === "[DONE]") return;
      if (event.error) throw new Error(event.error);
      if (event.delta) onDelta(event.delta);
    }
  }
}
