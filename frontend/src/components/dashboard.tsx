"use client";

import { useEffect, useState } from "react";
import { AuthBar } from "@/components/auth-bar";
import { EntryLog } from "@/components/entry-log";
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
    return <div className="h-10" aria-hidden />;
  }

  return (
    <div className="flex flex-col gap-8">
      <AuthBar user={user} />
      {user && <EntryLog />}
    </div>
  );
}
