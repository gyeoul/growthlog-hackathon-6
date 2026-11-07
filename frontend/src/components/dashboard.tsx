"use client";

import { useEffect, useState } from "react";
import { AuthBar } from "@/components/auth-bar";
import { EntryLog } from "@/components/entry-log";
import { Planner } from "@/components/planner";
import { StudyBoard } from "@/components/study-board";
import { getSession, type User } from "@/lib/api";

type Tab = "planner" | "studies";

const TABS: { id: Tab; label: string; blurb: string }[] = [
  {
    id: "planner",
    label: "학기 플래너",
    blurb: "수강 강의와 마감 일정으로 시간표를 짭니다",
  },
  {
    id: "studies",
    label: "스터디",
    blurb: "관심사를 함께 파는 사람들을 모읍니다",
  },
];

/** Owns the session and the top-level tabs so every panel agrees on who is logged in. */
export function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [tab, setTab] = useState<Tab>("planner");

  useEffect(() => {
    getSession()
      .then(setUser)
      .finally(() => setLoaded(true));
  }, []);

  if (!loaded) {
    return <div className="card-muted h-24 animate-pulse" aria-hidden />;
  }

  return (
    <div className="flex flex-col gap-6">
      <AuthBar user={user} />

      <div
        role="tablist"
        aria-label="주요 기능"
        className="grid grid-cols-2 gap-1 rounded-xl border border-line bg-surface-muted p-1"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            id={`tab-${t.id}`}
            onClick={() => setTab(t.id)}
            className={`flex cursor-pointer flex-col items-start gap-0.5 rounded-lg px-4 py-3 text-left transition-colors ${
              tab === t.id
                ? "bg-surface text-ink shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
                : "text-muted hover:bg-surface/60 hover:text-ink"
            }`}
          >
            <span className="text-sm font-semibold tracking-tight">{t.label}</span>
            <span className="text-[11px] leading-snug text-muted">{t.blurb}</span>
          </button>
        ))}
      </div>

      <section
        role="tabpanel"
        id={`panel-${tab}`}
        aria-labelledby={`tab-${tab}`}
        className="flex flex-col gap-6"
      >
        {tab === "planner" &&
          (user ? (
            <Planner />
          ) : (
            <p className="card text-sm text-muted">
              시간표를 만들려면 로그인하세요. 스터디 목록은 로그인 없이도 볼 수 있습니다.
            </p>
          ))}

        {tab === "studies" && <StudyBoard user={user} />}
      </section>

      {user && (
        <details className="group card p-0">
          <summary className="flex cursor-pointer list-none items-center gap-2 px-5 py-4 [&::-webkit-details-marker]:hidden">
            <span className="card-title">성장 기록</span>
            <span className="text-xs text-muted">배운 것을 남겨 두는 곳</span>
            <span className="ml-auto text-muted transition-transform group-open:rotate-180">
              ⌄
            </span>
          </summary>
          <div className="border-t border-line p-5">
            <EntryLog />
          </div>
        </details>
      )}
    </div>
  );
}
