# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0/).

## [Unreleased]

### Added

- The `gpunit` package skeleton: the CLI parser with its usage exit `2`, `gpunit.toml` loaded strictly into
  a `Spec`, and the `.gpunit/` session files with a fresh keypair at `0600`.
- The gate grows to `uv sync`, ruff, ty and pytest before `openspec validate`, so the package is checked offline.
- The `Provider` seam and its RunPod implementation on `urllib`: the key only in a request header, a 400
  refused, a 5xx or a lost answer `Lost`, a listing that never reads a look-alike or a bare pod as ours.
