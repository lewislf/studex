// Mantine imports
import '@mantine/core/styles.css';
import { MantineProvider } from '@mantine/core';
import { Outlet } from "react-router";

export default function App() {
    return (
        <MantineProvider>
            <div>
                <h1>Hello from Home</h1>
                <Outlet />
            </div>
        </MantineProvider>
    );
}

