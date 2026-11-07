export type User = {
  id: number;
  email: string;
  name: string | null;
  picture: string | null;
  created_at: string;
  last_login_at: string;
};

export type Entry = {
  id: number;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
};

export type EntryInput = { title: string; content: string };

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

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = `요청 실패 (HTTP ${res.status})`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON (proxy) error: keep the status line.
    }
    throw new Error(detail);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export function listEntries(): Promise<{ entries: Entry[] }> {
  return request<{ entries: Entry[] }>("/api/entries");
}

export function createEntry(input: EntryInput): Promise<Entry> {
  return request<Entry>("/api/entries", { method: "POST", body: JSON.stringify(input) });
}

export function updateEntry(id: number, input: EntryInput): Promise<Entry> {
  return request<Entry>(`/api/entries/${id}`, {
    method: "PUT",
    body: JSON.stringify(input),
  });
}

export function deleteEntry(id: number): Promise<void> {
  return request<void>(`/api/entries/${id}`, { method: "DELETE" });
}
