// Mantine imports
import '@mantine/core/styles.css';
import { useState, useCallback, useEffect } from 'react';
import { Outlet, Navigate, useNavigate } from 'react-router';
import Header from './components/Common/Header.jsx';
import Footer from './components/Common/Footer.jsx';
import { AppShell } from '@mantine/core';

import profileImage from './assets/generic-profile.svg'
import { parseUserProfile } from './utils/userHelpers.js'
import { getSession, saveSession, clearSession, getAuthHeaders } from './hooks/useAuth.js'

const API_URL = import.meta.env.VITE_API_URL;

export default function App() {
    const navigate = useNavigate();

    // All hooks run unconditionally, on every render: sessionData can go
    // from a stale cached value to null WITHIN this same mounted instance
    // (refreshUser clearing it below on a 404), so the "no session" early
    // return must come AFTER every hook, never before.
    const [sessionData, setSessionData] = useState(() => getSession());

    const refreshUser = useCallback(async () => {
        const session = getSession();
        if (!session?.id) return;
        try {
            const res = await fetch(`${API_URL}/users/${session.id}`, { headers: getAuthHeaders() });
            if (res.ok) {
                const updated = await res.json();
                const withToken = { ...updated, token: session.token };
                saveSession(withToken);
                setSessionData(withToken);
            } else if (res.status === 404) {
                clearSession();
                setSessionData(null);
            }
        } catch {
            // Network hiccup: keep the cached session data on screen.
        }
    }, []);

    // Counters (resumos/mapas/flashcards) are only as fresh as the session
    // saved in localStorage, which can go stale between logins. Refresh once
    // whenever the app shell mounts, not only right after an upload.
    useEffect(() => {
        // refreshUser awaits the network before any setState, so it cannot
        // trigger a synchronous cascading render here.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        refreshUser();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    if (!sessionData) {
        return <Navigate to="/login" replace />;
    }

    const user = parseUserProfile(sessionData);

    function handleLogout() {
        clearSession();
        navigate('/login', { replace: true });
    }

    return (
        <AppShell header={{ height: 60 }} footer={{ height: 60 }} padding="md">
            <AppShell.Header>
                <Header
                    name={user.name}
                    avatarUrl={user.avatar || profileImage}
                    onLogout={handleLogout}
                />
            </AppShell.Header>

            <AppShell.Main bg="blue.3">
                <Outlet context={{ ...user, refreshUser }} />
            </AppShell.Main>

            <Footer />
        </AppShell>
    );
}
