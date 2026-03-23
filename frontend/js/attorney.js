/**
 * Verom.ai — Attorney Portal
 */
(function () {
    'use strict';

    // ========================================
    // Demo Data
    // ========================================
    const DEMO_CASES = [
        { id: 'c1', name: 'Maria Garcia', type: 'Student Visa', sub: 'F-1', country: 'United States', status: 'new', note: '', date: '2026-03-20' },
        { id: 'c2', name: 'Ahmed Hassan', type: 'Skilled Worker Visa', sub: '', country: 'United Kingdom', status: 'new', note: '', date: '2026-03-19' },
        { id: 'c3', name: 'Raj Mehta', type: 'H-1B Initial', sub: 'H-1B', country: 'United States', status: 'in_progress', note: 'Filed Mar 15', date: '2026-03-15' },
        { id: 'c4', name: 'Li Wei', type: 'F-1 Student Visa', sub: 'F-1', country: 'United States', status: 'in_progress', note: 'Documents In Review', date: '2026-03-12' },
        { id: 'c5', name: 'John Lee', type: 'H-1B Transfer', sub: 'H-1B', country: 'United States', status: 'in_progress', note: 'Preparing Filing', date: '2026-03-10' },
        { id: 'c6', name: 'Priya Patel', type: 'EAD Renewal', sub: 'EAD', country: 'United States', status: 'in_progress', note: 'Awaiting Documents', date: '2026-03-08' },
        { id: 'c7', name: 'Ana Santos', type: 'O-1 Extraordinary Ability', sub: 'O-1', country: 'United States', status: 'rfe', note: 'RFE Due Apr 5', date: '2026-03-01', deadline: '2026-04-05' },
        { id: 'c8', name: 'Yuki Tanaka', type: 'O-1 Petition', sub: 'O-1', country: 'United States', status: 'approved', note: 'Approved Mar 18', date: '2026-03-18' },
        { id: 'c9', name: 'Wei Chen', type: 'EB-2 NIW', sub: 'EB-2', country: 'United States', status: 'approved', note: 'Approved Mar 10', date: '2026-03-10' }
    ];

    const DEMO_BROWSE = [
        { id: 'b1', appId: 'VRM-2847', type: 'F-1 Student Visa', country: 'United States', origin: 'India', score: 82, docs: '6/8' },
        { id: 'b2', appId: 'VRM-2851', type: 'H-1B Transfer', country: 'United States', origin: 'China', score: 91, docs: '8/8' },
        { id: 'b3', appId: 'VRM-2855', type: 'O-1 Extraordinary Ability', country: 'United States', origin: 'Brazil', score: 74, docs: '5/10' },
        { id: 'b4', appId: 'VRM-2860', type: 'K-1 Fiance Visa', country: 'United States', origin: 'Philippines', score: 88, docs: '7/8' }
    ];

    const DEMO_EVENTS = [
        { id: 'e1', date: '2026-04-05', title: 'RFE Response', caseRef: 'Ana Santos', urgent: true },
        { id: 'e2', date: '2026-04-12', title: 'H-1B Filing', caseRef: 'John Lee', urgent: true },
        { id: 'e3', date: '2026-04-15', title: 'Client Consultation', caseRef: 'Maria Garcia', urgent: false },
        { id: 'e4', date: '2026-04-18', title: 'I-140 Priority Date', caseRef: 'Wei Chen', urgent: false },
        { id: 'e5', date: '2026-04-25', title: 'EAD Renewal', caseRef: 'Priya Patel', urgent: false }
    ];

    const DEMO_PAYMENTS = [
        { name: 'Yuki Tanaka', desc: 'O-1 Petition (Complete)', amount: 5500 },
        { name: 'Raj Mehta', desc: 'H-1B Initial (Filing Fee)', amount: 3000 },
        { name: 'Wei Chen', desc: 'EB-2 NIW (Complete)', amount: 7500 },
        { name: 'Li Wei', desc: 'F-1 Consultation', amount: 750 },
        { name: 'Ana Santos', desc: 'O-1 Retainer', amount: 2500 }
    ];

    const DEMO_PROFILE = {
        name: 'Sarah Kim', email: 'sarah.kim@lawfirm.com', barNumber: 'NY-2015-28394',
        jurisdiction: 'United States - New York', yearsExp: 12,
        specializations: 'H-1B, O-1, EB-2, F-1, Family-based',
        bio: 'Immigration attorney with 12 years of experience specializing in employment-based and student visas. Member of AILA.',
        maxCases: 15, acceptingCases: true
    };

    // ========================================
    // State
    // ========================================
    const STORE_KEY = 'verom_attorney';
    let state;

    function loadState() {
        try {
            const saved = localStorage.getItem(STORE_KEY);
            if (saved) { state = JSON.parse(saved); return; }
        } catch (e) { /* use defaults */ }
        state = {
            profile: { ...DEMO_PROFILE },
            cases: DEMO_CASES.map(c => ({ ...c })),
            browse: DEMO_BROWSE.map(b => ({ ...b })),
            events: DEMO_EVENTS.map(e => ({ ...e })),
            calMonth: new Date().getMonth(),
            calYear: new Date().getFullYear()
        };
    }
    function saveState() { localStorage.setItem(STORE_KEY, JSON.stringify(state)); }
    loadState();

    // ========================================
    // Toast
    // ========================================
    function showToast(msg, type) {
        let c = document.querySelector('.toast-ctr');
        if (!c) {
            c = document.createElement('div');
            c.className = 'toast-ctr';
            c.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:10000;display:flex;flex-direction:column;gap:8px';
            document.body.appendChild(c);
        }
        const t = document.createElement('div');
        const colors = { success: '#16a34a', error: '#ef4444', info: '#2563eb' };
        t.style.cssText = `padding:14px 20px;border-radius:10px;color:#fff;font-size:14px;font-weight:500;box-shadow:0 4px 12px rgba(0,0,0,0.2);background:${colors[type] || colors.info};animation:toastIn 0.3s ease;max-width:360px`;
        t.textContent = msg;
        c.appendChild(t);
        setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity 0.3s'; setTimeout(() => t.remove(), 300); }, 3000);
    }

    // inject toast animation
    const style = document.createElement('style');
    style.textContent = '@keyframes toastIn{from{opacity:0;transform:translateY(12px)}to{opacity:1}}' +
        '.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:9000;display:flex;align-items:center;justify-content:center;animation:toastIn 0.2s ease}' +
        '.modal-box{background:#fff;border-radius:16px;max-width:560px;width:90%;max-height:85vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,0.3);padding:32px}' +
        '.modal-box h2{font-size:20px;font-weight:700;margin-bottom:16px}' +
        '.modal-box .form-group{margin-bottom:16px}' +
        '.modal-box .form-group label{display:block;font-size:13px;font-weight:600;color:#334155;margin-bottom:6px}' +
        '.modal-box .form-input{width:100%;padding:10px 14px;border:1px solid #cbd5e1;border-radius:8px;font-family:inherit;font-size:14px}' +
        '.modal-box .form-input:focus{outline:none;border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,0.15)}' +
        '.modal-actions{display:flex;gap:12px;justify-content:flex-end;margin-top:24px}';
    document.head.appendChild(style);

    // ========================================
    // Modal
    // ========================================
    function showModal(title, bodyHtml, actions) {
        closeModal();
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
        const box = document.createElement('div');
        box.className = 'modal-box';
        box.innerHTML = `<h2>${title}</h2>${bodyHtml}<div class="modal-actions"></div>`;
        const actDiv = box.querySelector('.modal-actions');
        (actions || []).forEach(a => {
            const btn = document.createElement('button');
            btn.className = 'btn ' + (a.cls || 'btn-outline');
            btn.textContent = a.label;
            btn.addEventListener('click', () => { if (a.onClick) a.onClick(); });
            actDiv.appendChild(btn);
        });
        overlay.appendChild(box);
        document.body.appendChild(overlay);
    }
    function closeModal() {
        document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
    }

    // ========================================
    // Navigation
    // ========================================
    function initNav() {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
                const page = document.getElementById('page-' + tab.dataset.tab);
                if (page) page.classList.add('active');
                refreshPage(tab.dataset.tab);
            });
        });
        // Session
        const session = (() => { try { return JSON.parse(localStorage.getItem('verom_session')); } catch (e) { return null; } })();
        if (session && session.firstName) {
            const initials = (session.firstName[0] + (session.lastName || ' ')[0]).toUpperCase();
            const av = document.querySelector('.avatar');
            if (av) av.textContent = initials;
        }
    }

    // ========================================
    // Dashboard
    // ========================================
    function renderDashboard() {
        const cases = state.cases;
        const active = cases.filter(c => c.status !== 'approved').length;
        const approved = cases.filter(c => c.status === 'approved').length;
        const rfe = cases.filter(c => c.status === 'rfe').length;
        // Update stat cards
        const stats = document.querySelectorAll('#page-dashboard .stat-value');
        if (stats[0]) stats[0].textContent = active;
        if (stats[1]) stats[1].textContent = approved > 0 ? Math.round((approved / cases.length) * 100) + '%' : '0%';
        if (stats[2]) stats[2].textContent = rfe + cases.filter(c => c.status === 'new').length;

        // Recent activity
        const actBody = document.querySelector('#page-dashboard .card:first-of-type .card-body');
        if (actBody && cases.length) {
            actBody.innerHTML = cases.slice(0, 5).map(c => {
                const badge = c.status === 'approved' ? 'badge-green' : c.status === 'rfe' ? 'badge-red' : c.status === 'new' ? 'badge-amber' : 'badge-blue';
                const label = c.status === 'approved' ? 'Approved' : c.status === 'rfe' ? 'Urgent' : c.status === 'new' ? 'New' : 'In Progress';
                return `<div class="earning-row"><span><strong>${c.name}</strong> &mdash; ${c.type}</span><span class="badge ${badge}">${label}</span></div>`;
            }).join('');
        }

        // Deadlines
        const dlBody = document.querySelectorAll('#page-dashboard .card')[1];
        if (dlBody) {
            const deadlines = state.events.sort((a, b) => a.date.localeCompare(b.date)).slice(0, 5);
            const inner = dlBody.querySelector('.card-body');
            if (inner) {
                inner.innerHTML = deadlines.map(e => {
                    const d = new Date(e.date + 'T00:00:00');
                    const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                    const clr = e.urgent ? 'color:var(--red-500)' : '';
                    return `<div class="earning-row" style="flex-direction:column;gap:4px"><strong style="${clr}">${label}</strong><span style="font-size:13px">${e.caseRef} &mdash; ${e.title}</span></div>`;
                }).join('');
            }
        }
    }

    // ========================================
    // Cases Pipeline
    // ========================================
    function renderCases() {
        const page = document.getElementById('page-cases');
        if (!page) return;
        const pipeline = page.querySelector('.pipeline');
        if (!pipeline) return;

        const groups = { new: [], in_progress: [], rfe: [], approved: [] };
        state.cases.forEach(c => { if (groups[c.status]) groups[c.status].push(c); });

        // Ensure header has add button
        let header = page.querySelector('.page-header');
        if (header && !header.querySelector('.btn-primary')) {
            const btn = document.createElement('button');
            btn.className = 'btn btn-primary';
            btn.textContent = '+ New Case';
            btn.addEventListener('click', showAddCaseModal);
            header.appendChild(btn);
        }

        const columns = pipeline.querySelectorAll('.pipeline-col');
        const statusKeys = ['new', 'in_progress', 'rfe', 'approved'];
        const statusLabels = ['New', 'In Progress', 'RFE / Action', 'Approved'];

        statusKeys.forEach((key, i) => {
            if (!columns[i]) return;
            const cases = groups[key] || [];
            columns[i].innerHTML = `
                <div class="pipeline-header"><h4>${statusLabels[i]}</h4><div class="pipeline-count">${cases.length}</div></div>
                ${cases.map(c => {
                    const border = key === 'rfe' ? 'border-left:3px solid var(--red-500)' : key === 'approved' ? 'border-left:3px solid var(--green-500)' : '';
                    const noteColor = key === 'rfe' ? 'color:var(--red-500)' : key === 'approved' ? 'color:var(--green-500)' : '';
                    return `<div class="case-card" style="${border}" data-id="${c.id}">
                        <div class="case-name">${c.name}</div>
                        <div class="case-meta">${c.type}</div>
                        <div class="case-type" style="${noteColor}">${c.note || c.country}</div>
                    </div>`;
                }).join('')}
            `;
            // Click handlers
            columns[i].querySelectorAll('.case-card').forEach(card => {
                card.addEventListener('click', () => showCaseDetail(card.dataset.id));
            });
        });
    }

    function showCaseDetail(id) {
        const c = state.cases.find(x => x.id === id);
        if (!c) return;
        const statusOpts = ['new', 'in_progress', 'rfe', 'approved'].map(s =>
            `<option value="${s}" ${s === c.status ? 'selected' : ''}>${s.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>`
        ).join('');
        const body = `
            <div style="background:var(--slate-50);border-radius:8px;padding:16px;margin-bottom:16px">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:14px">
                    <div><span style="color:var(--slate-500)">Client:</span> <strong>${c.name}</strong></div>
                    <div><span style="color:var(--slate-500)">Visa Type:</span> <strong>${c.type}</strong></div>
                    <div><span style="color:var(--slate-500)">Country:</span> <strong>${c.country}</strong></div>
                    <div><span style="color:var(--slate-500)">Date Added:</span> <strong>${c.date || 'N/A'}</strong></div>
                </div>
            </div>
            <div class="form-group">
                <label>Status</label>
                <select class="form-input" id="modalCaseStatus">${statusOpts}</select>
            </div>
            <div class="form-group">
                <label>Notes</label>
                <textarea class="form-input" rows="3" id="modalCaseNotes">${c.note || ''}</textarea>
            </div>`;
        showModal(`Case: ${c.name}`, body, [
            { label: 'Delete', cls: 'btn-outline', onClick: () => { state.cases = state.cases.filter(x => x.id !== id); saveState(); closeModal(); renderCases(); renderDashboard(); showToast('Case removed', 'info'); } },
            { label: 'Save', cls: 'btn-primary', onClick: () => {
                c.status = document.getElementById('modalCaseStatus').value;
                c.note = document.getElementById('modalCaseNotes').value;
                saveState(); closeModal(); renderCases(); renderDashboard();
                showToast('Case updated', 'success');
            }}
        ]);
    }

    function showAddCaseModal() {
        const body = `
            <div class="form-group"><label>Client Name</label><input type="text" class="form-input" id="newCaseName" placeholder="Full name"></div>
            <div class="form-group"><label>Visa Type</label><input type="text" class="form-input" id="newCaseType" placeholder="e.g. H-1B, O-1, F-1"></div>
            <div class="form-group"><label>Country</label>
                <select class="form-input" id="newCaseCountry">
                    <option>United States</option><option>United Kingdom</option><option>Canada</option><option>Australia</option><option>Germany</option><option>New Zealand</option>
                </select>
            </div>
            <div class="form-group"><label>Notes</label><textarea class="form-input" rows="2" id="newCaseNotes" placeholder="Initial notes..."></textarea></div>`;
        showModal('New Case', body, [
            { label: 'Cancel', cls: 'btn-outline', onClick: closeModal },
            { label: 'Create', cls: 'btn-primary', onClick: () => {
                const name = document.getElementById('newCaseName').value.trim();
                if (!name) { showToast('Client name is required', 'error'); return; }
                state.cases.push({
                    id: 'c' + Date.now(),
                    name,
                    type: document.getElementById('newCaseType').value || 'General',
                    sub: '',
                    country: document.getElementById('newCaseCountry').value,
                    status: 'new',
                    note: document.getElementById('newCaseNotes').value,
                    date: new Date().toISOString().slice(0, 10)
                });
                saveState(); closeModal(); renderCases(); renderDashboard();
                showToast('Case created for ' + name, 'success');
            }}
        ]);
    }

    // ========================================
    // Browse Cases
    // ========================================
    function renderBrowse() {
        const page = document.getElementById('page-browse');
        if (!page) return;
        const container = page.querySelector('.card .card-body') || page.querySelector('.card');
        if (!container) return;

        const filterDiv = container.querySelector('div[style*="display:flex"]');
        // Get filter values
        const selects = page.querySelectorAll('.form-input');
        const typeFilter = selects[0] ? selects[0].value : 'All Visa Types';
        const countryFilter = selects[1] ? selects[1].value : 'United States';

        let items = state.browse;
        if (typeFilter !== 'All Visa Types') {
            const map = { 'Student Visas': 'Student', 'Work Visas': 'H-1B', 'Family / Spouse': 'K-1', 'Permanent Residency': 'EB' };
            const kw = map[typeFilter] || typeFilter;
            items = items.filter(b => b.type.includes(kw));
        }

        // Build rows
        const body = container.querySelector('[style*="padding:0"]') || container;
        // Keep filter row, rebuild listing rows
        const rows = body.querySelectorAll('div[style*="padding:16px 24px"]');
        rows.forEach(r => { if (!r.querySelector('select')) r.remove(); });

        items.forEach(b => {
            const scoreColor = b.score >= 85 ? 'var(--green-500)' : b.score >= 75 ? 'var(--amber-500)' : 'var(--red-500)';
            const row = document.createElement('div');
            row.style.cssText = 'padding:16px 24px;border-bottom:1px solid var(--slate-100);display:flex;justify-content:space-between;align-items:center';
            row.innerHTML = `
                <div>
                    <div style="font-size:15px;font-weight:600">Applicant #${b.appId}</div>
                    <div style="font-size:13px;color:var(--slate-500)">${b.type} &middot; ${b.country} &middot; ${b.origin}</div>
                    <div style="font-size:13px;color:var(--slate-500);margin-top:4px">AI Score: <strong style="color:${scoreColor}">${b.score}%</strong> &middot; Documents: ${b.docs} uploaded</div>
                </div>
                <div style="display:flex;gap:8px">
                    <button class="btn btn-outline btn-sm browse-detail" data-id="${b.id}">View Details</button>
                    <button class="btn btn-success btn-sm browse-accept" data-id="${b.id}">Accept Case</button>
                </div>`;
            body.appendChild(row);
        });

        if (items.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'empty-state';
            empty.innerHTML = '<span class="empty-icon">&#128269;</span><h3 style="font-size:18px;color:var(--slate-700)">No cases match your filters</h3><p style="font-size:14px">Try broadening your search criteria.</p>';
            body.appendChild(empty);
        }

        // Event listeners
        body.querySelectorAll('.browse-detail').forEach(btn => {
            btn.addEventListener('click', () => {
                const b = state.browse.find(x => x.id === btn.dataset.id);
                if (!b) return;
                showModal(`Applicant #${b.appId}`, `
                    <div style="background:var(--slate-50);border-radius:8px;padding:16px;margin-bottom:16px;font-size:14px">
                        <p><strong>Visa Type:</strong> ${b.type}</p>
                        <p><strong>Country:</strong> ${b.country}</p>
                        <p><strong>Origin:</strong> ${b.origin}</p>
                        <p><strong>AI Score:</strong> ${b.score}%</p>
                        <p><strong>Documents:</strong> ${b.docs} uploaded</p>
                    </div>
                    <p style="font-size:14px;color:var(--slate-600)">This applicant has been pre-screened by Verom AI. Accepting this case will add it to your pipeline.</p>
                `, [{ label: 'Close', cls: 'btn-outline', onClick: closeModal }]);
            });
        });

        body.querySelectorAll('.browse-accept').forEach(btn => {
            btn.addEventListener('click', () => {
                const b = state.browse.find(x => x.id === btn.dataset.id);
                if (!b) return;
                state.cases.push({
                    id: 'c' + Date.now(), name: 'Applicant #' + b.appId, type: b.type, sub: '',
                    country: b.country, status: 'new', note: 'Accepted from marketplace', date: new Date().toISOString().slice(0, 10)
                });
                state.browse = state.browse.filter(x => x.id !== b.id);
                saveState(); renderBrowse(); renderCases(); renderDashboard();
                showToast('Case accepted! Added to your pipeline.', 'success');
            });
        });

        // Filter listeners
        selects.forEach(s => {
            if (!s._bound) {
                s._bound = true;
                s.addEventListener('change', renderBrowse);
            }
        });
    }

    // ========================================
    // Calendar
    // ========================================
    function renderCalendar() {
        const page = document.getElementById('page-calendar');
        if (!page) return;
        const grid = page.querySelector('.card:first-of-type');
        if (!grid) return;

        const year = state.calYear;
        const month = state.calMonth;
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

        // Header with nav
        const hdr = grid.querySelector('.card-header');
        if (hdr) {
            hdr.innerHTML = `
                <button class="btn btn-outline btn-sm" id="calPrev">&larr;</button>
                <h3>${monthNames[month]} ${year}</h3>
                <div style="display:flex;gap:8px">
                    <button class="btn btn-outline btn-sm" id="calNext">&rarr;</button>
                    <button class="btn btn-primary btn-sm" id="calAdd">+ Event</button>
                </div>`;
            document.getElementById('calPrev').addEventListener('click', () => {
                state.calMonth--; if (state.calMonth < 0) { state.calMonth = 11; state.calYear--; }
                renderCalendar();
            });
            document.getElementById('calNext').addEventListener('click', () => {
                state.calMonth++; if (state.calMonth > 11) { state.calMonth = 0; state.calYear++; }
                renderCalendar();
            });
            document.getElementById('calAdd').addEventListener('click', showAddEventModal);
        }

        const body = grid.querySelector('.card-body');
        if (!body) return;

        const firstDay = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();
        const today = new Date();
        const eventDates = new Set(state.events.map(e => e.date));

        let html = '<div class="calendar-grid">';
        ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(d => html += `<div class="cal-header">${d}</div>`);
        for (let i = 0; i < firstDay; i++) html += '<div class="cal-day empty"></div>';
        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
            const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
            const hasEvent = eventDates.has(dateStr);
            html += `<div class="cal-day${isToday ? ' today' : ''}${hasEvent ? ' has-event' : ''}" data-date="${dateStr}">${d}</div>`;
        }
        html += '</div>';
        body.innerHTML = html;

        // Click day to show events
        body.querySelectorAll('.cal-day[data-date]').forEach(day => {
            day.addEventListener('click', () => {
                const events = state.events.filter(e => e.date === day.dataset.date);
                if (events.length) {
                    showModal(`Events on ${day.dataset.date}`, events.map(e =>
                        `<div style="padding:12px 0;border-bottom:1px solid var(--slate-100)"><strong>${e.title}</strong><br><span style="font-size:13px;color:var(--slate-500)">${e.caseRef}</span></div>`
                    ).join(''), [{ label: 'Close', cls: 'btn-outline', onClick: closeModal }]);
                }
            });
        });

        // Events sidebar
        const sidebar = page.querySelectorAll('.card')[1];
        if (sidebar) {
            const sBody = sidebar.querySelector('.card-body');
            const upcoming = state.events.sort((a, b) => a.date.localeCompare(b.date)).slice(0, 6);
            if (sBody) {
                sBody.innerHTML = upcoming.map(e => {
                    const d = new Date(e.date + 'T00:00:00');
                    const label = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                    const clr = e.urgent ? 'color:var(--red-500)' : e.date < new Date().toISOString().slice(0, 10) ? '' : 'color:var(--amber-500)';
                    return `<div class="earning-row" style="flex-direction:column;gap:4px"><strong style="${clr}">${label}</strong><span style="font-size:13px">${e.caseRef} &mdash; ${e.title}</span></div>`;
                }).join('') || '<div class="empty-state">No upcoming events</div>';
            }
        }
    }

    function showAddEventModal() {
        const body = `
            <div class="form-group"><label>Date</label><input type="date" class="form-input" id="newEvtDate" value="${new Date().toISOString().slice(0, 10)}"></div>
            <div class="form-group"><label>Title</label><input type="text" class="form-input" id="newEvtTitle" placeholder="e.g. Filing Deadline"></div>
            <div class="form-group"><label>Related Case</label>
                <select class="form-input" id="newEvtCase">
                    <option value="">None</option>
                    ${state.cases.map(c => `<option value="${c.name}">${c.name} - ${c.type}</option>`).join('')}
                </select>
            </div>
            <div class="form-group"><label><input type="checkbox" id="newEvtUrgent"> Mark as urgent</label></div>`;
        showModal('Add Calendar Event', body, [
            { label: 'Cancel', cls: 'btn-outline', onClick: closeModal },
            { label: 'Add Event', cls: 'btn-primary', onClick: () => {
                const title = document.getElementById('newEvtTitle').value.trim();
                if (!title) { showToast('Title is required', 'error'); return; }
                state.events.push({
                    id: 'e' + Date.now(),
                    date: document.getElementById('newEvtDate').value,
                    title,
                    caseRef: document.getElementById('newEvtCase').value || 'General',
                    urgent: document.getElementById('newEvtUrgent').checked
                });
                saveState(); closeModal(); renderCalendar();
                showToast('Event added', 'success');
            }}
        ]);
    }

    // ========================================
    // Earnings
    // ========================================
    function renderEarnings() {
        // Earnings are static demo data, no dynamic rendering needed
        // The HTML is already populated correctly
    }

    // ========================================
    // Profile
    // ========================================
    function renderProfile() {
        const page = document.getElementById('page-profile');
        if (!page) return;
        const p = state.profile;
        const inputs = page.querySelectorAll('.form-input');
        if (inputs[0]) inputs[0].value = p.name;
        if (inputs[1]) inputs[1].value = p.email;
        if (inputs[2]) inputs[2].value = p.barNumber;
        if (inputs[3]) inputs[3].value = p.jurisdiction;
        if (inputs[4]) inputs[4].value = p.yearsExp;
        if (inputs[5]) inputs[5].value = p.specializations;
        const textarea = page.querySelector('textarea');
        if (textarea) textarea.value = p.bio;

        // Max cases and accepting
        const cards = page.querySelectorAll('.card');
        if (cards.length >= 3) {
            const avInputs = cards[2].querySelectorAll('.form-input');
            if (avInputs[0]) avInputs[0].value = p.maxCases;
            if (avInputs[1]) avInputs[1].value = p.acceptingCases ? 'Yes' : 'No - At capacity';
        }

        // Save Profile button
        const saveBtn = page.querySelector('.btn-primary');
        if (saveBtn && !saveBtn._bound) {
            saveBtn._bound = true;
            saveBtn.addEventListener('click', () => {
                state.profile.name = inputs[0] ? inputs[0].value : p.name;
                state.profile.email = inputs[1] ? inputs[1].value : p.email;
                state.profile.barNumber = inputs[2] ? inputs[2].value : p.barNumber;
                state.profile.jurisdiction = inputs[3] ? inputs[3].value : p.jurisdiction;
                state.profile.yearsExp = inputs[4] ? parseInt(inputs[4].value) || 0 : p.yearsExp;
                state.profile.specializations = inputs[5] ? inputs[5].value : p.specializations;
                state.profile.bio = textarea ? textarea.value : p.bio;
                saveState();
                showToast('Profile saved successfully', 'success');
            });
        }

        // Update Availability button
        const avBtn = page.querySelector('.btn-outline[style*="width:100%"]');
        if (avBtn && !avBtn._bound) {
            avBtn._bound = true;
            avBtn.addEventListener('click', () => {
                const cards2 = page.querySelectorAll('.card');
                if (cards2.length >= 3) {
                    const avInputs = cards2[2].querySelectorAll('.form-input');
                    state.profile.maxCases = avInputs[0] ? parseInt(avInputs[0].value) || 15 : 15;
                    state.profile.acceptingCases = avInputs[1] ? avInputs[1].value === 'Yes' : true;
                }
                saveState();
                showToast('Availability updated', 'success');
            });
        }
    }

    // ========================================
    // Page refresh
    // ========================================
    function refreshPage(tab) {
        switch (tab) {
            case 'dashboard': renderDashboard(); break;
            case 'cases': renderCases(); break;
            case 'browse': renderBrowse(); break;
            case 'calendar': renderCalendar(); break;
            case 'earnings': renderEarnings(); break;
            case 'profile': renderProfile(); break;
        }
    }

    // ========================================
    // Init
    // ========================================
    initNav();
    renderDashboard();
    renderCases();
    renderProfile();

})();
