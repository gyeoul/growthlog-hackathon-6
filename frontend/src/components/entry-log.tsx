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
      <form onSubmit={submit} className="card-muted flex flex-col gap-3">
        <h3 className="card-title">{editingId === null ? "새 기록" : "기록 수정"}</h3>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
          placeholder="제목"
          className="input"
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          maxLength={20000}
          rows={4}
          placeholder="오늘의 성장 기록"
          className="input resize-y"
        />
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="submit"
            disabled={!title.trim() || saving}
            className="btn btn-primary"
          >
            {saving ? "저장 중…" : editingId === null ? "저장" : "변경 저장"}
          </button>
          {editingId !== null && (
            <button type="button" onClick={reset} className="btn">
              취소
            </button>
          )}
          <span className="ml-auto text-xs text-muted">{entries.length}개 저장됨</span>
        </div>
      </form>

      {error && (
        <p role="alert" className="alert-error">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-muted">불러오는 중…</p>
      ) : entries.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line-strong px-4 py-10 text-center text-sm text-muted">
          아직 저장된 기록이 없습니다. 첫 기록을 남겨 보세요.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="rounded-xl border border-line bg-surface p-4 transition-colors hover:border-line-strong"
            >
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-sm font-semibold">{entry.title}</h3>
                  <p className="mt-0.5 text-xs text-muted">
                    {formatDate(entry.created_at)}
                    {entry.updated_at !== entry.created_at && " · 수정됨"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => startEdit(entry)}
                  className="btn btn-sm btn-ghost border-line text-ink-soft"
                >
                  수정
                </button>
                <button
                  type="button"
                  onClick={() => void remove(entry)}
                  className="btn btn-sm btn-ghost btn-danger border-line"
                >
                  삭제
                </button>
              </div>
              {entry.content && (
                <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-ink-soft">
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
