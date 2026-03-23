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
- [ ] **AI-powered client intake** — dynamic questionnaires that adapt by visa type and status
- [ ] **Multi-language intake forms** — clients fill out in their language, attorney sees English
- [ ] **Document collection portal** — clients upload docs via secure link, AI validates completeness
- [ ] **AI document scanning & OCR** — scan physical documents, passports, I-94s, approval notices
- [ ] **Photo/document quality checker** — rejects blurry scans, wrong formats before submission
- [ ] **Smart form auto-population** — intake answers pre-fill USCIS/government forms automatically
- [ ] **Intake-to-case pipeline** — completed intake flows directly into case file, zero re-entry
- [ ] **Automatic family member profile creation** — intake data auto-creates linked profiles for spouse, children, parents with relationship mapping
- [ ] **Conditional logic questionnaires** — questions adapt based on previous answers, visa type, and immigration status

**Case Management**
- [ ] Case dashboard — all cases, statuses, next actions in one view
- [ ] Document management (organize, tag, version control per case)
- [ ] Case notes and internal memos
- [ ] Case timeline/history view
- [ ] **RFE tracking and response tools** — track RFE deadlines, draft responses with AI assistance
- [ ] **AI RFE response builder** — ML-powered: summarize RFE notice, match evidence, draft response with citations
- [ ] **Form auto-fill engine** — enter client data once, populate across all required forms (I-130, I-485, I-765, I-131, etc.)
- [ ] **Bi-directional form sync** — change data in a form, it updates the client profile; change the profile, all forms update automatically
- [ ] **Auto-fill empty fields with N/A** — per USCIS guidelines, auto-populate blank fields to prevent rejection
- [ ] **350+ government forms library** — always-updated, pre-formatted immigration forms (SLA: updated within 1 hour of official USCIS release)
- [ ] **Batch form generation** — family-based cases generate all related forms at once
- [ ] **Real-time collaborative form editing** — attorney and client simultaneously edit the same form with live chat (LollyForms-killer)
- [ ] **H-1B electronic registration module** — dedicated workflow for H-1B lottery registration and selection tracking
- [ ] **SOC code selection engine** — AI analyzes job descriptions to recommend correct SOC codes for labor certifications
- [ ] **Petition completeness scoring** — 9+ factor algorithm evaluates petition readiness with visual report (fee, specialty occupation, LCA, qualifications, employer-employee relationship, etc.)
- [ ] **Exhibit list auto-structuring** — AI categorizes, renames, and orders all supporting documents for submission
- [ ] **Petition packet assembly** — combine all forms, support letters, exhibits, and cover letter into submission-ready packet (PDF or physical mail format)
- [ ] **Document Q&A** — upload an RFE, decision, or government notice and chat with it in natural language to extract facts and identify issues

**Deadline & Calendar Management**
- [x] **Automated deadline tracking** — every filing window, renewal, RFE deadline tracked automatically
- [x] **Smart calendar integration** — sync to Google Calendar, Outlook, Apple Calendar
- [x] **Deadline calculation engine** — auto-calculates deadlines from receipt dates, priority dates, filing requirements
- [x] **Team-wide deadline visibility** — paralegals, associates, and partners see all deadlines
- [x] **Escalation alerts** — deadlines approaching without action trigger escalating notifications

**Client Communication Automation**
- [ ] **Automated client status updates** — clients get progress notifications without attorney effort
- [ ] **Secure client portal** — clients check their own case status, upload docs, see next steps
- [ ] **Automated email/SMS sequences** — document reminders, appointment confirmations, status changes
- [ ] **AI-translated client messages** — attorney writes in English, client reads in their language (with disclaimer)
- [ ] **AI client chatbot** — instant answers to common client questions (case status, next steps, document requirements) without attorney effort
- [ ] **WhatsApp integration** — communicate with international clients during consular processing via WhatsApp

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
- [ ] **NVC (National Visa Center) status tracking** — document submission status, fee payment tracking for consular processing
- [ ] Policy change alerts — automated monitoring of Federal Register, USCIS announcements
- [ ] Court decision feed — relevant immigration law updates
- [ ] Filing fee calculator — auto-updated from agency fee schedules
- [ ] **Attorney gets notified BEFORE the client** — solve the #1 USCIS portal complaint

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

