"use client";

import { useEffect, useState } from "react";
import {
  createEntry,
  deleteEntry,
  listEntries,
  updateEntry,
  type Entry,
} from "@/lib/api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function EntryLog() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let cancelled = false;
    listEntries()
      .then((data) => {
        if (cancelled) return;
        setEntries(data.entries);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "기록을 불러오지 못했습니다.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const reset = () => {
    setTitle("");
    setContent("");
    setEditingId(null);
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || saving) return;
    setSaving(true);
    try {
      if (editingId === null) {
        await createEntry({ title: title.trim(), content });
      } else {
        await updateEntry(editingId, { title: title.trim(), content });
      }
      reset();
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장하지 못했습니다.");
    } finally {
      setSaving(false);
    }
  }

  function startEdit(entry: Entry) {
    setEditingId(entry.id);
    setTitle(entry.title);
    setContent(entry.content);
  }

  async function remove(entry: Entry) {
    if (!window.confirm(`"${entry.title}" 기록을 삭제할까요?`)) return;
    try {
      await deleteEntry(entry.id);
      if (editingId === entry.id) reset();
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "삭제하지 못했습니다.");
    }
  }

  return (
    <section className="flex w-full flex-col gap-5">
      <form
        onSubmit={submit}
        className="flex flex-col gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"
      >
        <h2 className="text-sm font-semibold">
          {editingId === null ? "새 기록" : "기록 수정"}
        </h2>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
          placeholder="제목"
          className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          maxLength={20000}
          rows={4}
          placeholder="오늘의 성장 기록"
          className="resize-y rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm outline-none focus:border-[var(--accent)]"
        />
        <div className="flex items-center gap-2">
          <button
            type="submit"
            disabled={!title.trim() || saving}
            className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            {saving ? "저장 중…" : editingId === null ? "저장" : "변경 저장"}
          </button>
          {editingId !== null && (
            <button
              type="button"
              onClick={reset}
              className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm"
            >
              취소
            </button>
          )}
          <span className="ml-auto text-xs text-[var(--muted)]">
            {entries.length}개 저장됨
          </span>
        </div>
      </form>

      {error && (
        <p
          role="alert"
          className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-400"
        >
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-[var(--muted)]">불러오는 중…</p>
      ) : entries.length === 0 ? (
        <p className="rounded-xl border border-dashed border-[var(--border)] px-4 py-8 text-center text-sm text-[var(--muted)]">
          아직 저장된 기록이 없습니다. 첫 기록을 남겨 보세요.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"
            >
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-sm font-semibold">{entry.title}</h3>
                  <p className="mt-0.5 text-xs text-[var(--muted)]">
                    {formatDate(entry.created_at)}
                    {entry.updated_at !== entry.created_at && " · 수정됨"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => startEdit(entry)}
                  className="rounded-lg border border-[var(--border)] px-2.5 py-1 text-xs"
                >
                  수정
                </button>
                <button
                  type="button"
                  onClick={() => void remove(entry)}
                  className="rounded-lg border border-[var(--border)] px-2.5 py-1 text-xs text-red-600 hover:border-red-500/60 dark:text-red-400"
                >
                  삭제
                </button>
              </div>
              {entry.content && (
                <p className="mt-2 whitespace-pre-wrap break-words text-sm">
                  {entry.content}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
