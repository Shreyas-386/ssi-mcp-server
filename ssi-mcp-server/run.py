#!/usr/bin/env python3
"""
Convenience entry point: `python run.py`.

Equivalent to `python -m app.main`, provided at the repo root because that's
the invocation most process managers / Dockerfiles / MCP client configs
expect to find.
"""

from app.main import main

if __name__ == "__main__":
    main()
