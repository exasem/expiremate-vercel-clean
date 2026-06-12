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
- ✅ JWT auth: register / login / logout / me + brute-force-light protection
- ✅ Items: post (multipart photo upload + AI moderation), list with filters, detail
- ✅ Claim flow: 4-digit claim code, owner-confirm endpoint, status state machine (active → claimed → completed)
- ✅ Reports endpoint
- ✅ Stripe verify ($2) + donate ($3/$5/$10/custom up to $1000) checkout + status polling + webhook
- ✅ Donation thermometer (live stats) + donor leaderboard
- ✅ Image upload + public file serve via /api/files/{path}
- ✅ Frontend: 13 routes — Home, Browse, ItemDetail, Post, Dashboard, Donate, Verify, PaymentSuccess, Leaderboard, HowItWorks, Safety, Login, Register
- ✅ Safety disclaimer + 18+ checkbox on signup
- ✅ Mobile-responsive sticky nav with hamburger
- ✅ Test report iteration_1: backend 34/34 pass; frontend 85% (post-fix: title + checkbox)

## P0 (post-launch)
- Auto-expire items 24h after expiration_date (cron / scheduled task)
- Email verification on signup (via Resend)
- In-app chat between poster + claimer (no PII exchange)
- Photo verification on the actual item against the claim code (anti-fraud)

## P1
- Real Persona / Stripe Identity integration for ID document upload (currently $2 fee is the safety gate; doc upload not enforced)
- Push notifications when a new item is posted in your ZIP
- Tax receipts for donors
- Admin dashboard for the founder to review reports

## P2
- Mobile native app (React Native)
- Business accounts (grocery stores donate)
- Referral system
- Multi-language

## Known limitations
- Cross-site cookies may not persist on some browsers; bearer token fallback used
- Webhook signature swallowed gracefully (returns ok:false on bad sig) — set up real webhook secret in prod
- claim_code uses random.randint — fine for MVP, swap to secrets.randbelow for prod
