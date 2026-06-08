import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "CHARUTEI — Inteligência em Charutos",
  description: "Identifique, colecione e descubra harmonizações de charutos com IA.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur sticky top-0 z-50">
          <nav className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2 font-bold text-lg tracking-tight">
              <span className="text-amber-400">&#9670;</span>
              <span>CHARUTEI</span>
            </Link>
            <div className="flex gap-6 ml-auto text-sm font-medium">
              <Link
                href="/"
                className="text-zinc-400 hover:text-amber-400 transition-colors"
              >
                Identificar
              </Link>
              <Link
                href="/humidor"
                className="text-zinc-400 hover:text-amber-400 transition-colors"
              >
                Humidor
              </Link>
              <Link
                href="/catalog"
                className="text-zinc-400 hover:text-amber-400 transition-colors"
              >
                Catálogo
              </Link>
            </div>
          </nav>
        </header>
        <main className="max-w-5xl mx-auto px-4 py-10">{children}</main>
        <footer className="border-t border-zinc-800 mt-20 py-6 text-center text-xs text-zinc-600">
          CHARUTEI MVP &middot; 117 charutos &middot; cascata cost-aware &middot;{" "}
          <span className="text-amber-700">LLM é o último recurso</span>
        </footer>
      </body>
    </html>
  );
}
