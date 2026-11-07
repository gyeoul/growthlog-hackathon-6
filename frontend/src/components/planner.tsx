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
    return error ? (
      <ErrorBox message={error} />
    ) : (
      <div className="card-muted h-40 animate-pulse" aria-hidden />
    );
  }

  const today = isoDate(new Date());
  const todayBlocks = data.blocks.filter((b) => b.date === today);
  const ready = data.semester !== null && data.slots.length > 0 && data.courses.length > 0;

  return (
    <section className="flex w-full flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <div
          role="tablist"
          aria-label="플래너 보기"
          className="inline-flex rounded-xl border border-line bg-surface-muted p-1 text-sm"
        >
          {(["plan", "setup"] as const).map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={`cursor-pointer rounded-lg px-3.5 py-1.5 font-medium transition-colors ${
                tab === t
                  ? "bg-surface text-ink shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
                  : "text-muted hover:text-ink"
              }`}
            >
              {t === "plan" ? "시간표" : "설정"}
            </button>
          ))}
        </div>

        {data.semester && (
          <span className="chip">
            학기 종료 {data.semester.end_date}
            <span className="text-brand">· {dDay(data.semester.end_date)}</span>
          </span>
        )}

        <button
          type="button"
          onClick={() => void generate()}
          disabled={!ready || generating}
          title={ready ? "" : "학기 기간, 강의, 공부 가능한 시간을 먼저 저장해 주세요"}
          className="btn btn-primary ml-auto"
        >
          {generating ? "계획 중…" : data.blocks.length ? "다시 계획" : "계획 만들기"}
        </button>
      </div>

      {error && <ErrorBox message={error} onClose={() => setError(null)} />}

      {result && (
        <div
          className={result.unscheduled.length ? "alert-warn" : "alert-success"}
          role="status"
        >
          <div className="flex-1">
            <p className="font-medium">
              남은 기간에 {result.scheduled}개 블록을 배치했습니다.
            </p>
            {result.unscheduled.length > 0 && (
              <p className="mt-1 text-xs leading-relaxed opacity-90">
                시간이 부족해 마감 전에 넣지 못한 항목 {result.unscheduled.length}개:{" "}
                {result.unscheduled.slice(0, 5).join(", ")}
                {result.unscheduled.length > 5 && " 외"}. 공부 시간을 늘리고 다시
                계획해 보세요.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => setResult(null)}
            aria-label="닫기"
            className="shrink-0 opacity-60 transition hover:opacity-100"
          >
            ×
          </button>
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

          <div className="flex flex-wrap items-center gap-2 text-sm">
            <button
              type="button"
              onClick={() => setWeekStart((w) => addDays(w, -7))}
              className="btn btn-sm border-line text-ink-soft"
            >
              ← 지난주
            </button>
            <button
              type="button"
              onClick={() => setWeekStart(mondayOf(new Date()))}
              className="btn btn-sm border-line text-ink-soft"
            >
              이번 주
            </button>
            <button
              type="button"
              onClick={() => setWeekStart((w) => addDays(w, 7))}
              className="btn btn-sm border-line text-ink-soft"
            >
              다음 주 →
            </button>
            <span className="ml-auto text-xs text-muted">
              블록을 누르면 완료로 표시됩니다
            </span>
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

function TodayCard(props: {
  blocks: PlanBlock[];
  courses: Course[];
  onToggle: (b: PlanBlock) => void;
}) {
  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-baseline gap-2">
        <h2 className="card-title">오늘 할 일</h2>
        <span className="ml-auto text-xs text-muted">{props.blocks.length}개</span>
      </div>
      {props.blocks.length === 0 ? (
        <p className="text-xs text-muted">오늘은 계획된 공부가 없습니다.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {props.blocks.map((b) => (
            <li key={b.id}>
              <label className="flex cursor-pointer items-center gap-2.5 rounded-lg px-1 py-1.5 text-sm transition-colors hover:bg-surface-muted">
                <input
                  type="checkbox"
                  checked={b.done}
                  onChange={() => props.onToggle(b)}
                  className="h-4 w-4 shrink-0 cursor-pointer accent-[var(--color-brand)]"
                />
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ background: courseColor(props.courses, b.course_id) }}
                />
                <span
                  className={`min-w-0 flex-1 truncate ${
                    b.done ? "text-muted line-through" : ""
                  }`}
                >
                  {b.title}
                </span>
                <span className="shrink-0 text-xs tabular-nums text-muted">
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
    <div className="card flex flex-col gap-3">
      <h2 className="card-title">과목별 진행률</h2>
      {data.courses.length === 0 && (
        <p className="text-xs text-muted">설정에서 강의를 추가해 주세요.</p>
      )}
      {data.courses.map((c) => {
        const done = lecturesDone(c, data.blocks);
        const next = data.deadlines.find(
          (d) => d.course_id === c.id && d.due_date >= isoDate(new Date()),
        );
        return (
          <div key={c.id} className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-xs">
              <span className="min-w-0 flex-1 truncate font-medium text-ink-soft">
                {c.name}
              </span>
              <span className="tabular-nums text-muted">
                {done}/{c.total_lectures}강
                {next && ` · ${next.title} ${dDay(next.due_date)}`}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-surface-muted">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(done / c.total_lectures) * 100}%`,
                  background: courseColor(data.courses, c.id),
                }}
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
    <p role="alert" className="alert-error">
      <span className="flex-1">{message}</span>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="닫기"
          className="shrink-0 opacity-60 transition hover:opacity-100"
        >
          ×
        </button>
      )}
    </p>
  );
}
