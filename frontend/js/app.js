/**
 * ImmigrationAI - Main Application
 */

(function () {
    'use strict';

    // ========================================
    // State
    // ========================================
    let employees = [];
    let cases = [];
    let lastReport = null;
    let currentPage = 'dashboard';

    // ========================================
    // Navigation
    // ========================================

    function initNavigation() {
        document.querySelectorAll('[data-page]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                navigateTo(link.dataset.page);
            });
        });

        document.getElementById('navToggle').addEventListener('click', () => {
            document.getElementById('navLinks').classList.toggle('open');
        });
    }

    function navigateTo(page) {
        currentPage = page;

        // Update nav links
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        document.querySelectorAll(`.nav-link[data-page="${page}"]`).forEach(l => l.classList.add('active'));

        // Show page
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const pageEl = document.getElementById(`page-${page}`);
        if (pageEl) pageEl.classList.add('active');

        // Close mobile nav
        document.getElementById('navLinks').classList.remove('open');

        // Refresh page data
        refreshCurrentPage();
    }

    function refreshCurrentPage() {
        switch (currentPage) {
            case 'dashboard': refreshDashboard(); break;
            case 'employees': renderEmployeeTable(); break;
            case 'compliance': break;
            case 'cases': renderCases(); break;
            case 'reports': break;
            case 'alerts': renderAlerts(); break;
        }
    }

    // ========================================
    // Toast Notifications
    // ========================================

    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // ========================================
    // Data Loading
    // ========================================

    async function loadAllData() {
        try {
            const [empData, caseData] = await Promise.all([
                API.listEmployees(),
                API.listCases().catch(() => []),
            ]);
            employees = empData || [];
            cases = caseData || [];
        } catch (err) {
            console.error('Failed to load data:', err);
            showToast('Failed to load data. Please refresh.', 'error');
        }
    }

    async function runFullScan() {
        try {
            lastReport = await API.generateReport();
            refreshDashboard();
            showToast('Compliance scan complete', 'success');
        } catch (err) {
            showToast('Failed to run compliance scan', 'error');
        }
    }

    // ========================================
    // Dashboard
    // ========================================

    async function refreshDashboard() {
        // Always reload employees first
        try {
            employees = await API.listEmployees();
        } catch (e) { /* use cached */ }

        try {
            lastReport = await API.generateReport();
        } catch (e) { /* use cached */ }

        const total = employees.length;
        const report = lastReport;

        // Stats
        document.getElementById('statTotal').textContent = total;
        document.getElementById('statCompliant').textContent = report ? report.compliant_count : total;
        document.getElementById('statExpiring').textContent = report ? report.expiring_soon_count : 0;
        document.getElementById('statNonCompliant').textContent = report ? report.non_compliant_count : 0;

        // Compliance Rate
        const rate = report ? report.compliance_rate || (total === 0 ? 100 : 0) : 100;
        document.getElementById('complianceRate').textContent = rate.toFixed(1) + '%';
        const fill = document.getElementById('complianceFill');
        fill.style.width = rate + '%';
        fill.className = 'meter-fill' + (rate < 50 ? ' danger' : rate < 80 ? ' warning' : '');
        document.getElementById('complianceRate').style.color =
            rate >= 80 ? 'var(--success)' : rate >= 50 ? 'var(--warning)' : 'var(--danger)';

        // Notification badge
        const alertCount = report ? (report.alerts || []).length : 0;
        const badge = document.getElementById('notifBadge');
        badge.textContent = alertCount;
        badge.style.display = alertCount > 0 ? 'flex' : 'none';

        // Risk Summary
        const risks = report ? (report.risk_summary || {}) : {};
        const maxRisk = Math.max(1, ...Object.values(risks));
        ['critical', 'high', 'medium', 'low'].forEach(level => {
            const count = risks[level] || 0;
            const pct = (count / maxRisk) * 100;
            const el = document.getElementById('risk' + level.charAt(0).toUpperCase() + level.slice(1));
            if (el) el.style.width = pct + '%';
            const countEl = document.getElementById('risk' + level.charAt(0).toUpperCase() + level.slice(1) + 'Count');
            if (countEl) countEl.textContent = count;
        });

        // Recent Alerts
        renderRecentAlerts(report ? report.alerts || [] : []);

        // Upcoming Expirations
        renderUpcomingExpirations();

        // Visa Distribution
        renderVisaDistribution();
    }

    function renderRecentAlerts(alerts) {
        const container = document.getElementById('recentAlerts');
        if (!alerts.length) {
            container.innerHTML = '<div class="empty-state"><span class="empty-icon">&#9989;</span><p>No alerts. All employees are compliant.</p></div>';
            return;
        }
        container.innerHTML = alerts.slice(0, 5).map(a => `
            <div class="violation-item">
                <div class="violation-indicator ${a.risk_level}"></div>
                <div class="violation-content">
                    <div class="violation-header">
                        <span class="violation-title">${escapeHtml(a.title)}</span>
                        <span class="badge badge-${riskBadgeClass(a.risk_level)}">${a.risk_level}</span>
                    </div>
                    <div class="violation-desc">${escapeHtml(a.description)}</div>
                </div>
            </div>
        `).join('');
    }

    function renderUpcomingExpirations() {
        const container = document.getElementById('upcomingExpirations');
        const expiring = employees
            .filter(e => e.visa_expiration_date)
            .map(e => ({ ...e, daysLeft: daysBetween(new Date(), new Date(e.visa_expiration_date)) }))
            .filter(e => e.daysLeft > 0 && e.daysLeft <= 90)
            .sort((a, b) => a.daysLeft - b.daysLeft)
            .slice(0, 5);

        if (!expiring.length) {
            container.innerHTML = '<div class="empty-state"><span class="empty-icon">&#128197;</span><p>No upcoming expirations in the next 90 days.</p></div>';
            return;
        }

        container.innerHTML = expiring.map(e => `
            <div class="violation-item">
                <div class="violation-indicator ${e.daysLeft <= 30 ? 'high' : 'medium'}"></div>
                <div class="violation-content">
                    <div class="violation-header">
                        <span class="violation-title">${escapeHtml(e.first_name)} ${escapeHtml(e.last_name)}</span>
                        <span class="badge badge-${e.daysLeft <= 30 ? 'danger' : 'warning'}">${e.daysLeft} days</span>
                    </div>
                    <div class="violation-desc">${e.visa_type} expires ${e.visa_expiration_date}</div>
                </div>
            </div>
        `).join('');
    }

    function renderVisaDistribution() {
        const container = document.getElementById('visaDistribution');
        if (!employees.length) {
            container.innerHTML = '<div class="empty-state"><span class="empty-icon">&#128202;</span><p>Add employees to see visa distribution.</p></div>';
            return;
        }

        const counts = {};
        employees.forEach(e => { counts[e.visa_type] = (counts[e.visa_type] || 0) + 1; });
        const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
        const max = Math.max(1, ...sorted.map(s => s[1]));
        const colors = ['#2563eb', '#059669', '#d97706', '#dc2626', '#0891b2', '#7c3aed', '#ec4899', '#f97316'];

        container.innerHTML = '<div class="risk-bars">' + sorted.map(([type, count], i) => `
            <div class="risk-row">
                <span class="risk-label" style="width:100px">${escapeHtml(type)}</span>
                <div class="risk-bar">
                    <div class="risk-fill" style="width:${(count/max)*100}%;background:${colors[i % colors.length]}"></div>
                </div>
                <span class="risk-count">${count}</span>
            </div>
        `).join('') + '</div>';
    }

    // ========================================
    // Employees
    // ========================================

    function renderEmployeeTable() {
        const tbody = document.getElementById('employeeTableBody');
        const emptyState = document.getElementById('employeeEmptyState');
        const table = document.getElementById('employeeTable');
        const search = (document.getElementById('employeeSearch').value || '').toLowerCase();
        const visaFilter = document.getElementById('visaFilter').value;

        let filtered = employees;
        if (search) {
            filtered = filtered.filter(e =>
                (e.first_name + ' ' + e.last_name).toLowerCase().includes(search) ||
                e.email.toLowerCase().includes(search) ||
                (e.department || '').toLowerCase().includes(search)
            );
        }
        if (visaFilter) {
            filtered = filtered.filter(e => e.visa_type === visaFilter);
        }

        if (!filtered.length) {
            table.style.display = 'none';
            emptyState.style.display = '';
            return;
        }

        table.style.display = '';
        emptyState.style.display = 'none';

        tbody.innerHTML = filtered.map(e => {
            const days = e.visa_expiration_date ? daysBetween(new Date(), new Date(e.visa_expiration_date)) : null;
            const riskClass = days === null ? 'gray' : days <= 0 ? 'danger' : days <= 30 ? 'warning' : days <= 90 ? 'info' : 'success';
            const riskLabel = days === null ? 'N/A' : days <= 0 ? 'Expired' : days <= 30 ? 'High' : days <= 90 ? 'Medium' : 'Low';
            return `<tr>
                <td><strong>${escapeHtml(e.first_name)} ${escapeHtml(e.last_name)}</strong><br><span style="font-size:12px;color:var(--gray-400)">${escapeHtml(e.email)}</span></td>
                <td>${escapeHtml(e.department || '-')}</td>
                <td><span class="badge badge-info">${escapeHtml(e.visa_type)}</span></td>
                <td><span class="badge badge-${statusBadge(e.visa_status)}">${e.visa_status.replace('_', ' ')}</span></td>
                <td>${e.visa_expiration_date || '-'}${days !== null ? ` <small>(${days}d)</small>` : ''}</td>
                <td>${e.i9_completed ? '<span class="badge badge-success">Done</span>' : '<span class="badge badge-danger">Missing</span>'}</td>
                <td><span class="badge badge-${riskClass}">${riskLabel}</span></td>
                <td>
                    <div class="action-btn-group">
                        <button class="action-btn" onclick="App.checkSingleEmployee('${escapeHtml(e.id)}')">Check</button>
                        <button class="action-btn danger" onclick="App.deleteEmployee('${escapeHtml(e.id)}')">Delete</button>
                    </div>
                </td>
            </tr>`;
        }).join('');
    }

    // ========================================
    // Cases
    // ========================================

    function renderCases() {
        const emptyState = document.getElementById('casesEmptyState');
        const stages = { draft: [], filed: [], pending: [], rfe_received: [], approved: [] };

        cases.forEach(c => {
            const key = c.status === 'rfe_responded' ? 'rfe_received' : c.status;
            if (stages[key]) stages[key].push(c);
        });

        const hasAnyCases = cases.length > 0;
        emptyState.style.display = hasAnyCases ? 'none' : '';
        document.querySelector('.pipeline').style.display = hasAnyCases ? '' : 'none';

        const stageMap = {
            draft: 'caseDraft',
            filed: 'caseFiled',
            pending: 'casePending',
            rfe_received: 'caseRFE',
            approved: 'caseApproved',
        };
        const countMap = {
            draft: 'caseDraftCount',
            filed: 'caseFiledCount',
            pending: 'casePendingCount',
            rfe_received: 'caseRFECount',
            approved: 'caseApprovedCount',
        };

        Object.entries(stages).forEach(([stage, items]) => {
            const el = document.getElementById(stageMap[stage]);
            const countEl = document.getElementById(countMap[stage]);
            if (countEl) countEl.textContent = items.length;
            if (el) {
                el.innerHTML = items.map(c => {
                    const emp = employees.find(e => e.id === c.employee_id);
                    return `<div class="case-card">
                        <div class="case-card-type">${escapeHtml(c.case_type)}</div>
                        <div class="case-card-employee">${emp ? escapeHtml(emp.first_name + ' ' + emp.last_name) : c.employee_id}</div>
                        ${c.receipt_number ? `<div class="case-card-receipt">${escapeHtml(c.receipt_number)}</div>` : ''}
                    </div>`;
                }).join('');
            }
        });
    }

    // ========================================
    // Compliance Check
    // ========================================

    async function runComplianceCheck() {
        try {
            lastReport = await API.generateReport();
            renderViolations(lastReport.violations || []);
            showToast(`Found ${lastReport.violations.length} violation(s)`, lastReport.violations.length ? 'warning' : 'success');
        } catch (err) {
            showToast('Compliance check failed', 'error');
        }
    }

    function renderViolations(violations) {
        const container = document.getElementById('violationsList');
        const filter = document.getElementById('violationFilter').value;

        let filtered = violations;
        if (filter) {
            filtered = filtered.filter(v => v.risk_level === filter);
        }

        if (!filtered.length) {
            container.innerHTML = '<div class="empty-state"><span class="empty-icon">' +
                (violations.length ? '&#128270;' : '&#9989;') +
                '</span><p>' + (violations.length ? 'No violations match the filter.' : 'No violations found. All employees are compliant!') + '</p></div>';
            return;
        }

        container.innerHTML = filtered.map(v => {
            const emp = employees.find(e => e.id === v.employee_id);
            return `<div class="violation-item">
                <div class="violation-indicator ${v.risk_level}"></div>
                <div class="violation-content">
                    <div class="violation-header">
                        <span class="violation-title">${escapeHtml(v.rule_name)}${emp ? ` - ${escapeHtml(emp.first_name)} ${escapeHtml(emp.last_name)}` : ''}</span>
                        <span class="badge badge-${riskBadgeClass(v.risk_level)}">${v.risk_level}</span>
                    </div>
                    <div class="violation-desc">${escapeHtml(v.description)}</div>
                    ${v.recommendation ? `<div class="violation-recommendation">${escapeHtml(v.recommendation)}</div>` : ''}
                </div>
            </div>`;
        }).join('');
    }

    async function checkSingleEmployee(id) {
        try {
            const violations = await API.checkEmployee(id);
            navigateTo('compliance');
            renderViolations(violations);
            const emp = employees.find(e => e.id === id);
            const name = emp ? `${emp.first_name} ${emp.last_name}` : id;
            showToast(`${violations.length} issue(s) found for ${name}`, violations.length ? 'warning' : 'success');
        } catch (err) {
            showToast('Compliance check failed: ' + err.message, 'error');
        }
    }

    // ========================================
    // Reports
    // ========================================

    async function generateReport() {
        try {
            lastReport = await API.generateReport();
            renderReportData(lastReport);
            showToast('Report generated', 'success');
        } catch (err) {
            showToast('Failed to generate report', 'error');
        }
    }

    function renderReportData(report) {
        document.getElementById('reportTotal').textContent = report.total_employees;
        document.getElementById('reportCompliant').textContent = report.compliant_count;
        document.getElementById('reportExpiring').textContent = report.expiring_soon_count;
        document.getElementById('reportViolations').textContent = report.violations.length;

        // Violation breakdown by rule
        const byRule = {};
        report.violations.forEach(v => {
            byRule[v.rule_name] = (byRule[v.rule_name] || 0) + 1;
        });

        const colors = { 'Visa Expiration Check': 'var(--danger)', 'I-9 Compliance Check': 'var(--warning)', 'LCA Wage Compliance Check': 'var(--primary)', 'Work Authorization Gap Check': '#7c3aed' };
        const breakdownEl = document.getElementById('violationBreakdown');
        breakdownEl.innerHTML = Object.entries(byRule).map(([name, count]) => `
            <div class="breakdown-item">
                <div class="breakdown-dot" style="background:${colors[name] || 'var(--gray-400)'}"></div>
                <span class="breakdown-name">${escapeHtml(name)}</span>
                <span class="breakdown-count">${count}</span>
            </div>
        `).join('') || '<p style="color:var(--gray-400);font-size:14px">No violations to report.</p>';

        // Detail table
        const tbody = document.getElementById('reportTableBody');
        const empViolations = {};
        report.violations.forEach(v => {
            if (!empViolations[v.employee_id]) empViolations[v.employee_id] = [];
            empViolations[v.employee_id].push(v);
        });

        const rows = employees.map(e => {
            const evs = empViolations[e.id] || [];
            const highest = evs.length ? highestRisk(evs.map(v => v.risk_level)) : 'none';
            return `<tr>
                <td><strong>${escapeHtml(e.first_name)} ${escapeHtml(e.last_name)}</strong></td>
                <td>${escapeHtml(e.visa_type)}</td>
                <td>${e.visa_expiration_date || 'N/A'}</td>
                <td>${evs.length}</td>
                <td>${highest !== 'none' ? `<span class="badge badge-${riskBadgeClass(highest)}">${highest}</span>` : '<span class="badge badge-success">Clean</span>'}</td>
                <td style="font-size:13px;max-width:250px">${evs.length ? escapeHtml(evs[0].recommendation) : 'No action needed'}</td>
            </tr>`;
        });

        tbody.innerHTML = rows.join('') || '<tr><td colspan="6" style="text-align:center;color:var(--gray-400);padding:40px">No employees to report on.</td></tr>';
    }

    function exportCSV() {
        if (!employees.length) {
            showToast('No data to export', 'warning');
            return;
        }

        const report = lastReport;
        const empViolations = {};
        if (report) {
            report.violations.forEach(v => {
                if (!empViolations[v.employee_id]) empViolations[v.employee_id] = [];
                empViolations[v.employee_id].push(v);
            });
        }

        const headers = ['Name', 'Email', 'Department', 'Visa Type', 'Status', 'Expiration', 'I-9 Complete', 'Violations', 'Highest Risk'];
        const rows = employees.map(e => {
            const evs = empViolations[e.id] || [];
            return [
                `${e.first_name} ${e.last_name}`,
                e.email,
                e.department || '',
                e.visa_type,
                e.visa_status,
                e.visa_expiration_date || '',
                e.i9_completed ? 'Yes' : 'No',
                evs.length,
                evs.length ? highestRisk(evs.map(v => v.risk_level)) : 'Clean',
            ];
        });

        const csv = [headers, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `compliance-report-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('Report exported', 'success');
    }

    // ========================================
    // Alerts
    // ========================================

    function renderAlerts() {
        const container = document.getElementById('alertsList');
        const alerts = lastReport ? (lastReport.alerts || []) : [];

        if (!alerts.length) {
            container.innerHTML = '<div class="empty-state"><span class="empty-icon">&#128276;</span><h3>No active alerts</h3><p>All employees are in compliance. Alerts will appear here when issues are detected.</p></div>';
            return;
        }

        container.innerHTML = alerts.map(a => {
            const emp = a.employee_id ? employees.find(e => e.id === a.employee_id) : null;
            return `<div class="alert-item">
                <div class="alert-indicator ${a.risk_level}"></div>
                <div class="alert-content">
                    <div class="alert-title">${escapeHtml(a.title)}</div>
                    <div class="alert-desc">${escapeHtml(a.description)}</div>
                    <div class="alert-meta">
                        ${emp ? `<span>Employee: ${escapeHtml(emp.first_name)} ${escapeHtml(emp.last_name)}</span>` : ''}
                        <span>Risk: ${a.risk_level.toUpperCase()}</span>
                    </div>
                </div>
                <div class="alert-actions">
                    <span class="badge badge-${riskBadgeClass(a.risk_level)}">${a.risk_level}</span>
                </div>
            </div>`;
        }).join('');
    }

    // ========================================
    // Employee Modal
    // ========================================

    let editingEmployeeId = null;

    function openEmployeeModal(employeeId = null) {
        editingEmployeeId = employeeId;
        const modal = document.getElementById('employeeModal');
        const form = document.getElementById('employeeForm');
        const title = document.getElementById('employeeModalTitle');

        form.reset();

        if (employeeId) {
            const emp = employees.find(e => e.id === employeeId);
            if (emp) {
                title.textContent = 'Edit Employee';
                document.getElementById('empFirstName').value = emp.first_name;
                document.getElementById('empLastName').value = emp.last_name;
                document.getElementById('empEmail').value = emp.email;
                document.getElementById('empDepartment').value = emp.department || '';
                document.getElementById('empJobTitle').value = emp.job_title || '';
                document.getElementById('empCitizenship').value = emp.country_of_citizenship;
                document.getElementById('empVisaType').value = emp.visa_type;
                document.getElementById('empVisaStatus').value = emp.visa_status;
                document.getElementById('empVisaExpiration').value = emp.visa_expiration_date || '';
                document.getElementById('empWorkAuthStart').value = emp.work_authorization_start || '';
                document.getElementById('empWorkAuthEnd').value = emp.work_authorization_end || '';
                document.getElementById('empHireDate').value = emp.hire_date || '';
                document.getElementById('empI9Completed').checked = emp.i9_completed;
                document.getElementById('empI9Expiration').value = emp.i9_expiration_date || '';
                document.getElementById('empActualWage').value = emp.actual_wage || '';
                document.getElementById('empPrevailingWage').value = emp.prevailing_wage || '';
                document.getElementById('empWorksiteCity').value = emp.worksite_city || '';
                document.getElementById('empWorksiteState').value = emp.worksite_state || '';
                document.getElementById('empNotes').value = emp.notes || '';
            }
        } else {
            title.textContent = 'Add Employee';
        }

        modal.classList.add('active');
    }

    function closeEmployeeModal() {
        document.getElementById('employeeModal').classList.remove('active');
        editingEmployeeId = null;
    }

    async function saveEmployee(e) {
        e.preventDefault();

        const empData = {
            id: editingEmployeeId || generateId(),
            first_name: document.getElementById('empFirstName').value.trim(),
            last_name: document.getElementById('empLastName').value.trim(),
            email: document.getElementById('empEmail').value.trim(),
            department: document.getElementById('empDepartment').value.trim(),
            job_title: document.getElementById('empJobTitle').value.trim(),
            country_of_citizenship: document.getElementById('empCitizenship').value.trim(),
            visa_type: document.getElementById('empVisaType').value,
            visa_status: document.getElementById('empVisaStatus').value,
            visa_expiration_date: document.getElementById('empVisaExpiration').value || null,
            work_authorization_start: document.getElementById('empWorkAuthStart').value || null,
            work_authorization_end: document.getElementById('empWorkAuthEnd').value || null,
            hire_date: document.getElementById('empHireDate').value || null,
            i9_completed: document.getElementById('empI9Completed').checked,
            i9_expiration_date: document.getElementById('empI9Expiration').value || null,
            actual_wage: parseFloat(document.getElementById('empActualWage').value) || null,
            prevailing_wage: parseFloat(document.getElementById('empPrevailingWage').value) || null,
            worksite_city: document.getElementById('empWorksiteCity').value.trim(),
            worksite_state: document.getElementById('empWorksiteState').value.trim(),
            notes: document.getElementById('empNotes').value.trim(),
        };

        try {
            if (editingEmployeeId) {
                // Delete old and recreate (API doesn't have PUT yet)
                await API.deleteEmployee(editingEmployeeId).catch(() => {});
            }
            await API.createEmployee(empData);
            employees = await API.listEmployees();
            closeEmployeeModal();
            refreshCurrentPage();
            showToast(`Employee ${empData.first_name} ${empData.last_name} saved`, 'success');
        } catch (err) {
            showToast('Failed to save employee: ' + err.message, 'error');
        }
    }

    async function deleteEmployee(id) {
        const emp = employees.find(e => e.id === id);
        const name = emp ? `${emp.first_name} ${emp.last_name}` : id;
        if (!confirm(`Delete ${name}? This cannot be undone.`)) return;

        try {
            await API.deleteEmployee(id);
            employees = await API.listEmployees();
            refreshCurrentPage();
            showToast(`${name} deleted`, 'success');
        } catch (err) {
            showToast('Failed to delete: ' + err.message, 'error');
        }
    }

    // ========================================
    // Case Modal
    // ========================================

    function openCaseModal() {
        const modal = document.getElementById('caseModal');
        const form = document.getElementById('caseForm');
        form.reset();

        // Populate employee dropdown
        const select = document.getElementById('caseEmployee');
        select.innerHTML = '<option value="">Select employee...</option>' +
            employees.map(e => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.first_name)} ${escapeHtml(e.last_name)}</option>`).join('');

        modal.classList.add('active');
    }

    function closeCaseModal() {
        document.getElementById('caseModal').classList.remove('active');
    }

    async function saveCase(e) {
        e.preventDefault();

        const caseData = {
            id: generateId(),
            employee_id: document.getElementById('caseEmployee').value,
            case_type: document.getElementById('caseType').value,
            receipt_number: document.getElementById('caseReceipt').value.trim() || null,
            status: document.getElementById('caseStatus').value,
            priority_date: document.getElementById('casePriorityDate').value || null,
            filed_date: document.getElementById('caseFiledDate').value || null,
            attorney_name: document.getElementById('caseAttorneyName').value.trim(),
            attorney_email: document.getElementById('caseAttorneyEmail').value.trim(),
            notes: document.getElementById('caseNotes').value.trim(),
        };

        try {
            await API.createCase(caseData);
            cases = await API.listCases().catch(() => []);
            closeCaseModal();
            renderCases();
            showToast('Case created', 'success');
        } catch (err) {
            showToast('Failed to create case: ' + err.message, 'error');
        }
    }

    // ========================================
    // Utilities
    // ========================================

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    function generateId() {
        return 'EMP' + Date.now().toString(36).toUpperCase() + Math.random().toString(36).substring(2, 6).toUpperCase();
    }

    function daysBetween(d1, d2) {
        return Math.ceil((d2 - d1) / (1000 * 60 * 60 * 24));
    }

    function riskBadgeClass(level) {
        return { critical: 'danger', high: 'warning', medium: 'info', low: 'gray', info: 'gray' }[level] || 'gray';
    }

    function statusBadge(status) {
        return { active: 'success', expiring_soon: 'warning', expired: 'danger', pending_renewal: 'info', pending_initial: 'info', revoked: 'danger' }[status] || 'gray';
    }

    function highestRisk(levels) {
        const order = ['critical', 'high', 'medium', 'low', 'info'];
        for (const r of order) {
            if (levels.includes(r)) return r;
        }
        return 'info';
    }

    // ========================================
    // Event Binding
    // ========================================

    function bindEvents() {
        // Employee modal
        ['addEmployeeBtn', 'addEmployeeBtnPage', 'addFirstEmployee'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('click', () => openEmployeeModal());
        });
        document.getElementById('closeEmployeeModal').addEventListener('click', closeEmployeeModal);
        document.getElementById('cancelEmployee').addEventListener('click', closeEmployeeModal);
        document.getElementById('employeeForm').addEventListener('submit', saveEmployee);

        // Case modal
        ['addCaseBtn', 'addFirstCase'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('click', openCaseModal);
        });
        document.getElementById('closeCaseModal').addEventListener('click', closeCaseModal);
        document.getElementById('cancelCase').addEventListener('click', closeCaseModal);
        document.getElementById('caseForm').addEventListener('submit', saveCase);

        // Dashboard actions
        document.getElementById('refreshDashboard').addEventListener('click', refreshDashboard);
        document.getElementById('runFullScan').addEventListener('click', runFullScan);

        // Compliance
        document.getElementById('runComplianceCheck').addEventListener('click', runComplianceCheck);
        document.getElementById('violationFilter').addEventListener('change', () => {
            if (lastReport) renderViolations(lastReport.violations || []);
        });

        // Reports
        document.getElementById('generateReport').addEventListener('click', generateReport);
        document.getElementById('exportReport').addEventListener('click', exportCSV);

        // Employee search/filter
        document.getElementById('employeeSearch').addEventListener('input', renderEmployeeTable);
        document.getElementById('visaFilter').addEventListener('change', renderEmployeeTable);

        // Alerts
        document.getElementById('markAllRead').addEventListener('click', () => {
            if (lastReport) lastReport.alerts = [];
            renderAlerts();
            showToast('All alerts marked as resolved', 'success');
        });

        // Notification bell
        document.getElementById('notificationBtn').addEventListener('click', () => navigateTo('alerts'));

        // Close modals on overlay click
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) overlay.classList.remove('active');
            });
        });

        // Escape key closes modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
            }
        });
    }

    // ========================================
    // Init
    // ========================================

    async function init() {
        initNavigation();
        bindEvents();
        await loadAllData();
        refreshDashboard();
    }

    // Expose global functions for inline handlers
    window.App = {
        checkSingleEmployee,
        deleteEmployee,
    };

    // Start
    document.addEventListener('DOMContentLoaded', init);

})();
