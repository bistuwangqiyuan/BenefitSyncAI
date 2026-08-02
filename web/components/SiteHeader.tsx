import Link from "next/link";
import { NAV, SITE } from "@/lib/site";

export function SiteHeader() {
  return (
    <header className="border-b border-[var(--line)] bg-[var(--surface)]/90 backdrop-blur-md sticky top-0 z-40">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="group flex flex-col leading-tight">
          <span className="font-[family-name:var(--font-display)] text-xl tracking-tight text-[var(--ink)]">
            {SITE.name}
          </span>
          <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
            {SITE.nameCn} · free tools
          </span>
        </Link>
        <nav className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1 text-sm">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-[var(--ink-soft)] transition hover:text-[var(--accent)]"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
