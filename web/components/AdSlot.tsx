/**
 * Reserved display-ad slot. Renders nothing until NEXT_PUBLIC_ADSENSE_CLIENT is set.
 * Beneficiaries remain free; ads are the consumer-side monetization path from the BP.
 */
export function AdSlot({ slot }: { slot?: string }) {
  const client = process.env.NEXT_PUBLIC_ADSENSE_CLIENT;
  if (!client) return null;

  return (
    <aside
      className="my-6 flex min-h-[90px] items-center justify-center rounded-lg border border-dashed border-[var(--line)] bg-[var(--surface)] text-xs text-[var(--muted)]"
      data-ad-slot={slot ?? "reserved"}
      aria-label="Advertisement"
    >
      {/* Wire AdSense script in layout when client id is configured */}
      Ad placement reserved
    </aside>
  );
}
