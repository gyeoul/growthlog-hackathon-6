import { Suspense } from "react";
import { Dashboard } from "@/components/dashboard";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-10 px-4 py-12">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">성장 기록</h1>
        <p className="text-sm text-[var(--muted)]">
          @knou.ac.kr 계정으로 로그인하고, 오늘의 성장을 남겨 두세요.
        </p>
      </div>

      <Suspense fallback={<div className="h-10" />}>
        <Dashboard />
      </Suspense>
    </main>
  );
}
