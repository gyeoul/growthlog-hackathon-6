"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { logout, startLogin, type User } from "@/lib/api";

const ERRORS: Record<string, string> = {
  domain: "회원이 아닙니다. @knou.ac.kr 계정으로만 가입할 수 있습니다.",
  state: "로그인 요청이 만료되었습니다. 다시 시도해 주세요.",
  google: "구글 로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.",
  config:
    "로그인 설정이 완료되지 않았습니다. backend/.env 에 GOOGLE_CLIENT_ID 와 GOOGLE_CLIENT_SECRET 을 채운 뒤 서버를 재시작하세요.",
};

export function AuthBar({ user }: { user: User | null }) {
  const params = useSearchParams();
  const router = useRouter();

  // Capture on the first render: the URL is cleaned up below, and the values
  // would be gone by the time a later render reads them.
  const [authError] = useState(() => params.get("auth_error"));
  const [missing] = useState(() => params.get("missing"));
  const [startError, setStartError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);

  // Drop the error from the URL so a refresh does not repeat stale news.
  useEffect(() => {
    if (params.get("auth_error")) router.replace("/", { scroll: false });
  }, [params, router]);

  const baseError =
    startError ?? (authError ? (ERRORS[authError] ?? "로그인에 실패했습니다.") : null);
  const shownError =
    baseError && !dismissed
      ? baseError + (authError === "config" && missing ? ` (누락: ${missing})` : "")
      : null;

  if (!user) {
    return (
      <div className="flex flex-col gap-4">
        <div className="card flex flex-col items-center gap-4 text-center sm:flex-row sm:text-left">
          <div className="flex flex-1 flex-col gap-1">
            <p className="card-title">로그인이 필요합니다</p>
            <p className="text-xs leading-relaxed text-muted">
              학교 계정으로 로그인하면 시간표와 성장 기록을 저장할 수 있습니다.
            </p>
          </div>
          <button
            type="button"
            onClick={async () => {
              setDismissed(false);
              setStartError(await startLogin());
            }}
            className="btn btn-primary w-full sm:w-auto"
          >
            <GoogleMark />
            Google 계정으로 로그인
          </button>
        </div>
        <p className="text-center text-xs text-muted">
          한국방송통신대학교 구성원(@knou.ac.kr)만 이용할 수 있습니다.
        </p>
        {shownError && (
          <p role="alert" className="alert-error">
            <span className="flex-1">{shownError}</span>
            <button
              type="button"
              onClick={() => setDismissed(true)}
              aria-label="닫기"
              className="shrink-0 opacity-60 transition hover:opacity-100"
            >
              ×
            </button>
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="card flex items-center gap-3 py-4">
      {user.picture ? (
        // Plain <img>: the avatar host is not known ahead of time for next/image.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={user.picture}
          alt=""
          className="h-10 w-10 rounded-full border border-line object-cover"
          referrerPolicy="no-referrer"
        />
      ) : (
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-soft text-sm font-semibold text-brand-dark">
          {(user.name ?? user.email)[0]}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold">{user.name ?? user.email}</p>
        <p className="truncate text-xs text-muted">{user.email}</p>
      </div>
      <button
        type="button"
        onClick={async () => {
          await logout();
          // Reload so the session-dependent views re-read the server state.
          window.location.reload();
        }}
        className="btn btn-sm btn-ghost border-line"
      >
        로그아웃
      </button>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 48 48" className="h-4 w-4 shrink-0" aria-hidden>
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
