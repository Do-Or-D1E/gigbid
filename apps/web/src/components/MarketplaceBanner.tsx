import { useHealth } from "../lib/health";

export const MARKETPLACE_DOWN_TEXT = "Marketplace unavailable - GigBid has queued your work and will resume automatically.";

/** Persistent banner shown while /api/health reports the marketplace as down (or an API call returned 503). */
export default function MarketplaceBanner() {
  const { marketplaceDown, detail } = useHealth();
  if (!marketplaceDown) return null;
  return (
    <div className="banner banner--warn" role="alert" data-testid="marketplace-banner">
      <strong>{MARKETPLACE_DOWN_TEXT}</strong>
      {detail && <span className="banner__detail">{detail}</span>}
    </div>
  );
}
