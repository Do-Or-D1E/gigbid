import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

interface Toast {
  id: number;
  text: string;
  tone: "ok" | "error";
}
interface ToastApi {
  ok: (text: string) => void;
  error: (text: string) => void;
}
const Ctx = createContext<ToastApi | null>(null);
let seq = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: Toast["tone"]) => {
    const id = seq++;
    setItems((x) => [...x, { id, text, tone }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), tone === "error" ? 8000 : 4000);
  }, []);
  const api = useMemo<ToastApi>(() => ({ ok: (t) => push(t, "ok"), error: (t) => push(t, "error") }), [push]);
  return (
    <Ctx.Provider value={api}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast toast--${t.tone}`}>
            <span>{t.text}</span>
            <button type="button" className="btn btn--ghost btn--sm" aria-label="Dismiss message" onClick={() => setItems((x) => x.filter((i) => i.id !== t.id))}>
              Close
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast(): ToastApi {
  const v = useContext(Ctx);
  if (!v) throw new Error("useToast outside ToastProvider");
  return v;
}
