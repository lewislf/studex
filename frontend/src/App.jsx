// Mantine imports
import '@mantine/core/styles.css';
import { Outlet } from 'react-router';
import Header from './components/Common/Header.jsx';
import Footer from './components/Common/Footer.jsx';
import { AppShell } from '@mantine/core';

export default function App() {
    return (
        // Outer level of the application
        <AppShell header={{ height: 60 }} footer={{ height: 60 }} padding="md">
            {/* Header */}
            <AppShell.Header>
                <Header />
            </AppShell.Header>

            {/* Content */}
            <AppShell.Main>
                <Outlet />
            </AppShell.Main>

            {/* Footer */}
            <AppShell.Footer>
                <Footer />
            </AppShell.Footer>
        </AppShell>
    );
}
