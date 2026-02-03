import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 允许外部图片
  images: {
    remotePatterns: [],
  },
  // 实验性功能
  experimental: {},
};

export default nextConfig;
