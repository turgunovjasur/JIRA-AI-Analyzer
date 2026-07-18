import type { Metadata } from "next";
import { DM_Mono, DM_Sans } from "next/font/google";

import { VersionGuard } from "@/components/version-guard";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "QA-Assistant Portal",
  description: "Unified QA workspace for customers, admins and operations teams",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="uz" className={`${dmSans.variable} ${dmMono.variable}`}>
      <body className="page-root">
        {children}
        <VersionGuard />
      </body>
    </html>
  );
}
