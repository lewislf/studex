// Default imports
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Router config
import routes from "./routes.jsx";
import { createBrowserRouter, RouterProvider } from "react-router";
const router = createBrowserRouter(routes);

// Default css
import './styles/root.css'

createRoot(document.getElementById('root')).render(
    <StrictMode>
        <RouterProvider router={router} />
    </StrictMode>,
)

