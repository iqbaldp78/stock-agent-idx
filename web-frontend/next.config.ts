import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.BACKEND_URL ?? "http://localhost:8000";
    return [
      {
        source: "/api/dashboard/stats",
        destination: `${backendUrl}/api/stats`,
        basePath: false,
      },
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
        basePath: false,
      },
    ];
  },
};

export default nextConfig;
