import { Suspense } from "react";
import { Dashboard } from "@/components/dashboard";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-10 px-4 py-12">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">학기 플래너</h1>
        <p className="text-sm text-[var(--muted)]">
          수강 강의와 마감 일정을 넣으면, 학기 끝까지 남은 날짜에 공부 시간표를 짜 드립니다.
        </p>
      </div>

      <Suspense fallback={<div className="h-10" />}>
        <Dashboard />
      </Suspense>
    </main>
  );
}
