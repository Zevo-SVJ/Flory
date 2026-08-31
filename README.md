# Worth

**Is it actually worth it?**

Worth is a purchase-decision product. You paste something you're thinking about
buying; Worth investigates the price, reviews, trust, risks and alternatives,
and gives you a verdict — **Buy**, **Think twice** or **Skip** — with the
evidence behind it and the money you'd save or overspend.

Most shopping tools help you find products. Worth helps you decide whether the
one you're looking at is worth your money.

---

## ⚠️ What is real and what is not

Worth's research engine **is not built yet**. The full product experience is —
submit, progress, result, share — but the analysis behind it comes from a
clearly-labelled development fixture engine.

|                  |                                                                                                                                                                                                                                   |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ✅ **Real**      | Landing page, auth (email + Google OAuth), URL preservation through sign-up, onboarding, dashboard, analyze flow, result page, history, settings, screenshot upload to private storage, public share links, database schema + RLS |
| 🟡 **Fixture**   | Every score, verdict, price, signal, evidence line and alternative. Produced by `FixtureEngine`, flagged `is_fixture`, and surfaced to the user with a visible notice on every result                                             |
| ❌ **Not built** | Research engine, scraping, price history, review analysis, screenshot understanding, Stripe/billing, browser extension, notifications, analytics                                                                                  |

**Nothing mocked is presented to a user as real.** See `<FixtureNotice />`.

---

## Stack

- **Next.js 16** (App Router, `proxy.ts` — the convention that replaced
  `middleware.ts`)
- **React 19**, **TypeScript 5.9**
- **Tailwind CSS v4** (CSS-first `@theme`, no config file)
- **Supabase** — Postgres, Auth, Storage, via `@supabase/ssr`

Five runtime dependencies total. No UI kit, no animation library, no icon
package — see "Dependency policy" below.

---

## Getting started

```bash
npm install
cp .env.example .env.local   # fill in your Supabase values
npm run dev
```

The landing page works without any configuration. Accounts and analyses need
Supabase — the app shows a setup notice instead of crashing if it's missing.

### Scripts

| Command                   | What it does                                             |
| ------------------------- | -------------------------------------------------------- |
| `npm run dev`             | Development server                                       |
| `npm run build`           | Production build (succeeds without Supabase credentials) |
| `npm run typecheck`       | `tsc --noEmit`                                           |
| `npm run lint`            | ESLint                                                   |
| `npm run test:responsive` | Playwright: overflow + touch targets at 320–1280px       |

---

## Supabase setup

**1. Create a project** at supabase.com, then copy the URL and the publishable
(anon) key into `.env.local`.

**2. Run the migrations**, in order, from `supabase/migrations/`:

| File              | What it creates                                                  |
| ----------------- | ---------------------------------------------------------------- |
| `…_init.sql`      | `profiles`, `user_preferences`, `analyses` + indexes             |
| `…_rls.sql`       | Row Level Security, enabled **and forced**, per-command policies |
| `…_functions.sql` | `updated_at` triggers, sign-up trigger, `get_public_analysis()`  |
| `…_storage.sql`   | Private `analysis-uploads` bucket + ownership policies           |

Either paste them into the SQL editor in order, or `supabase db push` with the
CLI linked.

**3. Configure Auth → URL Configuration**

- Site URL: your deployment origin (`http://localhost:3000` locally)
- Redirect URLs: add `http://localhost:3000/**` and your production origin

**4. Enable Google OAuth**

- Google Cloud Console → Credentials → OAuth 2.0 Client ID (Web application)
- Authorised redirect URI: `https://<project-ref>.supabase.co/auth/v1/callback`
- Paste the client ID and secret into Supabase → Authentication → Providers →
  Google

**5. Email templates** (Authentication → Email Templates)

Point the confirmation and recovery links at the token-hash route:

```
{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email
{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=recovery&next=/reset-password
```

### Environment variables

