# AI Immigration Compliance - CLAUDE.md

## Project Philosophy
- **Zero tolerance for broken experiences.** No 404s, no "coming soon", no placeholder pages. Every link works, every feature is complete, or it doesn't exist yet.
- **30-second rule.** First-time visitors decide in 30 seconds. The site must immediately demonstrate value and professionalism.
- **Fix it, don't ask.** If you encounter a bug, broken link, incomplete feature, or UX issue — fix it immediately. No asking for permission.
- **Outperform competitors.** Every feature must be better than what Envoy Global, LawLogix, Tracker Corp, and others offer. More features, cleaner UI, faster workflows.
- **Honest and straightforward.** No marketing fluff. Show real value immediately.
- **Legal protection first.** Never make claims about pricing, fees, outcomes, or guarantees that could expose the company to liability. We are a technology platform, not a law firm.

## Development Rules
- Never commit placeholder or stub content to user-facing pages
- Never leave broken routes or dead links
- Every UI component must be fully functional before shipping
- If a feature isn't ready, remove the link/reference entirely — don't show it
- Always test the full user flow before pushing
- Mobile-responsive is mandatory, not optional
- UI must be visually consistent across all pages — same design system, same level of polish
- No specific fee amounts, pricing promises, or outcome guarantees in marketing copy
- All legal content and attorney communications must be in English (destination country language)

## Tech Stack
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy
- **Frontend:** HTML5, CSS3, Vanilla JS (no framework yet)
- **Tests:** pytest
- **Deployment:** Vercel (serverless)

## Project Structure
```
src/immigration_compliance/
├── models/          # Pydantic data models
├── engine/          # Compliance rule engine
├── services/        # Business logic layer
└── api/             # FastAPI endpoints
frontend/
├── landing.html     # Public marketing landing page
├── index.html       # App dashboard (employer compliance)
├── css/
│   ├── landing.css  # Landing page styles
│   └── styles.css   # Dashboard design system
└── js/
    ├── api.js       # API client
    └── app.js       # Dashboard application logic
tests/               # Test suite
api/                 # Vercel serverless functions
```

---

## Product Roadmap & Checklist

### Platform Vision
Verom.ai is an **AI-powered immigration platform** that dramatically reduces attorney workload through automation — intake, document validation, status tracking, deadline management, and client communication. By making attorneys' lives easier first, we build trust and adoption, then layer on a marketplace connecting pre-screened applicants with attorneys who have capacity. It also provides employer-facing immigration compliance management.

### Go-To-Market Strategy
**Lead with tools, layer on the marketplace.**
- **Phase A — Attorney adoption:** Free/low-cost tools that save attorneys hours per week on existing caseload. The pitch: *"We're not adding to your pile — we're shrinking it."*
- **Phase B — Marketplace activation:** Once attorneys trust the platform, introduce opt-in pre-screened case matching with capacity controls ("I can take 3 new cases this month").
- **Phase C — Full ecosystem:** Applicants, attorneys, and employers all on one platform with AI powering every workflow.

**Marketing message:** Verom automates the 80% of immigration casework that isn't legal judgment — so attorneys can focus on the 20% that is.

### Target User Types
- [x] **Applicants** — Students, workers, spouses/families, investors seeking visas
- [x] **Attorneys** — Licensed immigration lawyers who need workload automation (PRIMARY adoption target)
- [x] **Employers** — Companies managing workforce immigration compliance (current dashboard)

### Visa Categories to Support
- [x] **Student visas** — F-1, J-1, Tier 4, Study Permits, subclass 500, etc.
- [x] **Work visas** — H-1B, L-1, O-1, TN, Skilled Worker, EU Blue Card, etc.
- [x] **Spouse/Family visas** — K-1, I-130, Partner visas, dependent visas
- [x] **Permanent residency** — Green Cards, ILR, PR applications, EB categories
- [x] **Investor/Entrepreneur visas** — E-2, EB-5, Innovator, Start-up visas
- [ ] **Asylum/Refugee** — Future consideration

### Immigration Corridors (Countries)
**Phase 1 — Launch:**
- [x] United States (F-1, H-1B, L-1, O-1, Green Card, etc.)
- [x] United Kingdom (Student visa, Skilled Worker, ILR)
- [x] Canada (Study Permits, PGWP, Express Entry)
- [x] Australia (subclass 500, 482, 189/190)
- [x] Germany (Student visa, EU Blue Card, Job Seeker)
- [x] New Zealand (Student visa, Skilled Migrant)

