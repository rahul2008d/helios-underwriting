"""Shared pytest fixtures and configuration."""

import os

# Force test environment before any imports trigger settings
os.environ.setdefault("ENVIRONMENT", "test")
