"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { logout, startLogin, type User } from "@/lib/api";

const ERRORS: Record<string, string> = {
  domain: "회원이 아닙니다. @knou.ac.kr 계정으로만 가입할 수 있습니다.",
  state: "로그인 요청이 만료되었습니다. 다시 시도해 주세요.",
  google: "구글 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.",
  config: "로그인 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.",
};

export function AuthBar({ user }: { user: User | null }) {
  const params = useSearchParams();
  const router = useRouter();

  // Capture the error on the first render, before the URL is cleaned up.
  const [authError] = useState(() => params.get("auth_error"));
  const [startError, setStartError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);

  // Drop the error from the URL so a refresh does not repeat stale news.
  useEffect(() => {
    if (params.get("auth_error")) router.replace("/", { scroll: false });
  }, [params, router]);

  const shownError =
    startError ??
    (authError && !dismissed ? (ERRORS[authError] ?? "로그인에 실패했습니다.") : null);

  if (!user) {
    return (
      <div className="flex flex-col gap-3">
        <button
          type="button"
          onClick={async () => {
            setDismissed(false);
            setStartError(await startLogin());
          }}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-2.5 text-sm font-medium transition hover:border-[var(--accent)]"
        >
          <GoogleMark />
          Google 계정으로 로그인
        </button>
        <p className="text-center text-xs text-[var(--muted)]">
          한국방송통신대학교 구성원(@knou.ac.kr)만 이용할 수 있습니다.
        </p>
        {shownError && (
          <p
            role="alert"
            className="flex items-start gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-400"
          >
            <span className="flex-1">{shownError}</span>
            <button
              type="button"
              onClick={() => setDismissed(true)}
              aria-label="닫기"
              className="shrink-0 opacity-60 hover:opacity-100"
            >
              ×
            </button>
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
      {user.picture ? (
        // Plain <img>: the avatar host is not known ahead of time for next/image.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={user.picture}
          alt=""
          className="h-9 w-9 rounded-full"
          referrerPolicy="no-referrer"
        />
      ) : (
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent)] text-sm text-white">
          {(user.name ?? user.email)[0]}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{user.name ?? user.email}</p>
        <p className="truncate text-xs text-[var(--muted)]">{user.email}</p>
      </div>
      <button
        type="button"
        onClick={async () => {
          await logout();
          // Reload so the session-dependent views re-read the server state.
          window.location.reload();
        }}
        className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs text-[var(--muted)] transition hover:text-[var(--fg)]"
      >
        로그아웃
      </button>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 48 48" className="h-4 w-4" aria-hidden>
      <path
        fill="#EA4335"
        d="M24 9.5c3.5 0 6.6 1.2 9 3.6l6.7-6.7C35.6 2.6 30.2 0 24 0 14.6 0 6.5 5.5 2.6 13.4l7.8 6.1C12.3 13.2 17.6 9.5 24 9.5z"
      />
      <path
        fill="#4285F4"
        d="M46.1 24.5c0-1.6-.1-2.8-.4-4.1H24v8.5h12.6c-.3 2.2-1.7 5.4-4.8 7.6l7.6 5.9c4.5-4.2 6.7-10.3 6.7-17.9z"
      />
      <path
        fill="#FBBC05"
        d="M10.4 28.5A14.5 14.5 0 0 1 9.6 24c0-1.6.3-3.1.8-4.5l-7.8-6.1A24 24 0 0 0 0 24c0 3.9.9 7.5 2.6 10.6l7.8-6.1z"
      />
      <path
        fill="#34A853"
        d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.6-5.9c-2.1 1.4-4.8 2.4-8.3 2.4-6.4 0-11.7-3.7-13.6-8.9l-7.8 6.1C6.5 42.5 14.6 48 24 48z"
      />
    </svg>
  );
}
