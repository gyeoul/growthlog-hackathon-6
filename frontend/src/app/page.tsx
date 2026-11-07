import { Suspense } from "react";
import { Dashboard } from "@/components/dashboard";

export default function Home() {
  return (
    <>
      <header className="sticky top-0 z-10 border-b border-line bg-canvas/85 backdrop-blur">
        <div className="mx-auto flex w-full max-w-5xl items-center gap-3 px-5 py-4">
          <span
            aria-hidden
            className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand text-[13px] font-bold text-white"
          >
            G
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-[15px] font-semibold tracking-tight">그로스로그</span>
            <span className="text-[15px] font-semibold tracking-tight text-brand">스터디</span>
          </div>
          <span className="ml-auto hidden text-xs text-muted sm:block">
            한국방송통신대학교 구성원 전용
          </span>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-5 py-10">
        <div className="flex flex-col gap-3">
          <p className="eyebrow">Semester Planner</p>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            남은 학기, 무엇을 언제 할지 한눈에
          </h1>
          <p className="max-w-2xl text-sm leading-relaxed text-muted">
            수강 강의와 마감 일정, 공부 가능한 시간을 넣으면 학기 끝까지 시간표를 짜
            드립니다.
          </p>
        </div>

        <Suspense fallback={<div className="h-10" />}>
          <Dashboard />
        </Suspense>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto w-full max-w-5xl px-5 py-6 text-xs text-muted">
          그로스로그 · 함께 배우면 문화
        </div>
      </footer>
    </>
  );
}
