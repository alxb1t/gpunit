"""Print each card's hourly price and the most a live run can cost.

e.g. `python live/price.py live/gpunit.dead.toml`; with no path, `make live`'s spec.
"""

import sys
from pathlib import Path

from gpunit.runpod import RunPod
from gpunit.spec import load_spec

path = (
    Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("gpunit.toml")
)
spec = load_spec(path)
provider = RunPod()
hourly = {card: provider.gpu(card).hourly for card in spec.gpus}
for card, price in hourly.items():
    print(f"{card}: ${price}/h")
# The pod bills while it waits for SSH, and boot arms the ceiling only after.
wait_s = spec.timeout_s
most = max(hourly.values()) * (spec.ceiling_s + wait_s) / 3600
print(f"at most ${most:.2f} for {spec.ceiling_s}s and a {wait_s}s wait for SSH")
