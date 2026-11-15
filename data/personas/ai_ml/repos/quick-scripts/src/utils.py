import subprocess
import sys

from torch import nn
import torch


def smoke_test(url: str) -> None:
    out = subprocess.run(["curl", "-sf", f"{url}/healthz"], capture_output=True, text=True)
    if out.returncode != 0:
        print("health check failed", out.stderr)
        sys.exit(1)
    print("healthy:", out.stdout.strip())


def canary_ok(old_p95_ms: float, new_p95_ms: float, tolerance: float = 1.15) -> bool:
    return new_p95_ms <= old_p95_ms * tolerance


class DonationNet(nn.Module):
    def __init__(self, n_in: int, n_hidden: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_in, n_hidden), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(n_hidden, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


def train_epoch(model, loader, opt, device="cuda"):
    model.train()
    total = 0.0
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)
        opt.zero_grad()
        loss = nn.functional.binary_cross_entropy_with_logits(model(xb), yb)
        loss.backward()
        opt.step()
        total += loss.item() * len(xb)
    return total / len(loader.dataset)
