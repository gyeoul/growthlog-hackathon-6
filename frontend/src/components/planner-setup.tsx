"use client";

import { useState } from "react";
import {
  createCourse,
  createDeadline,
  deleteCourse,
  deleteDeadline,
  saveAvailability,
  saveSemester,
  type Course,
  type Deadline,
  type DeadlineKind,
  type Semester,
  type Slot,
} from "@/lib/api";
import { DEADLINE_LABELS, WEEKDAYS, courseColor, dDay } from "@/lib/planner";

const input = "input w-auto";
const primary = "btn btn-primary";
const subtle = "btn btn-sm border-line text-ink-soft";
const card = "card flex flex-col gap-3";

type Props = {
  semester: Semester | null;
  courses: Course[];
  deadlines: Deadline[];
  slots: Slot[];
  onChange: () => void;
  onError: (message: string) => void;
};

/** Everything the planner needs as input, one card per kind of data. */
export function PlannerSetup(props: Props) {
  return (
    <div className="flex flex-col gap-4">
      <SemesterCard {...props} />
      <CoursesCard {...props} />
      <DeadlinesCard {...props} />
      <AvailabilityCard {...props} />
    </div>
  );
}

function useAction({ onChange, onError }: Props) {
  const [busy, setBusy] = useState(false);
  async function run(action: () => Promise<unknown>): Promise<boolean> {
    setBusy(true);
    try {
      await action();
      onChange();
      return true;
    } catch (err) {
      onError(err instanceof Error ? err.message : "저장하지 못했습니다.");
      return false;
    } finally {
      setBusy(false);
    }
  }
  return { busy, run };
}

function SemesterCard(props: Props) {
  const { busy, run } = useAction(props);
  const [start, setStart] = useState(props.semester?.start_date ?? "");
  const [end, setEnd] = useState(props.semester?.end_date ?? "");

  return (
    <form
      className={card}
      onSubmit={(e) => {
        e.preventDefault();
        void run(() => saveSemester({ start_date: start, end_date: end }));
      }}
    >
      <div className="flex flex-col gap-1">
        <p className="eyebrow">Step 1</p>
        <h2 className="card-title">학기 기간</h2>
        <p className="text-xs text-muted">종료일은 마지막 기말시험 날짜로 넣어 주세요.</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input type="date" value={start} onChange={(e) => setStart(e.target.value)} className={input} required />
        <span className="text-sm text-muted">~</span>
        <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className={input} required />
        <button type="submit" disabled={busy || !start || !end} className={primary}>
          저장
        </button>
      </div>
    </form>
  );
}

const EMPTY_COURSE = { name: "", credits: 3, total_lectures: 15, done_lectures: 0, minutes_per_lecture: 50 };

function CoursesCard(props: Props) {
  const { busy, run } = useAction(props);
  const [form, setForm] = useState(EMPTY_COURSE);
  const set = (key: keyof typeof form, value: string) =>
    setForm((f) => ({ ...f, [key]: key === "name" ? value : Number(value) }));

  return (
    <section className={card}>
      <div className="flex flex-col gap-1">
        <p className="eyebrow">Step 2</p>
        <h2 className="card-title">수강 강의</h2>
      </div>
      {props.courses.length > 0 && (
        <ul className="flex flex-col gap-2">
          {props.courses.map((c) => (
            <li key={c.id} className="flex items-center gap-2 rounded-lg px-1 py-1 text-sm transition-colors hover:bg-surface-muted">
              <span className="h-3 w-3 shrink-0 rounded-full" style={{ background: courseColor(props.courses, c.id) }} />
              <span className="min-w-0 flex-1 truncate">
                {c.name}
                <span className="ml-2 text-xs text-muted">
                  {c.credits}학점 · {c.total_lectures}강 중 {c.done_lectures}강 수강 · {c.minutes_per_lecture}분/강
                </span>
              </span>
              <button
                type="button"
                className={`${subtle} btn-danger`}
                onClick={() => {
                  if (window.confirm(`"${c.name}"과 관련 일정·계획을 모두 삭제할까요?`)) {
                    void run(() => deleteCourse(c.id));
                  }
                }}
              >
                삭제
              </button>
            </li>
          ))}
        </ul>
      )}
      <form
        className="grid grid-cols-2 gap-2 sm:grid-cols-6"
        onSubmit={async (e) => {
          e.preventDefault();
          if (await run(() => createCourse({ ...form, name: form.name.trim() }))) setForm(EMPTY_COURSE);
        }}
      >
        <input
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="과목명"
          maxLength={100}
          className={`${input} col-span-2`}
          required
        />
        <NumberField label="학점" value={form.credits} min={1} max={6} onChange={(v) => set("credits", v)} />
        <NumberField label="전체 강의" value={form.total_lectures} min={1} max={30} onChange={(v) => set("total_lectures", v)} />
        <NumberField label="들은 강의" value={form.done_lectures} min={0} max={form.total_lectures} onChange={(v) => set("done_lectures", v)} />
        <NumberField label="강의당 분" value={form.minutes_per_lecture} min={10} max={240} onChange={(v) => set("minutes_per_lecture", v)} />
        <button type="submit" disabled={busy || !form.name.trim()} className={`${primary} col-span-2 sm:col-span-6`}>
          강의 추가
        </button>
      </form>
    </section>
  );
}

