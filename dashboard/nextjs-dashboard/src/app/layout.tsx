import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { Toaster } from "@/components/organisms/Toaster";
import { ConnectionStatus } from "@/components/atoms/ConnectionStatus";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "RNR Enhanced Cognee Dashboard",
    template: "%s | RNR Enhanced Cognee",
  },
  description:
    "Enterprise-grade AI memory management system with real-time updates, advanced search, and powerful analytics.",
  keywords: [
    "AI",
    "memory",
    "dashboard",
    "cognee",
    "knowledge management",
    "analytics",
    "visualization",
  ],
  authors: [{ name: "RNR Enhanced Cognee Team" }],
  creator: "RNR Enhanced Cognee",
  publisher: "RNR Enhanced Cognee",
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || "http://localhost:9050"),
  openGraph: {
    type: "website",
    locale: "en_US",
    url: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:9050",
    title: "RNR Enhanced Cognee Dashboard",
    description:
      "Enterprise-grade AI memory management system with real-time updates, advanced search, and powerful analytics.",
    siteName: "RNR Enhanced Cognee",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "RNR Enhanced Cognee Dashboard",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "RNR Enhanced Cognee Dashboard",
    description:
      "Enterprise-grade AI memory management system with real-time updates, advanced search, and powerful analytics.",
    images: ["/og-image.png"],
    creator: "@enhancedcognee",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-16x16.png",
    apple: "/apple-touch-icon.png",
  },
  manifest: "/manifest.json",
  viewport: {
    width: "device-width",
    initialScale: 1,
    maximumScale: 5,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          <div className="flex min-h-screen flex-col">
            <Header />
            <div className="flex flex-1">
              <Sidebar />
              <main className="flex-1 md:pl-64">
                <div className="container py-6">{children}</div>
              </main>
            </div>
          </div>
          <Toaster />
          <ConnectionStatus />
        </Providers>
      </body>
    </html>
  );
}
