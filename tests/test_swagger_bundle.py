import shutil
from unittest.mock import patch

import pytest

from backend.services.swagger_bundle import resolve_swagger_cli


def test_resolve_swagger_cli_finds_executable():
    with patch.object(shutil, "which") as mock_which:
        mock_which.side_effect = lambda name: (
            "C:\\npm\\swagger-cli.cmd" if name == "swagger-cli.cmd" else None
        )
        cmd = resolve_swagger_cli()
        assert cmd == ["C:\\npm\\swagger-cli.cmd"]


def test_resolve_swagger_cli_falls_back_to_npx():
    with patch.object(shutil, "which") as mock_which:
        def lookup(name):
            if name == "npx":
                return "C:\\npm\\npx.cmd"
            return None

        mock_which.side_effect = lookup
        cmd = resolve_swagger_cli()
        assert cmd == ["C:\\npm\\npx.cmd", "@apidevtools/swagger-cli"]


def test_resolve_swagger_cli_raises_when_missing():
    with patch.object(shutil, "which", return_value=None):
        with pytest.raises(RuntimeError, match="swagger-cli not found"):
            resolve_swagger_cli()
