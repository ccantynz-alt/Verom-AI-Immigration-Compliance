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
- [ ] **Applicants** — Students, workers, spouses/families, investors seeking visas
- [ ] **Attorneys** — Licensed immigration lawyers who need workload automation (PRIMARY adoption target)
- [x] **Employers** — Companies managing workforce immigration compliance (current dashboard)

### Visa Categories to Support
- [ ] **Student visas** — F-1, J-1, Tier 4, Study Permits, subclass 500, etc.
- [ ] **Work visas** — H-1B, L-1, O-1, TN, Skilled Worker, EU Blue Card, etc.
- [ ] **Spouse/Family visas** — K-1, I-130, Partner visas, dependent visas
- [ ] **Permanent residency** — Green Cards, ILR, PR applications, EB categories
- [ ] **Investor/Entrepreneur visas** — E-2, EB-5, Innovator, Start-up visas
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
- [ ] Multi-language UI toggle (Mandarin, Spanish, Hindi, Arabic, French, Portuguese)
- [ ] Hero background image/illustration (immigration/global theme)
- [x] Pricing section — safe, no specific dollar amounts
- [x] Legal disclaimer: "Verom is a technology platform and does not provide legal advice"

#### Applicant Portal
- [ ] Role-based login (applicant vs attorney vs employer)
- [ ] Onboarding wizard — select visa type, destination country, personal details
- [ ] AI application assistant — guided step-by-step visa application
- [ ] Document upload with AI validation and red-flag detection
- [ ] Application strength scoring
- [ ] Attorney matching engine — by country, specialization, availability
- [ ] Secure messaging with matched attorney
- [ ] Real-time application status tracking
- [ ] Deadline tracking with smart reminders
- [ ] Embassy appointment scheduling help
- [ ] Post-approval checklist (travel, housing, enrollment/employment)
- [ ] Visa renewal reminders
- [ ] Multi-language applicant UI (labels, tooltips, instructions)
- [ ] All legal documents and case content remain in English

#### Attorney Portal — Phase A: Workload Automation Tools (BUILD FIRST)
These are the tools that get attorneys to sign up. They save time on *existing* caseload.
The pitch: "9 hours/week of manual admin work eliminated. $230K/year in recovered billable time."

**Onboarding & Profile**
- [ ] Attorney profile creation (jurisdiction, specializations, capacity)
- [ ] Verification system (bar number, credentials)
- [ ] Import existing caseload — bulk CSV/Excel upload of current cases and clients

**Client Intake Automation** (biggest pain point — firms spend days on intake)
- [ ] **AI-powered client intake** — dynamic questionnaires that adapt by visa type and status
- [ ] **Multi-language intake forms** — clients fill out in their language, attorney sees English
- [ ] **Document collection portal** — clients upload docs via secure link, AI validates completeness
- [ ] **AI document scanning & OCR** — scan physical documents, passports, I-94s, approval notices
- [ ] **Photo/document quality checker** — rejects blurry scans, wrong formats before submission
- [ ] **Smart form auto-population** — intake answers pre-fill USCIS/government forms automatically
- [ ] **Intake-to-case pipeline** — completed intake flows directly into case file, zero re-entry

**Case Management**
- [ ] Case dashboard — all cases, statuses, next actions in one view
- [ ] Document management (organize, tag, version control per case)
- [ ] Case notes and internal memos
- [ ] Case timeline/history view
- [ ] **RFE tracking and response tools** — track RFE deadlines, draft responses with AI assistance
- [ ] **Form auto-fill engine** — enter client data once, populate across all required forms (I-130, I-485, I-765, I-131, etc.)
- [ ] **350+ government forms library** — always-updated, pre-formatted immigration forms
- [ ] **Batch form generation** — family-based cases generate all related forms at once

**Deadline & Calendar Management**
- [ ] **Automated deadline tracking** — every filing window, renewal, RFE deadline tracked automatically
- [ ] **Smart calendar integration** — sync to Google Calendar, Outlook, Apple Calendar
- [ ] **Deadline calculation engine** — auto-calculates deadlines from receipt dates, priority dates, filing requirements
- [ ] **Team-wide deadline visibility** — paralegals, associates, and partners see all deadlines
- [ ] **Escalation alerts** — deadlines approaching without action trigger escalating notifications

**Client Communication Automation**
- [ ] **Automated client status updates** — clients get progress notifications without attorney effort
- [ ] **Secure client portal** — clients check their own case status, upload docs, see next steps
- [ ] **Automated email/SMS sequences** — document reminders, appointment confirmations, status changes
- [ ] **AI-translated client messages** — attorney writes in English, client reads in their language (with disclaimer)

