import type { Metadata } from "next";
import { Oswald, Inter, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import "./global.css";

const display = Oswald({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
});

const body = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Nifty Scout Report",
  description:
    "Daily NSE stock rankings, scouted and scored like a football Team of the Week.",
};

const NAV_LINKS = [
  { href: "/", label: "Today" },
  { href: "/archive", label: "Archive" },
  { href: "/leaderboard", label: "Leaderboard" },
  { href: "/portfolio", label: "Your XI" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body className="font-body bg-stadium-gradient min-h-screen">
        <header className="border-b border-white/10">
          <nav className="mx-auto max-w-6xl flex items-center justify-between px-6 py-4">
            <Link href="/" className="font-display text-xl tracking-wide text-gold">
              NIFTY SCOUT
            </Link>
            <ul className="flex gap-6 text-sm text-ink-secondary">
              {NAV_LINKS.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="hover:text-gold transition-colors"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-8 text-xs text-ink-muted border-t border-white/10 mt-16">
          Generated automatically from NSE/Yahoo Finance data. Not investment
          advice — scores reflect historical technical factors only.
        </footer>
      </body>
    </html>
  );
}
