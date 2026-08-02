export const SITE = {
  name: "DepositDay",
  nameCn: "到账日",
  tagline: "Know when benefits land — free tools, public rules, zero login.",
  description:
    "Free deposit-date calculators for state EBT/SNAP and federal benefit calendars. Not affiliated with SSA, USDA, or any government agency.",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "https://depositday.vercel.app",
  editorName: process.env.NEXT_PUBLIC_EDITOR_NAME ?? "DepositDay Editorial",
  correctionEmail: process.env.NEXT_PUBLIC_CORRECTION_EMAIL ?? "",
  githubIssues:
    process.env.NEXT_PUBLIC_GITHUB_ISSUES ??
    "https://github.com/bistuwangqiyuan/BenefitSyncAI/issues",
  nonAffiliation:
    "DepositDay is an independent information tool. It is not affiliated with, endorsed by, or sponsored by the U.S. Social Security Administration, USDA, any state human-services agency, Direct Express, or any other government entity.",
} as const;

export const NAV = [
  { href: "/", label: "EBT calculator" },
  { href: "/federal", label: "Federal calendar" },
  { href: "/direct-express", label: "Direct Express" },
  { href: "/api-docs", label: "Rules API" },
  { href: "/about", label: "About" },
] as const;
