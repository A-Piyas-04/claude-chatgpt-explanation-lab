/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The API base URL is read server-side only, so the researcher token and the
  // API location never reach the client bundle.
  env: {},
  experimental: { typedRoutes: false },
};

export default nextConfig;
