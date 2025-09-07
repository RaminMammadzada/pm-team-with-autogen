#!/usr/bin/env python3
"""Compatibility wrapper pointing to new CLI entry point.

Allows: python examples/run_demo.py "Initiative" --blocker X --autogen
"""
from pm_team.cli import main

if __name__ == "__main__":  # pragma: no cover
    main()