function NumberField(props: { label: string; value: number; min: number; max: number; onChange: (v: string) => void }) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-muted">
      {props.label}
      <input
        type="number"
        value={props.value}
        min={props.min}
        max={props.max}
        onChange={(e) => props.onChange(e.target.value)}
        className={input}
        required
      />
    </label>
  );
}

function DeadlinesCard(props: Props) {
  const { busy, run } = useAction(props);
  const [courseId, setCourseId] = useState("");
  const [kind, setKind] = useState<DeadlineKind>("assignment");
  const [title, setTitle] = useState("");
  const [due, setDue] = useState("");
  const names = new Map(props.courses.map((c) => [c.id, c.name]));
  const selected = courseId || String(props.courses[0]?.id ?? "");

  return (
    <section className={card}>
      <div className="flex flex-col gap-1">
        <p className="eyebrow">Step 3</p>
        <h2 className="card-title">과제·출석수업·시험 일정</h2>
      </div>
      {props.courses.length === 0 ? (
        <p className="text-xs text-muted">강의를 먼저 추가해 주세요.</p>
      ) : (
        <form
          className="flex flex-wrap gap-2"
          onSubmit={async (e) => {
            e.preventDefault();
            const ok = await run(() =>
              createDeadline({ course_id: Number(selected), kind, title: title.trim(), due_date: due }),
            );
            if (ok) {
              setTitle("");
              setDue("");
            }
          }}
        >
          <select value={selected} onChange={(e) => setCourseId(e.target.value)} className={input}>
            {props.courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <select value={kind} onChange={(e) => setKind(e.target.value as DeadlineKind)} className={input}>
            {Object.entries(DEADLINE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="이름 (선택)"
            maxLength={100}
            className={`${input} min-w-0 flex-1`}
          />
          <input type="date" value={due} onChange={(e) => setDue(e.target.value)} className={input} required />
          <button type="submit" disabled={busy || !due} className={primary}>
            추가
          </button>
        </form>
      )}
      {props.deadlines.length > 0 && (
        <ul className="flex flex-col gap-1.5">
          {props.deadlines.map((d) => (
            <li key={d.id} className="flex items-center gap-2 rounded-lg px-1 py-1 text-sm transition-colors hover:bg-surface-muted">
              <span className="w-14 shrink-0 text-xs font-semibold tabular-nums text-brand">{dDay(d.due_date)}</span>
              <span className="min-w-0 flex-1 truncate">
                {names.get(d.course_id)} · {d.title}
                <span className="ml-2 text-xs text-muted">
                  {DEADLINE_LABELS[d.kind]} · {d.due_date}
                </span>
              </span>
              <button
                type="button"
                className={`${subtle} btn-danger`}
                onClick={() => void run(() => deleteDeadline(d.id))}
              >
                삭제
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function AvailabilityCard(props: Props) {
  const { busy, run } = useAction(props);
  const [rows, setRows] = useState<Slot[]>(props.slots);
  const update = (i: number, patch: Partial<Slot>) =>
    setRows((r) => r.map((row, j) => (j === i ? { ...row, ...patch } : row)));

  return (
    <form
      className={card}
      onSubmit={(e) => {
        e.preventDefault();
        void run(() => saveAvailability(rows));
      }}
    >
      <div className="flex flex-col gap-1">
        <p className="eyebrow">Step 4</p>
        <h2 className="card-title">공부 가능한 시간 (매주 반복)</h2>
        {rows.length === 0 && (
          <p className="text-xs text-muted">예: 평일 21:00–23:00, 토요일 10:00–13:00</p>
        )}
      </div>
      {rows.map((row, i) => (
        <div key={i} className="flex flex-wrap items-center gap-2">
          <select
            value={row.weekday}
            onChange={(e) => update(i, { weekday: Number(e.target.value) })}
            className={input}
          >
            {WEEKDAYS.map((label, d) => (
              <option key={d} value={d}>
                {label}요일
              </option>
            ))}
          </select>
          <input type="time" value={row.start_time} onChange={(e) => update(i, { start_time: e.target.value })} className={input} required />
          <span className="text-sm text-muted">~</span>
          <input type="time" value={row.end_time} onChange={(e) => update(i, { end_time: e.target.value })} className={input} required />
          <button type="button" className={subtle} onClick={() => setRows((r) => r.filter((_, j) => j !== i))}>
            빼기
          </button>
        </div>
      ))}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={subtle}
          onClick={() => setRows((r) => [...r, { weekday: 0, start_time: "21:00", end_time: "23:00" }])}
        >
          + 시간 추가
        </button>
        <button
          type="button"
          className={subtle}
          onClick={() =>
            setRows((r) => [
              ...r,
              ...[0, 1, 2, 3, 4].map((weekday) => ({ weekday, start_time: "21:00", end_time: "23:00" })),
            ])
          }
        >
          + 평일 저녁 일괄 추가
        </button>
        <button type="submit" disabled={busy} className={`${primary} ml-auto`}>
          저장
        </button>
      </div>
    </form>
  );
}