**Phase 2 — Expansion:**
- [ ] Ireland (Stamp 1/2, Critical Skills)
- [ ] France (Talent Passport, Student visa)
- [ ] Netherlands (Highly Skilled Migrant, Orientation Year)
- [ ] Japan (Engineer/Specialist, Student)
- [ ] Singapore (Employment Pass, S Pass)
- [ ] UAE (Golden Visa, Employment visa)

**Phase 3 — Full Global:**
- [ ] China (inbound work permits, student visas)
- [ ] South Korea, India, Brazil, South Africa, and more

### Core Features Checklist

#### Landing Page / Marketing Site
- [x] Professional hero section
- [x] Value proposition — clear, honest, no fluff
- [x] Applicant features section (AI assistant, attorney matching, tracking)
- [x] Attorney features section (client pipeline, pre-screened apps, tools)
- [x] How It Works flow (applicant + attorney)
- [x] Supported countries section
- [x] Footer with legal disclaimers
- [x] Mobile responsive
- [x] Multi-language UI toggle (Mandarin, Spanish, Hindi, Arabic, French, Portuguese)
- [x] Hero background image/illustration (immigration/global theme)
- [x] Pricing section — safe, no specific dollar amounts
- [x] Legal disclaimer: "Verom is a technology platform and does not provide legal advice"

#### Applicant Portal
- [x] Role-based login (applicant vs attorney vs employer)
- [x] Onboarding wizard — select visa type, destination country, personal details
- [x] AI application assistant — guided step-by-step visa application
- [x] Document upload with AI validation and red-flag detection
- [x] Application strength scoring
- [x] Attorney matching engine — by country, specialization, availability
- [x] Secure messaging with matched attorney
- [x] Real-time application status tracking
- [x] Deadline tracking with smart reminders
- [x] Embassy appointment scheduling help
- [x] Post-approval checklist (travel, housing, enrollment/employment)
- [x] Visa renewal reminders
- [x] Multi-language applicant UI (labels, tooltips, instructions)
- [x] All legal documents and case content remain in English

#### Attorney Portal — Phase A: Workload Automation Tools (BUILD FIRST)
These are the tools that get attorneys to sign up. They save time on *existing* caseload.
The pitch: "9 hours/week of manual admin work eliminated. $230K/year in recovered billable time."

**Onboarding & Profile**
- [x] Attorney profile creation (jurisdiction, specializations, capacity)
- [x] Verification system (bar number, credentials)
- [x] Import existing caseload — bulk CSV/Excel upload of current cases and clients

**Client Intake Automation** (biggest pain point — firms spend days on intake)
- [x] **AI-powered client intake** — dynamic questionnaires that adapt by visa type and status
- [x] **Multi-language intake forms** — clients fill out in their language, attorney sees English
- [x] **Document collection portal** — clients upload docs via secure link, AI validates completeness
- [x] **AI document scanning & OCR** — scan physical documents, passports, I-94s, approval notices
- [x] **Photo/document quality checker** — rejects blurry scans, wrong formats before submission
- [x] **Smart form auto-population** — intake answers pre-fill USCIS/government forms automatically
- [x] **Intake-to-case pipeline** — completed intake flows directly into case file, zero re-entry

**Case Management**
- [x] Case dashboard — all cases, statuses, next actions in one view
- [x] Document management (organize, tag, version control per case)
- [x] Case notes and internal memos
- [x] Case timeline/history view
- [x] **RFE tracking and response tools** — track RFE deadlines, draft responses with AI assistance
- [x] **Form auto-fill engine** — enter client data once, populate across all required forms (I-130, I-485, I-765, I-131, etc.)
- [x] **350+ government forms library** — always-updated, pre-formatted immigration forms
- [x] **Batch form generation** — family-based cases generate all related forms at once

**Deadline & Calendar Management**
- [x] **Automated deadline tracking** — every filing window, renewal, RFE deadline tracked automatically
- [x] **Smart calendar integration** — sync to Google Calendar, Outlook, Apple Calendar
- [x] **Deadline calculation engine** — auto-calculates deadlines from receipt dates, priority dates, filing requirements
- [x] **Team-wide deadline visibility** — paralegals, associates, and partners see all deadlines
- [x] **Escalation alerts** — deadlines approaching without action trigger escalating notifications

**Client Communication Automation**
- [x] **Automated client status updates** — clients get progress notifications without attorney effort
- [x] **Secure client portal** — clients check their own case status, upload docs, see next steps
- [x] **Automated email/SMS sequences** — document reminders, appointment confirmations, status changes
- [x] **AI-translated client messages** — attorney writes in English, client reads in their language (with disclaimer)

