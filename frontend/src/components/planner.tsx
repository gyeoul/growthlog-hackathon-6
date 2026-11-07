"use client";

import { useEffect, useState } from "react";
import {
  generatePlan,
  getAvailability,
  getSemester,
  isoDate,
  listBlocks,
  listCourses,
  listDeadlines,
  setBlockDone,
  type Course,
  type Deadline,
  type GenerateResult,
  type PlanBlock,
  type Semester,
  type Slot,
} from "@/lib/api";
import { BLOCK_LABELS, addDays, courseColor, dDay, lecturesDone, mondayOf } from "@/lib/planner";
import { PlannerSetup } from "@/components/planner-setup";
import { Timetable } from "@/components/timetable";

type Data = {
  semester: Semester | null;
  courses: Course[];
  deadlines: Deadline[];
  slots: Slot[];
  blocks: PlanBlock[];
};

async function loadAll(): Promise<Data> {
  const [semester, courses, deadlines, slots, blocks] = await Promise.all([
    getSemester(),
    listCourses(),
    listDeadlines(),
    getAvailability(),
    listBlocks(),
  ]);
  return { semester, courses, deadlines, slots, blocks };
}

/** Owns the planner's data so the setup forms and the timetable never disagree. */
export function Planner() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"plan" | "setup">("plan");
  const [weekStart, setWeekStart] = useState(() => mondayOf(new Date()));
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const reload = () => setReloadKey((k) => k + 1);

  useEffect(() => {
    let cancelled = false;
    loadAll()
      .then((next) => {
        if (cancelled) return;
        setData(next);
        // First visit with nothing set up yet: start on the setup forms.
        setTab((t) => (next.semester === null && next.courses.length === 0 ? "setup" : t));
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "불러오지 못했습니다.");
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      setResult(await generatePlan());
      setTab("plan");
      setWeekStart(mondayOf(new Date()));
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "계획을 만들지 못했습니다.");
    } finally {
      setGenerating(false);
    }
  }

  async function toggle(block: PlanBlock) {
    try {
      const updated = await setBlockDone(block.id, !block.done);
      setData((d) => d && { ...d, blocks: d.blocks.map((b) => (b.id === updated.id ? updated : b)) });
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장하지 못했습니다.");
    }
  }

  if (!data) {
    return error ? <ErrorBox message={error} /> : <p className="text-sm text-[var(--muted)]">불러오는 중…</p>;
  }

  const today = isoDate(new Date());
  const todayBlocks = data.blocks.filter((b) => b.date === today);
  const ready = data.semester !== null && data.slots.length > 0 && data.courses.length > 0;

  return (
    <section className="flex w-full flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex rounded-lg border border-[var(--border)] p-0.5 text-sm">
          {(["plan", "setup"] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`rounded-md px-3 py-1.5 ${tab === t ? "bg-[var(--accent)] text-white" : ""}`}
            >
              {t === "plan" ? "시간표" : "설정"}
            </button>
          ))}
        </div>
        {data.semester && (
          <span className="text-xs text-[var(--muted)]">
            학기 종료 {data.semester.end_date} · {dDay(data.semester.end_date)}
          </span>
        )}
        <button
          type="button"
          onClick={() => void generate()}
          disabled={!ready || generating}
          title={ready ? "" : "학기 기간, 강의, 공부 가능한 시간을 먼저 저장해 주세요"}
          className="ml-auto rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          {generating ? "계획 중…" : data.blocks.length ? "다시 계획" : "계획 만들기"}
        </button>
      </div>

      {error && <ErrorBox message={error} onClose={() => setError(null)} />}

      {result && (
        <div
          className={`rounded-xl border px-4 py-3 text-sm ${
            result.unscheduled.length
              ? "border-amber-500/40 bg-amber-500/10"
              : "border-green-600/40 bg-green-600/10"
          }`}
        >
          <p>남은 기간에 {result.scheduled}개 블록을 배치했습니다.</p>
          {result.unscheduled.length > 0 && (
            <p className="mt-1 text-xs">
              시간이 부족해 마감 전에 넣지 못한 항목 {result.unscheduled.length}개:{" "}
              {result.unscheduled.slice(0, 5).join(", ")}
              {result.unscheduled.length > 5 && " 외"}. 공부 시간을 늘리고 다시 계획해 보세요.
            </p>
          )}
        </div>
      )}

      {tab === "setup" ? (
        <PlannerSetup
          // Remount once the saved values come back, so the forms show them.
          key={JSON.stringify([data.semester, data.slots])}
          {...data}
          onChange={reload}
          onError={setError}
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <TodayCard blocks={todayBlocks} courses={data.courses} onToggle={toggle} />
            <ProgressCard data={data} />
          </div>

          <div className="flex items-center gap-2 text-sm">
            <button type="button" onClick={() => setWeekStart((w) => addDays(w, -7))} className="rounded-lg border border-[var(--border)] px-3 py-1">
              ← 지난주
            </button>
            <button type="button" onClick={() => setWeekStart(mondayOf(new Date()))} className="rounded-lg border border-[var(--border)] px-3 py-1">
              이번 주
            </button>
            <button type="button" onClick={() => setWeekStart((w) => addDays(w, 7))} className="rounded-lg border border-[var(--border)] px-3 py-1">
              다음 주 →
            </button>
            <span className="ml-auto text-xs text-[var(--muted)]">블록을 누르면 완료로 표시됩니다</span>
          </div>
          <Timetable
            weekStart={weekStart}
            courses={data.courses}
            blocks={data.blocks}
            slots={data.slots}
            onToggle={toggle}
          />
        </>
      )}
    </section>
  );
}