**AI Legal Research & Drafting** (Docketwise IQ-killer — our AI must be better)
- [ ] **AI-powered legal research** — search immigration case law, policy memos, AAO decisions, BIA precedent
- [ ] **AI draft generation** — cover letters, RFE responses, support letters, legal briefs, motions
- [ ] **AI case strategy engine** — "based on similar approved cases, here's the recommended approach and evidence list"
- [ ] **Precedent citation finder** — AI finds relevant approved petitions, AAO decisions, and circuit court rulings
- [ ] **AI brief writer** — generate first drafts of legal briefs for EOIR/BIA proceedings
- [ ] **AI petition drafting (full document)** — generate 20+ page petition letters with exhibits, appendix, and citations in minutes (Visalaw.ai Drafts-killer)
- [ ] **AI support letter generation** — auto-draft employer support letters, expert opinion letters from case data
- [ ] **Bulk letter generation** — produce multiple reference letters and expert opinion letters at once from templates
- [ ] **AI redrafting** — refine individual sections or regenerate entire drafts with targeted feedback
- [ ] **Policy change impact analyzer** — when a new policy memo drops, AI flags which active cases are affected

**CRM & Lead Management** (no competitor combines CRM + case management this well)
- [ ] **Website lead capture forms** — embeddable on attorney's own website, leads flow into pipeline
- [ ] **Multi-channel lead intake** — WhatsApp, Facebook Messenger, SMS, website chat, phone
- [ ] **AI lead scoring** — ranks potential clients by case viability, complexity, and fee potential
- [ ] **Consultation scheduler** — clients self-book paid consultations (Calendly-style, integrated)
- [ ] **Follow-up automation** — drip email/SMS sequences for leads who didn't convert
- [ ] **Referral tracking** — track which clients came from which referral source, measure ROI
- [ ] **Lead-to-client conversion pipeline** — visual Kanban board from inquiry → consultation → retained → active case

