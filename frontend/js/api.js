/**
 * API client for Verom.ai backend
 */

const API = {
    BASE_URL: '/api',

    async request(method, path, body = null) {
        const options = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (body !== null) {
            options.body = JSON.stringify(body);
        }
        const resp = await fetch(`${this.BASE_URL}${path}`, options);
        if (resp.status === 204) return null;
        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.detail || `Request failed (${resp.status})`);
        }
        return data;
    },

    // ----------------------------------------
    // Employee endpoints
    // ----------------------------------------

    async createEmployee(employee) {
        return this.request('POST', '/employees', employee);
    },

    async listEmployees() {
        return this.request('GET', '/employees');
    },

    async getEmployee(id) {
        return this.request('GET', `/employees/${encodeURIComponent(id)}`);
    },

    async deleteEmployee(id) {
        return this.request('DELETE', `/employees/${encodeURIComponent(id)}`);
    },

    // ----------------------------------------
    // Compliance endpoints
    // ----------------------------------------

    async checkEmployee(employeeId, asOf = null) {
        const body = asOf ? { as_of: asOf } : {};
        return this.request('POST', `/compliance/check/${encodeURIComponent(employeeId)}`, body);
    },

    async generateReport(asOf = null) {
        const body = asOf ? { as_of: asOf } : {};
        return this.request('POST', '/compliance/report', body);
    },

    // ----------------------------------------
    // Case endpoints
    // ----------------------------------------

    async createCase(caseData) {
        return this.request('POST', '/cases', caseData);
    },

    async listCases() {
        return this.request('GET', '/cases');
    },

    async getCase(id) {
        return this.request('GET', `/cases/${encodeURIComponent(id)}`);
    },

    async updateCaseStatus(id, status) {
        return this.request('PATCH', `/cases/${encodeURIComponent(id)}/status`, { status });
    },

    async deleteCase(id) {
        return this.request('DELETE', `/cases/${encodeURIComponent(id)}`);
    },

    // ----------------------------------------
    // Document endpoints
    // ----------------------------------------

    async createDocument(doc) {
        return this.request('POST', '/documents', doc);
    },

    async listDocuments(employee_id = null, category = null) {
        const params = new URLSearchParams();
        if (employee_id) params.set('employee_id', employee_id);
        if (category) params.set('category', category);
        const qs = params.toString();
        return this.request('GET', `/documents${qs ? '?' + qs : ''}`);
    },

    async getDocument(id) {
        return this.request('GET', `/documents/${encodeURIComponent(id)}`);
    },

    async deleteDocument(id) {
        return this.request('DELETE', `/documents/${encodeURIComponent(id)}`);
    },

    async getExpiringDocuments(days = null) {
        const qs = days !== null ? `?days=${encodeURIComponent(days)}` : '';
        return this.request('GET', `/documents/expiring${qs}`);
    },

    // ----------------------------------------
    // Audit endpoints
    // ----------------------------------------

    async getAuditTrail(employee_id = null, limit = null) {
        const params = new URLSearchParams();
        if (employee_id) params.set('employee_id', employee_id);
        if (limit !== null) params.set('limit', limit);
        const qs = params.toString();
        return this.request('GET', `/audit-trail${qs ? '?' + qs : ''}`);
    },

    async getAuditStats() {
        return this.request('GET', '/audit-trail/stats');
    },

    async runICEAudit() {
        return this.request('POST', '/audit/ice-simulation', {});
    },

    // ----------------------------------------
    // PAF endpoints
    // ----------------------------------------

    async createPAF(paf) {
        return this.request('POST', '/pafs', paf);
    },

    async listPAFs(employee_id = null) {
        const qs = employee_id ? `?employee_id=${encodeURIComponent(employee_id)}` : '';
        return this.request('GET', `/pafs${qs}`);
    },

    async getPAF(id) {
        return this.request('GET', `/pafs/${encodeURIComponent(id)}`);
    },

    async updatePAFDocument(paf_id, body) {
        return this.request('PATCH', `/pafs/${encodeURIComponent(paf_id)}/document`, body);
    },

    async deletePAF(id) {
        return this.request('DELETE', `/pafs/${encodeURIComponent(id)}`);
    },

    // ----------------------------------------
    // Regulatory endpoints
    // ----------------------------------------

    async getFeed() {
        return this.request('GET', '/regulatory/feed');
    },

    async getUpdates(category = null, impact_level = null, action_required = null) {
        const params = new URLSearchParams();
        if (category) params.set('category', category);
        if (impact_level) params.set('impact_level', impact_level);
        if (action_required !== null) params.set('action_required', action_required);
        const qs = params.toString();
        return this.request('GET', `/regulatory/updates${qs ? '?' + qs : ''}`);
    },

    async getProcessingTimes(form_type = null) {
        const qs = form_type ? `?form_type=${encodeURIComponent(form_type)}` : '';
        return this.request('GET', `/regulatory/processing-times${qs}`);
    },

    async getVisaBulletin(category = null, country = null) {
        const params = new URLSearchParams();
        if (category) params.set('category', category);
        if (country) params.set('country', country);
        const qs = params.toString();
        return this.request('GET', `/regulatory/visa-bulletin${qs ? '?' + qs : ''}`);
    },

    // ----------------------------------------
    // Global endpoints
    // ----------------------------------------

    async getCountries() {
        return this.request('GET', '/global/countries');
    },

    async getCountry(code) {
        return this.request('GET', `/global/countries/${encodeURIComponent(code)}`);
    },

    async createAssignment(assignment) {
        return this.request('POST', '/global/assignments', assignment);
    },

    async listAssignments(employee_id = null) {
        const qs = employee_id ? `?employee_id=${encodeURIComponent(employee_id)}` : '';
        return this.request('GET', `/global/assignments${qs}`);
    },

    async deleteAssignment(id) {
        return this.request('DELETE', `/global/assignments/${encodeURIComponent(id)}`);
    },

    async addTravel(travel) {
        return this.request('POST', '/global/travel', travel);
    },

    async listTravel(employee_id = null) {
        const qs = employee_id ? `?employee_id=${encodeURIComponent(employee_id)}` : '';
        return this.request('GET', `/global/travel${qs}`);
    },

    async getGlobalCompliance(employee_id) {
        return this.request('GET', `/global/compliance/${encodeURIComponent(employee_id)}`);
    },

    // ----------------------------------------
    // HRIS / Integration endpoints
    // ----------------------------------------

    async getProviders() {
        return this.request('GET', '/hris/providers');
    },

    async createIntegration(integration) {
        return this.request('POST', '/hris/integrations', integration);
    },

    async listIntegrations() {
        return this.request('GET', '/hris/integrations');
    },

    async getIntegration(id) {
        return this.request('GET', `/hris/integrations/${encodeURIComponent(id)}`);
    },

    async updateIntegrationStatus(id, body) {
        return this.request('PATCH', `/hris/integrations/${encodeURIComponent(id)}/status`, body);
    },

    async runSync(id) {
        return this.request('POST', `/hris/integrations/${encodeURIComponent(id)}/sync`, {});
    },

    async deleteIntegration(id) {
        return this.request('DELETE', `/hris/integrations/${encodeURIComponent(id)}`);
    },

    async getDefaultMappings(provider) {
        return this.request('GET', `/hris/mappings/${encodeURIComponent(provider)}`);
    },
};
