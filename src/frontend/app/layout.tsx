import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Multimodal Scout',
  description: 'AI-powered content scouting system',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}