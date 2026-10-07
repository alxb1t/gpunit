"""Print each card's hourly price and the most a `make live` run can cost."""

from pathlib import Path

from gpunit.runpod import RunPod
from gpunit.spec import load_spec

spec = load_spec(Path(__file__).with_name("gpunit.toml"))
provider = RunPod()
hourly = {card: provider.gpu(card).hourly for card in spec.gpus}
for card, price in hourly.items():
    print(f"{card}: ${price}/h")
print(
    f"at most ${max(hourly.values()) * spec.ceiling_s / 3600:.2f} for {spec.ceiling_s}s"
)
