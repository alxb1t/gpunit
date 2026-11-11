"""Print each card's hourly price and the most a live run can cost.

e.g. `python live/price.py live/gpunit.dead.toml`; with no path, `make live`'s spec.
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

from gpunit import providers
from gpunit.serve.session import most_cost
from gpunit.spec import load_spec

path = (
    Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("gpunit.toml")
)
spec = load_spec(path)
provider = providers.build(os.environ)
hourly = {card: provider.gpu(card).hourly for card in spec.gpus}
for card, price in hourly.items():
    print(f"{card}: ${price}/h")
most = most_cost(Decimal(str(max(hourly.values()))), spec)
print(f"at most ${most} for {spec.ceiling_s}s and a {spec.timeout_s}s wait for SSH")