**Trust Accounting & Billing** (LollyLaw's #1 selling point — we must match it)
- [ ] **Built-in IOLTA trust accounting** — three-way reconciliation (bank, trust ledger, client ledgers)
- [ ] **Flat-fee billing with trust compliance** — auto-transfer from trust to operating when milestones hit
- [ ] **Payment plan management** — recurring billing with automatic trust compliance tracking
- [ ] **LawPay / Stripe Connect integration** — bar-compliant payment processing
- [ ] **Government filing fee tracking** — track USCIS fees paid vs attorney fees vs costs advanced
- [ ] **Time tracking** — start/stop timers on case activities, auto-capture time in forms/portals
- [ ] **Billable vs non-billable categorization** — distinguish between billable work and admin overhead
- [ ] **Invoice generation** — create professional invoices from time entries and flat fees
- [ ] **Milestone billing** — bill by case phase (filing, RFE response, approval), not just hourly or flat
- [ ] **QR code invoice payments** — clients scan and pay instantly from their phone
- [ ] **Retainer management** — track retainer balances, auto-notify when running low
- [ ] **Financial dashboards** — revenue, outstanding AR, trust balances, monthly trends

**E-Filing & Government Portal Integration** (go beyond status checking — actually FILE from our platform)
- [ ] **Direct USCIS e-filing** — submit forms from our platform without switching to USCIS portal
- [ ] **DOL FLAG direct filing** — PERM labor certifications and LCA submissions from within the tool
- [ ] **DOS CEAC integration** — push DS-160/DS-260 data, pull consular appointment status
- [ ] **Auto-receipt capture** — when USCIS sends receipt numbers, auto-extract and file to case
- [ ] **E-filing status tracking** — track submission status, acceptance/rejection, with auto-retry on failures
- [ ] **EOIR ECAS e-filing** — file immigration court documents directly (PDF auto-formatted to 300 DPI requirements)

**Team Management & Firm Operations** (INSZoom's enterprise advantage — we take it)
- [ ] **Role-based access control** — attorney, paralegal, legal assistant, admin, partner permission levels
- [ ] **Task assignment and tracking** — assign tasks to team members with deadlines and priorities
- [ ] **Workload balancing dashboard** — visualize who's overloaded, redistribute cases intelligently
- [ ] **Paralegal workflow queues** — structured task lists by role and priority
- [ ] **Firm-wide case visibility** — partners see everything, associates see their cases, paralegals see assigned tasks
- [ ] **Activity audit log** — track who did what, when, for compliance and accountability
- [ ] **Multi-office support** — firms with multiple locations can manage across offices
- [ ] **Immigration budgeting & planning tools** — help firms forecast immigration spend, case volume, and staffing needs

**Conflict Check & Ethics Compliance** (legally required — no serious platform skips this)
- [ ] **Automated conflict of interest checking** — cross-reference new clients against all existing and past cases
- [ ] **Adverse party detection** — flag when a new client's employer/sponsor appears as adverse in another case
- [ ] **Ethics wall management** — restrict access when conflicts exist, document the wall
- [ ] **Conflict check audit trail** — maintain records for bar compliance and malpractice insurance

**Case Intelligence & Prediction** (our AI moat — nobody does this well yet)
- [ ] **Family relationship mapping** — visualize petitioner, beneficiary, derivative beneficiaries, dependencies
- [ ] **Case dependency tracking** — "this I-485 can't file until this I-140 is approved"
- [ ] **Priority date forecasting** — AI predicts when priority dates will become current based on historical Visa Bulletin trends
- [ ] **Case outcome prediction** — "cases like this have X% approval rate at Y service center" (with disclaimers)
- [ ] **Filing strategy optimizer** — recommend service center, filing timing, premium processing decision
- [ ] **Processing time predictor** — "based on current trends, expect a decision in X weeks from Y service center"
- [ ] **Judge analytics for EOIR cases** — grant rates, common denial reasons, recommended preparation strategies
- [ ] **RFE predictor** — flag potential RFE triggers before filing based on case characteristics

**Template Library & Document Assembly** (saves hours per case)
- [ ] **Cover letter templates** — by visa type, pre-written and customizable with firm branding
- [ ] **RFE response templates** — organized by common RFE reasons (insufficient evidence, wage issues, specialty occupation, etc.)
- [ ] **Support letter templates** — employer letters, expert opinion letters, professor recommendation letters
- [ ] **Legal brief templates** — for EOIR master calendar, individual merits, motions to reopen/reconsider
- [ ] **Mail merge engine** — auto-merge client data into any Word/PDF template
- [ ] **Firm-specific template library** — attorneys save their own templates, share across the firm
- [ ] **G-28 auto-generation** — generate and track G-28 (Notice of Entry of Appearance) for every case

**Mobile App** (attorneys live on their phones)
- [ ] **Native iOS + Android app** — not just responsive web, a real app
- [ ] **Push notifications** — deadlines, case updates, new leads, client messages, government status changes
- [ ] **Mobile document scanning** — camera → OCR → AI classification → filed to correct case
- [ ] **Quick case status checks** — swipe through cases, see status at a glance
- [ ] **Mobile client communication** — respond to client messages on the go
- [ ] **Offline mode** — view case details and notes without internet, sync when connected

**Competitor Migration & Onboarding** (remove every barrier to switching)
- [ ] **One-click data migration** — import from Docketwise, INSZoom, LollyLaw, Clio, eImmigration
- [ ] **Smart CSV/Excel field mapping** — AI maps imported columns to our data model automatically
- [ ] **"Switch in a weekend" migration wizard** — guided step-by-step data import with validation
- [ ] **White-glove onboarding assistance** — free migration support for firms switching from competitors
- [ ] **Parallel run mode** — run both systems simultaneously during transition, compare outputs

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
- [ ] Country-specific visa requirement databases
- [ ] AI document analysis (OCR + validation)
- [ ] Application strength scoring algorithm
- [ ] Attorney-applicant matching algorithm
- [ ] **AI legal research engine** — immigration case law, policy memos, AAO/BIA decisions
- [ ] **AI document drafting engine** — cover letters, briefs, RFE responses, support letters
- [ ] **Case outcome prediction model** — approval probability by visa type, service center, case characteristics
- [ ] **Priority date forecasting model** — predict Visa Bulletin movement based on historical data
- [ ] **RFE risk assessment** — flag potential RFE triggers before filing
- [ ] **Processing time prediction** — estimate decision timeline by form type and service center
- [ ] **Policy change impact engine** — when new guidance drops, auto-flag affected active cases
- [ ] **Smart form auto-population engine** — single intake → populate all required government forms
- [ ] **Document classification AI** — auto-categorize uploaded documents by type (passport, I-94, pay stub, etc.)
- [ ] **170-language OCR extraction** — extract data from documents in any language (match Filevine's bar)
- [ ] **Conflict detection AI** — flag discrepancies between extracted document data and existing database records
- [ ] **Document Q&A engine** — upload RFEs, decisions, notices — chat with them in natural language
- [ ] **Translation engine** — client-facing content translation with legal disclaimers
- [ ] **Conflict of interest detection** — cross-reference new clients against existing case database

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
- [ ] Role-based access control (attorney, paralegal, admin, partner, applicant, employer)
- [ ] Applicant endpoints
- [ ] Attorney endpoints
- [ ] Attorney matching endpoints
- [ ] Messaging system (secure, encrypted, per-case threads)
- [ ] Payment processing integration (LawPay, Stripe Connect)
- [ ] Multi-language content delivery
- [ ] Trust accounting / IOLTA endpoints
- [ ] CRM / lead management endpoints
- [ ] Consultation scheduling endpoints
- [ ] AI legal research endpoints
- [ ] AI document drafting endpoints
- [ ] Government e-filing proxy endpoints (USCIS, DOL FLAG, EOIR ECAS)
- [ ] Conflict check endpoints
- [ ] Template library endpoints
- [ ] Time tracking endpoints
- [ ] Team management / task assignment endpoints
- [ ] Mobile push notification service
- [ ] Webhook system for real-time integrations
- [ ] Data migration / import endpoints (competitor platforms)
- [ ] Audit log system

### Competitive Benchmarks
Check these competitors quarterly and ensure we match or exceed:

**Attorney Case Management (PRIMARY competitors):**
- [ ] **Docketwise** — market leader for small/mid firms, Smart Forms, Docketwise IQ AI ($69-199/user/mo)
- [ ] **INSZoom (Mitratech)** — enterprise/corporate immigration, multi-country, RPA bot ($200-500+/user/mo)
- [ ] **LollyLaw** — 40+ workflows, trust accounting, real-time collaborative forms
- [ ] **eImmigration (Cerenade)** — 300+ multilingual forms, all-in-one, solo practitioner friendly ($55+/user/mo)
- [ ] **Imagility** — AI petition drafting, I-9/LCA/PAF compliance modules
- [ ] **CampLegal** — claims 80% case prep reduction, strong CRM/lead management
- [ ] **Bridge US** — immigration case management for attorneys

**General Legal Platforms (with immigration capabilities):**
- [ ] **Clio** — most widely used legal platform, immigration via Docketwise/PrimaFacie integration ($49+/user/mo)
- [ ] **MyCase** — direct USCIS/DOL/CEAC API integrations, immigration add-on powered by Docketwise

**AI-First Competitors (emerging threat):**
- [ ] **Visalaw.ai / Gen** — AILA partnership, GPT-4 powered legal research and drafting
- [ ] **LegistAI** — native AI architecture for legal research and document drafting
- [ ] **Drafty.ai** — automates document drafting based on firm preferences

**Employer Compliance:**
- [ ] **Envoy Global** — employer immigration management (valued at $1.4B)
- [ ] **LawLogix** — I-9/E-Verify compliance
- [ ] **Tracker Corp** — I-9 compliance
- [ ] **Fragomen** — global immigration services (enterprise)

**Consumer/Marketplace:**
- [ ] **Boundless** — consumer immigration (family/spouse visas)
- [ ] **Visabot/ImmiHelp** — consumer visa assistance

**Adjacent (Global Mobility / EOR):**
- [ ] **Deel** — global hiring + immigration ($1.3B revenue, different model but brand awareness threat)
- [ ] **Envoy Global** — employer-side immigration management

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

### Revenue Model
**Target: Global Powerhouse ($50M+ ARR)**

**Revenue Streams:**
- **Attorney SaaS subscriptions** — $79-199/user/month (Phase A, primary revenue driver)
- **Enterprise/corporate plans** — $200-500+/user/month for multi-office firms and corporate immigration depts
- **Marketplace referral fees** — percentage per matched case (Phase B, secondary revenue)
- **Employer compliance subscriptions** — $50-200/employee/year for compliance management
- **Premium AI features** — AI research, drafting, prediction as premium tier add-ons
- **Data migration services** — white-glove onboarding from competitors (one-time fee)

**What we do NOT do:**
- No escrow accounts — too much compliance overhead, not enough margin
- No holding client funds — use LawPay/Stripe Connect for bar-compliant payment processing
- No fixed pricing for attorneys — they set their own fees, we take a referral cut on marketplace matches
- No EOR/employer-of-record services — that's Deel's model, not ours

**Anti-disintermediation strategy:**
- The tool IS the moat — if an attorney's entire caseload lives here (forms, deadlines, client portal, documents), they won't take clients offline to save a referral fee
- Switching cost is high once data is in the system
- Value lock-in over financial lock-in

### Legal Safeguards
- [ ] Terms of Service — clearly state we are a technology platform
- [ ] Attorney Terms — separate agreement for attorney network participation
- [ ] Privacy Policy — GDPR compliant (handling international user data)
- [ ] No guaranteed outcomes — never promise approval rates or success
- [ ] No fixed pricing claims — attorneys set their own fees, we do not dictate
- [ ] No fee comparison claims — do not state "cheaper than" or "no $X fees"
- [ ] Dispute resolution process documented
- [ ] Platform liability disclaimers on all attorney matching
- [ ] Data handling compliant with destination country regulations

### Security & Compliance Certifications (Enterprise requirement)
- [ ] **SOC 2 Type II certification** — required for enterprise clients
- [ ] **ISO 27001 certification** — international security standard
- [ ] **GDPR compliance** — mandatory for EU user data
- [ ] **CCPA compliance** — mandatory for California user data
- [ ] **HIPAA compliance** — some immigration cases involve medical records
- [ ] **AES-256 encryption** — data at rest and in transit
- [ ] **Multi-factor authentication** — for all user roles
- [ ] **Zero-retention AI policy** — client data processed by AI is never stored or used for training
- [ ] **99.9% uptime SLA** — for enterprise clients
- [ ] **Penetration testing** — annual third-party security audits
