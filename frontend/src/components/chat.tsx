"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { streamChat, type ChatMessage } from "@/lib/api";
import { Markdown } from "@/components/markdown";

const SUGGESTIONS = [
  "이 웹앱의 구조를 요약해줘",
  "FastAPI에 새 엔드포인트를 추가하려면?",
  "SSE 스트리밍은 어떻게 동작해?",
];

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
  }, []);

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content || busy) return;

      const history: ChatMessage[] = [...messages, { role: "user", content }];
      setMessages([...history, { role: "assistant", content: "" }]);
      setInput("");
      setError(null);
      setBusy(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat(history, {
          signal: controller.signal,
          onDelta: (delta) =>
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = { ...last, content: last.content + delta };
              return next;
            }),
        });
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "알 수 없는 오류가 발생했습니다.");
        }
      } finally {
        // Drop an empty assistant placeholder so the transcript stays honest.
        setMessages((prev) =>
          prev.length > 0 && prev[prev.length - 1].content === "" ? prev.slice(0, -1) : prev,
        );
        if (abortRef.current === controller) {
          abortRef.current = null;
          setBusy(false);
        }
        inputRef.current?.focus();
      }
    },
    [busy, messages],
  );

  const empty = messages.length === 0;

  return (
    <div className="mx-auto flex h-dvh w-full max-w-3xl flex-col px-4">
      <header className="flex items-center justify-between gap-4 py-5">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Assistant</h1>
          <p className="text-sm text-[var(--muted)]">
            Next.js + FastAPI · 스트리밍 응답
          </p>
        </div>
        <button
          type="button"
          onClick={() => setMessages([])}
          disabled={empty || busy}
          className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--muted)] transition hover:text-[var(--fg)] disabled:opacity-40"
        >
          새 대화
        </button>
      </header>

      <div ref={listRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto pb-6">
        {empty ? (
          <div className="flex h-full flex-col items-center justify-center gap-6 py-16 text-center">
            <p className="text-2xl font-semibold tracking-tight">무엇을 도와드릴까요?</p>
            <div className="flex w-full flex-col gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void send(s)}
                  className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-left text-sm transition hover:border-[var(--accent)]"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div
              key={i}
              className={m.role === "user" ? "flex justify-end" : "flex justify-start"}
            >
              <div
                className={
                  m.role === "user"
                    ? "max-w-[85%] rounded-2xl rounded-br-md bg-[var(--accent)] px-4 py-2.5 text-sm whitespace-pre-wrap text-white"
                    : "max-w-[85%] min-w-0 rounded-2xl rounded-bl-md bg-[var(--surface)] px-4 py-3"
                }
              >
                {m.role === "user" ? m.content : <Markdown>{m.content}</Markdown>}
                {busy && i === messages.length - 1 && m.role === "assistant" && (
                  <span className="ml-0.5 inline-block h-4 w-2 animate-pulse bg-current align-middle" />
                )}
              </div>
            </div>
          ))
        )}

        {error && (
          <div
            role="alert"
            className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-400"
          >
            {error}
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send(input);
        }}
        className="bg-[var(--bg)] pb-5 pt-2"
      >
        <div className="flex items-end gap-2 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-2 focus-within:border-[var(--accent)]">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                void send(input);
              }
            }}
            rows={1}
            placeholder="메시지를 입력하세요 (Shift+Enter로 줄바꿈)"
            className="max-h-48 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-[var(--muted)]"
          />
          {busy ? (
            <button
              type="button"
              onClick={stop}
              className="rounded-xl border border-[var(--border)] px-3 py-2 text-sm"
            >
              중지
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              className="rounded-xl bg-[var(--accent)] px-3 py-2 text-sm font-medium text-white disabled:opacity-40"
            >
              전송
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
