import Link from "next/link";
import { SITE } from "@/lib/site";

export function SiteFooter({
  updatedAt,
  citations,
}: {
  updatedAt?: string;
  citations?: { title: string; url: string }[];
}) {
  return (
    <footer className="mt-auto border-t border-[var(--line)] bg-[var(--surface-2)]">
      <div className="mx-auto max-w-5xl space-y-4 px-4 py-8 text-sm text-[var(--muted)]">
        <p className="max-w-3xl leading-relaxed text-[var(--ink-soft)]">
          {SITE.nonAffiliation}
        </p>
        <p>
          Beneficiaries never pay. We do not collect login credentials, full case
          numbers, SSNs, or card numbers. Calculations run in your browser.
        </p>
        {(updatedAt || SITE.editorName) && (
          <p>
            Editorial: <strong className="text-[var(--ink)]">{SITE.editorName}</strong>
            {updatedAt ? ` · Data updated ${updatedAt}` : null}
          </p>
        )}
        {citations && citations.length > 0 && (
          <div>
            <p className="mb-1 font-medium text-[var(--ink-soft)]">Sources</p>
            <ul className="list-inside list-disc space-y-1">
              {citations.map((c) => (
                <li key={c.url}>
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--accent)] underline-offset-2 hover:underline"
                  >
                    {c.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="flex flex-wrap gap-4 pt-2">
          <Link href="/disclaimer" className="hover:text-[var(--accent)]">
            Disclaimer
          </Link>
          <Link href="/privacy" className="hover:text-[var(--accent)]">
            Privacy
          </Link>
          <Link href="/about" className="hover:text-[var(--accent)]">
            About
          </Link>
          <a
            href={SITE.githubIssues}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-[var(--accent)]"
          >
            Report a correction
          </a>
        </div>
      </div>
    </footer>
  );
}