**Government Portal Unification** (attorneys currently log into 5+ separate portals daily)
- [x] **Single-dashboard government status** — USCIS, DOL, EOIR, SEVIS status in one place
- [x] USCIS case status API — real-time petition status updates
- [x] USCIS processing times feed — auto-updated processing windows
- [x] Visa Bulletin feed — priority date tracking (EB, FB categories)
- [x] SEVIS integration — student visa status verification
- [x] DOL PERM/LCA case status — labor certification tracking
- [x] EOIR/Immigration Court case tracking
- [x] UK Home Office status tracking
- [x] IRCC (Canada) application status feed
- [x] DHA (Australia) VEVO integration
- [x] Policy change alerts — automated monitoring of Federal Register, USCIS announcements
- [x] Court decision feed — relevant immigration law updates
- [x] Filing fee calculator — auto-updated from agency fee schedules
- [x] **Attorney gets notified BEFORE the client** — solve the #1 USCIS portal complaint

**Integrations & Data Import/Export**
- [x] **Excel/CSV import & export** — case lists, client data, deadline reports
- [x] **Google Sheets integration** — live sync for firms that track in spreadsheets
- [x] **Microsoft Office integration** — Word templates for cover letters, briefs, memos
- [x] **Google Workspace integration** — Docs, Drive, Gmail
- [x] **Outlook/Gmail email integration** — file emails to cases automatically
- [x] **Cloud storage sync** — Dropbox, Google Drive, OneDrive, Box
- [x] **E-signature integration** — DocuSign, Adobe Sign for G-28, retainer agreements
- [x] **Accounting/billing integration** — QuickBooks, Xero, FreshBooks
- [x] **Calendar sync** — Google Calendar, Outlook, iCal
- [x] **Zapier/Make integration** — connect to 5000+ apps for custom workflows
- [x] **API access** — firms with custom tools can integrate programmatically

**Analytics & Reporting**
- [x] Success analytics (approval rates, processing times by case type)
- [x] Caseload reports — volume, status breakdown, bottlenecks
- [x] Revenue/billing reports
- [x] Staff productivity metrics
- [x] **Exportable reports** — PDF, Excel, CSV for partners and clients

**Physical Document Handling** (yes, paper is still very much alive)
- [x] **Mobile scan-to-case** — photograph documents with phone, AI files them to correct case
- [x] **USCIS notice scanner** — scan physical USCIS mail, auto-extract receipt numbers, dates, case types
- [x] **Passport/ID scanner** — OCR extraction of biographical data from travel documents
- [x] **Fax-to-digital pipeline** — receive faxes digitally, auto-file to cases (many courts still fax)
- [x] **Physical mail tracking** — log expected USCIS mail, flag when 30-day delivery window passes

#### Attorney Portal — Phase B: Marketplace Layer (AFTER ADOPTION)
These features activate once attorneys trust the platform and opt in.

**Why we verify: a message to attorneys.**
Every verification step and safety check exists to protect everyone — attorneys included. Fraudulent actors posing as attorneys damage public trust in the entire immigration bar. Our verification process means that when an applicant finds you on Verom, they already trust the platform — which means they trust you. Verified attorneys get a trust badge, priority placement, and access to higher-quality pre-screened cases. The safer the marketplace, the better it works for legitimate practitioners.

**Marketplace Features**
- [x] Client pipeline dashboard — browse and accept pre-screened cases
- [x] Capacity controls — attorneys set how many new cases they can take
- [x] Attorneys set their own fees (platform does NOT dictate pricing)
- [x] Secure messaging with applicants
- [x] Earnings dashboard
- [x] Client reviews and ratings (verified outcomes only)

**Attorney Verification & Trust** (protects attorneys AND applicants)
- [x] **Bar number verification** — automated lookup against state bar association databases (all US jurisdictions)
- [x] **International credential verification** — SRA (UK), Law Society (Canada), MARA (Australia), etc.
- [x] **Disciplinary record check** — cross-reference against bar disciplinary databases, flag suspensions/disbarments
- [x] **Malpractice insurance verification** — require proof of active coverage
- [x] **Identity verification** — government-issued ID + video verification for initial onboarding
- [x] **Manual review for first cohort** — human review of all attorney applications during platform launch
- [x] **Ongoing monitoring** — periodic re-verification of bar status and disciplinary records
- [x] **Verified attorney trust badge** — visible to applicants, signals platform-vetted credentials
- [x] **Fraud reporting mechanism** — attorneys and applicants can flag suspicious accounts for rapid review

