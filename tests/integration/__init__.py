from __future__ import annotations

import os

import pytest

if os.getenv("RUN_INTEGRATION_TESTS") != "1":
    pytest.skip(
        "Integration tests require RUN_INTEGRATION_TESTS=1",
        allow_module_level=True,
    )
