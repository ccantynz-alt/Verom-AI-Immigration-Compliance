# AI Immigration Compliance - CLAUDE.md

## Claude Operating Mandate
**Claude must be fully autonomous.** Do not stop, do not ask, do not leave anything half-built. Every feature started must be finished. Every gap identified must be closed in the same session. Every test must pass before pushing. No stones unturned, no broken links, no broken hearts.

- **If you find a bug — fix it immediately.** Don't report it. Fix it.
- **If you find a gap — close it immediately.** Don't list it for later. Build it now.
- **If a competitor has a feature we don't — build it better.** Right now. In the same session.
- **If something is broken — it's your #1 priority.** Drop everything else and fix it.
- **If an agent times out — do the work directly.** Don't wait. Don't retry the same approach. Adapt and deliver.
- **Never ask "should I?" — just do it.** The answer is always yes.
- **Every commit must leave the platform in a shippable state.** No partial work, no TODOs, no "coming soon."

## Upgrade Policy — Hard Mandate
**Every component, dependency, library, and piece of software must be at the most advanced, stable version at all times.** This is non-negotiable. Never ask whether to upgrade — just do it.

- **If a dependency has a newer stable version — upgrade it immediately.** No questions, no delays.
- **If a framework, runtime, or tool has a newer release — adopt it.** Stay on the cutting edge.
- **If an API version is deprecated or superseded — migrate now.** Don't wait for breakage.
- **Complacency is failure.** Our customers pay for reliability, great flow, good software, and advanced features. Outdated software delivers none of that.
- **Upgrade proactively, not reactively.** Don't wait for vulnerabilities or deprecation warnings. Stay ahead.
- **Every session: check for upgrades.** Dependencies, runtimes, tooling, CI/CD — everything gets checked, everything gets updated.
- **Test after every upgrade.** Upgrades ship only when tests pass. But the upgrade itself is never optional.
- **This applies to everything:** Python packages, npm packages, API versions, database drivers, deployment configs, CI/CD pipelines, linters, formatters, test frameworks — no exceptions.

## Competitive Dominance Rules
We are not trying to keep up with the competition. We are trying to be **50-70% ahead** of every competitor at all times.

- **Monitor competitors continuously.** Every session, check for new entrants, new features, new funding. Build counter-features before they ship.
- **International competitive crawling.** Track competitors across US, UK, Canada, Australia, EU markets. New immigration tech tools appearing anywhere in the world must be identified and countered.
- **Feature parity is failure.** If a competitor has Feature X, we need Feature X + 3 things they don't have.
- **Speed is the moat.** Ship faster than anyone. First to market with every feature that matters.
- **Architecture for domination.** Design systems, services, and APIs that can absorb any competitor's feature set within one development session.