**Escrow Payment System** (no one gets burned)
- [x] **Platform-managed escrow** — applicant payments held by platform, never sent directly to attorney
- [x] **Milestone-based release** — funds released at defined stages (e.g., intake complete → forms filed → receipt notice received → case resolved)
- [x] **Milestone definitions per visa type** — each visa category has appropriate payment release triggers
- [x] **Auto-refund on inactivity** — if attorney takes no action within agreed timeframe, funds automatically returned to applicant
- [x] **Partial release option** — attorneys can receive partial payment at early milestones to cover filing fees and initial work
- [x] **Filing proof requirements** — receipt numbers, USCIS confirmations, or equivalent proof required before milestone payment release
- [x] **Payment processor integration** — Stripe Connect (or equivalent) for escrow, payouts, and compliance
- [x] **Attorney payout dashboard** — clear view of held funds, released funds, pending milestones, and payout history
- [x] **Applicant payment transparency** — applicants see exactly where their money is and what triggers release
- [x] **Platform fee structure** — transparent transaction fee disclosed to both parties before engagement

**Fraud Detection & Monitoring**
- [x] **Activity monitoring** — flag attorneys who collect cases but never update status or file
- [x] **Filing verification** — automated USCIS receipt number validation against case status API
- [x] **Complaint rate tracking** — attorneys with abnormal complaint patterns flagged for review
- [x] **Behavioral anomaly detection** — AI flags unusual patterns (rapid case collection, no filings, template responses)
- [x] **Attorney performance scoring** — internal score based on filing rates, response times, outcomes, and client feedback
- [x] **Graduated consequences** — warning → payment hold → suspension → removal for policy violations
- [x] **Cross-platform fraud check** — check for attorneys flagged on other legal platforms or consumer protection databases

**Applicant Protection**
- [x] **Dispute resolution process** — structured mediation with platform support before escalation
- [x] **Money-back protection window** — full refund available within defined period if no substantive work performed
- [x] **Off-platform payment warnings** — clear messaging: "Never pay outside Verom. Payments outside the platform are not protected."
- [x] **Attorney response time SLAs** — if attorney doesn't respond within X hours, applicant can reassign case
- [x] **Case transfer mechanism** — if attorney is removed or unresponsive, applicant's case and documents transfer to a new attorney seamlessly
- [x] **Outcome-verified reviews only** — reviews tied to actual case outcomes, preventing fake testimonials

#### Employer Compliance Dashboard (existing)
- [x] Employee management with visa tracking
- [x] Compliance checker (visa expiration, I-9, wage, work auth)
- [x] Real-time compliance metrics
- [x] Case tracker (petition pipeline)
- [x] Document management
- [x] ICE audit simulator
- [x] Public Access File (PAF) tracking
- [x] Regulatory intelligence (policy updates, processing times, visa bulletin)
- [x] Global immigration (multi-country permits, travel tracking)
- [x] HRIS integrations
- [x] Reports and analytics
- [x] Alerts center
- [x] Visual polish — match landing page quality
- [x] Consistent icon system (replace Unicode emoji with SVG or icon font)

#### AI/Compliance Engine
- [x] Rule-based compliance evaluator
- [x] Visa expiration monitoring
- [x] I-9 compliance tracking
- [x] LCA wage compliance
- [x] Work authorization gap detection
- [x] Country-specific visa requirement databases
- [x] AI document analysis (OCR + validation)
- [x] Application strength scoring algorithm
- [x] Attorney-applicant matching algorithm

#### Backend / API
- [x] FastAPI application
- [x] Employee CRUD
- [x] Compliance check endpoints
- [x] Case management endpoints
- [x] Document management endpoints
- [x] ICE audit simulation endpoint
- [x] PAF management endpoints
- [x] Regulatory intelligence endpoints
- [x] Global immigration endpoints
- [x] HRIS integration endpoints
- [x] Authentication and authorization (JWT/OAuth)
- [x] Role-based access control
- [x] Applicant endpoints
- [x] Attorney endpoints
- [x] Attorney matching endpoints
- [x] Messaging system
- [x] Payment processing integration
- [x] Multi-language content delivery

### Competitive Benchmarks
Check these competitors quarterly and ensure we match or exceed:
- [x] **Envoy Global** — employer immigration management (researched, features matched/exceeded)
- [x] **LawLogix** — I-9/E-Verify compliance (researched, E-Verify + bulk I-9 built)
- [x] **Tracker Corp** — I-9 compliance (researched, features matched/exceeded)
- [x] **Fragomen** — global immigration services (enterprise) (researched, multi-country built)
- [x] **Boundless** — consumer immigration (family/spouse visas) (researched, consumer portal built)
- [x] **Visabot/ImmiHelp** — consumer visa assistance (AI engine exceeds)
- [x] **Bridge US** — immigration case management for attorneys (researched, attorney portal exceeds)

