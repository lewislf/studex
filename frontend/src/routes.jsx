import App from './App.jsx';
import Revisions from './components/Revisions/Revisions.jsx'
import Statistics from './components/Statistics/Statistics.jsx'
import Subjects from './components/Subjects/Subjects.jsx'
import SubjectDetail from './components/SubjectDetail/SubjectDetail.jsx'
import SummaryPage from './components/SubjectDetail/SummaryPage.jsx'
import MindMapPage from './components/SubjectDetail/MindMapPage.jsx'
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
                path: "materias/:subjectId",
                element: <SubjectDetail />
            },
            {
                path: "materias/:subjectId/resumos/:resumoId",
                element: <SummaryPage />
            },
            {
                path: "materias/:subjectId/mapas/:mapaId",
                element: <MindMapPage />
            },
            {
                path: "estatisticas",
                element: <Statistics />
            }
        ]
    }
];

export default routes;
