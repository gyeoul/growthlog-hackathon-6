export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">Next.js + FastAPI</h1>
      <p className="text-sm text-[var(--muted)]">
        골격 준비 완료 — <code className="font-mono">/api/*</code>는 FastAPI로
        프록시됩니다.
      </p>
    </main>
  );
}
