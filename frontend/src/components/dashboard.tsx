"use client";

import { useEffect, useState } from "react";
import { AuthBar } from "@/components/auth-bar";
import { EntryLog } from "@/components/entry-log";
import { Planner } from "@/components/planner";
import { getSession, type User } from "@/lib/api";

/** Owns the session so the login screen and the log never disagree. */
export function Dashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getSession()
      .then(setUser)
      .finally(() => setLoaded(true));
  }, []);

  if (!loaded) {
    return <div className="card-muted h-24 animate-pulse" aria-hidden />;
  }

  return (
    <div className="flex flex-col gap-8">
      <AuthBar user={user} />
      {user && <Planner />}
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
