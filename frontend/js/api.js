/**
 * ExamAI - API Module
 * Fetch wrapper with automatic JWT auth headers and error handling.
 */

const Api = {
    BASE: 'http://localhost:8000',

    _headers(extra = {}) {
        const headers = { ...extra };
        const token = Auth.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    },

    async get(path) {
        const res = await fetch(`${this.BASE}${path}`, {
            headers: this._headers(),
        });
        return this._handle(res);
    },

    async post(path, body = null) {
        const opts = {
            method: 'POST',
            headers: this._headers({ 'Content-Type': 'application/json' }),
        };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(`${this.BASE}${path}`, opts);
        return this._handle(res);
    },

    async put(path, body) {
        const res = await fetch(`${this.BASE}${path}`, {
            method: 'PUT',
            headers: this._headers({ 'Content-Type': 'application/json' }),
            body: JSON.stringify(body),
        });
        return this._handle(res);
    },

    async del(path) {
        const res = await fetch(`${this.BASE}${path}`, {
            method: 'DELETE',
            headers: this._headers(),
        });
        return this._handle(res);
    },

    async upload(path, formData) {
        const res = await fetch(`${this.BASE}${path}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${Auth.getToken()}` },
            body: formData,
        });
        return this._handle(res);
    },

    async downloadBlob(path) {
        const res = await fetch(`${this.BASE}${path}`, {
            headers: { 'Authorization': `Bearer ${Auth.getToken()}` },
        });
        if (!res.ok) throw new Error('Download failed');
        return await res.blob();
    },

    async _handle(res) {
        if (res.status === 401) {
            Auth.logout();
            throw new Error('Session expired');
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(err.detail || 'Request failed');
        }
        return res.json();
    }
};
