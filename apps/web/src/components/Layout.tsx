import { useEffect, useRef } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import MarketplaceBanner from "./MarketplaceBanner";
import { useAuth } from "../lib/auth";

const NAV = [
  { to: "/inbox", label: "Inbox" },
  { to: "/pipeline", label: "Pipeline" },
  { to: "/messages", label: "Messages" },
  { to: "/runs", label: "Runs" },
  { to: "/analytics", label: "Analytics" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const main = useRef<HTMLElement>(null);

  // Move focus to the main region on navigation so keyboard and screen reader users start at the content.
  useEffect(() => {
    main.current?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [loc.pathname]);

  const links = (
    <>
      {NAV.map((n) => (
        <NavLink key={n.to} to={n.to} className={({ isActive }) => `nav__link${isActive ? " is-active" : ""}`}>
          {n.label}
        </NavLink>
      ))}
    </>
  );

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="sidebar">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            G
          </span>
          <span className="brand__name">GigBid</span>
        </div>
        <nav className="nav" aria-label="Main">
          {links}
        </nav>
        <div className="sidebar__foot">
          <p className="sidebar__user" title={user?.email}>
            {user?.name ?? "Signed in"}
          </p>
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => {
              signOut();
              nav("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="content">
        <MarketplaceBanner />
        <main id="main" ref={main} tabIndex={-1} className="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
