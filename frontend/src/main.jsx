// Default imports
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Mantine imports
import { MantineProvider } from '@mantine/core';
import { theme } from './styles/Mantine/theme.js'

// Router config
import routes from "./routes.jsx";
import { createBrowserRouter, RouterProvider } from "react-router";
const router = createBrowserRouter(routes);

// // Default css
// import './styles/root.css'
// import './styles/reset.css'

createRoot(document.getElementById('root')).render(
    <StrictMode>
        {/* Provider for mantine variables and css reset */}
        <MantineProvider theme={theme}>
            {/* Router to manage page transitions */}
            <RouterProvider router={router} />
        </MantineProvider>
    </StrictMode>,
)

