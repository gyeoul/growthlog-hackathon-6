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

/**
 * The Next.js proxy answers with HTML when FastAPI is not running, so a 500 with
 * a non-JSON body means "backend down", not a bug in the request.
 */
function describeFailure(res: Response, body: unknown): string {
  // FastAPI error shape: {"detail": "..."}. Narrow instead of asserting a shape.
  if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
    return body.detail;
  }
  if (res.status >= 500 && !res.headers.get("content-type")?.includes("application/json")) {
    return `백엔드에 연결할 수 없습니다 (HTTP ${res.status}). FastAPI가 :8000에서 실행 중인지 확인하세요.`;
  }
  return `요청 실패 (HTTP ${res.status})`;
}

/** Asks the backend who is logged in. Never throws: anonymous is a normal state. */
export async function getSession(): Promise<User | null> {
  const res = await fetch("/api/auth/session", { cache: "no-store" });
  if (!res.ok) return null;
  const data = (await res.json().catch(() => null)) as SessionState | null;
  return data?.user ?? null;
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
}

/**
 * Navigates to the OAuth entry point only when the backend actually answers.
 * Without this the browser lands on the proxy's raw "Internal Server Error"
 * page whenever FastAPI is not running.
 *
 * Returns an error message instead of navigating on failure.
 */
export async function startLogin(): Promise<string | null> {
  try {
    const res = await fetch("/api/health", { cache: "no-store" });
    if (!res.ok) {
      return `백엔드에 연결할 수 없습니다 (HTTP ${res.status}). FastAPI가 :8000에서 실행 중인지 확인하세요.`;
    }
  } catch {
    return "백엔드에 연결할 수 없습니다. FastAPI가 :8000에서 실행 중인지 확인하세요.";
  }
  // Full navigation is required: this is an API redirect, not a Next.js page.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign("/api/auth/google/login");
  return null;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(describeFailure(res, await res.json().catch(() => null)));
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