**Government Portal Unification** (attorneys currently log into 5+ separate portals daily)
- [ ] **Single-dashboard government status** — USCIS, DOL, EOIR, SEVIS status in one place
- [ ] USCIS case status API — real-time petition status updates
- [ ] USCIS processing times feed — auto-updated processing windows
- [ ] Visa Bulletin feed — priority date tracking (EB, FB categories)
- [ ] SEVIS integration — student visa status verification
- [ ] DOL PERM/LCA case status — labor certification tracking
- [ ] EOIR/Immigration Court case tracking
- [ ] UK Home Office status tracking
- [ ] IRCC (Canada) application status feed
- [ ] DHA (Australia) VEVO integration
- [ ] Policy change alerts — automated monitoring of Federal Register, USCIS announcements
- [ ] Court decision feed — relevant immigration law updates
- [ ] Filing fee calculator — auto-updated from agency fee schedules
- [ ] **Attorney gets notified BEFORE the client** — solve the #1 USCIS portal complaint

**Integrations & Data Import/Export**
- [ ] **Excel/CSV import & export** — case lists, client data, deadline reports
- [ ] **Google Sheets integration** — live sync for firms that track in spreadsheets
- [ ] **Microsoft Office integration** — Word templates for cover letters, briefs, memos
- [ ] **Google Workspace integration** — Docs, Drive, Gmail
- [ ] **Outlook/Gmail email integration** — file emails to cases automatically
- [ ] **Cloud storage sync** — Dropbox, Google Drive, OneDrive, Box
- [ ] **E-signature integration** — DocuSign, Adobe Sign for G-28, retainer agreements
- [ ] **Accounting/billing integration** — QuickBooks, Xero, FreshBooks
- [ ] **Calendar sync** — Google Calendar, Outlook, iCal
- [ ] **Zapier/Make integration** — connect to 5000+ apps for custom workflows
- [ ] **API access** — firms with custom tools can integrate programmatically

**Analytics & Reporting**
- [ ] Success analytics (approval rates, processing times by case type)
- [ ] Caseload reports — volume, status breakdown, bottlenecks
- [ ] Revenue/billing reports
- [ ] Staff productivity metrics
- [ ] **Exportable reports** — PDF, Excel, CSV for partners and clients

**Physical Document Handling** (yes, paper is still very much alive)
- [ ] **Mobile scan-to-case** — photograph documents with phone, AI files them to correct case
- [ ] **USCIS notice scanner** — scan physical USCIS mail, auto-extract receipt numbers, dates, case types
- [ ] **Passport/ID scanner** — OCR extraction of biographical data from travel documents
- [ ] **Fax-to-digital pipeline** — receive faxes digitally, auto-file to cases (many courts still fax)
- [ ] **Physical mail tracking** — log expected USCIS mail, flag when 30-day delivery window passes

#### Attorney Portal — Phase B: Marketplace Layer (AFTER ADOPTION)
These features activate once attorneys trust the platform and opt in.

**Why we verify: a message to attorneys.**
Every verification step and safety check exists to protect everyone — attorneys included. Fraudulent actors posing as attorneys damage public trust in the entire immigration bar. Our verification process means that when an applicant finds you on Verom, they already trust the platform — which means they trust you. Verified attorneys get a trust badge, priority placement, and access to higher-quality pre-screened cases. The safer the marketplace, the better it works for legitimate practitioners.

**Marketplace Features**
- [ ] Client pipeline dashboard — browse and accept pre-screened cases
- [ ] Capacity controls — attorneys set how many new cases they can take
- [ ] Attorneys set their own fees (platform does NOT dictate pricing)
- [ ] Secure messaging with applicants
- [ ] Earnings dashboard
- [ ] Client reviews and ratings (verified outcomes only)

**Attorney Verification & Trust** (protects attorneys AND applicants)
- [ ] **Bar number verification** — automated lookup against state bar association databases (all US jurisdictions)
- [ ] **International credential verification** — SRA (UK), Law Society (Canada), MARA (Australia), etc.
- [ ] **Disciplinary record check** — cross-reference against bar disciplinary databases, flag suspensions/disbarments
- [ ] **Malpractice insurance verification** — require proof of active coverage
- [ ] **Identity verification** — government-issued ID + video verification for initial onboarding
- [ ] **Manual review for first cohort** — human review of all attorney applications during platform launch
- [ ] **Ongoing monitoring** — periodic re-verification of bar status and disciplinary records
- [ ] **Verified attorney trust badge** — visible to applicants, signals platform-vetted credentials
- [ ] **Fraud reporting mechanism** — attorneys and applicants can flag suspicious accounts for rapid review

