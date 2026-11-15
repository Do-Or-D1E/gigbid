import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { endpoints } from "../../lib/endpoints";
import { useAction, useDocumentTitle } from "../../lib/hooks";
import { InlineError } from "../../components/States";
import MarketplaceBanner from "../../components/MarketplaceBanner";

export default function LoginPage() {
  useDocumentTitle("Sign in");
  const { user, signIn } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const from = (loc.state as { from?: string } | null)?.from;
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submit = useAction(async () => {
    const out = mode === "login" ? await endpoints.login({ email, password }) : await endpoints.register({ email, password, name });
    signIn(out.token, out.user);
    nav(out.user.onboarded ? (from ?? "/inbox") : "/onboarding", { replace: true });
  });

  if (user) return <Navigate to={user.onboarded ? "/inbox" : "/onboarding"} replace />;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void submit.call();
  };

  return (
    <div className="auth">
      <MarketplaceBanner />
      <div className="auth__panel">
        <div className="brand brand--large">
          <span className="brand__mark" aria-hidden="true">
            G
          </span>
          <span className="brand__name">GigBid</span>
        </div>
        <h1>{mode === "login" ? "Sign in" : "Create your account"}</h1>
        <p className="muted">GigBid finds and drafts freelance proposals. You approve every one before it is sent.</p>

        <div className="tabs" role="tablist" aria-label="Sign in or register">
          <button type="button" role="tab" aria-selected={mode === "login"} className={`tab${mode === "login" ? " is-active" : ""}`} onClick={() => setMode("login")}>
            Sign in
          </button>
          <button type="button" role="tab" aria-selected={mode === "register"} className={`tab${mode === "register" ? " is-active" : ""}`} onClick={() => setMode("register")}>
            Register
          </button>
        </div>

        <form onSubmit={onSubmit} className="form" aria-label={mode === "login" ? "Sign in" : "Register"}>
          {mode === "register" && (
            <div className="field">
              <label htmlFor="name">Name</label>
              <input id="name" name="name" autoComplete="name" required value={name} onChange={(e) => setName(e.target.value)} />
            </div>
          )}
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" name="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={mode === "register" ? 8 : undefined}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {mode === "register" && <span className="hint">At least 8 characters.</span>}
          </div>
          <InlineError message={submit.error} />
          <button type="submit" className="btn btn--primary btn--block" disabled={submit.busy}>
            {submit.busy ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
