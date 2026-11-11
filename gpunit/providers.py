"""The one place that builds the provider."""

from collections.abc import Mapping

from gpunit.provider import Provider
from gpunit.runpod import RunPod


def build(environ: Mapping[str, str]) -> Provider:
    """Return the provider; RunPod, until a `provider` key chooses."""
    return RunPod(environ)
