"""Fake Google IdP for local login testing without real Google credentials.

Run:  python3 scripts/fake_idp.py
Then start the backend with:

  GOOGLE_CLIENT_ID=fake-client GOOGLE_CLIENT_SECRET=fake-secret \
  GOOGLE_AUTHORIZE_URL=http://127.0.0.1:8099/authorize \
  GOOGLE_TOKEN_URL=http://127.0.0.1:8099/token \
  GOOGLE_USERINFO_URL=http://127.0.0.1:8099/userinfo \
  uv run uvicorn app.main:app --reload --port 8000

Pick a scenario with `GET /scenario?code=<code>`; the codes below are defined
in PROFILES and cover the accepted and rejected paths.
"""

import json
import pathlib
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8099
SCENARIO_FILE = "/tmp/idp-scenario"  # or set via /scenario?code=...
PROFILES = {
    # code -> userinfo payload
    "code-member": {
        "sub": "google-sub-1",
        "email": "student@knou.ac.kr",
        "email_verified": True,
        "name": "김학생",
        "picture": None,
    },
    "code-case": {
        "sub": "google-sub-2",
        "email": "Case.Test@KNOU.AC.KR",
        "email_verified": True,
        "name": "대소문자",
        "picture": "",
    },
    "code-outsider": {
        "sub": "google-sub-3",
        "email": "someone@gmail.com",
        "email_verified": True,
        "name": "외부인",
        "picture": None,
    },
    "code-spoof": {
        "sub": "google-sub-4",
        "email": "attacker@knou.ac.kr.evil.com",
        "email_verified": True,
        "name": "스푸핑",
        "picture": None,
    },
    "code-unverified": {
        "sub": "google-sub-5",
        "email": "unverified@knou.ac.kr",
        "email_verified": False,
        "name": "미인증",
        "picture": None,
    },
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep the smoke output readable
        pass

    def _send(self, status, body=b"", headers=None):
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)

        if url.path == "/authorize":
            if q.get("client_id") != ["fake-client"]:
                return self._send(400, b"bad client_id")
            if "openid" not in q.get("scope", [""])[0]:
                return self._send(400, b"bad scope")
            # Scenario is chosen out-of-band by the smoke test (see /scenario).
            try:
                code = pathlib.Path(SCENARIO_FILE).read_text().strip() or "code-member"
            except OSError:
                code = "code-member"
            code = q.get("login_hint", [code])[0]
            location = f"{q['redirect_uri'][0]}?" + urllib.parse.urlencode(
                {"code": code, "state": q["state"][0]}
            )
            return self._send(302, headers={"Location": location})

        if url.path == "/userinfo":
            auth = self.headers.get("Authorization", "")
            if not auth.startswith("Bearer tok-"):
                return self._send(401, b'{"error":"bad token"}')
            profile = PROFILES.get(auth.removeprefix("Bearer tok-"))
            if profile is None:
                return self._send(404, b'{"error":"unknown user"}')
            return self._send(200, json.dumps(profile).encode(), {"Content-Type": "application/json"})

        if url.path == "/scenario":
            pathlib.Path(SCENARIO_FILE).write_text(q.get("code", ["code-member"])[0])
            return self._send(200, b"ok")

        self._send(404, b"not found")

    def do_POST(self):
        if self.path != "/token":
            return self._send(404, b"not found")
        length = int(self.headers.get("Content-Length", 0))
        form = urllib.parse.parse_qs(self.rfile.read(length).decode())
        if form.get("code", [""])[0] not in PROFILES:
            return self._send(400, b'{"error":"invalid_grant"}')
        body = json.dumps(
            {
                "access_token": f"tok-{form['code'][0]}",
                "token_type": "Bearer",
                "expires_in": 3600,
                "id_token": "ignored",
            }
        ).encode()
        return self._send(200, body, {"Content-Type": "application/json"})


if __name__ == "__main__":
    print(f"fake IdP on http://127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
