"use client";

import { useEffect, useState } from "react";
import {
  createStudy,
  getStudy,
  joinStudy,
  leaveStudy,
  listStudies,
  type Study,
  type StudyDetail,
  type User,
} from "@/lib/api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ko-KR", { month: "long", day: "numeric" });
}

/** Study list, creation form and detail panel. Reads are public; writes need a session. */
export function StudyBoard({ user }: { user: User | null }) {
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [openId, setOpenId] = useState<number | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let cancelled = false;
    listStudies()
      .then((next) => {
        if (cancelled) return;
        setStudies(next);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "불러오지 못했습니다.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  if (loading) {
    return <div className="card-muted h-40 animate-pulse" aria-hidden />;
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          {studies.length}개의 스터디 · 관심사를 함께 파는 사람들
        </p>
        {user && !creating && (
          <button type="button" onClick={() => setCreating(true)} className="btn btn-primary">
            + 스터디 열기
          </button>
        )}
      </div>

      {error && <p className="alert-error">{error}</p>}

      {creating && (
        <CreateStudyForm
          onCancel={() => setCreating(false)}
          onCreated={(study) => {
            setCreating(false);
            setOpenId(study.id);
            reload();
          }}
        />
      )}

      {!user && (
        <p className="alert-warn">
          둘러보기는 누구나 가능합니다. 스터디를 열거나 참여하려면 Google 계정으로 로그인하세요.
        </p>
      )}

      {studies.length === 0 ? (
        creating ? null : (
          <div className="card flex flex-col items-center gap-3 py-12 text-center">
            <p className="card-title">아직 열린 스터디가 없습니다</p>
            <p className="text-sm text-muted">
              {user
                ? "첫 스터디를 열어 함께 공부할 사람을 모아 보세요."
                : "로그인하면 첫 스터디를 열 수 있습니다."}
            </p>
          </div>
        )
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2">
          {studies.map((study) => (
            <li key={study.id}>
              <StudyCard
                study={study}
                open={openId === study.id}
                user={user}
                onToggle={() => setOpenId((id) => (id === study.id ? null : study.id))}
                onChanged={reload}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StudyCard({
  study,
  open,
  user,
  onToggle,
  onChanged,
}: {
  study: Study;
  open: boolean;
  user: User | null;
  onToggle: () => void;
  onChanged: () => void;
}) {
  const full = !study.is_open;

  return (
    <div className="card flex h-full flex-col gap-3">
      <div className="flex items-start gap-2">
        <h3 className="card-title flex-1">{study.title}</h3>
        <span className={`chip ${study.is_open ? "chip-brand" : ""}`}>
          {full ? "마감" : `${study.member_count}/${study.capacity}`}
        </span>
      </div>
      <p className="line-clamp-3 text-sm leading-relaxed text-ink-soft">{study.description}</p>
      <p className="text-xs text-muted">
        {study.owner.name} · {formatDate(study.created_at)} · {study.member_count}명 참여
      </p>
      <div className="mt-auto flex items-center gap-2">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          className="btn btn-sm flex-1 text-ink-soft"
        >
          {open ? "접기" : "참여자 보기"}
        </button>
        {user && <JoinButton study={study} user={user} onChanged={onChanged} />}
      </div>
      {open && <StudyDetailPanel id={study.id} onChanged={onChanged} />}
    </div>
  );
}

function JoinButton({
  study,
  user,
  onChanged,
}: {
  study: Study;
  user: User;
  onChanged: () => void;
}) {
  const [detail, setDetail] = useState<StudyDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Ownership is already in the list payload, so the button is correct before
  // the detail request resolves (and no request is wasted on your own study).
  const isOwner = study.owner.id === user.id;

  useEffect(() => {
    if (isOwner) return;
    let cancelled = false;
    getStudy(study.id)
      .then((next) => {
        if (!cancelled) setDetail(next);
      })
      .catch(() => {
        // Session expired: the neutral state below is still safe.
      });
    return () => {
      cancelled = true;
    };
  }, [study.id, isOwner]);

  async function act() {
    if (!detail) return;
    setBusy(true);
    setError(null);
    try {
      const next = detail.is_member
        ? await leaveStudy(study.id)
        : await joinStudy(study.id);
      setDetail(next);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "처리하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  if (isOwner) {
    return <span className="chip">내가 연 스터디</span>;
  }

  if (!detail) {
    return <span className="btn btn-sm btn-ghost" aria-hidden />;
  }

  if (!detail.is_member && !study.is_open) {
    return (
      <button type="button" disabled className="btn btn-sm">
        마감됨
      </button>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={act}
        disabled={busy}
        className={`btn btn-sm ${detail.is_member ? "btn-ghost" : "btn-primary"}`}
        title={error ?? undefined}
      >
        {busy ? "처리 중…" : detail.is_member ? "탈퇴" : "참여"}
      </button>
      {error && <span className="text-xs text-danger">{error}</span>}
    </>
  );
}

function StudyDetailPanel({ id, onChanged }: { id: number; onChanged: () => void }) {
  const [detail, setDetail] = useState<StudyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getStudy(id)
      .then((next) => {
        if (!cancelled) setDetail(next);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "불러오지 못했습니다.");
      });
    return () => {
      cancelled = true;
    };
  }, [id, onChanged]);

  if (error) return <p className="alert-error">{error}</p>;
  if (!detail) return <div className="divider pt-3 text-xs text-muted">불러오는 중…</div>;

  return (
    <div className="divider flex flex-col gap-2 pt-3">
      <p className="field-label">
        참여자 {detail.members.length}명 / 정원 {detail.capacity}명
      </p>
      <ul className="flex flex-wrap gap-1.5">
        {detail.members.map((m) => (
          <li key={m.user_id} className="chip">
            {m.name}
            {m.user_id === detail.owner.id && (
              <span className="font-medium text-brand-ink">· 방장</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CreateStudyForm({
  onCancel,
  onCreated,
}: {
  onCancel: () => void;
  onCreated: (study: StudyDetail) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [capacity, setCapacity] = useState(6);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      onCreated(await createStudy({ title, description, capacity }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "스터디를 열지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="card flex flex-col gap-3">
      <p className="card-title">새 스터디</p>
      <label className="flex flex-col gap-1">
        <span className="field-label">제목</span>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={100}
          required
          placeholder="예: 컴퓨터과학 개론 함께 듣기"
          className="input"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="field-label">소개</span>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={2000}
          required
          rows={4}
          placeholder="무엇을, 어떻게, 얼마나 자주 함께할지 적어 주세요."
          className="input resize-y"
        />
      </label>
      <label className="flex max-w-[12rem] flex-col gap-1">
        <span className="field-label">모집 인원 (2~100명)</span>
        <input
          type="number"
          min={2}
          max={100}
          value={capacity}
          onChange={(e) => setCapacity(Number(e.target.value))}
          className="input tabular-nums"
        />
      </label>
      {error && <p className="alert-error">{error}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={busy || !title.trim() || !description.trim()} className="btn btn-primary">
          {busy ? "여는 중…" : "스터디 열기"}
        </button>
        <button type="button" onClick={onCancel} className="btn btn-ghost">
          취소
        </button>
      </div>
    </form>
  );
}
