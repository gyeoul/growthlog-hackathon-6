"use client";

import { isoDate, type Course, type PlanBlock, type Slot } from "@/lib/api";
import { BLOCK_LABELS, WEEKDAYS, addDays, courseColor, toMinutes } from "@/lib/planner";

const PX_PER_MINUTE = 0.9;

type Props = {
  weekStart: Date;
  courses: Course[];
  blocks: PlanBlock[];
  slots: Slot[];
  onToggle: (block: PlanBlock) => void;
};

/** Monday-to-Sunday grid; free time is shaded, planned blocks sit on top. */
export function Timetable({ weekStart, courses, blocks, slots, onToggle }: Props) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const isos = days.map(isoDate);
  const weekBlocks = blocks.filter((b) => isos.includes(b.date));
  const today = isoDate(new Date());

  // Show only the hours that matter: free time and planned blocks, padded to the hour.
  const edges = [
    ...slots.flatMap((s) => [toMinutes(s.start_time), toMinutes(s.end_time)]),
    ...weekBlocks.flatMap((b) => [toMinutes(b.start_time), toMinutes(b.end_time)]),
  ];
  const first = edges.length ? Math.floor(Math.min(...edges) / 60) : 9;
  const last = edges.length ? Math.ceil(Math.max(...edges) / 60) : 18;
  const hours = Array.from({ length: Math.max(1, last - first) }, (_, i) => first + i);
  const top = (hhmm: string) => (toMinutes(hhmm) - first * 60) * PX_PER_MINUTE;
  const height = hours.length * 60 * PX_PER_MINUTE;

  return (
    <div className="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--surface)]">
      <div className="grid min-w-[640px] grid-cols-[3rem_repeat(7,1fr)]">
        <div />
        {days.map((d, i) => (
          <div
            key={i}
            className={`border-b border-l border-[var(--border)] py-2 text-center text-xs ${
              isos[i] === today ? "font-semibold text-[var(--accent)]" : ""
            }`}
          >
            {WEEKDAYS[i]} {d.getMonth() + 1}/{d.getDate()}
          </div>
        ))}

        <div className="relative" style={{ height }}>
          {hours.map((h, i) => (
            <span
              key={h}
              className="absolute right-1 -translate-y-1/2 text-[10px] text-[var(--muted)]"
              style={{ top: i * 60 * PX_PER_MINUTE }}
            >
              {i === 0 ? "" : `${h}:00`}
            </span>
          ))}
        </div>

        {days.map((_, i) => (
          <div key={i} className="relative border-l border-[var(--border)]" style={{ height }}>
            {hours.slice(1).map((h, j) => (
              <div
                key={h}
                className="absolute inset-x-0 border-t border-dashed border-[var(--border)]"
                style={{ top: (j + 1) * 60 * PX_PER_MINUTE }}
              />
            ))}
            {slots
              .filter((s) => s.weekday === i)
              .map((s, j) => (
                <div
                  key={j}
                  className="absolute inset-x-0 bg-[var(--accent)]/5"
                  style={{ top: top(s.start_time), height: top(s.end_time) - top(s.start_time) }}
                />
              ))}
            {weekBlocks
              .filter((b) => b.date === isos[i])
              .map((b) => (
                <button
                  key={b.id}
                  type="button"
                  onClick={() => onToggle(b)}
                  title={`${b.title} ${b.start_time}–${b.end_time} · 눌러서 ${b.done ? "완료 취소" : "완료"}`}
                  className={`absolute inset-x-0.5 overflow-hidden rounded-md px-1.5 py-0.5 text-left text-[11px] leading-tight text-white transition hover:brightness-110 ${
                    b.done ? "opacity-40 line-through" : ""
                  }`}
                  style={{
                    top: top(b.start_time) + 1,
                    height: top(b.end_time) - top(b.start_time) - 2,
                    background: courseColor(courses, b.course_id),
                  }}
                >
                  <span className="block truncate font-medium">{b.title}</span>
                  <span className="block truncate opacity-80">
                    {b.start_time} · {BLOCK_LABELS[b.kind]}
                  </span>
                </button>
              ))}
          </div>
        ))}
      </div>
    </div>
  );
}