function TodayCard(props: { blocks: PlanBlock[]; courses: Course[]; onToggle: (b: PlanBlock) => void }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <h2 className="text-sm font-semibold">오늘 할 일</h2>
      {props.blocks.length === 0 ? (
        <p className="text-xs text-[var(--muted)]">오늘은 계획된 공부가 없습니다.</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {props.blocks.map((b) => (
            <li key={b.id}>
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input type="checkbox" checked={b.done} onChange={() => props.onToggle(b)} />
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: courseColor(props.courses, b.course_id) }} />
                <span className={`min-w-0 flex-1 truncate ${b.done ? "text-[var(--muted)] line-through" : ""}`}>
                  {b.title}
                </span>
                <span className="text-xs tabular-nums text-[var(--muted)]">
                  {b.start_time} · {BLOCK_LABELS[b.kind]}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ProgressCard({ data }: { data: Data }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <h2 className="text-sm font-semibold">과목별 진행률</h2>
      {data.courses.length === 0 && <p className="text-xs text-[var(--muted)]">설정에서 강의를 추가해 주세요.</p>}
      {data.courses.map((c) => {
        const done = lecturesDone(c, data.blocks);
        const next = data.deadlines.find((d) => d.course_id === c.id && d.due_date >= isoDate(new Date()));
        return (
          <div key={c.id} className="flex flex-col gap-1">
            <div className="flex items-center gap-2 text-xs">
              <span className="min-w-0 flex-1 truncate font-medium">{c.name}</span>
              <span className="tabular-nums text-[var(--muted)]">
                {done}/{c.total_lectures}강
                {next && ` · ${next.title} ${dDay(next.due_date)}`}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-[var(--border)]">
              <div
                className="h-full rounded-full"
                style={{ width: `${(done / c.total_lectures) * 100}%`, background: courseColor(data.courses, c.id) }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ErrorBox({ message, onClose }: { message: string; onClose?: () => void }) {
  return (
    <p
      role="alert"
      className="flex items-start gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-400"
    >
      <span className="flex-1">{message}</span>
      {onClose && (
        <button type="button" onClick={onClose} aria-label="닫기" className="shrink-0 opacity-60 hover:opacity-100">
          ×
        </button>
      )}
    </p>
  );
}
