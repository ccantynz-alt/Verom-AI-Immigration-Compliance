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
Verom.ai is a **global immigration marketplace** connecting applicants (students, workers, families) with licensed immigration attorneys, powered by AI compliance tools. It also provides employer-facing immigration compliance management.

### Target User Types
- [ ] **Applicants** — Students, workers, spouses/families, investors seeking visas
- [ ] **Attorneys** — Licensed immigration lawyers seeking qualified client leads
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

#### Attorney Portal
- [ ] Attorney profile creation (jurisdiction, specializations, capacity)
- [ ] Verification system (bar number, credentials)
- [ ] Client pipeline dashboard — browse and accept cases
- [ ] Case management tools (documents, notes, status updates)
- [ ] Secure messaging with applicants
- [ ] Earnings dashboard
- [ ] Success analytics (approval rates, processing times)
- [ ] Deadline alerts and calendar integration
- [ ] Attorneys set their own fees (platform does NOT dictate pricing)
- [ ] **Government agency direct feeds and integrations:**
  - [ ] USCIS case status API — real-time petition status updates
  - [ ] USCIS processing times feed — auto-updated processing windows
  - [ ] Visa Bulletin feed — priority date tracking (EB, FB categories)
  - [ ] SEVIS integration — student visa status verification
  - [ ] DOL PERM/LCA case status — labor certification tracking
  - [ ] UK Home Office status tracking
  - [ ] IRCC (Canada) application status feed
  - [ ] DHA (Australia) VEVO integration
  - [ ] Policy change alerts — automated monitoring of Federal Register, USCIS announcements
  - [ ] Court decision feed — relevant immigration law updates
  - [ ] Filing fee calculator — auto-updated from agency fee schedules

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
- [ ] Privacy Policy — GDPR compliant (handling international user data)
- [ ] No guaranteed outcomes — never promise approval rates or success
- [ ] No fixed pricing claims — attorneys set their own fees, we do not dictate
- [ ] No fee comparison claims — do not state "cheaper than" or "no $X fees"
- [ ] Dispute resolution process documented
- [ ] Platform liability disclaimers on all attorney matching
- [ ] Data handling compliant with destination country regulations
