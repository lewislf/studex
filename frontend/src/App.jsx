// Mantine imports
import '@mantine/core/styles.css';
import { MantineProvider, AppShell } from '@mantine/core';
import { Outlet } from 'react-router';
import { theme } from './styles/Mantine/theme.js'
import Header from './components/Common/Header.jsx';
import Footer from './components/Common/Footer.jsx';

export default function App() {
    return (
        // Provider for mantine variables and css reset
        <MantineProvider theme={theme}>
            {/* Outer level of the application */}
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
        </MantineProvider>
    );
}
