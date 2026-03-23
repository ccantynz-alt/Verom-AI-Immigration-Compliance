(function() {
    'use strict';

    // =========================================================================
    // CONSTANTS
    // =========================================================================

    const STORAGE_KEY = 'verom_applicant';
    const SESSION_KEY = 'verom_session';

    const TYPE_LABELS = {
        student: 'Student Visa',
        work: 'Work Visa',
        family: 'Family / Spouse',
        pr: 'Permanent Residency',
        investor: 'Investor / Entrepreneur',
        other: 'Other'
    };

    const COUNTRY_LABELS = {
        US: 'United States',
        UK: 'United Kingdom',
        CA: 'Canada',
        AU: 'Australia',
        DE: 'Germany',
        NZ: 'New Zealand'
    };

    const ATTORNEYS = [
        { id: 'att-1', name: 'Sarah Kim', initials: 'SK', country: 'United States', specialization: 'Student & Work Visas', approvalRate: 96, years: 12, rating: 4.9 },
        { id: 'att-2', name: 'James Patel', initials: 'JP', country: 'United Kingdom', specialization: 'Skilled Worker & ILR', approvalRate: 94, years: 8, rating: 4.8 },
        { id: 'att-3', name: 'Maria Lopez', initials: 'ML', country: 'Canada', specialization: 'Express Entry & Study Permits', approvalRate: 97, years: 15, rating: 4.9 },
        { id: 'att-4', name: 'Daniel Weber', initials: 'DW', country: 'Germany', specialization: 'EU Blue Card & Student', approvalRate: 92, years: 10, rating: 4.7 }
    ];

    const DOCUMENT_TYPES = [
        'Passport',
        'Financial Evidence',
        'Acceptance Letter',
        'Academic Transcripts',
        'Language Test',
        'Police Clearance',
        'Medical Exam',
        'Photo'
    ];

    // Map document types to the required documents checklist labels
    const DOC_TYPE_TO_CHECKLIST = {
        'Passport': 'Passport (biographical page)',
        'Photo': 'Passport-size photograph',
        'Financial Evidence': 'Financial evidence (bank statements, sponsorship letter)',
        'Acceptance Letter': 'Acceptance letter / employment offer',
        'Academic Transcripts': 'Academic transcripts / diplomas',
        'Language Test': 'English language test results (IELTS, TOEFL)',
        'Police Clearance': 'Police clearance certificate',
        'Medical Exam': 'Medical examination results'
    };

    // =========================================================================
    // STATE MANAGEMENT
    // =========================================================================

    /** Returns default empty state structure */
    const defaultState = () => ({
        application: null,
        documents: [],
        consultations: [],
        messages: []
    });

    /** Load state from localStorage */
    const loadState = () => {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                const parsed = JSON.parse(raw);
                return Object.assign(defaultState(), parsed);
            }
        } catch (e) {
            // corrupted data — start fresh
        }
        return defaultState();
    };

    /** Save state to localStorage */
    const saveState = (state) => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    };

    let state = loadState();

    // =========================================================================
    // TOAST NOTIFICATIONS
    // =========================================================================

    let toastContainer = null;

    /**
     * Show a toast notification.
     * @param {string} message - The text to display
     * @param {'success'|'error'|'info'} type - Toast type
     */
    const showToast = (message, type = 'info') => {
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:10000;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
            document.body.appendChild(toastContainer);
        }

        const colors = {
            success: { bg: '#f0fdf4', border: '#22c55e', text: '#16a34a' },
            error: { bg: '#fef2f2', border: '#ef4444', text: '#dc2626' },
            info: { bg: '#eff6ff', border: '#3b82f6', text: '#2563eb' }
        };
        const c = colors[type] || colors.info;

        const toast = document.createElement('div');
        toast.style.cssText = `
            background: ${c.bg}; border: 1px solid ${c.border}; color: ${c.text};
            padding: 14px 20px; border-radius: 10px; font-size: 14px; font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.12); pointer-events: auto;
            animation: fadeIn 200ms ease; font-family: 'Inter', sans-serif;
            max-width: 360px;
        `;
        toast.textContent = message;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.transition = 'opacity 300ms ease, transform 300ms ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    };

    // =========================================================================
    // MODAL SYSTEM
    // =========================================================================

    let activeModal = null;

    /**
     * Show a modal dialog.
     * @param {string} title - Modal heading
     * @param {string} bodyHTML - HTML content for the body
     * @param {Array<{label: string, className: string, onClick: Function}>} actions - Button configs
     */
    const showModal = (title, bodyHTML, actions) => {
        closeModal();

        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed; inset: 0; background: rgba(0,0,0,0.4);
            z-index: 9000; display: flex; align-items: center; justify-content: center;
            animation: fadeIn 150ms ease;
        `;
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal();
        });

        const card = document.createElement('div');
        card.style.cssText = `
            background: #fff; border-radius: 16px; padding: 32px;
            max-width: 480px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            font-family: 'Inter', sans-serif;
        `;

        const h = document.createElement('h3');
        h.style.cssText = 'font-size: 18px; font-weight: 700; margin-bottom: 16px;';
        h.textContent = title;
        card.appendChild(h);

        const body = document.createElement('div');
        body.style.cssText = 'font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 24px;';
        body.innerHTML = bodyHTML;
        card.appendChild(body);

        const footer = document.createElement('div');
        footer.style.cssText = 'display: flex; gap: 12px; justify-content: flex-end;';

        actions.forEach((action) => {
            const btn = document.createElement('button');
            btn.className = 'btn ' + (action.className || '');
            btn.textContent = action.label;
            btn.style.cssText = 'font-family: inherit; cursor: pointer;';
            btn.addEventListener('click', () => {
                if (action.onClick) action.onClick();
            });
            footer.appendChild(btn);
        });

        card.appendChild(footer);
        overlay.appendChild(card);
        document.body.appendChild(overlay);
        activeModal = overlay;
    };

    /** Close the currently open modal */
    const closeModal = () => {
        if (activeModal) {
            activeModal.remove();
            activeModal = null;
        }
    };

    // =========================================================================
    // SESSION AWARENESS
    // =========================================================================

    const loadSession = () => {
        try {
            const raw = localStorage.getItem(SESSION_KEY);
            if (raw) return JSON.parse(raw);
        } catch (e) { /* ignore */ }
        return null;
    };

    const applySession = () => {
        const session = loadSession();
        const avatarEl = document.querySelector('.nav-right .avatar');
        if (session && session.name && avatarEl) {
            const parts = session.name.trim().split(/\s+/);
            const initials = parts.map(p => p[0]).join('').toUpperCase().slice(0, 2);
            avatarEl.textContent = initials;
        }
    };

    // =========================================================================
    // TAB NAVIGATION
    // =========================================================================

    const switchTab = (tabName) => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        const tab = document.querySelector(`.nav-tab[data-tab="${tabName}"]`);
        if (tab) tab.classList.add('active');

        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const page = document.getElementById('page-' + tabName);
        if (page) page.classList.add('active');

        // Refresh page-specific content
        if (tabName === 'dashboard') renderDashboard();
        if (tabName === 'documents') renderDocuments();
        if (tabName === 'messages') renderMessages();
        if (tabName === 'attorneys') renderAttorneyButtons();
    };

    const initTabs = () => {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });
    };

    // =========================================================================
    // WIZARD
    // =========================================================================

    let currentStep = 1;
    let wizardData = { type: '', country: '', firstName: '', lastName: '', dob: '', citizenship: '', email: '', notes: '' };

    const showStep = (step) => {
        currentStep = step;
        for (let i = 1; i <= 4; i++) {
            const el = document.getElementById('step' + i);
            if (el) el.style.display = i === step ? '' : 'none';
        }
        updateStepIndicators();
    };

    const updateStepIndicators = () => {
        const steps = document.querySelectorAll('.wizard-step');
        const connectors = document.querySelectorAll('.step-connector');

        steps.forEach((s, idx) => {
            const circle = s.querySelector('.step-circle');
            const label = s.querySelector('.step-label');
            circle.classList.remove('active', 'completed');
            label.classList.remove('active', 'completed');

            if (idx + 1 < currentStep) {
                circle.classList.add('completed');
                circle.innerHTML = '&#10003;';
                label.classList.add('completed');
            } else if (idx + 1 === currentStep) {
                circle.classList.add('active');
                circle.textContent = idx + 1;
                label.classList.add('active');
            } else {
                circle.textContent = idx + 1;
            }
        });

        connectors.forEach((c, idx) => {
            c.classList.toggle('completed', idx + 1 < currentStep);
        });
    };

    const initWizard = () => {
        // Step 1: Visa type selection
        document.querySelectorAll('#step1 .option-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('#step1 .option-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                wizardData.type = card.dataset.value;
                document.getElementById('step1Next').disabled = false;
            });
        });

        // Step 2: Country selection
        document.querySelectorAll('#step2 .option-card').forEach(card => {
            card.addEventListener('click', () => {
                document.querySelectorAll('#step2 .option-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                wizardData.country = card.dataset.value;
                document.getElementById('step2Next').disabled = false;
            });
        });

        // Step navigation buttons
        document.getElementById('step1Next').addEventListener('click', () => showStep(2));
        document.getElementById('step2Back').addEventListener('click', () => showStep(1));
        document.getElementById('step2Next').addEventListener('click', () => showStep(3));
        document.getElementById('step3Back').addEventListener('click', () => showStep(2));

        document.getElementById('step3Next').addEventListener('click', () => {
            // Gather form data
            wizardData.firstName = document.getElementById('appFirstName').value.trim();
            wizardData.lastName = document.getElementById('appLastName').value.trim();
            wizardData.dob = document.getElementById('appDOB').value;
            wizardData.citizenship = document.getElementById('appCitizenship').value.trim();
            wizardData.email = document.getElementById('appEmail').value.trim();
            wizardData.notes = document.getElementById('appNotes').value.trim();

            // Populate review
            document.getElementById('reviewType').textContent = TYPE_LABELS[wizardData.type] || wizardData.type;
            document.getElementById('reviewCountry').textContent = COUNTRY_LABELS[wizardData.country] || wizardData.country;
            document.getElementById('reviewName').textContent = (wizardData.firstName + ' ' + wizardData.lastName).trim() || '-';
            document.getElementById('reviewCitizenship').textContent = wizardData.citizenship || '-';

            showStep(4);
        });

        document.getElementById('step4Back').addEventListener('click', () => showStep(3));

        document.getElementById('step4Submit').addEventListener('click', () => {
            // Save application to state
            const now = new Date();
            state.application = {
                type: wizardData.type,
                typeLabel: TYPE_LABELS[wizardData.type] || wizardData.type,
                country: wizardData.country,
                countryLabel: COUNTRY_LABELS[wizardData.country] || wizardData.country,
                firstName: wizardData.firstName,
                lastName: wizardData.lastName,
                dob: wizardData.dob,
                citizenship: wizardData.citizenship,
                email: wizardData.email,
                notes: wizardData.notes,
                status: 'In Review',
                submittedAt: now.toISOString(),
                strengthScore: 45 // Base score: wizard completed, no docs yet
            };
            saveState(state);

            showToast('Application submitted successfully!', 'success');
            switchTab('dashboard');
        });
    };

    // =========================================================================
    // DASHBOARD
    // =========================================================================

    const calculateStrength = () => {
        if (!state.application) return 0;
        let score = 30; // Base: wizard completed

        // +5 for each personal detail filled
        if (state.application.firstName) score += 5;
        if (state.application.lastName) score += 5;
        if (state.application.dob) score += 5;
        if (state.application.citizenship) score += 5;
        if (state.application.email) score += 5;

        // +8 for each uploaded document (up to 40 max from docs)
        const docBonus = Math.min(state.documents.length * 8, 40);
        score += docBonus;

        // +5 for having a consultation
        if (state.consultations.length > 0) score += 5;

        return Math.min(score, 100);
    };

    const renderDashboard = () => {
        const page = document.getElementById('page-dashboard');
        if (!state.application) return;

        const app = state.application;
        const strength = calculateStrength();

        // Compute next deadline (30 days from submission)
        const submitted = new Date(app.submittedAt);
        const docDeadline = new Date(submitted);
        docDeadline.setDate(docDeadline.getDate() + 14);
        const reviewDeadline = new Date(submitted);
        reviewDeadline.setDate(reviewDeadline.getDate() + 28);
        const submitDeadline = new Date(submitted);
        submitDeadline.setDate(submitDeadline.getDate() + 42);

        const fmtDate = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const fmtSubmitDate = fmtDate(submitted);

        // Determine next upcoming deadline
        const now = new Date();
        let nextDeadline = submitDeadline;
        if (now < docDeadline) nextDeadline = docDeadline;
        else if (now < reviewDeadline) nextDeadline = reviewDeadline;

        // Determine strength class
        const strengthClass = strength >= 70 ? 'good' : 'warn';

        // Check which doc types have been uploaded
        const uploadedTypes = new Set(state.documents.map(d => d.type));

        // Checklist logic
        const hasPassport = uploadedTypes.has('Passport');
        const hasFinancial = uploadedTypes.has('Financial Evidence');
        const hasAcceptance = uploadedTypes.has('Acceptance Letter');
        const hasConsultation = state.consultations.length > 0;

        const checkIcon = '<span class="check">&#10003;</span>';
        const uncheckIcon = '<span class="uncheck">&#9675;</span>';

        const dashHTML = `
            <h1 style="font-size:28px;font-weight:800;margin-bottom:8px">My Application Dashboard</h1>
            <p style="color:var(--slate-500);margin-bottom:28px">Track your <strong>${app.typeLabel}</strong> application to <strong>${app.countryLabel}</strong>.</p>

            <div class="dashboard-grid">
                <div class="stat-card">
                    <div class="stat-label">Application Status</div>
                    <div class="stat-value" style="color:var(--blue-600);font-size:20px">${app.status}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Application Strength</div>
                    <div class="stat-value ${strengthClass}">${strength}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Next Deadline</div>
                    <div class="stat-value warn" style="font-size:20px">${fmtDate(nextDeadline)}</div>
                </div>
            </div>

            <div class="card">
                <div class="card-header"><h3>Application Checklist</h3></div>
                <div class="card-body">
                    <div class="checklist-item">${checkIcon}<span class="checklist-text">Personal information completed</span><span class="badge badge-green">Done</span></div>
                    <div class="checklist-item">${checkIcon}<span class="checklist-text">Visa type and destination selected</span><span class="badge badge-green">Done</span></div>
                    <div class="checklist-item">${checkIcon}<span class="checklist-text">AI compliance pre-check passed</span><span class="badge badge-green">Done</span></div>
                    <div class="checklist-item">${hasPassport ? checkIcon : uncheckIcon}<span class="checklist-text">Upload passport copy</span><span class="badge ${hasPassport ? 'badge-green' : 'badge-amber'}">${hasPassport ? 'Done' : 'Required'}</span></div>
                    <div class="checklist-item">${hasFinancial ? checkIcon : uncheckIcon}<span class="checklist-text">Upload financial evidence</span><span class="badge ${hasFinancial ? 'badge-green' : 'badge-amber'}">${hasFinancial ? 'Done' : 'Required'}</span></div>
                    <div class="checklist-item">${hasAcceptance ? checkIcon : uncheckIcon}<span class="checklist-text">Upload acceptance letter / employment offer</span><span class="badge ${hasAcceptance ? 'badge-green' : 'badge-amber'}">${hasAcceptance ? 'Done' : 'Required'}</span></div>
                    <div class="checklist-item">${hasConsultation ? checkIcon : uncheckIcon}<span class="checklist-text">Attorney review (optional)</span><span class="badge ${hasConsultation ? 'badge-green' : 'badge-blue'}">${hasConsultation ? 'Requested' : 'Optional'}</span></div>
                    <div class="checklist-item">${uncheckIcon}<span class="checklist-text">Final submission</span><span class="badge badge-amber">Pending</span></div>
                </div>
            </div>

            <div class="card">
                <div class="card-header"><h3>Timeline</h3></div>
                <div class="card-body">
                    <div class="checklist-item">${checkIcon}<span class="checklist-text"><strong>${fmtSubmitDate}</strong> &mdash; Application started</span></div>
                    <div class="checklist-item">${now > docDeadline ? checkIcon : uncheckIcon}<span class="checklist-text"><strong>${fmtDate(docDeadline)}</strong> &mdash; Documents due</span></div>
                    <div class="checklist-item">${uncheckIcon}<span class="checklist-text"><strong>${fmtDate(reviewDeadline)}</strong> &mdash; Attorney review deadline</span></div>
                    <div class="checklist-item">${uncheckIcon}<span class="checklist-text"><strong>${fmtDate(submitDeadline)}</strong> &mdash; Submission deadline</span></div>
                </div>
            </div>
        `;

        page.innerHTML = dashHTML;
    };

    // =========================================================================
    // ATTORNEYS
    // =========================================================================

    const renderAttorneyButtons = () => {
        const cards = document.querySelectorAll('.attorney-card');
        cards.forEach((card, idx) => {
            const attorney = ATTORNEYS[idx];
            if (!attorney) return;

            const btn = card.querySelector('.btn');
            if (!btn) return;

            const isRequested = state.consultations.some(c => c.attorneyId === attorney.id);

            if (isRequested) {
                btn.textContent = 'Consultation Requested';
                btn.disabled = true;
                btn.className = 'btn btn-sm';
                btn.style.cssText = 'width:100%;background:var(--green-50);color:var(--green-600);border:1px solid var(--green-500);cursor:default;';
            } else {
                btn.textContent = 'Request Consultation';
                btn.disabled = false;
                btn.className = 'btn btn-primary btn-sm';
                btn.style.cssText = 'width:100%;';
            }

            // Remove old listeners by replacing node
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);

            if (!isRequested) {
                newBtn.addEventListener('click', () => requestConsultation(attorney));
            }
        });
    };

    const requestConsultation = (attorney) => {
        showModal(
            'Request Consultation',
            `Request a consultation with <strong>${attorney.name}</strong>? They specialize in <strong>${attorney.specialization}</strong> in <strong>${attorney.country}</strong>.`,
            [
                { label: 'Cancel', className: 'btn-outline', onClick: closeModal },
                {
                    label: 'Confirm',
                    className: 'btn-primary',
                    onClick: () => {
                        state.consultations.push({
                            attorneyId: attorney.id,
                            attorneyName: attorney.name,
                            specialization: attorney.specialization,
                            country: attorney.country,
                            requestedAt: new Date().toISOString()
                        });
                        saveState(state);
                        closeModal();
                        showToast(`Consultation requested with ${attorney.name}!`, 'success');
                        renderAttorneyButtons();
                    }
                }
            ]
        );
    };

    // =========================================================================
    // DOCUMENTS
    // =========================================================================

    const renderDocuments = () => {
        const page = document.getElementById('page-documents');
        const uploadedTypes = new Set(state.documents.map(d => d.type));

        // Build required documents checklist
        const requiredDocs = [
            { type: 'Passport', label: 'Passport (biographical page)', required: true },
            { type: 'Photo', label: 'Passport-size photograph', required: true },
            { type: 'Financial Evidence', label: 'Financial evidence (bank statements, sponsorship letter)', required: true },
            { type: 'Acceptance Letter', label: 'Acceptance letter / employment offer', required: true },
            { type: 'Academic Transcripts', label: 'Academic transcripts / diplomas', required: false },
            { type: 'Language Test', label: 'English language test results (IELTS, TOEFL)', required: false },
            { type: 'Police Clearance', label: 'Police clearance certificate', required: false },
            { type: 'Medical Exam', label: 'Medical examination results', required: false }
        ];

        const checklistHTML = requiredDocs.map(doc => {
            const uploaded = uploadedTypes.has(doc.type);
            const icon = uploaded ? '<span class="check">&#10003;</span>' : '<span class="uncheck">&#9675;</span>';
            const badgeClass = uploaded ? 'badge-green' : (doc.required ? 'badge-amber' : 'badge-blue');
            const badgeText = uploaded ? 'Uploaded' : (doc.required ? 'Required' : 'Conditional');
            return `<div class="checklist-item">${icon}<span class="checklist-text">${doc.label}</span><span class="badge ${badgeClass}">${badgeText}</span></div>`;
        }).join('');

        // Build uploaded documents list
        let uploadedHTML = '';
        if (state.documents.length > 0) {
            uploadedHTML = `
                <div class="card">
                    <div class="card-header"><h3>Uploaded Documents</h3></div>
                    <div class="card-body">
                        ${state.documents.map((doc, idx) => {
                            const uploadDate = new Date(doc.uploadedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
                            return `
                                <div class="checklist-item" style="align-items:flex-start">
                                    <span class="check">&#128196;</span>
                                    <span class="checklist-text">
                                        <strong>${doc.name}</strong><br>
                                        <span style="font-size:12px;color:var(--slate-400)">${doc.type} &middot; Uploaded ${uploadDate}</span>
                                        ${doc.notes ? `<br><span style="font-size:12px;color:var(--slate-500)">${doc.notes}</span>` : ''}
                                    </span>
                                    <button class="btn btn-outline btn-sm doc-remove-btn" data-idx="${idx}" style="flex-shrink:0;padding:6px 12px;font-size:12px;color:var(--red-500);border-color:var(--red-500);">Remove</button>
                                </div>`;
                        }).join('')}
                    </div>
                </div>`;
        }

        page.innerHTML = `
            <h1 style="font-size:28px;font-weight:800;margin-bottom:8px">My Documents</h1>
            <p style="color:var(--slate-500);margin-bottom:28px">Upload and manage your visa application documents.</p>

            <div class="card">
                <div class="card-header">
                    <h3>Required Documents</h3>
                    <button class="btn btn-primary btn-sm" id="uploadDocBtn">+ Upload Document</button>
                </div>
                <div class="card-body">
                    ${checklistHTML}
                </div>
            </div>

            ${uploadedHTML}
        `;

        // Bind upload button
        document.getElementById('uploadDocBtn').addEventListener('click', showUploadModal);

        // Bind remove buttons
        page.querySelectorAll('.doc-remove-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const idx = parseInt(btn.dataset.idx, 10);
                state.documents.splice(idx, 1);
                saveState(state);
                showToast('Document removed.', 'info');
                renderDocuments();
            });
        });
    };

    const showUploadModal = () => {
        const optionsHTML = DOCUMENT_TYPES.map(t => `<option value="${t}">${t}</option>`).join('');

        showModal(
            'Upload Document',
            `
                <div style="margin-bottom:16px">
                    <label style="display:block;font-size:13px;font-weight:600;color:#334155;margin-bottom:6px">Document File</label>
                    <input type="file" id="modalFileInput" style="width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;font-family:inherit;background:#fff;">
                </div>
                <div style="margin-bottom:16px">
                    <label style="display:block;font-size:13px;font-weight:600;color:#334155;margin-bottom:6px">Document Type</label>
                    <select id="modalDocType" style="width:100%;padding:12px 16px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;font-family:inherit;background:#fff;color:#1e293b;">
                        ${optionsHTML}
                    </select>
                </div>
                <div>
                    <label style="display:block;font-size:13px;font-weight:600;color:#334155;margin-bottom:6px">Notes (optional)</label>
                    <textarea id="modalDocNotes" rows="2" style="width:100%;padding:12px 16px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px;font-family:inherit;resize:vertical;color:#1e293b;" placeholder="Any additional details..."></textarea>
                </div>
            `,
            [
                { label: 'Cancel', className: 'btn-outline', onClick: closeModal },
                {
                    label: 'Upload',
                    className: 'btn-primary',
                    onClick: () => {
                        const fileInput = document.getElementById('modalFileInput');
                        const docType = document.getElementById('modalDocType').value;
                        const notes = document.getElementById('modalDocNotes').value.trim();

                        if (!fileInput.files || fileInput.files.length === 0) {
                            showToast('Please select a file to upload.', 'error');
                            return;
                        }

                        const file = fileInput.files[0];
                        state.documents.push({
                            name: file.name,
                            type: docType,
                            notes: notes,
                            size: file.size,
                            uploadedAt: new Date().toISOString()
                        });
                        saveState(state);
                        closeModal();
                        showToast(`"${file.name}" uploaded successfully!`, 'success');
                        renderDocuments();
                    }
                }
            ]
        );
    };

    // =========================================================================
    // MESSAGES
    // =========================================================================

    const renderMessages = () => {
        const page = document.getElementById('page-messages');
        const hasConsultation = state.consultations.length > 0;

        if (!hasConsultation) {
            // Show empty state
            page.innerHTML = `
                <h1 style="font-size:28px;font-weight:800;margin-bottom:8px">Messages</h1>
                <p style="color:var(--slate-500);margin-bottom:28px">Communicate securely with your matched attorney.</p>
                <div class="card">
                    <div class="card-header"><h3>Conversation</h3></div>
                    <div class="card-body">
                        <div class="empty-state">
                            <span class="empty-icon">&#128172;</span>
                            <h3 style="font-size:18px;color:var(--slate-700);margin-bottom:8px">No messages yet</h3>
                            <p style="font-size:14px">Once you're matched with an attorney, your secure conversation will appear here.</p>
                            <button class="btn btn-primary btn-sm" style="margin-top:16px" id="msgFindAttorneyBtn">Find an Attorney</button>
                        </div>
                    </div>
                </div>
            `;
            const findBtn = document.getElementById('msgFindAttorneyBtn');
            if (findBtn) findBtn.addEventListener('click', () => switchTab('attorneys'));
            return;
        }

        // Show message interface
        const consultation = state.consultations[0];
        const attorney = ATTORNEYS.find(a => a.id === consultation.attorneyId) || { name: consultation.attorneyName, initials: consultation.attorneyName.split(' ').map(w => w[0]).join('') };

        const session = loadSession();
        const userName = (state.application ? (state.application.firstName + ' ' + state.application.lastName).trim() : '') || (session ? session.name : '') || 'You';
        const userInitials = userName.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2) || 'YO';

        // Build message bubbles
        const messagesHTML = state.messages.map(msg => {
            const isUser = msg.sender === 'user';
            const avatarBg = isUser ? 'var(--blue-600)' : 'var(--violet-600)';
            const name = isUser ? userName : attorney.name;
            const initials = isUser ? userInitials : (attorney.initials || attorney.name.split(' ').map(w => w[0]).join(''));
            const time = new Date(msg.timestamp).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

            return `
                <div class="message">
                    <div class="msg-avatar" style="background:${avatarBg}">${initials}</div>
                    <div class="msg-content">
                        <div class="msg-name">${name}</div>
                        <div class="msg-text">${msg.text}</div>
                        <div class="msg-time">${time}</div>
                    </div>
                </div>
            `;
        }).join('');

        page.innerHTML = `
            <h1 style="font-size:28px;font-weight:800;margin-bottom:8px">Messages</h1>
            <p style="color:var(--slate-500);margin-bottom:28px">Conversation with <strong>${attorney.name}</strong> &middot; ${consultation.specialization}</p>
            <div class="card">
                <div class="card-header"><h3>Conversation with ${attorney.name}</h3></div>
                <div class="card-body" style="padding:0;">
                    <div class="message-list" id="messageList">
                        ${messagesHTML || '<div style="padding:24px;text-align:center;color:var(--slate-400);font-size:14px;">Start the conversation by sending a message below.</div>'}
                    </div>
                    <div style="padding:16px 20px;border-top:1px solid var(--slate-100);display:flex;gap:12px;align-items:flex-end;">
                        <textarea id="messageInput" rows="2" placeholder="Type your message..." style="flex:1;padding:12px 16px;border:1px solid var(--slate-300);border-radius:8px;font-family:inherit;font-size:14px;resize:none;color:var(--slate-800);"></textarea>
                        <button class="btn btn-primary btn-sm" id="sendMessageBtn" style="height:44px;">Send</button>
                    </div>
                </div>
            </div>
        `;

        // Scroll to bottom
        const list = document.getElementById('messageList');
        if (list) list.scrollTop = list.scrollHeight;

        // Bind send button
        document.getElementById('sendMessageBtn').addEventListener('click', sendMessage);

        // Enter key sends (Shift+Enter for newline)
        document.getElementById('messageInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    };

    const sendMessage = () => {
        const input = document.getElementById('messageInput');
        const text = input.value.trim();
        if (!text) return;

        // Add user message
        state.messages.push({
            sender: 'user',
            text: text,
            timestamp: new Date().toISOString()
        });
        saveState(state);
        input.value = '';
        renderMessages();

        // Simulate attorney response after 2 seconds
        const consultation = state.consultations[0];
        const attorney = ATTORNEYS.find(a => a.id === consultation.attorneyId) || { name: consultation.attorneyName };

        const responses = [
            `Thank you for reaching out! I've reviewed your application details and everything looks on track. Let me know if you have specific questions about your ${state.application ? state.application.typeLabel : 'visa'} application.`,
            `Great question. For ${state.application ? state.application.countryLabel : 'your destination'}, you'll want to make sure all supporting documents are submitted well before the deadline. I can help you prioritize.`,
            `I'd recommend gathering your financial evidence and acceptance letter as soon as possible. These are the most common reasons for delays.`,
            `I've seen many similar cases and the key is thorough documentation. Let's schedule a call to discuss your specific situation in detail.`,
            `That's a good point. I'll prepare a checklist of documents specific to your case type and send it over shortly.`
        ];
        const responseText = responses[state.messages.length % responses.length];

        setTimeout(() => {
            state.messages.push({
                sender: 'attorney',
                text: responseText,
                timestamp: new Date().toISOString()
            });
            saveState(state);
            renderMessages();
        }, 2000);
    };

    // =========================================================================
    // INITIALIZATION
    // =========================================================================

    const init = () => {
        applySession();
        initTabs();
        initWizard();

        // If application already exists, default to dashboard
        if (state.application) {
            switchTab('dashboard');
        }

        // Initial render for attorney buttons
        renderAttorneyButtons();
    };

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
