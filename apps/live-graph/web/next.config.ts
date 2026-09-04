import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The UI is entirely client-side and is served by the backend, so it ships as
  // static files rather than as a second Node process.
  output: "export",
  // The repo sits inside a larger workspace with its own lockfile; pin the root
  // so Turbopack does not walk up and pick the wrong one.
  turbopack: { root: __dirname },
};

export default nextConfig;
