# DepositDay (到账日)

Free, no-login EBT/SNAP deposit-date calculators and federal payment calendars.

**Not affiliated with SSA, USDA, or any government agency.**

## Develop

```bash
npm install
npm run dev
npm test
npm run build
```

Validate rule JSON from repo root:

```bash
python scripts/validate_rules.py
```

## Deploy (Vercel)

Root directory: `web`. Set env vars from `.env.example`.

## Red lines

No SSA proxy login, no credential vaults, no beneficiary fees, no balance scraping.
