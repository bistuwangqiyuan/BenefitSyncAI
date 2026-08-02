import { SITE } from "@/lib/site";

export function Byline({ updatedAt }: { updatedAt: string }) {
  return (
    <p className="text-xs text-[var(--muted)]">
      By <span className="text-[var(--ink-soft)]">{SITE.editorName}</span>
      {" · "}
      Updated <time dateTime={updatedAt}>{updatedAt}</time>
      {" · "}
      Independent, non-government tool
    </p>
  );
}
