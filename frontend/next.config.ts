import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Minimal, self-contained production image for Docker (see frontend/Dockerfile).
  output: "standalone",
};

export default nextConfig;
