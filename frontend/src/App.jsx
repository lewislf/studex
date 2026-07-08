// Mantine imports
import '@mantine/core/styles.css';
import { Outlet, Navigate, useNavigate } from 'react-router';
import Header from './components/Common/Header.jsx';
import Footer from './components/Common/Footer.jsx';
import { AppShell } from '@mantine/core';

import profileImage from './assets/generic-profile.svg'
import { parseUserProfile } from './utils/userHelpers.js'
import { getSession, clearSession } from './hooks/useAuth.js'

export default function App() {
    const navigate = useNavigate();

    // Without an active session, the app requires login before any screen.
    const session = getSession();
    if (!session) {
        return <Navigate to="/login" replace />;
    }

    // The session already matches the backend user shape (flat id/name/email +
    // gamification/counters), so it maps straight through the profile parser.
    const user = parseUserProfile(session);

    function handleLogout() {
        clearSession();
        navigate('/login', { replace: true });
    }

    return (
        // Outer level of the application
        <AppShell header={{ height: 60 }} footer={{ height: 60 }} padding="md">
            {/* Header */}
            <AppShell.Header>
                <Header
                    name={user.name}
                    avatarUrl={user.avatar || profileImage}
                    onLogout={handleLogout}
                />
            </AppShell.Header>

            {/* Content */}
            <AppShell.Main bg="blue.3">
                <Outlet context={user} />
            </AppShell.Main>

            <Footer />
        </AppShell>
    );
}
