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

/** Like `request`, but `null` on 401 so anonymous visitors can browse. Never throws for auth. */
export async function requestOptional<T>(url: string): Promise<T | null> {
  const res = await fetch(url, { cache: "no-store" });
  if (res.status === 401) return null;
  if (!res.ok) {
    throw new Error(describeFailure(res, await res.json().catch(() => null)));
  }
  return (await res.json()) as T;
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

// --- semester planner ------------------------------------------------------

export type Semester = { start_date: string; end_date: string };

export type Course = {
  id: number;
  name: string;
  credits: number;
  total_lectures: number;
  done_lectures: number;
  minutes_per_lecture: number;
};

export type CourseInput = Omit<Course, "id">;

export type DeadlineKind = "assignment" | "attendance" | "exam";

export type Deadline = {
  id: number;
  course_id: number;
  kind: DeadlineKind;
  title: string;
  due_date: string;
};

export type DeadlineInput = Omit<Deadline, "id">;

/** weekday: 0 = Monday … 6 = Sunday. */
export type Slot = { weekday: number; start_time: string; end_time: string };

export type PlanBlock = {
  id: number;
  course_id: number;
  deadline_id: number | null;
  kind: "lecture" | "assignment" | "attendance" | "review";
  title: string;
  date: string;
  start_time: string;
  end_time: string;
  done: boolean;
};

export type GenerateResult = { scheduled: number; unscheduled: string[] };

const json = (body: unknown) => JSON.stringify(body);

export async function getSemester(): Promise<Semester | null> {
  return (await request<{ semester: Semester | null }>("/api/semester")).semester;
}

export function saveSemester(input: Semester): Promise<Semester> {
  return request<Semester>("/api/semester", { method: "PUT", body: json(input) });
}

export async function listCourses(): Promise<Course[]> {
  return (await request<{ courses: Course[] }>("/api/courses")).courses;
}

export function createCourse(input: CourseInput): Promise<Course> {
  return request<Course>("/api/courses", { method: "POST", body: json(input) });
}

export function updateCourse(id: number, input: CourseInput): Promise<Course> {
  return request<Course>(`/api/courses/${id}`, { method: "PUT", body: json(input) });
}

export function deleteCourse(id: number): Promise<void> {
  return request<void>(`/api/courses/${id}`, { method: "DELETE" });
}

export async function listDeadlines(): Promise<Deadline[]> {
  return (await request<{ deadlines: Deadline[] }>("/api/deadlines")).deadlines;
}

export function createDeadline(input: DeadlineInput): Promise<Deadline> {
  return request<Deadline>("/api/deadlines", { method: "POST", body: json(input) });
}

export function deleteDeadline(id: number): Promise<void> {
  return request<void>(`/api/deadlines/${id}`, { method: "DELETE" });
}

export async function getAvailability(): Promise<Slot[]> {
  return (await request<{ slots: Slot[] }>("/api/availability")).slots;
}

export async function saveAvailability(slots: Slot[]): Promise<Slot[]> {
  const res = await request<{ slots: Slot[] }>("/api/availability", {
    method: "PUT",
    body: json({ slots }),
  });
  return res.slots;
}

export async function listBlocks(): Promise<PlanBlock[]> {
  return (await request<{ blocks: PlanBlock[] }>("/api/plan")).blocks;
}

/** Sends the browser's local date/time so "today" is the member's today. */
export function generatePlan(now: Date = new Date()): Promise<GenerateResult> {
  const pad = (n: number) => String(n).padStart(2, "0");
  return request<GenerateResult>("/api/plan/generate", {
    method: "POST",
    body: json({ today: isoDate(now), now: `${pad(now.getHours())}:${pad(now.getMinutes())}` }),
  });
}

export function setBlockDone(id: number, done: boolean): Promise<PlanBlock> {
  return request<PlanBlock>(`/api/plan/blocks/${id}`, {
    method: "PATCH",
    body: json({ done }),
  });
}

/** Local-time `YYYY-MM-DD` (toISOString would shift the date to UTC). */
export function isoDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// --- studies ---------------------------------------------------------------

export type StudyOwner = { id: number; name: string };

export type Study = {
  id: number;
  title: string;
  description: string;
  capacity: number;
  member_count: number;
  owner: StudyOwner;
  created_at: string;
  is_open: boolean;
};

export type StudyMember = { user_id: number; name: string; joined_at: string };

export type StudyDetail = Study & {
  members: StudyMember[];
  is_member: boolean;
  is_owner: boolean;
};

export type StudyInput = { title: string; description: string; capacity: number };

/** Public list. Detail is public too, but join/leave/create need a session. */
export async function listStudies(): Promise<Study[]> {
  return (await request<{ studies: Study[] }>("/api/studies")).studies;
}

export function getStudy(id: number): Promise<StudyDetail> {
  return request<StudyDetail>(`/api/studies/${id}`);
}

export function createStudy(input: StudyInput): Promise<StudyDetail> {
  return request<StudyDetail>("/api/studies", { method: "POST", body: json(input) });
}

export function joinStudy(id: number): Promise<StudyDetail> {
  return request<StudyDetail>(`/api/studies/${id}/join`, { method: "POST" });
}

export function leaveStudy(id: number): Promise<StudyDetail> {
  return request<StudyDetail>(`/api/studies/${id}/members/me`, { method: "DELETE" });
}
