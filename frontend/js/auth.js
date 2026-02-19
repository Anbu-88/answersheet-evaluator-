/**
 * ExamAI - Auth Module
 * Handles JWT token storage, login/logout, and role-based redirects.
 */

const API_BASE = 'http://localhost:8000';

const Auth = {
    getToken() {
        return localStorage.getItem('examai_token');
    },

    getUser() {
        const data = localStorage.getItem('examai_user');
        return data ? JSON.parse(data) : null;
    },

    isLoggedIn() {
        return !!this.getToken();
    },

    async login(email, password) {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Login failed');
        }

        const data = await res.json();
        localStorage.setItem('examai_token', data.access_token);
        localStorage.setItem('examai_user', JSON.stringify(data.user));
        return data;
    },

    logout() {
        localStorage.removeItem('examai_token');
        localStorage.removeItem('examai_user');
        window.location.href = '/index.html';
    },

    redirectToDashboard() {
        const user = this.getUser();
        if (!user) return;
        switch (user.role) {
            case 'admin': window.location.href = '/admin.html'; break;
            case 'teacher': window.location.href = '/teacher.html'; break;
            case 'student': window.location.href = '/student.html'; break;
            default: window.location.href = '/index.html';
        }
    },

    /** Call this on protected pages to guard access */
    requireAuth(allowedRoles = []) {
        if (!this.isLoggedIn()) {
            window.location.href = '/index.html';
            return false;
        }
        const user = this.getUser();
        if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
            window.location.href = '/index.html';
            return false;
        }
        return true;
    }
};
