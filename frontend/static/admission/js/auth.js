// Copia local de auth.js servida desde /static/admission/js/auth.js

function jwtPayload(token) {
    try {
        const part = token.split('.')[1];
        const base = part.replace(/-/g, '+').replace(/_/g, '/');
        const json = decodeURIComponent(atob(base).split('').map(c=> '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)).join(''));
        return JSON.parse(json);
    } catch (e) {
        return null;
    }
}

function getStoredToken() {
    try {
        return localStorage.getItem('authToken') || localStorage.getItem('auth_token') || (function() {
            const m = document.cookie.match(/(^|; )auth_token=([^;]+)/);
            return m ? decodeURIComponent(m[2]) : null;
        })();
    } catch (e) {
        return null;
    }
}

function isTokenValid(token) {
    if (!token) return false;
    if (token.startsWith('FHIR-')) {
        try {
            const b = token.slice(5);
            const obj = JSON.parse(atob(b));
            return obj.expires > (Date.now()/1000);
        } catch (e) { return false; }
    }
    const payload = jwtPayload(token);
    return payload && payload.exp && (payload.exp > (Date.now()/1000));
}

function wrapFHIR(accessToken) {
    const payload = jwtPayload(accessToken);
    if (!payload || !payload.exp) throw new Error('No exp in token');
    const obj = {expires: payload.exp, token: accessToken};
    return 'FHIR-' + btoa(JSON.stringify(obj));
}

function unwrapFHIR(token) {
    if (!token) return null;
    if (token.startsWith('FHIR-')) {
        try {
            const b = token.slice(5);
            const obj = JSON.parse(atob(b));
            return obj.token || null;
        } catch (e) {
            return null;
        }
    }
    return token;
}

function requireAuth() {
    const token = getStoredToken();
    if (!token || !isTokenValid(token)) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

window.auth = {
    jwtPayload,
    getStoredToken,
    isTokenValid,
    wrapFHIR,
    requireAuth
};
window.auth.unwrapFHIR = unwrapFHIR;
