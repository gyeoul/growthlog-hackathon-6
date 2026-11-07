export type User = {
  id: number;
  email: string;
  name: string | null;
  picture: string | null;
  created_at: string;
  last_login_at: string;
};

type SessionState = { user: User | null };

/** Asks the backend who is logged in. Never throws: anonymous is a normal state. */
export async function getSession(): Promise<User | null> {
  const res = await fetch("/api/auth/session", { cache: "no-store" });
  if (!res.ok) return null;
  const data = (await res.json()) as SessionState;
  return data.user;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
}
