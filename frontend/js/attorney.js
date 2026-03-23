/**
 * Verom.ai — Attorney Portal Application Logic
 */
(function() {
    'use strict';

    // State
    var currentPage = 'dashboard';
    var currentCase = null;

    // Demo Data
    var demoData = {
        stats: { activeCases: 24, pendingIntakes: 8, upcomingDeadlines: 5, unreadMessages: 12, casesThisMonth: 3, approvalRate: 94.2 },
        cases: [
            { id: 'C-2026-001', client: 'Maria Santos', visaType: 'H-1B', status: 'pending', priority: 'high', deadline: '2026-04-15', lastActivity: '2 hours ago', receipt: 'WAC-26-123-45678' },
            { id: 'C-2026-002', client: 'Chen Wei', visaType: 'I-485', status: 'rfe', priority: 'critical', deadline: '2026-04-01', lastActivity: '1 day ago', receipt: 'LIN-26-087-12345' },
            { id: 'C-2026-003', client: 'Ahmed Hassan', visaType: 'O-1', status: 'filed', priority: 'medium', deadline: '2026-05-20', lastActivity: '3 days ago', receipt: 'EAC-26-234-56789' },
            { id: 'C-2026-004', client: 'Yuki Tanaka', visaType: 'L-1A', status: 'approved', priority: 'low', deadline: null, lastActivity: '1 week ago', receipt: 'WAC-26-345-67890' },
            { id: 'C-2026-005', client: 'Priya Sharma', visaType: 'EB-2 NIW', status: 'pending', priority: 'high', deadline: '2026-04-30', lastActivity: '5 hours ago', receipt: 'SRC-26-456-78901' },
            { id: 'C-2026-006', client: 'James O\'Brien', visaType: 'UK Skilled Worker', status: 'filed', priority: 'medium', deadline: '2026-05-10', lastActivity: '2 days ago', receipt: null },
            { id: 'C-2026-007', client: 'Sofia Rodriguez', visaType: 'Express Entry', status: 'draft', priority: 'low', deadline: '2026-06-01', lastActivity: '4 days ago', receipt: null },
            { id: 'C-2026-008', client: 'Kim Soo-yeon', visaType: 'F-1 OPT', status: 'pending', priority: 'high', deadline: '2026-04-20', lastActivity: '6 hours ago', receipt: 'WAC-26-567-89012' }
        ],
        intakes: [
            { id: 'INT-001', client: 'Ana Petrova', visaType: 'H-1B', country: 'United States', date: '2026-03-20', completeness: 85, status: 'in_progress' },
            { id: 'INT-002', client: 'Rafael Mendez', visaType: 'I-130', country: 'United States', date: '2026-03-19', completeness: 100, status: 'completed' },
            { id: 'INT-003', client: 'Li Mei', visaType: 'Skilled Worker', country: 'United Kingdom', date: '2026-03-18', completeness: 45, status: 'in_progress' },
            { id: 'INT-004', client: 'Omar Al-Farsi', visaType: 'Express Entry', country: 'Canada', date: '2026-03-17', completeness: 20, status: 'new' },
            { id: 'INT-005', client: 'Kenji Yamamoto', visaType: 'O-1', country: 'United States', date: '2026-03-16', completeness: 60, status: 'in_progress' }
        ],
        deadlines: [
            { id: 'D-001', caseId: 'C-2026-002', title: 'RFE Response Due', date: '2026-04-01', type: 'rfe_response', urgency: 'critical' },
            { id: 'D-002', caseId: 'C-2026-001', title: 'H-1B Registration Window', date: '2026-04-15', type: 'filing_window', urgency: 'warning' },
            { id: 'D-003', caseId: 'C-2026-008', title: 'OPT Application Deadline', date: '2026-04-20', type: 'filing_window', urgency: 'warning' },
            { id: 'D-004', caseId: 'C-2026-005', title: 'Evidence Submission', date: '2026-04-30', type: 'custom', urgency: 'normal' },
            { id: 'D-005', caseId: 'C-2026-006', title: 'CoS Expiration', date: '2026-05-10', type: 'renewal', urgency: 'normal' },
            { id: 'D-006', caseId: 'C-2026-003', title: 'Biometrics Appointment', date: '2026-05-20', type: 'biometrics', urgency: 'normal' },
            { id: 'D-007', caseId: 'C-2026-007', title: 'Express Entry Profile Update', date: '2026-06-01', type: 'custom', urgency: 'normal' },
            { id: 'D-008', caseId: 'C-2026-001', title: 'I-129 Premium Processing Window', date: '2026-06-15', type: 'filing_window', urgency: 'normal' }
        ],
        messages: [
            { thread: 'Maria Santos - H-1B', messages: [
                { sender: 'Maria Santos', content: 'Hi, do you have an update on my petition?', time: '10:30 AM', sent: false },
                { sender: 'You', content: 'Yes! Your LCA was certified yesterday. We are preparing the I-129 petition now.', time: '11:15 AM', sent: true },
                { sender: 'Maria Santos', content: 'That\'s great news! When do you expect to file?', time: '11:20 AM', sent: false }
            ], unread: 1 },
            { thread: 'Chen Wei - I-485', messages: [
                { sender: 'Chen Wei', content: 'I received the RFE notice in the mail today', time: 'Yesterday', sent: false },
                { sender: 'You', content: 'Thank you for letting me know. Please scan and upload it through the portal. I will review and start drafting the response.', time: 'Yesterday', sent: true }
            ], unread: 0 },
            { thread: 'Ahmed Hassan - O-1', messages: [
                { sender: 'Ahmed Hassan', content: 'Can we schedule a call to discuss the recommendation letters?', time: '2 days ago', sent: false }
            ], unread: 1 },
            { thread: 'Priya Sharma - EB-2 NIW', messages: [
                { sender: 'Priya Sharma', content: 'I have uploaded my latest publications list', time: '3 days ago', sent: false },
                { sender: 'You', content: 'Received. These strengthen your case considerably. I will incorporate them into the petition letter.', time: '3 days ago', sent: true }
            ], unread: 0 },
            { thread: 'Kim Soo-yeon - F-1 OPT', messages: [
                { sender: 'Kim Soo-yeon', content: 'My OPT STEM extension — when should I apply?', time: '4 days ago', sent: false }
            ], unread: 1 }
        ],
        govStatuses: {
            uscis: [
                { receipt: 'WAC-26-123-45678', form: 'I-129', status: 'Case Was Received', updated: '2026-03-18', client: 'Maria Santos' },
                { receipt: 'LIN-26-087-12345', form: 'I-485', status: 'Request for Evidence Was Sent', updated: '2026-03-15', client: 'Chen Wei' },
                { receipt: 'EAC-26-234-56789', form: 'I-140', status: 'Case Is Being Actively Reviewed', updated: '2026-03-20', client: 'Ahmed Hassan' }
            ],
            dol: [{ caseNumber: 'A-19145-12345', type: 'PERM', status: 'In Review', updated: '2026-03-10', client: 'Priya Sharma' }],
            sevis: [{ id: 'N0012345678', status: 'Active', school: 'MIT', client: 'Kim Soo-yeon' }],
            ukHomeOffice: [{ ref: 'GWF012345678', type: 'Skilled Worker', status: 'Awaiting Decision', client: 'James O\'Brien' }],
            ircc: [{ appNumber: 'E001234567', type: 'Express Entry', status: 'Application Received', client: 'Sofia Rodriguez' }]
        },
        marketplace: [
            { id: 'ML-001', visaType: 'H-1B', country: 'US', complexity: 'Standard', urgency: 'Normal', budget: 'Standard Rate', description: 'Software engineer at tech company, MS in CS from US university' },
            { id: 'ML-002', visaType: 'I-130/I-485', country: 'US', complexity: 'Complex', urgency: 'High', budget: 'Premium Rate', description: 'Spouse petition with concurrent filing, prior visa overstay' },
            { id: 'ML-003', visaType: 'O-1B', country: 'US', complexity: 'Complex', urgency: 'Normal', budget: 'Premium Rate', description: 'Film director with international awards and festival screenings' },
            { id: 'ML-004', visaType: 'Express Entry', country: 'Canada', complexity: 'Standard', urgency: 'Normal', budget: 'Standard Rate', description: 'IT professional, CRS score 470, employer LMIA approved' }
        ]
    };

    // Navigation
    function navigate(page) {
        currentPage = page;
        document.querySelectorAll('.atty-page').forEach(function(p) { p.classList.remove('active'); });
        document.querySelectorAll('.atty-nav-item').forEach(function(n) { n.classList.remove('active'); });
        var pageEl = document.getElementById('atty-page-' + page);
        if (pageEl) pageEl.classList.add('active');
        var navEl = document.querySelector('[data-atty-page="' + page + '"]');
        if (navEl) navEl.classList.add('active');
    }

    // Toast
    function showToast(message) {
        var toast = document.getElementById('attyToast');
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(function() { toast.classList.remove('show'); }, 3000);
    }

    // Initialize navigation
    document.querySelectorAll('.atty-nav-item').forEach(function(item) {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            var page = this.getAttribute('data-atty-page');
            if (page) navigate(page);
        });
    });

    // Mobile toggle
    var mobileToggle = document.getElementById('attyMobileToggle');
    var sidebar = document.getElementById('attySidebar');
    if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
    }

    // Quick action buttons
    document.querySelectorAll('[data-action]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var action = this.getAttribute('data-action');
            switch(action) {
                case 'new-intake': navigate('intake'); break;
                case 'add-case': navigate('cases'); showToast('New case form opened'); break;
                case 'check-status': navigate('government'); break;
                case 'send-message': navigate('messages'); break;
                case 'convert-to-case': showToast('Intake converted to case successfully'); break;
                case 'auto-fill': showToast('Form auto-filled from case data'); break;
                case 'export-pdf': showToast('Report exported as PDF'); break;
                case 'export-excel': showToast('Report exported as Excel'); break;
                case 'export-csv': showToast('Report exported as CSV'); break;
                case 'accept-case': showToast('Case accepted and added to your pipeline'); break;
                case 'generate-intake': showToast('New intake form generated'); break;
                case 'share-link': showToast('Secure intake link copied to clipboard'); break;
                case 'scan-document': showToast('Document scan initiated — AI processing...'); break;
                case 'export-ical': showToast('Calendar exported in iCal format'); break;
                case 'export-google': showToast('Events synced to Google Calendar'); break;
                case 'export-outlook': showToast('Events synced to Outlook Calendar'); break;
                case 'check-all-statuses': showToast('Checking all government portal statuses...'); break;
                case 'send-message-btn': showToast('Message sent'); break;
                case 'run-import': showToast('Bulk import started — processing CSV...'); break;
                default: showToast(action + ' action triggered');
            }
        });
    });

    // Render functions
    function renderBadge(status) {
        var colors = {
            pending: 'blue', filed: 'cyan', approved: 'green', denied: 'red',
            rfe: 'yellow', draft: 'gray', critical: 'red', warning: 'yellow',
            normal: 'blue', high: 'yellow', medium: 'blue', low: 'gray',
            new: 'blue', in_progress: 'yellow', completed: 'green'
        };
        var color = colors[status] || 'gray';
        return '<span class="atty-badge atty-badge-' + color + '">' + status.replace(/_/g, ' ').toUpperCase() + '</span>';
    }

    // Render deadlines with urgency
    function renderDeadlines() {
        var container = document.getElementById('attyDeadlinesList');
        if (!container) return;
        var html = '<table class="atty-table"><thead><tr><th>Deadline</th><th>Case</th><th>Type</th><th>Date</th><th>Urgency</th></tr></thead><tbody>';
        demoData.deadlines.forEach(function(d) {
            var daysUntil = Math.ceil((new Date(d.date) - new Date()) / (1000*60*60*24));
            var urgencyBadge = daysUntil <= 10 ? 'red' : daysUntil <= 30 ? 'yellow' : 'green';
            html += '<tr><td><strong>' + d.title + '</strong></td><td>' + d.caseId + '</td><td>' + d.type.replace(/_/g, ' ') + '</td><td>' + d.date + ' <small style="color:var(--gray-400)">(' + daysUntil + ' days)</small></td><td><span class="atty-badge atty-badge-' + urgencyBadge + '">' + (daysUntil <= 10 ? 'URGENT' : daysUntil <= 30 ? 'SOON' : 'OK') + '</span></td></tr>';
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    }

    // Render messages
    function renderMessages() {
        var threadList = document.getElementById('attyThreadList');
        var chatArea = document.getElementById('attyChatMessages');
        if (!threadList || !chatArea) return;

        var html = '';
        demoData.messages.forEach(function(t, i) {
            var active = i === 0 ? ' active' : '';
            html += '<div class="atty-thread-item' + active + '" data-thread="' + i + '"><div class="atty-thread-name">' + t.thread + '</div><div class="atty-thread-preview">' + t.messages[t.messages.length-1].content.substring(0,50) + '...</div><div class="atty-thread-meta"><span class="atty-thread-time">' + t.messages[t.messages.length-1].time + '</span>' + (t.unread > 0 ? '<span class="atty-unread-dot"></span>' : '') + '</div></div>';
        });
        threadList.innerHTML = html;

        // Render first thread messages
        renderChatMessages(0);

        // Thread click handlers
        threadList.querySelectorAll('.atty-thread-item').forEach(function(item) {
            item.addEventListener('click', function() {
                threadList.querySelectorAll('.atty-thread-item').forEach(function(i) { i.classList.remove('active'); });
                this.classList.add('active');
                renderChatMessages(parseInt(this.getAttribute('data-thread')));
            });
        });
    }

    function renderChatMessages(threadIndex) {
        var chatArea = document.getElementById('attyChatMessages');
        if (!chatArea) return;
        var html = '';
        demoData.messages[threadIndex].messages.forEach(function(m) {
            html += '<div class="atty-chat-bubble ' + (m.sent ? 'sent' : 'received') + '">' + m.content + '<div style="font-size:11px;opacity:0.7;margin-top:4px">' + m.time + '</div></div>';
        });
        chatArea.innerHTML = html;
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    // Initialize
    function init() {
        renderDeadlines();
        renderMessages();
        navigate('dashboard');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for external use
    window.attySPA = { navigate: navigate, showToast: showToast };
})();
