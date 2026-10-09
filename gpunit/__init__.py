"""Open, use and close a RunPod GPU session from any project."""

# Before the imports: `gpunit.runpod` reads it while this package is still loading.
__version__ = "0.2.0"

from gpunit.library import Interrupted, Refused, Session, TeardownFailed, session
from gpunit.provider import Lost
from gpunit.spec import load_spec

__all__ = [
    "Interrupted",
    "Lost",
    "Refused",
    "Session",
    "TeardownFailed",
    "load_spec",
    "session",
]
