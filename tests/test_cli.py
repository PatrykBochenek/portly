"""Tests for the portly command-line interface."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

import portly
from portly import PortlyPortError
from portly.cli import main


class TestCheck:
    """Tests for the ``check`` subcommand."""

    def test_available_port(self, free_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["check", str(free_port)]) == 0
        assert "available" in capsys.readouterr().out

    def test_busy_port(self, busy_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["check", str(busy_port)]) == 1
        assert "in use" in capsys.readouterr().out

    def test_json(self, free_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["--json", "check", str(free_port)]) == 0
        data = json.loads(capsys.readouterr().out)
        assert data == {"port": free_port, "available": True}

    def test_json_after_subcommand(
        self, free_port: int, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["check", str(free_port), "--json"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert data["available"] is True


class TestFind:
    """Tests for the ``find`` subcommand."""

    def test_find_free(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["find"]) == 0
        port = int(capsys.readouterr().out.strip())
        assert 1 <= port <= 65535
        assert portly.is_available(port)

    def test_preferred_when_free(self, free_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["find", "--preferred", str(free_port)]) == 0
        assert int(capsys.readouterr().out.strip()) == free_port

    def test_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["find", "--json"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert "port" in data


class TestScan:
    """Tests for the ``scan`` subcommand."""

    def test_mixed_ports(
        self, temp_server: tuple[object, int], capsys: pytest.CaptureFixture[str]
    ) -> None:
        _server, busy = temp_server
        free = portly.find_free()
        assert main(["scan", str(busy), str(free)]) == 0
        out = capsys.readouterr().out
        assert f"{busy}: in use" in out
        assert f"{free}: free" in out

    def test_json(
        self, temp_server: tuple[object, int], capsys: pytest.CaptureFixture[str]
    ) -> None:
        _server, busy = temp_server
        assert main(["scan", "--json", str(busy)]) == 0
        data = json.loads(capsys.readouterr().out)
        assert str(busy) in data
        assert data[str(busy)] is not None

    def test_hidden_owner(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(portly, "scan", lambda ports: {p: None for p in ports})
        monkeypatch.setattr(portly, "is_available", lambda port: False)
        assert main(["scan", "8000"]) == 0
        assert "in use (owner not visible)" in capsys.readouterr().out


class TestInfo:
    """Tests for the ``info`` subcommand."""

    def test_busy_port(
        self, temp_server: tuple[object, int], capsys: pytest.CaptureFixture[str]
    ) -> None:
        _server, port = temp_server
        assert main(["info", str(port)]) == 0
        out = capsys.readouterr().out
        assert "pid:" in out
        assert "name:" in out
        assert "cmd:" in out

    def test_free_port(self, free_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["info", str(free_port)]) == 1
        assert "free" in capsys.readouterr().out

    def test_json_busy(
        self, temp_server: tuple[object, int], capsys: pytest.CaptureFixture[str]
    ) -> None:
        _server, port = temp_server
        assert main(["info", "--json", str(port)]) == 0
        data = json.loads(capsys.readouterr().out)
        assert data["port"] == port
        assert data["info"] is not None
        assert data["info"]["pid"] > 0

    def test_json_free_port(self, free_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["info", "--json", str(free_port)]) == 1
        data = json.loads(capsys.readouterr().out)
        assert data == {"port": free_port, "info": None}

    def test_hidden_owner(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(portly, "get_info", lambda port: None)
        monkeypatch.setattr(portly, "is_available", lambda port: False)
        assert main(["info", "8000"]) == 0
        assert "in use (owner not visible)" in capsys.readouterr().out

    def test_json_hidden_owner(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(portly, "get_info", lambda port: None)
        monkeypatch.setattr(portly, "is_available", lambda port: False)
        assert main(["info", "--json", "8000"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert data == {"port": 8000, "info": None}


class TestKill:
    """Tests for the ``kill`` subcommand."""

    def test_free_port(self, free_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["kill", str(free_port)]) == 0
        assert "free" in capsys.readouterr().out

    def test_busy_port(
        self,
        subprocess_server: tuple[subprocess.Popen[bytes], int],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        proc, port = subprocess_server
        assert main(["kill", str(port)]) == 0
        assert portly.is_available(port)
        proc.wait(timeout=5)

    def test_force(
        self,
        subprocess_server: tuple[subprocess.Popen[bytes], int],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        proc, port = subprocess_server
        assert main(["kill", "--force", str(port)]) == 0
        proc.wait(timeout=5)


class TestWait:
    """Tests for the ``wait`` subcommand."""

    def test_already_free(self, free_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["wait", str(free_port)]) == 0
        assert "free" in capsys.readouterr().out

    def test_timeout(self, busy_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["wait", "--timeout", "1", str(busy_port)]) == 1
        assert "still in use" in capsys.readouterr().err


class TestWaitForServer:
    """Tests for the ``wait-for-server`` subcommand."""

    def test_listening(
        self, temp_server: tuple[object, int], capsys: pytest.CaptureFixture[str]
    ) -> None:
        _server, port = temp_server
        assert main(["wait-for-server", str(port)]) == 0
        assert "accepting" in capsys.readouterr().out

    def test_timeout(self, free_port: int, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["wait-for-server", "--timeout", "1", str(free_port)]) == 1
        assert "not accepting" in capsys.readouterr().err


class TestUsageErrors:
    """Tests for argparse usage errors (exit code 2)."""

    def test_missing_command(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 2

    def test_missing_port(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["check"])
        assert exc.value.code == 2

    def test_invalid_port(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["check", "not-a-port"])
        assert exc.value.code == 2

    def test_port_out_of_range(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["check", "70000"])
        assert exc.value.code == 2

    def test_negative_timeout(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["wait", "--timeout", "-1", "8000"])
        assert exc.value.code == 2

    def test_underscore_port_rejected(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["check", "8_000"])
        assert exc.value.code == 2

    def test_underscore_timeout_rejected(self) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["wait", "--timeout", "1_0", "8000"])
        assert exc.value.code == 2


class TestErrors:
    """Tests for graceful error handling in ``main``."""

    def test_broken_pipe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _ClosedStderr:
            def close(self) -> None:
                pass

        def boom(*args: object, **kwargs: object) -> bool:
            raise BrokenPipeError

        monkeypatch.setattr(sys, "stderr", _ClosedStderr())
        monkeypatch.setattr(portly, "is_available", boom)
        assert main(["check", "8000"]) == 1

    def test_portly_error(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def boom(*args: object, **kwargs: object) -> bool:
            raise PortlyPortError("boom")

        monkeypatch.setattr(portly, "is_available", boom)
        assert main(["check", "8000"]) == 1
        assert "boom" in capsys.readouterr().err


class TestInterrupt:
    """Tests for graceful KeyboardInterrupt handling."""

    def test_keyboard_interrupt(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def boom(*args: object, **kwargs: object) -> bool:
            raise KeyboardInterrupt

        monkeypatch.setattr(portly, "wait_until_free", boom)
        assert main(["wait", "8000"]) == 130
        assert "interrupted" in capsys.readouterr().err


class TestVersion:
    """Tests for the ``--version`` flag."""

    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        assert "portly" in capsys.readouterr().out
