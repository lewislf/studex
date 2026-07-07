import App from './App.jsx';
import Revisions from './components/Revisions/Revisions.jsx'
import Statistics from './components/Statistics/Statistics.jsx'
import Subjects from './components/Subjects/Subjects.jsx'
import Home from './components/Home/Home.jsx';
import ErrorPage from './components/Common/ErrorPage.jsx';
import Auth from './components/Auth/Auth.jsx';

const routes = [
    {
        // Login/Register screen outside the AppShell (no authenticated header/footer)
        path: "/login",
        element: <Auth />,
        errorElement: <ErrorPage />
    },
    {
        path: "/",
        element: <App />, // Root element
        errorElement: <ErrorPage />, // Fallback in case of misrouting
        children: [
            {
                index: true, // Default route
                element: <Home />
            },
            {
                path: "revisoes",
                element: <Revisions />
            },
            {
                path: "materias",
                element: <Subjects />
            },
            {
                path: "estatisticas",
                element: <Statistics />
            }
        ]
    }
];

export default routes;
