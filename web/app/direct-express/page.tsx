import { Byline } from "@/components/Byline";
import { getDirectExpress } from "@/lib/data";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Direct Express transition",
  description:
    "Facts and official links about the Direct Express card issuer transition. No card numbers collected.",
};

export default function DirectExpressPage() {
  const info = getDirectExpress();

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="font-[family-name:var(--font-display)] text-3xl md:text-4xl text-[var(--ink)]">
        {info.title}
      </h1>
      <Byline updatedAt={info.updated_at} />
      <p className="mt-4 max-w-2xl text-lg leading-relaxed text-[var(--ink-soft)]">
        {info.summary}
      </p>

      <section className="mt-10 max-w-2xl">
        <h2 className="font-[family-name:var(--font-display)] text-xl">Timeline</h2>
        <ol className="mt-4 space-y-4">
          {info.timeline.map((t) => (
            <li
              key={t.date + t.event}
              className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4"
            >
              <p className="font-mono text-xs text-[var(--accent)]">{t.date}</p>
              <p className="mt-1 text-[var(--ink-soft)]">{t.event}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-10 max-w-2xl">
        <h2 className="font-[family-name:var(--font-display)] text-xl">
          Cardholder notes
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-[var(--ink-soft)]">
          {info.cardholder_notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      </section>

      <section className="mt-10 max-w-2xl">
        <h2 className="font-[family-name:var(--font-display)] text-xl">
          Official links
        </h2>
        <ul className="mt-4 space-y-2">
          {info.official_links.map((l) => (
            <li key={l.url}>
              <a
                href={l.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent)] hover:underline"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