### New Competitors Identified (March 2026 Research)
- [ ] **Casium** (AI2 Incubator, $5M seed 2025) — agentic AI for visa filings, scans public data (HIGH THREAT)
- [ ] **LegalBridge AI** (2026 ABA TECHSHOW) — AI case management, 70+ firms, 60% prep time reduction (HIGH THREAT)
- [ ] **US Immigration AI** (LA, 2025) — unified AI case solution for full-spectrum immigration
- [ ] **Deel Immigration** (formerly LegalPad) — employer visa services in 25+ countries bundled with payroll (HIGH THREAT — very sticky)
- [ ] **Alma** — O-1A/H-1B with flat-rate pricing, 99%+ approval rate

### Market Domination Features (Nobody Has Built These Yet)
These are the features that win the billion-dollar market. Build before anyone else.

**Tier 1 — Build Immediately (Competitive Moat)**
- [ ] **Agentic AI intake-to-filing pipeline** — autonomous multi-step workflows (intake → validate → populate forms → generate letters → flag issues → queue for review)
- [ ] **H-1B wage-weighted lottery simulator** — model selection probability under new March 2026 rules, cost-benefit analysis for employers
- [ ] **EAD gap risk manager** — track every EAD in workforce, calculate 180-day filing windows, auto-generate renewals (automatic extensions eliminated Oct 2025)
- [ ] **Pre-filing compliance scanner** — mirror USCIS's own AI analysis (PAiTH) to catch issues BEFORE filing (same-day RFEs are now a thing)
- [ ] **USCIS Case Status API integration** — real-time via developer.uscis.gov (API is live and available)

**Tier 2 — Build Next (Differentiation)**
- [ ] **Cross-country immigration strategy optimizer** — input employee profile, get ranked visa pathways across US/UK/Canada/Australia/Germany with timelines and costs
- [ ] **Social media compliance audit tool** — DS-160 now requires social media disclosure for H-1B/H-4 (Dec 2025 requirement)
- [ ] **Regulatory change impact engine** — when Federal Register notice publishes, AI identifies every active case affected
- [ ] **Immigration-aware compensation planning** — connect visa strategy to salary decisions ("Level 3 wage increases H-1B selection by X%")
- [ ] **Government data transparency dashboard** — crowdsourced processing times from platform users where government data is lacking

**Tier 3 — Build for Stickiness (Users Never Leave)**
- [ ] **Gamified compliance scoring** — firm-wide score (0-100), case completion streaks, certification badges
- [ ] **Attorney outcome analytics** — match based on historical approval rates, RFE response success, processing times per visa type
- [ ] **Community forum & peer network** — attorney case strategy discussions, regulatory updates
- [ ] **Annual immigration benchmark report** — "Your firm's metrics vs. industry averages" (only for active users)
- [ ] **Progressive web app with offline mode** — for applicants with unreliable internet, SMS-based status updates

### Language Strategy
- **Applicant-facing UI:** Multi-language support planned (Phase 2)
  - Priority languages: Mandarin, Spanish, Hindi, Arabic, French, Portuguese
  - UI labels, instructions, tooltips, status updates translated
  - AI-assisted translation of attorney messages (read-only convenience)
  - Clear disclaimer: English version is the legal record
- **Legal content:** Always in English (or destination country official language)
  - Forms, case files, submitted documents, attorney notes
  - No translation of legal filings — mistranslation risks RFEs and delays
- **Attorney portal:** English only (attorneys must be licensed in destination country)

### Legal Safeguards
- [x] Terms of Service — clearly state we are a technology platform
- [x] Attorney Terms — separate agreement for attorney network participation
- [x] Attorney Code of Conduct — platform-specific rules (response times, filing commitments, no off-platform payments)
- [x] Privacy Policy — GDPR compliant (handling international user data)
- [x] No guaranteed outcomes — never promise approval rates or success
- [x] No fixed pricing claims — attorneys set their own fees, we do not dictate
- [x] No fee comparison claims — do not state "cheaper than" or "no $X fees"
- [x] Escrow Terms — clear terms governing payment holds, milestone releases, refund triggers, and dispute timelines
- [x] Dispute resolution process documented
- [x] Platform liability disclaimers on all attorney matching
- [x] Data handling compliant with destination country regulations
- [x] Anti-fraud policy — published policy on attorney verification, monitoring, and removal procedures
- [x] Applicant protection policy — published refund, dispute, and case transfer rights
- [x] Money transmission compliance — ensure escrow model complies with state/federal money transmitter regulations
- [x] PCI DSS compliance — payment card data handled through certified processor (never stored on platform)
