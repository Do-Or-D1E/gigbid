import type { ReactNode } from "react";

export function Skeleton({ lines = 3, height }: { lines?: number; height?: number }) {
  return (
    <div className="skeleton-group" role="status" aria-label="Loading">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: height ?? 16, width: `${100 - (i % 3) * 14}%` }} />
      ))}
      <span className="sr-only">Loading</span>
    </div>
  );
}

export function SkeletonCards({ count = 4 }: { count?: number }) {
  return (
    <div className="stack" role="status" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card">
          <div className="skeleton" style={{ height: 18, width: "55%" }} />
          <div className="skeleton" style={{ height: 12, width: "80%", marginTop: 12 }} />
          <div className="skeleton" style={{ height: 12, width: "35%", marginTop: 8 }} />
        </div>
      ))}
      <span className="sr-only">Loading</span>
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry, title = "Could not load this page" }: { message: string; onRetry?: () => void; title?: string }) {
  return (
    <div className="error-state" role="alert">
      <h3>{title}</h3>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function InlineError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="inline-error" role="alert">
      {message}
    </p>
  );
}

export function PageHeader({ title, children, sub }: { title: string; sub?: ReactNode; children?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {sub && <p className="muted">{sub}</p>}
      </div>
      {children && <div className="page-header__actions">{children}</div>}
    </header>
  );
}
