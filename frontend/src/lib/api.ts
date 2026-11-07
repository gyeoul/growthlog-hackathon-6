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
