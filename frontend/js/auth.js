/**
 * Verom.ai — Client-side auth guard.
 * Include this script on any protected page.
 * It checks for a valid token in localStorage and redirects to /login if missing.
 */
(function() {
    'use strict';

    const TOKEN_KEY = 'verom_token';
    const USER_KEY = 'verom_user';

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function getUser() {
        try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
        catch { return null; }
    }

    function logout() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        window.location.href = '/login';
    }

    // Expose globally for use in page scripts
    window.veromAuth = { getToken, getUser, logout };

    // Guard: redirect to login if no token
    if (!getToken()) {
        window.location.href = '/login';
        return;
    }

    // Set avatar initials from user data
    var user = getUser();
    if (user) {
        var initials = ((user.first_name || '')[0] || '') + ((user.last_name || '')[0] || '');
        var avatar = document.getElementById('userAvatar');
        if (avatar && initials) avatar.textContent = initials.toUpperCase();
    }

    // Verify token is still valid via /api/auth/me
    fetch('/api/auth/me', {
        headers: { 'Authorization': 'Bearer ' + getToken() },
    }).then(resp => {
        if (!resp.ok) {
            logout();
        }
    }).catch(() => {
        // Network error — don't log out, let page work offline
    });
})();
