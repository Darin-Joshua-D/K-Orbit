import React from 'react';
import { Inter, Fira_Code } from 'next/font/google';
import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth/auth-provider';
import { QueryProvider } from '@/lib/query/query-provider';
import { WebSocketProvider } from '@/lib/websocket/websocket-provider';
import { ThemeProvider } from '@/lib/theme/theme-provider';
import { GlobalAIChat } from '@/components/ai-coach/global-ai-chat';
import dynamic from 'next/dynamic';

// Client-only logout button floating top-right
// const GlobalLogout = dynamic(() => import('@/components/global-logout').then(m => m.GlobalLogout), { ssr: false });

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const firaCode = Fira_Code({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'K-Orbit | AI-Powered Corporate Learning',
    template: '%s | K-Orbit',
  },
  description: 'Transform your corporate onboarding and knowledge sharing with AI-powered learning experiences, gamification, and intelligent knowledge management.',
  keywords: [
    'corporate learning',
    'onboarding',
    'knowledge management',
    'AI learning',
    'gamification',
    'enterprise training',
    'LMS',
    'corporate education',
  ],
  authors: [{ name: 'K-Orbit Team' }],
  creator: 'K-Orbit',
  publisher: 'K-Orbit',
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://k-orbit.com',
    title: 'K-Orbit | AI-Powered Corporate Learning',
    description: 'Transform your corporate onboarding and knowledge sharing with AI-powered learning experiences.',
    siteName: 'K-Orbit',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'K-Orbit - AI-Powered Corporate Learning Platform',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'K-Orbit | AI-Powered Corporate Learning',
    description: 'Transform your corporate onboarding and knowledge sharing with AI-powered learning experiences.',
    images: ['/og-image.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png',
  },
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Preconnect to external domains */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        
        {/* Security headers */}
        <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
        <meta httpEquiv="X-Frame-Options" content="DENY" />
        <meta httpEquiv="X-XSS-Protection" content="1; mode=block" />
        
        {/* PWA theme color */}
        <meta name="theme-color" content="#0ea5e9" />
        <meta name="msapplication-TileColor" content="#0ea5e9" />
        
        {/* Apple specific meta tags */}
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="K-Orbit" />
      </head>
      <body className={`${inter.variable} ${firaCode.variable} font-sans antialiased`}>
        <ThemeProvider defaultTheme="system" storageKey="k-orbit-theme">
          <QueryProvider>
            <AuthProvider>
              <WebSocketProvider>
                {/* Main Application Content */}
                <div className="relative min-h-screen bg-background">
                  {/* Skip to main content link for accessibility */}
                  <a
                    href="#main-content"
                    className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-primary text-primary-foreground px-4 py-2 rounded-md z-50"
                  >
                    Skip to main content
                  </a>
                  
                  {/* Application layout */}
                  <main id="main-content" className="relative">
                    {children}
                  </main>
                  
                  {/* Global AI Chat - available on all authenticated pages */}
                  <GlobalAIChat />
                  {/* <GlobalLogout /> */}
                </div>
              </WebSocketProvider>
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
} 