"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/search", label: "Search" },
  { href: "/assistant", label: "AI Assistant" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
        <Link href="/" className="font-semibold tracking-tight text-slate-900">
          demo<span className="text-slate-400">-</span>rag
        </Link>
        <div className="flex gap-4 text-sm">
          {LINKS.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={
                  active
                    ? "font-medium text-slate-900"
                    : "text-slate-500 hover:text-slate-900"
                }
              >
                {link.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </header>
  );
}
