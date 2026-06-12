# ExpireMate — PRD

## Vision
A hyperlocal community platform where verified neighbors give unexpired-but-soon-to-expire food, sealed OTC medicine, pet supplies, and cleaning items to others nearby for free — before they spoil. Built by a high school student. Funded entirely by a $2 one-time ID verification fee + optional donations. Tagline: "Save food. Save meds. Send me to college."

## User Personas
- **Giver** — has nearly-expiring items at home; wants them used, not trashed.
- **Receiver** — low-income family, college student, elderly on fixed income, or anyone who hates waste.
- **Donor** — believes in the mission; tips into the founder's college fund.
- **Founder (admin)** — high school student receiving donations, reviewing reports.

## Core Architecture
- **Stack**: FastAPI + MongoDB (motor) + React 19 + Tailwind + Shadcn UI
- **Auth**: JWT (24h access + 7d refresh) via httpOnly cookies + bearer token fallback
- **Payments**: Stripe Checkout (real, test key) — verify fee + donations
- **Storage**: Emergent object storage for item photos
- **Moderation**: Claude Sonnet 4.6 via EMERGENT_LLM_KEY (blocks Rx, alcohol, drugs, weapons)
- **Domain model**: users, items, payment_transactions, reports

## What's been implemented (Feb 2026)
- ✅ JWT auth, registration, login, logout, /me + email verification + password reset
- ✅ Real Resend email integration (key wired) — receipts, password reset, ZIP alerts, verify
- ✅ Items: post (photo + AI moderation + SHA-256 photo dedup), list/filter, detail, bump-to-top (24h cooldown)
- ✅ Claim flow: 4-digit code, owner confirms, state machine
- ✅ In-app chat between poster + claimer (PII phone scrub, 5s polling)
- ✅ Reports + admin moderation dashboard
- ✅ Real Stripe Identity verification (replaces $2 fee — actual ID document upload via Stripe-hosted page)
- ✅ Stripe donations ($3/$5/$10/custom) + checkout + status polling + tax-receipt PDFs
- ✅ Donation thermometer + donor leaderboard + Donor-of-the-month spotlight
- ✅ Image upload + public /api/files/{path} serve
- ✅ Admin dashboard: overview, reports, users (ban/unban), email outbox
- ✅ Auto-expire background task (FastAPI in-process, every 30min)
- ✅ Impact counter (items rescued total / this week / pounds saved) on homepage
- ✅ Streak badges on dashboard (first rescue, 5/25 saved, donor, verified)
- ✅ Share buttons (Twitter, SMS, copy link) on item detail
- ✅ Tip Jar after pickup confirm (instant donation prompt)
- ✅ ZIP code email alerts — subscribe to a ZIP, get notified when items appear
- ✅ Browser web push (VAPID-signed, service worker, opt-in from dashboard)
- ✅ Open Graph + Twitter Card meta tags
- ✅ Tests: 74/74 backend passing (34+22+18); frontend 100%

## P0 / next
- Real Stripe LIVE key (currently test) — user needs to swap when ready to receive real money
- Verify a sending domain in Resend so emails reach everyone (currently only the account owner gets delivery)
- Stripe Identity must be enabled on the live account (auto when KYC done)
- Custom domain + lock CORS to it (still allow_origins=*)

## P1
- ZIP radius search (haversine on geocoded lat/lon) + optional map view
- Perceptual photo hashing (pHash) for stronger dedup
- Split server.py (1135 lines) into routers
- Persist EMAIL_LOG to MongoDB for real audit trail
- Admin search/filter + bulk actions
- SMS fallback for users who don't enable browser push

## P2
- Mobile native app (React Native)
- Business accounts (grocery stores)
- Referral system / "Share to unlock $1 off verify"
- Multi-language

## Known limitations
- Cross-site cookies may not persist; bearer token fallback used
- Webhook signature handling is permissive; configure proper secret in prod
- Email sending is MOCKED — links logged to console + visible in /admin → Outbox
- PII scrub limited to US phone numbers
