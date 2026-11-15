import { createBrowserRouter, Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./lib/auth";
import Layout from "./components/Layout";
import { EmptyState } from "./components/States";
import LoginPage from "./app/login/page";
import OnboardingPage from "./app/onboarding/page";
import InboxPage from "./app/inbox/page";
import JobDetailPage from "./app/jobs/[id]/page";
import StudioPage from "./app/studio/[id]/page";
import PipelinePage from "./app/pipeline/page";
import MessagesPage from "./app/messages/page";
import RunsPage from "./app/runs/page";
import RunPage from "./app/runs/[id]/page";
import AnalyticsPage from "./app/analytics/page";
import SettingsPage from "./app/settings/page";

/** Signed-in routes. Sends new users to onboarding and signed-out users to the login page. */
function RequireAuth() {
  const { user, booting } = useAuth();
  const loc = useLocation();
  if (booting) {
    return (
      <div className="boot" role="status">
        Loading GigBid...
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname + loc.search }} />;
  if (!user.onboarded && loc.pathname !== "/onboarding") return <Navigate to="/onboarding" replace />;
  return <Outlet />;
}

function NotFound() {
  return (
    <EmptyState title="Page not found" action={<Link className="btn" to="/inbox">Go to the inbox</Link>}>
      This address does not exist.
    </EmptyState>
  );
}

/** URL to page mapping. Page components live in src/app/<route>/page.tsx. */
export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      { path: "/onboarding", element: <OnboardingPage /> },
      {
        element: <Layout />,
        children: [
          { index: true, element: <Navigate to="/inbox" replace /> },
          { path: "/inbox", element: <InboxPage /> },
          { path: "/jobs/:id", element: <JobDetailPage /> },
          { path: "/studio/:id", element: <StudioPage /> },
          { path: "/pipeline", element: <PipelinePage /> },
          { path: "/messages", element: <MessagesPage /> },
          { path: "/messages/:threadId", element: <MessagesPage /> },
          { path: "/runs", element: <RunsPage /> },
          { path: "/runs/:id", element: <RunPage /> },
          { path: "/analytics", element: <AnalyticsPage /> },
          { path: "/settings", element: <SettingsPage /> },
          { path: "*", element: <NotFound /> },
        ],
      },
    ],
  },
]);
