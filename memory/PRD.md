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
- ✅ JWT auth: register / login / logout / me + password hashing
- ✅ Email verification + password reset (Resend MOCKED — dev_link returned + admin outbox)
- ✅ Items: post (multipart photo + AI moderation), list with filters, detail
- ✅ Claim flow: 4-digit claim code, owner-confirm endpoint, state machine
- ✅ In-app chat between poster + claimer (5s polling, PII phone scrub, thread closes on completion)
- ✅ Reports endpoint
- ✅ Stripe verify ($2) + donate ($3/$5/$10/custom) checkout + status polling + webhook
- ✅ Donation thermometer + donor leaderboard + per-user donations history + tax receipt PDF download
- ✅ Image upload + public /api/files/{path} serve
- ✅ Admin dashboard: overview, reports (with remove-item), users (ban/unban), email outbox
- ✅ Auto-expire background task (FastAPI in-process, every 30min)
- ✅ Frontend: 18 routes — Home, Browse, ItemDetail, Post, Dashboard, Donate, Verify, PaymentSuccess, Leaderboard, HowItWorks, Safety, Login, Register, Forgot/Reset/VerifyEmail, Admin
- ✅ Safety disclaimer + 18+ checkbox
- ✅ Mobile-responsive
- ✅ Tests: 56/56 passing (34 MVP regression + 22 iter-2 features)

## P0 (post-launch)
- Wire real Resend API for actual email sending (currently MOCKED)
- Real Persona / Stripe Identity for ID document upload
- Custom domain + production CORS lockdown

## P1
- Push notifications when a new item appears in your ZIP
- Admin search/filter on users + reports
- Bulk admin actions
- Email enumeration timing fix on forgot-password
- Split server.py into routers (auth/items/admin/payments/chat/donations)

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
