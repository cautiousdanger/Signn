import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow HMR websocket when the app is opened via 127.0.0.1 (not only localhost).
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
