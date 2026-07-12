import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || (process.env.NODE_ENV === 'development' ? "http://localhost:8000" : "http://web_api:8000");
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