| Variable                        | Required   | Notes                                                                                       |
| ------------------------------- | ---------- | ------------------------------------------------------------------------------------------- |
| `NEXT_PUBLIC_SUPABASE_URL`      | yes        | Project URL                                                                                 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | yes        | Publishable key. Public by design — RLS is the security boundary                            |
| `NEXT_PUBLIC_SITE_URL`          | production | Origin for OAuth redirects, canonicals, sitemap. Falls back to `VERCEL_URL`, then localhost |

There is deliberately **no service-role key**. Nothing in Worth needs to bypass
RLS, so the key that could is never introduced.

---

## Architecture

```
app/
  (marketing)/     landing, pricing        — static
  (auth)/          login, signup, forgot-password, reset-password
  (app)/           dashboard, analyze, analyze/[id], history, settings, onboarding
  auth/            callback, confirm, signout  — route handlers
  w/[slug]/        public shared verdict
components/  ui · worth · marketing · app · auth
lib/         supabase · auth · analysis · db · utils
supabase/migrations/
proxy.ts     session refresh + route gating
```

### The analysis boundary

The UI never contains research logic. One type flows through everything:

```
lib/analysis/types.ts      the Analysis contract
lib/analysis/service.ts    the only thing the UI calls
lib/analysis/engine/       AnalysisEngine interface + FixtureEngine
```

`<VerdictCard>` renders the landing page's example, a real result and a public
share page — all from the same `Analysis` type. **To ship real analysis:**
implement `AnalysisEngine` in `lib/analysis/engine/research.ts` and return it
from `getEngine()`. Nothing else changes.

### Security

- RLS **enabled and forced** on all three tables; separate policies per command
- **No anonymous policy on `analyses`.** Public shares go through
  `get_public_analysis()` — a `SECURITY DEFINER` function returning the verdict,
  money and signals only. The analysed URL, the screenshot path, the evidence
  sources and the owner are unreachable from a share link by construction
- All `SECURITY DEFINER` functions use `set search_path = ''` with fully
  qualified names and revoked public `EXECUTE`
- Storage bucket is private, scoped to `{user_id}/…` by policy
- `safeNext()` rejects protocol-relative and absolute redirect targets — no open
  redirect
- `getUser()` (which revalidates against the auth server), never `getSession()`,
  for anything gating access
- Sign-out is POST-only so a prefetch can't trigger it

### Design system

**Colour is a verdict.** The interface is ink on paper; chroma appears only
where Worth has an opinion — the verdict, the score, the money delta, a risk
signal. Buttons and navigation are never coloured.

Money is stored as **integer minor units** (`bigint`), never floats.

### Dependency policy

Declined deliberately: shadcn/ui and Radix (template aesthetics, four transitive
deps), framer-motion (~50 KB for effects CSS handles in 30 lines), lucide-react
(a few inline SVGs instead), zod (hand-written guards are clearer at this size —
add it when the engine introduces real payload parsing).

---

## Mobile

Mobile is the base layer; desktop is the enhancement. Verified by
`npm run test:responsive` at 320 / 375 / 390 / 430 / 768 / 1280 — horizontal
overflow and sub-44px touch targets are failing tests, not manual checks.

iPhone specifics: `viewport-fit=cover` with safe-area insets, `100dvh` rather
than `100vh`, 16px minimum input font size (below that iOS zooms on focus),
bottom tab bar in the app shell, and pinch-zoom left enabled.

---

## Pricing

Three paid plans, no permanent free tier, and **no prices yet** — they haven't
been decided, and inventing them would mislead early visitors. `lib/pricing.ts`
is the single source of truth; adding Stripe means adding `stripePriceId` there
plus a checkout route, with no page redesign.

## No fake social proof

Worth launches from zero. There are no invented user counts, testimonials,
ratings, press logos, savings claims or statistics anywhere in this codebase.
Every figure on the landing page is a labelled illustrative example.
