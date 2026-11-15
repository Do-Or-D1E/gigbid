from math import sqrt
import os

from scipy.stats import norm
import requests


EXPORT_URL = "https://data.mixpanel.com/api/2.0/export"


def export_events(from_date: str, to_date: str, event: str = "Signed Up"):
    resp = requests.get(
        EXPORT_URL,
        params={"from_date": from_date, "to_date": to_date, "event": f'["{event}"]'},
        auth=(os.environ["MIXPANEL_SECRET"], ""),
        timeout=120,
        stream=True,
    )
    resp.raise_for_status()
    for line in resp.iter_lines():
        if line:
            yield line.decode("utf-8")


def two_proportion_z(conv_a, n_a, conv_b, n_b):
    p_a, p_b = conv_a / n_a, conv_b / n_b
    pooled = (conv_a + conv_b) / (n_a + n_b)
    se = sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se
    return {"lift": p_b / p_a - 1, "z": z, "p_value": 2 * (1 - norm.cdf(abs(z)))}


def sample_size(base_rate, mde, alpha=0.05, power=0.8):
    p1, p2 = base_rate, base_rate * (1 + mde)
    za, zb = norm.ppf(1 - alpha / 2), norm.ppf(power)
    var = p1 * (1 - p1) + p2 * (1 - p2)
    return int(((za + zb) ** 2 * var) / (p2 - p1) ** 2) + 1
