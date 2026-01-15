import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  eslint: {
    // Allow build to succeed even with ESLint warnings/errors
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Allow build to succeed even with TypeScript errors
    ignoreBuildErrors: true,
  },
  // Remove rewrites - will be handled by middleware for proper runtime configuration
};

export default nextConfig;
