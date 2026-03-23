/**
 * Verom.ai — Applicant Portal Application Logic
 */
(function() {
    'use strict';

    var currentPage = 'dashboard';
    var wizardStep = 3;
    var totalSteps = 6;
    var selectedVisaType = 'work';
    var selectedCountry = 'us';

    var demoData = {
        profile: { name: 'Sarah Chen', visaType: 'H-1B', country: 'United States', step: 3, score: 78 },
        stats: { status: 'In Review', daysUntilDeadline: 45, docsUploaded: 6, docsRequired: 9, attorneyStatus: 'Matched' },
        documents: [
            { name: 'Passport (valid)', category: 'Identity', status: 'uploaded', date: '2026-03-10', quality: 96 },
            { name: 'Degree Certificate (BS)', category: 'Education', status: 'uploaded', date: '2026-03-11', quality: 92 },
            { name: 'Transcripts', category: 'Education', status: 'uploaded', date: '2026-03-11', quality: 88 },
            { name: 'Employer Offer Letter', category: 'Employment', status: 'uploaded', date: '2026-03-14', quality: 95 },
            { name: 'Resume/CV', category: 'Employment', status: 'uploaded', date: '2026-03-14', quality: 90 },
            { name: 'Previous Visa Copy (F-1)', category: 'Immigration', status: 'uploaded', date: '2026-03-15', quality: 85 },
            { name: 'Financial Statement', category: 'Financial', status: 'pending', date: null, quality: null },
            { name: 'Tax Returns (2 years)', category: 'Financial', status: 'pending', date: null, quality: null },
            { name: 'Passport-style Photos', category: 'Identity', status: 'pending', date: null, quality: null }
        ],
        attorneys: [
            { name: 'Jennifer Park', initials: 'JP', specs: 'H-1B, O-1, EB categories', languages: 'English, Korean', years: 12, rating: 4.9, matchScore: 96, availability: 'Available', responseTime: '< 4 hours' },
            { name: 'Michael Torres', initials: 'MT', specs: 'H-1B, L-1, TN', languages: 'English, Spanish', years: 8, rating: 4.7, matchScore: 89, availability: 'Available', responseTime: '< 8 hours' },
            { name: 'David Kim', initials: 'DK', specs: 'All employment-based', languages: 'English, Korean, Mandarin', years: 15, rating: 4.8, matchScore: 85, availability: 'Limited', responseTime: '< 12 hours' },
            { name: 'Sarah Williams', initials: 'SW', specs: 'H-1B, EB-2 NIW, O-1', languages: 'English', years: 10, rating: 4.6, matchScore: 82, availability: 'Available', responseTime: '< 6 hours' }
        ],
        statusPipeline: [
            { label: 'Application Submitted', status: 'completed', date: '2026-03-10' },
            { label: 'Documents Verified', status: 'completed', date: '2026-03-15' },
            { label: 'Attorney Review', status: 'active', date: 'In progress' },
            { label: 'Forms Filed', status: 'pending', date: 'Est. Apr 15' },
            { label: 'Gov. Processing', status: 'pending', date: 'Est. Jun-Sep' },
            { label: 'Decision', status: 'pending', date: 'Est. Oct 2026' }
        ],
        deadlines: [
            { title: 'Upload Financial Documents', date: '2026-04-05', daysLeft: 14, urgency: 'warning' },
            { title: 'Attorney Consultation', date: '2026-04-10', daysLeft: 19, urgency: 'normal' },
            { title: 'H-1B Registration Window Closes', date: '2026-04-15', daysLeft: 24, urgency: 'normal' },
            { title: 'Passport Photos Due', date: '2026-05-01', daysLeft: 40, urgency: 'normal' }
        ],
        appointments: [
            { title: 'Attorney Consultation — Jennifer Park', type: 'Video Call', date: '2026-04-10', time: '2:00 PM EST', status: 'confirmed' },
            { title: 'Interview Prep Session', type: 'Mock Interview', date: '2026-04-25', time: '10:00 AM EST', status: 'scheduled' }
        ],
        messages: [
            { thread: 'Jennifer Park — Attorney', messages: [
                { sender: 'Jennifer Park', content: 'Hi Sarah, I have reviewed your application materials. Everything looks strong. I have a few questions about your employer\'s prevailing wage determination.', time: '2 hours ago', sent: false },
                { sender: 'You', content: 'Thank you! The HR department confirmed the wage level is Level 2 for the SOC code. I can get the official LCA posting if needed.', time: '1 hour ago', sent: true },
                { sender: 'Jennifer Park', content: 'That would be helpful. Please upload the LCA when you have it. Also, do you have any publications or patents that could strengthen the petition?', time: '30 min ago', sent: false }
            ], unread: 1 },
            { thread: 'Verom Support', messages: [
                { sender: 'Verom Support', content: 'Welcome to Verom! Your account has been set up and you have been matched with Jennifer Park based on your visa type and preferences.', time: '5 days ago', sent: false }
            ], unread: 0 }
        ],
        resources: {
            postApproval: [
                { text: 'Book travel to the United States', done: false },
                { text: 'Arrange temporary housing', done: false },
                { text: 'Apply for Social Security Number', done: false },
                { text: 'Open a US bank account', done: false },
                { text: 'Set up health insurance', done: false },
                { text: 'Register for state ID/driver\'s license', done: false },
                { text: 'Notify employer of visa approval', done: false },
                { text: 'Schedule orientation with employer', done: false }
            ],
            costs: {
                'H-1B': { filing: '$460', fraud: '$500', premium: '$2,805 (optional)', biometrics: '$85', total: '$1,045 - $3,850' },
                'I-485': { filing: '$1,140', biometrics: '$85', ead: '$410', ap: '$575', medical: '$200-500', total: '$2,410 - $2,710' },
                'O-1': { filing: '$460', premium: '$2,805 (optional)', total: '$460 - $3,265' }
            }
        }
    };

    // Navigation
    function navigate(page) {
        currentPage = page;
        document.querySelectorAll('.app-page').forEach(function(p) { p.classList.remove('active'); });
        document.querySelectorAll('.app-nav-item').forEach(function(n) { n.classList.remove('active'); });
        var pageEl = document.getElementById('app-page-' + page);
        if (pageEl) pageEl.classList.add('active');
        var navEl = document.querySelector('[data-app-page="' + page + '"]');
        if (navEl) navEl.classList.add('active');
    }

    function showToast(message) {
        var toast = document.getElementById('appToast');
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(function() { toast.classList.remove('show'); }, 3000);
    }

    // Nav click handlers
    document.querySelectorAll('.app-nav-item').forEach(function(item) {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            var page = this.getAttribute('data-app-page');
            if (page) navigate(page);
        });
    });

    // Mobile toggle
    var mobileToggle = document.getElementById('appMobileToggle');
    var sidebar = document.getElementById('appSidebar');
    if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', function() { sidebar.classList.toggle('open'); });
    }

    // Action handlers
    document.querySelectorAll('[data-action]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var action = this.getAttribute('data-action');
            switch(action) {
                case 'upload-doc': showToast('Document upload dialog opened'); break;
                case 'message-attorney': navigate('messages'); break;
                case 'check-status': navigate('status'); break;
                case 'connect-attorney': showToast('Consultation request sent to attorney'); break;
                case 'schedule-consultation': showToast('Scheduling consultation...'); break;
                case 'start-interview-prep': showToast('Starting mock interview session...'); break;
                case 'wizard-next': wizardNext(); break;
                case 'wizard-prev': wizardPrev(); break;
                case 'send-message': showToast('Message sent'); break;
                case 'calculate-cost': showToast('Cost estimate calculated'); break;
                default: showToast(action + ' triggered');
            }
        });
    });

    // Wizard navigation
    function wizardNext() {
        if (wizardStep < totalSteps) {
            wizardStep++;
            updateWizard();
        }
    }

    function wizardPrev() {
        if (wizardStep > 1) {
            wizardStep--;
            updateWizard();
        }
    }

    function updateWizard() {
        document.querySelectorAll('.app-wizard-step').forEach(function(step, i) {
            step.classList.remove('active', 'completed');
            if (i + 1 < wizardStep) step.classList.add('completed');
            else if (i + 1 === wizardStep) step.classList.add('active');
        });
        document.querySelectorAll('.app-wizard-panel').forEach(function(panel, i) {
            panel.style.display = (i + 1 === wizardStep) ? 'block' : 'none';
        });
        var progress = document.getElementById('appWizardProgress');
        if (progress) progress.style.width = ((wizardStep / totalSteps) * 100) + '%';
    }

    // Visa type selection
    document.querySelectorAll('.app-visa-card').forEach(function(card) {
        card.addEventListener('click', function() {
            document.querySelectorAll('.app-visa-card').forEach(function(c) { c.classList.remove('selected'); });
            this.classList.add('selected');
            selectedVisaType = this.getAttribute('data-visa');
            showToast('Selected: ' + this.querySelector('h4').textContent);
        });
    });

    // Country selection
    document.querySelectorAll('.app-country-card').forEach(function(card) {
        card.addEventListener('click', function() {
            document.querySelectorAll('.app-country-card').forEach(function(c) { c.classList.remove('selected'); });
            this.classList.add('selected');
            selectedCountry = this.getAttribute('data-country');
            showToast('Selected: ' + this.querySelector('.name').textContent);
        });
    });

    // Render messages
    function renderMessages() {
        var chatArea = document.getElementById('appChatMessages');
        if (!chatArea || !demoData.messages[0]) return;
        var html = '';
        demoData.messages[0].messages.forEach(function(m) {
            html += '<div class="app-chat-bubble ' + (m.sent ? 'sent' : 'received') + '">' + m.content + '<div style="font-size:11px;opacity:0.7;margin-top:4px">' + m.time + '</div></div>';
        });
        chatArea.innerHTML = html;
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    function init() {
        renderMessages();
        updateWizard();
        navigate('dashboard');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.appSPA = { navigate: navigate, showToast: showToast };
})();
