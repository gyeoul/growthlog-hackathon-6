import { isoDate, type Course, type DeadlineKind, type PlanBlock } from "@/lib/api";

/** Monday-first, matching the backend's weekday numbering. */
export const WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"];

export const DEADLINE_LABELS: Record<DeadlineKind, string> = {
  assignment: "과제물",
  attendance: "출석수업",
  exam: "시험",
};

export const BLOCK_LABELS: Record<PlanBlock["kind"], string> = {
  lecture: "강의",
  assignment: "과제",
  attendance: "출석",
  review: "복습",
};

// Distinct hues that keep white text readable in both themes.
const COLORS = ["#4f46e5", "#0891b2", "#16a34a", "#d97706", "#db2777", "#7c3aed", "#dc2626"];

export function courseColor(courses: Course[], courseId: number): string {
  const index = courses.findIndex((c) => c.id === courseId);
  return COLORS[(index < 0 ? 0 : index) % COLORS.length];
}

export function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export function addDays(d: Date, days: number): Date {
  const next = new Date(d);
  next.setDate(next.getDate() + days);
  return next;
}

/** Local midnight of the Monday that starts `d`'s week. */
export function mondayOf(d: Date): Date {
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  return addDays(day, -((day.getDay() + 6) % 7));
}

export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** Whole days from today to `iso`; 0 means today. */
export function daysUntil(iso: string, today: Date = new Date()): number {
  const ms = parseDate(iso).getTime() - parseDate(isoDate(today)).getTime();
  return Math.round(ms / 86_400_000);
}

export function dDay(iso: string): string {
  const n = daysUntil(iso);
  return n === 0 ? "D-day" : n > 0 ? `D-${n}` : `D+${-n}`;
}

/** Lectures the member has finished: entered up front plus checked-off blocks. */
export function lecturesDone(course: Course, blocks: PlanBlock[]): number {
  const checked = blocks.filter(
    (b) => b.done && b.kind === "lecture" && b.course_id === course.id,
  ).length;
  return Math.min(course.total_lectures, course.done_lectures + checked);
}