## Competitive Intelligence Automation
- Crawl competitor websites, Product Hunt, TechCrunch, ABA TECHSHOW, AILA conferences for new immigration tech
- Track competitor GitHub repos, job postings, funding announcements for signal
- When a new competitor is identified: analyze their features, assess threat level, build counter-features, update threat matrix — all in one session
- Maintain the competitor intel service with real-time threat assessments
- Quarterly audit: every competitor checkbox in this file must have a corresponding service with tests

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
- [x] **AI-powered client intake** — dynamic questionnaires that adapt by visa type and status (12 visa types across US/UK/CA/AU/DE/NZ via IntakeEngineService)
- [x] **Multi-language intake forms** — clients fill out in their language, attorney sees English (TranslationService UI strings library covers 51 keys × 7 languages — English, Mandarin, Spanish, Hindi, Arabic, French, Portuguese; /api/translation/ui-strings/{lang} loads at page boot; legal record always remains English)
- [x] **Document collection portal** — clients upload docs via secure link, AI validates completeness (DocumentIntakeService + /intake/documents page: drag-drop upload, classification, quality + validation, real-time completeness vs the intake checklist, extracted-data conflict detection)
- [ ] **AI document scanning & OCR** — scan physical documents, passports, I-94s, approval notices
- [x] **Photo/document quality checker** — rejects blurry scans, wrong formats before submission (DocumentIntakeService quality stage: format/size/DPI/page-count gating with actionable recommendations)
- [x] **Smart form auto-population** — intake answers pre-fill USCIS/government forms automatically (FormPopulationService: 7-form schema registry covering G-28/I-129/I-130/I-485/I-765/I-131/DS-160 with field-level provenance — every value carries its source identifier and confidence; populate-bundle endpoint generates all forms for a visa type in one call)
- [x] **Intake-to-case pipeline** — completed intake flows directly into case file, zero re-entry (IntakeEngineService session → case)
- [x] **Automatic family member profile creation** — intake data auto-creates linked profiles for spouse, children, parents with relationship mapping (FamilyBundleService: 13 derivative-rule combinations covering H-1B/L-1/O-1/F-1/J-1/I-130/I-485 with derivative-visa mapping per relationship; auto-creates derivative workspace + derived intake session inheriting principal's address/employer/sponsor while clearing identity fields; surfaces age-cap warnings and CSPA flags)
- [x] **Conditional logic questionnaires** — questions adapt based on previous answers, visa type, and immigration status (rules-based engine with eligibility validation, document conditional inclusion, and red-flag detection)

**Case Management**
- [x] Case dashboard — all cases, statuses, next actions in one view (CaseWorkspaceService + /case page: unified system of record aggregating intake, documents, forms, attorney match, conflict checks, RFE risk, deadlines, notes, timeline; single `/api/case-workspaces/{id}/snapshot` returns the full state)
- [x] Document management (organize, tag, version control per case) (DocumentManagementService: 11-folder taxonomy (Identity, Sponsor, Education, Financial, Civil, Medical, Background, Evidentiary, Supporting, Internal, Correspondence); per-entry version stack with pinning; tag index for cross-folder lookup; comments with internal/client_visible visibility; share links with role + expiry; full activity log per entry covering view/download/tag/comment/share events; archive/restore; built on top of DocumentIntakeService)
- [x] Case notes and internal memos (CaseWorkspaceService.add_note with internal/client_visible visibility)
- [x] Case timeline/history view (CaseWorkspaceService timeline records 17 event kinds — case_created, intake_started/completed, document_uploaded, forms_populated, attorney_assigned, conflict_check_run, rfe_risk_assessed, case_filed, rfe_received/responded, decision_received, deadline_added, note_added, status_changed, milestone_reached)
- [x] **RFE tracking and response tools** — track RFE deadlines, draft responses with AI assistance (CaseWorkspaceService.add_rfe_response_deadline auto-computes 87-day response window; RFEResponseService produces full structured drafts in seconds)
- [x] **AI RFE response builder** — ML-powered: summarize RFE notice, match evidence, draft response with citations (RFEResponseService: 11-category rules-based classifier with regex pattern matching detects multiple discrete issues from a single RFE notice; per-category response templates with [VERIFIED]/[PENDING_VERIFICATION]/[CITATION_NEEDED] markers; matches uploaded exhibits to each issue type; auto-computes 87-day response deadline; renders text + review formats; same anti-hallucination discipline as the petition letter generator)
- [x] **Form auto-fill engine** — enter client data once, populate across all required forms (I-130, I-485, I-765, I-131, etc.) (FormPopulationService.populate_bundle)
- [x] **Bi-directional form sync** — change data in a form, it updates the client profile; change the profile, all forms update automatically (PATCH /api/forms/records/{id}/fields with provenance log + manual_overridden flag; re-running populate from a session re-pulls latest source values)
- [x] **Auto-fill empty fields with N/A** — per USCIS guidelines, auto-populate blank fields to prevent rejection (empty_field_default in FormPopulationService.populate)
- [ ] **350+ government forms library** — always-updated, pre-formatted immigration forms (SLA: updated within 1 hour of official USCIS release)
- [x] **Batch form generation** — family-based cases generate all related forms at once (FamilyBundleService.list_required_forms_for_bundle aggregates principal + derivative + EAD + Advance Parole forms across the family; FormPopulationService.populate_bundle generates them per workspace)
- [ ] **Real-time collaborative form editing** — attorney and client simultaneously edit the same form with live chat (LollyForms-killer)
- [ ] **H-1B electronic registration module** — dedicated workflow for H-1B lottery registration and selection tracking
- [x] **SOC code selection engine** — AI analyzes job descriptions to recommend correct SOC codes for labor certifications (SocCodeService: 39-entry catalog covering high-volume immigration occupations across IT, engineering, management, business/finance, healthcare, sciences, education, architecture/design, sales/marketing, legal; rules-based scoring with title-match (40pts), duty-keyword (30pts), skill-keyword (20pts), and managerial/research preference bonuses; flags Schedule A occupations, H-1B prevalence, L-1A managerial fit, O-1 / EB-1B research eligibility per match)
- [x] **Petition completeness scoring** — 9+ factor algorithm evaluates petition readiness with visual report (fee, specialty occupation, LCA, qualifications, employer-employee relationship, etc.) (CompletenessScorerService: USCIS PAiTH-style factor analysis with per-petition factor sets covering H-1B (11 factors), O-1 (9), EB-1A (8), I-485 (11), I-130 (9); each factor scored 0-100, weighted to overall, with regulatory citations and per-factor remediation steps; surfaces blockers (score<50, weight≥10) and warnings; tier classification: ready / near_ready / needs_work / weak / blocking)
- [x] **Exhibit list auto-structuring** — AI categorizes, renames, and orders all supporting documents for submission (PacketAssemblyService.assemble: every uploaded document is auto-tagged with sequential exhibit letters A/B/C/… in the cover letter and TOC; categorization comes from DocumentIntakeService classification)
- [x] **Petition packet assembly** — combine all forms, support letters, exhibits, and cover letter into submission-ready packet (PDF or physical mail format) (PacketAssemblyService: hand-written PDF 1.4 generator (zero deps) producing real filing-ready PDFs with cover letter, table of contents, populated forms grouped by section, exhibit list, and exhibit tab pages; three output formats: pdf / text / manifest)
- [x] **Document Q&A** — upload an RFE, decision, or government notice and chat with it in natural language to extract facts and identify issues (DocumentQAService: classifies USCIS notices into 7 doc types — RFE, approval, denial, NOID, I-539, policy memo, generic; structured fact extraction (receipt numbers, dates, citations, forms, response windows); 9-intent Q&A engine with grounded answers — every reply carries text excerpts proving the source; same anti-hallucination discipline as the chatbot)

**Deadline & Calendar Management**
- [x] **Automated deadline tracking** — every filing window, renewal, RFE deadline tracked automatically (CaseWorkspaceService + auto_compute_deadlines_from_filing for I-129/I-130/I-485/I-765/I-131; add_rfe_response_deadline auto-sets 87-day window)
- [x] **Smart calendar integration** — sync to Google Calendar, Outlook, Apple Calendar (CalendarSyncService: RFC 5545 ICS feed per user/workspace with 1-day + 7-day VALARM reminders; opaque subscription tokens with rotate/revoke; OAuth connection registry for direct push to Google/Outlook with queued push log)
- [x] **Deadline calculation engine** — auto-calculates deadlines from receipt dates, priority dates, filing requirements (per-form windows in CaseWorkspaceService.auto_compute_deadlines_from_filing)
- [x] **Team-wide deadline visibility** — paralegals, associates, and partners see all deadlines
- [x] **Escalation alerts** — deadlines approaching without action trigger escalating notifications

**Client Communication Automation**
- [x] **Automated client status updates** — clients get progress notifications without attorney effort (CaseWorkspaceService timeline + chatbot status answers grounded in workspace state)
- [x] **Secure client portal** — clients check their own case status, upload docs, see next steps (/applicant + /case + /intake/documents pages, all auth-gated and snapshot-driven)
- [ ] **Automated email/SMS sequences** — document reminders, appointment confirmations, status changes
- [x] **AI-translated client messages** — attorney writes in English, client reads in their language (with disclaimer) (TranslationService.translate_attorney_to_client + translate_client_to_attorney with auto-attached disclaimer in target language; LLM provider boundary stable — drop in DeepL / Google Translate / Anthropic; English remains the legal record per language strategy)
- [x] **AI client chatbot** — instant answers to common client questions (case status, next steps, document requirements) without attorney effort (ClientChatbotService: 12-intent rules-based classifier; answers ONLY from real workspace state with `grounded_in` field references — no hallucination; auto-handoff to attorney for low-confidence questions; attorney takeover/release for direct conversation; conversation persistence per workspace)
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
- [x] **Calendar sync** — Google Calendar, Outlook, iCal (CalendarSyncService — see Deadline & Calendar Management)
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
- [x] **AI-powered legal research** — search immigration case law, policy memos, AAO decisions, BIA precedent (LegalResearchService: 26-authority hand-curated seed corpus across 9 authority types — statutes/regulations/policy manual/AAO/BIA precedent/circuit court/SCOTUS/policy memos/USCIS alerts; precedential weighting (SCOTUS=100, statute=90, circuit=80, BIA=70...); rules-based ranking with title (5/term)/holding (3/term)/citation (8/term)/tag (6/each) + recency boost; pluggable boundary so the corpus swaps for a vector index in production)
- [x] **AI draft generation** — cover letters, RFE responses, support letters, legal briefs, motions (PetitionLetterService + RFEResponseService + SupportLetterService + PacketAssemblyService cover letters cover the petition letter, RFE response, and support letter slots; legal briefs / motions still pending)
- [ ] **AI case strategy engine** — "based on similar approved cases, here's the recommended approach and evidence list"
- [x] **Precedent citation finder** — AI finds relevant approved petitions, AAO decisions, and circuit court rulings (LegalResearchService.find_citations_for_section pulls top citations from a draft paragraph; find_citations_for_issue retrieves authorities by issue tag — designed to be called from the petition letter and RFE response generators)
- [ ] **AI brief writer** — generate first drafts of legal briefs for EOIR/BIA proceedings
- [x] **AI petition drafting (full document)** — generate 20+ page petition letters with exhibits, appendix, and citations in minutes (Visalaw.ai Drafts-killer) (PetitionLetterService: 5 petition kinds — O-1A, EB-1A, EB-2-NIW, H-1B, L-1A — with section-by-section assembly: header, introduction, beneficiary background, legal standard with INA + CFR + AAO citations, criterion-by-criterion evidence (Kazarian framework), Dhanasar prongs (NIW), specialty-occupation analysis (H-1B), L-1A elements, conclusion; every legal reference tagged [VERIFIED]/[PENDING_VERIFICATION]/[CITATION_NEEDED] so attorney sees exactly what needs human review; insufficient evidence sections marked [INSUFFICIENT_EVIDENCE] and excluded by default with force_include override)
- [x] **AI support letter generation** — auto-draft employer support letters, expert opinion letters from case data (SupportLetterService: 7 letter kinds — employer_support, expert_opinion, peer_recommendation, reference_letter, membership_attestation, critical_role, professor_endorsement; templated section assembly with case-specific fact substitution from intake + extracted documents; same [VERIFIED]/[PENDING_VERIFICATION]/[CITATION_NEEDED] discipline as petition letter)
- [x] **Bulk letter generation** — produce multiple reference letters and expert opinion letters at once from templates (SupportLetterService.generate_bulk: single call generates a plan of letters, each with its own kind / author / criterion focus; per-criterion expert letters for O-1/EB-1A petitions; succeeded/failed totals returned)
- [ ] **AI redrafting** — refine individual sections or regenerate entire drafts with targeted feedback
- [x] **Policy change impact analyzer** — when a new policy memo drops, AI flags which active cases are affected (RegulatoryImpactService: structured predicate DSL with all_of/any_of/not compound logic over snapshot fields; analyze_event walks every active workspace, returns per-case evidence + draft client notification + attorney action; supports 8 event kinds and 4 severity levels)

**CRM & Lead Management** (no competitor combines CRM + case management this well)
- [x] **Website lead capture forms** — embeddable on attorney's own website, leads flow into pipeline (LeadManagementService.capture_lead — no-auth public endpoint accepts inbound leads from any source; auto-scores immediately)
- [x] **Multi-channel lead intake** — WhatsApp, Facebook Messenger, SMS, website chat, phone (12 source channels: website_form, whatsapp, facebook_messenger, sms, phone, email, referral, walkin, social_media, google_ads, directory_listing, other)
- [x] **AI lead scoring** — ranks potential clients by case viability, complexity, and fee potential (LeadManagementService.rescore_lead: 9-component scoring (visa viability, doc readiness, engagement, fee potential, urgency, referral quality, geographic fit, conflict-free, communication health) with explainable score_reasons and tier classification (hot/warm/qualified/cold))
- [x] **Consultation scheduler** — clients self-book paid consultations (Calendly-style, integrated) (ConsultationBookingService: per-attorney availability windows (weekly recurring), blackout date ranges, configurable slot duration (15/30/45/60/90 min) + buffer between slots, min-notice + max-advance limits; public booking links per attorney with custom slug; per-link consult type + duration + fee; double-booking prevention; payment URL flow for paid consults; auto-confirmation for free; auto-emit attorney notification on booking)
- [ ] **Follow-up automation** — drip email/SMS sequences for leads who didn't convert
- [x] **Referral tracking** — track which clients came from which referral source, measure ROI (LeadManagementService.register_referral_source + source_attribution: per-source lead counts, retained counts, conversion rates, average lead score; warm-referral leads automatically score higher)
- [x] **Lead-to-client conversion pipeline** — visual Kanban board from inquiry → consultation → retained → active case (LeadManagementService 9-stage pipeline: inquiry → contacted → consultation_scheduled → consulted → proposal_sent → retained → active_case (or declined/lost); per-stage timestamps + history; pipeline_summary returns funnel counts and conversion rates)

**Trust Accounting & Billing** (LollyLaw's #1 selling point — we must match it)
- [x] **Built-in IOLTA trust accounting** — three-way reconciliation (bank, trust ledger, client ledgers) (TrustAccountingService: bar-required IOLTA implementation with deposit / invoice_payment / refund / disbursement / interest / adjustment / transfer transaction kinds; per-client sub-ledgers with overdraft prevention; refund/disbursement/adjustment require explicit reason; three-way reconciliation flags BANK_MISMATCH, TRUST_LEDGER_MISMATCH, NEGATIVE_CLIENT_LEDGER; client statements with date-ranged transaction history)
- [ ] **Flat-fee billing with trust compliance** — auto-transfer from trust to operating when milestones hit
- [ ] **Payment plan management** — recurring billing with automatic trust compliance tracking
- [ ] **LawPay / Stripe Connect integration** — bar-compliant payment processing
- [ ] **Government filing fee tracking** — track USCIS fees paid vs attorney fees vs costs advanced
- [x] **Time tracking** — start/stop timers on case activities, auto-capture time in forms/portals (TimeTrackingService: live timer with one-active-per-attorney enforcement; auto-stops on new timer start; 21 activity types covering full immigration workflow; auto-log hooks for platform actions like form_drafting and rfe_response_drafting)
- [x] **Billable vs non-billable categorization** — distinguish between billable work and admin overhead (per-activity billable defaults plus per-entry billable_override; case_administration/internal_meeting/training default to non-billable; summaries surface billable_hours separately from total)
- [x] **Invoice generation** — create professional invoices from time entries and flat fees (TimeTrackingService.generate_invoice produces draft invoices filtered to billable entries with per-activity breakdown, subtotal, currency, and date range)
- [ ] **Milestone billing** — bill by case phase (filing, RFE response, approval), not just hourly or flat
- [ ] **QR code invoice payments** — clients scan and pay instantly from their phone
- [ ] **Retainer management** — track retainer balances, auto-notify when running low
- [ ] **Financial dashboards** — revenue, outstanding AR, trust balances, monthly trends

**E-Filing & Government Portal Integration** (go beyond status checking — actually FILE from our platform)
- [x] **Direct USCIS e-filing** — submit forms from our platform without switching to USCIS portal (EFilingProxyService — uscis portal supports 14 forms: I-129/I-130/I-485/I-765/I-131/I-140/I-360/I-539/I-589/I-601/I-751/N-400/N-600/G-28; pre-submission validation enforces signed + completeness)
- [x] **DOL FLAG direct filing** — PERM labor certifications and LCA submissions from within the tool (EFilingProxyService — dol_flag portal supports ETA-9089 (PERM) and ETA-9035 (LCA) with proper receipt number format `[A-Z]-\d{3}-\d{5}-\d{6}`)
- [x] **DOS CEAC integration** — push DS-160/DS-260 data, pull consular appointment status (EFilingProxyService — dos_ceac portal supports DS-160/DS-260/DS-117/DS-2019 with `AA\d{8}` receipt format)
- [x] **Auto-receipt capture** — when USCIS sends receipt numbers, auto-extract and file to case (EFilingProxyService.submit auto-links the returned receipt number to the case workspace via `_cases.record_filing` immediately after the portal accepts)
- [x] **E-filing status tracking** — track submission status, acceptance/rejection, with auto-retry on failures (7-state lifecycle: draft → validating → submitting → submitted/failed/rejected → acknowledged; events log per state transition with timestamps and messages)
- [x] **EOIR ECAS e-filing** — file immigration court documents directly (PDF auto-formatted to 300 DPI requirements) (EFilingProxyService — eoir_ecas portal supports EOIR-26/EOIR-29/EOIR-33/EOIR-42A/EOIR-42B/EOIR-28 with 9-digit receipt format)

**Team Management & Firm Operations** (INSZoom's enterprise advantage — we take it)
- [x] **Role-based access control** — attorney, paralegal, legal assistant, admin, partner permission levels (TeamManagementService: 6 built-in roles — admin, partner, attorney, paralegal, legal_assistant, observer — plus firm-defined custom roles; 32 atomic permissions covering case, document, form, time, billing, trust, communication, filing, drafting, conflict, firm admin, and tasks; has_permission(user_id, permission) for atomic checks; case visibility tiered all/assigned/own)
- [x] **Task assignment and tracking** — assign tasks to team members with deadlines and priorities (TeamManagementService.create_task / update_task: priority levels low/normal/high/urgent; statuses open/in_progress/completed/blocked/cancelled; assigned_to_member_id, workspace_id, due_date)
- [x] **Workload balancing dashboard** — visualize who's overloaded, redistribute cases intelligently (TeamManagementService.get_workload_for_member counts active cases + open tasks + urgent tasks; get_firm_workload aggregates across all members for redistribution decisions)
- [x] **Paralegal workflow queues** — structured task lists by role and priority (list_tasks filterable by assigned_to_member_id + status + workspace_id + firm_id; paralegal role gets case.view + case.update + document.view + document.upload + form.view + form.populate + time.log + task.update_own permissions)
- [x] **Firm-wide case visibility** — partners see everything, associates see their cases, paralegals see assigned tasks (filter_visible_cases enforces case_visibility per role: admin/partner = "all" within firm, attorney/paralegal/legal_assistant/observer = "assigned" only)
- [x] **Activity audit log** — track who did what, when, for compliance and accountability (PersistentStore.log + get_log: SQLite-backed append-only audit trail with namespace/actor/target/action filters; never updated, never deleted; survives process restarts; queryable via /api/audit-log/persistent and /api/audit-log/summary)
- [x] **Multi-office support** — firms with multiple locations can manage across offices (TeamManagementService.add_office + Member.office_id; offices carry name/address/state per location)
- [ ] **Immigration budgeting & planning tools** — help firms forecast immigration spend, case volume, and staffing needs

**Conflict Check & Ethics Compliance** (legally required — no serious platform skips this)
- [ ] **Automated conflict of interest checking** — cross-reference new clients against all existing and past cases
- [ ] **Adverse party detection** — flag when a new client's employer/sponsor appears as adverse in another case
- [ ] **Ethics wall management** — restrict access when conflicts exist, document the wall
- [ ] **Conflict check audit trail** — maintain records for bar compliance and malpractice insurance

**Case Intelligence & Prediction** (our AI moat — nobody does this well yet)
- [x] **Family relationship mapping** — visualize petitioner, beneficiary, derivative beneficiaries, dependencies (FamilyBundleService bundle structure: principal_workspace_id + members[] with relationship + derivative_workspace_id; get_bundle_for_workspace lookup goes both directions)
- [ ] **Case dependency tracking** — "this I-485 can't file until this I-140 is approved"
- [ ] **Priority date forecasting** — AI predicts when priority dates will become current based on historical Visa Bulletin trends
- [ ] **Case outcome prediction** — "cases like this have X% approval rate at Y service center" (with disclaimers)
- [ ] **Filing strategy optimizer** — recommend service center, filing timing, premium processing decision
- [ ] **Processing time predictor** — "based on current trends, expect a decision in X weeks from Y service center"
- [ ] **Judge analytics for EOIR cases** — grant rates, common denial reasons, recommended preparation strategies
- [ ] **RFE predictor** — flag potential RFE triggers before filing based on case characteristics

**Template Library & Document Assembly** (saves hours per case)
- [ ] **Cover letter templates** — by visa type, pre-written and customizable with firm branding
- [x] **RFE response templates** — organized by common RFE reasons (insufficient evidence, wage issues, specialty occupation, etc.) (RFEResponseService.CATEGORY_RULES — 11 templates covering specialty occupation, employer-employee relationship, degree mismatch, evidentiary criteria, I-864 deficiency, marriage bona fides, status violation, public charge, financial evidence, missing form fields, generic requests; each template substitutes case-specific facts at render time)
- [ ] **Support letter templates** — employer letters, expert opinion letters, professor recommendation letters
- [ ] **Legal brief templates** — for EOIR master calendar, individual merits, motions to reopen/reconsider
- [ ] **Mail merge engine** — auto-merge client data into any Word/PDF template
- [ ] **Firm-specific template library** — attorneys save their own templates, share across the firm
- [ ] **G-28 auto-generation** — generate and track G-28 (Notice of Entry of Appearance) for every case

**Mobile App** (attorneys live on their phones)
- [ ] **Native iOS + Android app** — not just responsive web, a real app
- [x] **Push notifications** — deadlines, case updates, new leads, client messages, government status changes (NotificationService — multi-channel: in_app + email + sms + push + webhook; 16 event types covering case lifecycle, documents, communication, regulatory, billing, compliance; per-user preferences override per-event-type defaults; production swap-in for real push provider via dispatcher boundary)
- [ ] **Mobile document scanning** — camera → OCR → AI classification → filed to correct case
- [ ] **Quick case status checks** — swipe through cases, see status at a glance
- [ ] **Mobile client communication** — respond to client messages on the go
- [ ] **Offline mode** — view case details and notes without internet, sync when connected

**Competitor Migration & Onboarding** (remove every barrier to switching)
- [x] **One-click data migration** — import from Docketwise, INSZoom, LollyLaw, Clio, eImmigration (MigrationImporterService: 5 competitor profiles with auto-detection from CSV header signatures; per-profile field maps + value transforms; idempotent re-runs via row hashing)
- [x] **Smart CSV/Excel field mapping** — AI maps imported columns to our data model automatically (data-driven field_map per profile + value_transforms; auto-detection picks the right profile when headers match the signature, no manual selection needed)
- [x] **"Switch in a weekend" migration wizard** — guided step-by-step data import with validation (preview / dry_run / import endpoints with row-by-row validation + duplicate detection + skipped reasons in the report)
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
- [x] AI document analysis (OCR + validation) — DocumentIntakeService: classify (24 doc types), extract structured fields, quality + validation + expiry checks, extracted-vs-intake conflict detection
- [x] Application strength scoring algorithm — IntakeEngineService.score_strength with explainable factor weights per visa type
- [x] Attorney-applicant matching algorithm — AttorneyMatchService: 7-component scoring (specialization/country/language/capacity/red-flag handling/response time/approval rate) with reason chain
- [x] **AI legal research engine** — immigration case law, policy memos, AAO/BIA decisions (LegalResearchService — see AI-powered legal research entry)
- [ ] **AI document drafting engine** — cover letters, briefs, RFE responses, support letters
- [ ] **Case outcome prediction model** — approval probability by visa type, service center, case characteristics
- [ ] **Priority date forecasting model** — predict Visa Bulletin movement based on historical data
- [x] **RFE risk assessment** — flag potential RFE triggers before filing (RFEPredictorService with hand-curated trigger library + post-mitigation risk reduction estimates)
- [ ] **Processing time prediction** — estimate decision timeline by form type and service center
- [x] **Policy change impact engine** — when new guidance drops, auto-flag affected active cases (RegulatoryImpactService — see Government Portal section)
- [x] **Smart form auto-population engine** — single intake → populate all required government forms (FormPopulationService — see Phase A workload tools)
- [x] **Document classification AI** — auto-categorize uploaded documents by type (passport, I-94, pay stub, etc.) — DocumentIntakeService classify stage covers 24 document types via declared-type override + filename heuristics; pluggable for Textract / Google DocAI / Azure Form Recognizer at the `_classify` and `_extract` boundaries
- [ ] **170-language OCR extraction** — extract data from documents in any language (match Filevine's bar)
- [x] **Conflict detection AI** — flag discrepancies between extracted document data and existing database records (DocumentIntakeService.reconcile_against_checklist surfaces NAME_MISMATCH and other extracted-vs-intake conflicts; runs every reconcile cycle on the document collection page)
- [x] **Document Q&A engine** — upload RFEs, decisions, notices — chat with them in natural language (DocumentQAService — see Document Q&A entry above)
- [x] **Translation engine** — client-facing content translation with legal disclaimers (TranslationService — see Multi-language intake forms + AI-translated client messages)
- [x] **Conflict of interest detection** — cross-reference new clients against existing case database (ConflictCheckService — Model Rule 1.7/1.9/1.10 coverage, adverse-party detection, ethics walls)

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
- [x] Role-based access control (attorney, paralegal, admin, partner, applicant, employer) (TeamManagementService — see RBAC entry above)
- [ ] Applicant endpoints
- [ ] Attorney endpoints
- [ ] Attorney matching endpoints
- [ ] Messaging system (secure, encrypted, per-case threads)
- [ ] Payment processing integration (LawPay, Stripe Connect)
- [ ] Multi-language content delivery
- [x] Trust accounting / IOLTA endpoints (15 endpoints under /api/trust-accounting/* covering accounts, client ledgers, transactions, bank balance posting, three-way reconciliation, and client statements)
- [x] CRM / lead management endpoints (15 endpoints under /api/leads/* covering capture (no-auth), pipeline-stages, sources, list/detail, stage transitions, touchpoints, rescoring, workspace linkage, referral sources, and analytics — pipeline summary + source attribution)
- [x] Consultation scheduling endpoints (20 endpoints under /api/consultation-booking/* covering availability, blackouts, booking links, public slot lookup, public booking, payment confirmation, complete/no-show/cancel lifecycle, and attorney calendar)
- [ ] AI legal research endpoints
- [ ] AI document drafting endpoints
- [x] Government e-filing proxy endpoints (USCIS, DOL FLAG, EOIR ECAS) (10 endpoints under /api/efiling/* covering portals catalog, form-to-portal lookup, submission lifecycle (create/validate/submit/acknowledge), and listing; pluggable submitter factory so real OAuth wiring drops in cleanly)
- [x] Conflict check endpoints (POST /api/conflict-check/check, ethics walls, audit log)
- [ ] Template library endpoints
- [x] Time tracking endpoints (15 endpoints under /api/time-tracking/* covering activity types, billing rate, timers (start/stop/active), entries (CRUD), workspace + attorney summaries, invoice generation + lookup)
- [x] Team management / task assignment endpoints (20+ endpoints under /api/team/* covering firms, members, custom roles, offices, tasks, workload aggregation; me/permissions returns the calling user's effective permission set)
- [x] Mobile push notification service (NotificationService.emit dispatches to push channel via pluggable dispatcher; default stub for dev/test)
- [x] Webhook system for real-time integrations (NotificationService outbound webhooks with HMAC-SHA256 signature in header; secrets rotateable per webhook; delivery log per webhook; subscribe to specific event types per firm)
- [ ] Data migration / import endpoints (competitor platforms)
- [x] Audit log system (PersistentStore — SQLite-backed; see Activity audit log entry)

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
- [x] **Casium** (AI2 Incubator, $5M seed 2025) — agentic AI for visa filings, scans public data (HIGH THREAT — countered with agentic pipeline + marketplace + multi-country)
- [x] **LegalBridge AI** (2026 ABA TECHSHOW) — AI case management, 70+ firms, 60% prep time reduction (HIGH THREAT — countered with benchmarked time-savings engine showing >60% reduction with methodology)
- [x] **US Immigration AI** (LA, 2025) — unified AI case solution for full-spectrum immigration (countered with deeper features + multi-country)
- [x] **Deel Immigration** (formerly LegalPad) — employer visa services in 25+ countries bundled with payroll (HIGH THREAT — countered with deep HRIS integration, Deel import tool, lifecycle events)
- [x] **Alma** — O-1A/H-1B with flat-rate pricing, 99%+ approval rate (countered with flat-rate pricing packages + milestone escrow)

### Market Domination Features (Nobody Has Built These Yet)
These are the features that win the billion-dollar market. Build before anyone else.

**Tier 1 — Build Immediately (Competitive Moat)**
- [x] **Agentic AI intake-to-filing pipeline** — autonomous multi-step workflows (intake → validate → populate forms → generate letters → flag issues → queue for review)
- [x] **H-1B wage-weighted lottery simulator** — model selection probability under new March 2026 rules, cost-benefit analysis for employers
- [x] **EAD gap risk manager** — track every EAD in workforce, calculate 180-day filing windows, auto-generate renewals (automatic extensions eliminated Oct 2025)
- [x] **Pre-filing compliance scanner** — mirror USCIS's own AI analysis (PAiTH) to catch issues BEFORE filing (same-day RFEs are now a thing)
- [x] **USCIS Case Status API integration** — real-time via developer.uscis.gov (production-ready client with caching, batch ops, subscriptions)

**Tier 2 — Build Next (Differentiation)**
- [x] **Cross-country immigration strategy optimizer** — input employee profile, get ranked visa pathways across US/UK/Canada/Australia/Germany with timelines and costs
- [x] **Social media compliance audit tool** — DS-160 now requires social media disclosure for H-1B/H-4 (Dec 2025 requirement)
- [x] **Regulatory change impact engine** — when Federal Register notice publishes, AI identifies every active case affected
- [x] **Immigration-aware compensation planning** — connect visa strategy to salary decisions ("Level 3 wage increases H-1B selection by X%")
- [x] **Government data transparency dashboard** — crowdsourced processing times from platform users where government data is lacking

**Tier 3 — Build for Stickiness (Users Never Leave)**
- [x] **Gamified compliance scoring** — firm-wide score (0-100), case completion streaks, certification badges
- [x] **Attorney outcome analytics** — match based on historical approval rates, RFE response success, processing times per visa type
- [x] **Community forum & peer network** — attorney case strategy discussions, regulatory updates
- [x] **Annual immigration benchmark report** — "Your firm's metrics vs. industry averages" (only for active users)
- [x] **Progressive web app with offline mode** — for applicants with unreliable internet, SMS-based status updates

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