**Escrow Payment System** (no one gets burned)
- [ ] **Platform-managed escrow** — applicant payments held by platform, never sent directly to attorney
- [ ] **Milestone-based release** — funds released at defined stages (e.g., intake complete → forms filed → receipt notice received → case resolved)
- [ ] **Milestone definitions per visa type** — each visa category has appropriate payment release triggers
- [ ] **Auto-refund on inactivity** — if attorney takes no action within agreed timeframe, funds automatically returned to applicant
- [ ] **Partial release option** — attorneys can receive partial payment at early milestones to cover filing fees and initial work
- [ ] **Filing proof requirements** — receipt numbers, USCIS confirmations, or equivalent proof required before milestone payment release
- [ ] **Payment processor integration** — Stripe Connect (or equivalent) for escrow, payouts, and compliance
- [ ] **Attorney payout dashboard** — clear view of held funds, released funds, pending milestones, and payout history
- [ ] **Applicant payment transparency** — applicants see exactly where their money is and what triggers release
- [ ] **Platform fee structure** — transparent transaction fee disclosed to both parties before engagement

**Fraud Detection & Monitoring**
- [ ] **Activity monitoring** — flag attorneys who collect cases but never update status or file
- [ ] **Filing verification** — automated USCIS receipt number validation against case status API
- [ ] **Complaint rate tracking** — attorneys with abnormal complaint patterns flagged for review
- [ ] **Behavioral anomaly detection** — AI flags unusual patterns (rapid case collection, no filings, template responses)
- [ ] **Attorney performance scoring** — internal score based on filing rates, response times, outcomes, and client feedback
- [ ] **Graduated consequences** — warning → payment hold → suspension → removal for policy violations
- [ ] **Cross-platform fraud check** — check for attorneys flagged on other legal platforms or consumer protection databases

**Applicant Protection**
- [ ] **Dispute resolution process** — structured mediation with platform support before escalation
- [ ] **Money-back protection window** — full refund available within defined period if no substantive work performed
- [ ] **Off-platform payment warnings** — clear messaging: "Never pay outside Verom. Payments outside the platform are not protected."
- [ ] **Attorney response time SLAs** — if attorney doesn't respond within X hours, applicant can reassign case
- [ ] **Case transfer mechanism** — if attorney is removed or unresponsive, applicant's case and documents transfer to a new attorney seamlessly
- [ ] **Outcome-verified reviews only** — reviews tied to actual case outcomes, preventing fake testimonials

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
- [ ] Visual polish — match landing page quality
- [ ] Consistent icon system (replace Unicode emoji with SVG or icon font)

#### AI/Compliance Engine
- [x] Rule-based compliance evaluator
- [x] Visa expiration monitoring
- [x] I-9 compliance tracking
- [x] LCA wage compliance
- [x] Work authorization gap detection
- [ ] Country-specific visa requirement databases
- [ ] AI document analysis (OCR + validation)
- [ ] Application strength scoring algorithm
- [ ] Attorney-applicant matching algorithm

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
- [ ] Authentication and authorization (JWT/OAuth)
- [ ] Role-based access control
- [ ] Applicant endpoints
- [ ] Attorney endpoints
- [ ] Attorney matching endpoints
- [ ] Messaging system
- [ ] Payment processing integration
- [ ] Multi-language content delivery

### Competitive Benchmarks
Check these competitors quarterly and ensure we match or exceed:
- [ ] **Envoy Global** — employer immigration management
- [ ] **LawLogix** — I-9/E-Verify compliance
- [ ] **Tracker Corp** — I-9 compliance
- [ ] **Fragomen** — global immigration services (enterprise)
- [ ] **Boundless** — consumer immigration (family/spouse visas)
- [ ] **Visabot/ImmiHelp** — consumer visa assistance
- [ ] **Bridge US** — immigration case management for attorneys

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
- [ ] Terms of Service — clearly state we are a technology platform
- [ ] Attorney Terms — separate agreement for attorney network participation
- [ ] Attorney Code of Conduct — platform-specific rules (response times, filing commitments, no off-platform payments)
- [ ] Privacy Policy — GDPR compliant (handling international user data)
- [ ] No guaranteed outcomes — never promise approval rates or success
- [ ] No fixed pricing claims — attorneys set their own fees, we do not dictate
- [ ] No fee comparison claims — do not state "cheaper than" or "no $X fees"
- [ ] Escrow Terms — clear terms governing payment holds, milestone releases, refund triggers, and dispute timelines
- [ ] Dispute resolution process documented
- [ ] Platform liability disclaimers on all attorney matching
- [ ] Data handling compliant with destination country regulations
- [ ] Anti-fraud policy — published policy on attorney verification, monitoring, and removal procedures
- [ ] Applicant protection policy — published refund, dispute, and case transfer rights
- [ ] Money transmission compliance — ensure escrow model complies with state/federal money transmitter regulations
- [ ] PCI DSS compliance — payment card data handled through certified processor (never stored on platform)
