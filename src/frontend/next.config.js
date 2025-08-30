/** @type {import('next').NextConfig} */
const nextConfig = {
  // Only use standalone output in production builds
  ...(process.env.NODE_ENV === 'production' && { output: 'standalone' }),
}

module.exports = nextConfig