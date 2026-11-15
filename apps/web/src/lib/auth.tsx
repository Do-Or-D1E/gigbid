import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getToken, onApiProblem, setToken } from "./client";
import { endpoints } from "./endpoints";
import type { UserOut } from "./types";

interface AuthState {
  user: UserOut | null;
  /** true until the first /auth/me check finished */
  booting: boolean;
  signIn: (token: string, user: UserOut) => void;
  signOut: () => void;
  refresh: () => Promise<UserOut | null>;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [booting, setBooting] = useState<boolean>(() => !!getToken());

  const signOut = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const signIn = useCallback((token: string, u: UserOut) => {
    setToken(token);
    setUser(u);
    setBooting(false);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const u = await endpoints.me();
      setUser(u);
      return u;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    if (!getToken()) {
      setBooting(false);
      return;
    }
    let live = true;
    endpoints
      .me()
      .then((u) => live && setUser(u))
      .catch((e) => {
        if ((e as { status?: number }).status === 401) signOut();
      })
      .finally(() => live && setBooting(false));
    return () => {
      live = false;
    };
  }, [signOut]);

  // Any 401 from the API ends the session.
  useEffect(() => onApiProblem((status) => status === 401 && signOut()), [signOut]);

  const value = useMemo(() => ({ user, booting, signIn, signOut, refresh }), [user, booting, signIn, signOut, refresh]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}
