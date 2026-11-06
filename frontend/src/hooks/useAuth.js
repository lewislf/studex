import { useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL;
const STORAGE_KEY = 'studex_user';

/**
 * Persists the authenticated user (including JWT token) in localStorage.
 * @param {{id: number, name: string, email: string, token: string}} user
 */
export function saveSession(user) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

/**
 * Retrieves the authenticated user from localStorage, or null.
 */
export function getSession() {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
}

/**
 * Clears the current session.
 */
export function clearSession() {
    localStorage.removeItem(STORAGE_KEY);
}

/**
 * Returns Authorization header object for authenticated requests.
 * Returns an empty object when no session exists.
 * @returns {Record<string, string>}
 */
export function getAuthHeaders() {
    const session = getSession();
    if (!session?.token) return {};
    return { Authorization: `Bearer ${session.token}` };
}

/**
 * Hook exposing the register and login calls against the backend API.
 * Manages loading and error state natively.
 */
export function useAuth() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    /**
     * Registers a new user and opens the session.
     * @returns {Promise<Object|null>} saved user, or null on error.
     */
    const register = async ({ name, email, password }) => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_URL}/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password }),
            });

            if (!response.ok) {
                // 409 = email already registered; use the backend message when present.
                const detail = await response.json().catch(() => null);
                throw new Error(
                    detail?.error
                        ? (response.status === 409 ? 'Este email já está cadastrado.' : detail.error)
                        : 'Não foi possível criar a conta. Verifique os dados.'
                );
            }

            const { id, token } = await response.json();
            const user = { id, name, email, token };
            saveSession(user);
            return user;
        } catch (err) {
            setError(err.message || 'Houve algum erro durante o cadastro');
            return null;
        } finally {
            setLoading(false);
        }
    };

    /**
     * Authenticates an existing user and opens the session.
     * @returns {Promise<Object|null>} authenticated user, or null on error.
     */
    const login = async ({ email, password }) => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_URL}/users/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });

            if (!response.ok) {
                throw new Error('Email ou senha inválidos.');
            }

            const user = await response.json();
            saveSession(user);
            return user;
        } catch (err) {
            setError(err.message || 'Houve algum erro durante o login');
            return null;
        } finally {
            setLoading(false);
        }
    };

    return { register, login, loading, error };
}
