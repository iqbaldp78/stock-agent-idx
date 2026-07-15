import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    const backendUrl = "http://127.0.0.1:8000";
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
