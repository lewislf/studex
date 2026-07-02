import App from './App.jsx'
import Home from './components/Home/Home.jsx'
import ErrorPage from './components/Common/ErrorPage.jsx'

const routes = [
    {
        path: "/",
        element: <App />,
        errorElement: <ErrorPage />,
        children: [
            // Default route
            {
                index: true,
                element: <Home />
            },
            // Example
            // {
            //     path: "shop",
            //     element: <Shop />
            // },
        ]
    }
]

export default routes;
