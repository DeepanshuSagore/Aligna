import type { Metadata } from "next";
import { Schibsted_Grotesk, Inter, Noto_Sans, Fustat } from "next/font/google";
import "./globals.css";

const schibsted = Schibsted_Grotesk({
  variable: "--font-schibsted",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const notoSans = Noto_Sans({
  variable: "--font-noto-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const fustat = Fustat({
  variable: "--font-fustat",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "ScoutIQ - Hire Top Talent Faster With AI Precision",
  description: "AI-Powered Talent Scouting & Engagement Agent",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${schibsted.variable} ${inter.variable} ${notoSans.variable} ${fustat.variable} antialiased dark`}
    >
      <body className="font-inter bg-black text-white min-h-screen">
        {children}
      </body>
    </html>
  );
}
