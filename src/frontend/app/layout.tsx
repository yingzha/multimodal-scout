import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from './context/ThemeContext'

export const metadata: Metadata = {
  title: 'Multimodal Scout',
  description: 'Find top stories and papers related to multimodal AI and AI agents',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}