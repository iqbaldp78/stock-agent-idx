import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  basePath: "/web",
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || (process.env.NODE_ENV === 'development' ? "http://localhost:8000" : "http://web_api:8000");
    return [
      {
        source: "/web/api/dashboard/stats",
        destination: `${backendUrl}/api/stats`,
        basePath: false,
      },
      {
        source: "/api/dashboard/stats",
        destination: `${backendUrl}/api/stats`,
        basePath: false,
      },
      {
        source: "/web/api/:path*",
        destination: `${backendUrl}/api/:path*`,
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
