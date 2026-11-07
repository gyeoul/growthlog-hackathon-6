import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // Google OAuth only accepts the loopback IP form (127.0.0.1), not "localhost",
  // so the dev server is opened at 127.0.0.1:3000. Next.js blocks dev asset and
  // HMR requests from origins it does not know, which leaves the page stuck on
  // the Suspense fallback; allow the IP explicitly.
  allowedDevOrigins: ["127.0.0.1"],
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // Keeps the browser talking to one origin: no CORS, no API base URL to ship.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
