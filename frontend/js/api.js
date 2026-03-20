/**
 * API client for ImmigrationAI backend
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

    // Employee endpoints
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

    // Compliance endpoints
    async checkEmployee(employeeId, asOf = null) {
        const body = asOf ? { as_of: asOf } : {};
        return this.request('POST', `/compliance/check/${encodeURIComponent(employeeId)}`, body);
    },

    async generateReport(asOf = null) {
        const body = asOf ? { as_of: asOf } : {};
        return this.request('POST', '/compliance/report', body);
    },

    // Case endpoints
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
};
