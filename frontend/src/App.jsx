// Mantine imports
import '@mantine/core/styles.css';
import { Outlet } from 'react-router';
import Header from './components/Common/Header.jsx';
import Footer from './components/Common/Footer.jsx';
import { AppShell } from '@mantine/core';

import profileImage from './assets/generic-profile.svg'
import { parseUserProfile } from './utils/userHelpers.js'
import mock from './config/userProfileMock.json'

export default function App() {
    const user = parseUserProfile(mock);

    return (
        // Outer level of the application
        <AppShell header={{ height: 60 }} footer={{ height: 60 }} padding="md">
            {/* Header */}
            <AppShell.Header>
                <Header 
                    name={user.name} 
                    avatarUrl={user.avatar || profileImage} 
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
