import { Suspense } from "react";
import { AuthBar } from "@/components/auth-bar";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8 p-8">
      <div className="w-full max-w-sm space-y-2 text-center">
        <h1 className="text-2xl font-semibold tracking-tight">KNOU 로그인</h1>
        <p className="text-sm text-[var(--muted)]">
          @knou.ac.kr 계정으로만 가입할 수 있습니다.
        </p>
      </div>
      <div className="w-full max-w-sm">
        <Suspense fallback={<div className="h-10" />}>
          <AuthBar />
        </Suspense>
      </div>
    </main>
  );
}
