import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AION | Memory-Powered Business Intelligence",
  description: "AION researches companies, remembers prior investigations, tracks how signals change over time, and improves recommendations using accumulated business memory.",
  keywords: ["AION", "Business Intelligence", "Memory-powered AI", "B2B research", "Company intelligence", "Signal tracking"],
  openGraph: {
    title: "AION | Business Intelligence That Remembers",
    description: "AION researches companies, learns from every investigation, and builds persistent business memory so your next business decision is smarter than your last.",
    type: "website"
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-bg-primary text-fg-primary">
        {children}
      </body>
    </html>
  );
}
