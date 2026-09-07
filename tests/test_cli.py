"""Tests for the portly command-line interface."""

from __future__ import annotations

import contextlib
import errno
import io
import json
import os
import queue
import subprocess
import sys
import textwrap
import threading

import pytest

import portly
from portly import PortlyPortError
from portly.cli import main


def _run_broken_pipe_child(script: str, *, expect_ready: bool, case_name: str) -> tuple[int, str]:
    """Run a child whose stdout is closed before it emits its payload."""
    child_env = os.environ.copy()
    child_env.pop("PYTHONUNBUFFERED", None)
    with subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=child_env,
    ) as proc:
        assert proc.stdin is not None
        assert proc.stdout is not None
        assert proc.stderr is not None

        if expect_ready:
            ready_queue: queue.Queue[bytes] = queue.Queue()

            def read_ready() -> None:
                assert proc.stdout is not None
                ready_queue.put(proc.stdout.readline())

            ready_reader = threading.Thread(target=read_ready, daemon=True)
            ready_reader.start()
            try:
                ready = ready_queue.get(timeout=5)
            except queue.Empty:
                proc.kill()
                proc.wait(timeout=5)
                proc.stdout.close()
                ready_reader.join(timeout=5)
                pytest.fail(f"{case_name} subprocess did not signal readiness")
            ready_reader.join(timeout=5)
            if ready_reader.is_alive():
                proc.kill()
                proc.wait(timeout=5)
                proc.stdout.close()
                ready_reader.join(timeout=5)
                pytest.fail(f"{case_name} readiness reader did not exit")
            assert ready.splitlines() == [b"ready"]

        proc.stdout.close()
        proc.stdin.write(b"ack\n")
        with contextlib.suppress(BrokenPipeError):
            proc.stdin.flush()
        with contextlib.suppress(BrokenPipeError):
            proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
            pytest.fail(f"{case_name} subprocess did not exit")
        stderr = proc.stderr.read().decode("utf-8", errors="replace")
        returncode = proc.returncode

    assert returncode is not None
    return returncode, stderr


def _assert_clean_broken_pipe_stderr(stderr: str) -> None:
    """Reject interpreter-shutdown noise from broken-pipe subprocesses."""
    assert "Exception ignored" not in stderr
    assert "BrokenPipeError" not in stderr
    assert "broken pipe" not in stderr.lower()
    assert "Traceback (most recent call last):" not in stderr


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

    @pytest.mark.parametrize(
        "force_dup2_failure",
        [False, True],
        ids=["real-dup2", "dup2-failure"],
    )
    def test_broken_pipe(self, force_dup2_failure: bool) -> None:
        script = textwrap.dedent(
            """
            import os
            import sys

            import portly.cli as cli

            handler_result = None

            def emit_buffered_payload(args, json_out):
                global handler_result
                print("ready", flush=True)
                assert sys.stdin.buffer.readline() == b"ack\\n"
                print("payload")
                handler_result = 0
                return handler_result

            cli._cmd_scan = emit_buffered_payload

            if __FORCE_DUP2_FAILURE__:
                def fail_dup2(fd, target_fd):
                    raise OSError("forced dup2 failure")

                os.dup2 = fail_dup2

            result = cli.main(["scan", "1"])
            print(
                f"handler_returned={handler_result};main_returned={result}",
                file=sys.stderr,
                flush=True,
            )
            sys.exit(result)
            """
        ).replace("__FORCE_DUP2_FAILURE__", repr(force_dup2_failure))
        returncode, stderr = _run_broken_pipe_child(
            script, expect_ready=True, case_name="normal handler"
        )
        assert returncode == 1, stderr
        assert "handler_returned=0;main_returned=1" in stderr
        _assert_clean_broken_pipe_stderr(stderr)

    @pytest.mark.parametrize(
        "arg",
        ["--help", "--version"],
        ids=["help", "version"],
    )
    def test_broken_pipe_argparse_exit(self, arg: str) -> None:
        script = textwrap.dedent(
            """
            import sys

            import portly.cli as cli

            assert sys.stdin.buffer.readline() == b"ack\\n"
            result = cli.main([__ARG__])
            print(f"main_returned={result}", file=sys.stderr, flush=True)
            sys.exit(result)
            """
        ).replace("__ARG__", repr(arg))
        returncode, stderr = _run_broken_pipe_child(
            script, expect_ready=False, case_name=f"argparse {arg}"
        )
        assert returncode == 1, stderr
        assert "main_returned=1" in stderr
        _assert_clean_broken_pipe_stderr(stderr)

    @pytest.mark.parametrize(
        ("raise_statement", "diagnostic"),
        [
            ("raise PortlyPortError('boom')", "boom"),
            ("raise KeyboardInterrupt", "interrupted"),
        ],
        ids=["portly-error", "keyboard-interrupt"],
    )
    def test_broken_pipe_handled_outcome(self, raise_statement: str, diagnostic: str) -> None:
        script = textwrap.dedent(
            """
            import sys

            from portly import PortlyPortError
            import portly.cli as cli

            def emit_handled_payload(args, json_out):
                print("ready", flush=True)
                assert sys.stdin.buffer.readline() == b"ack\\n"
                print("payload")
                __RAISE__

            cli._cmd_scan = emit_handled_payload
            result = cli.main(["scan", "1"])
            print(f"main_returned={result}", file=sys.stderr, flush=True)
            sys.exit(result)
            """
        ).replace("__RAISE__", raise_statement)
        returncode, stderr = _run_broken_pipe_child(
            script, expect_ready=True, case_name="handled outcome"
        )
        assert returncode == 1, stderr
        assert diagnostic in stderr
        assert "main_returned=1" in stderr
        _assert_clean_broken_pipe_stderr(stderr)

    @pytest.mark.parametrize("platform", ["linux", "win32"])
    def test_handler_einval_is_not_a_broken_pipe(
        self, monkeypatch: pytest.MonkeyPatch, platform: str
    ) -> None:
        error = OSError(errno.EINVAL, "invalid command argument")

        def boom(*args: object, **kwargs: object) -> bool:
            raise error

        monkeypatch.setattr(sys, "platform", platform)
        monkeypatch.setattr(portly, "is_available", boom)
        with pytest.raises(OSError) as exc:
            main(["check", "8000"])
        assert exc.value is error

    @pytest.mark.parametrize("argv", [["--help"], ["check", "8000"]])
    @pytest.mark.parametrize(
        ("platform", "error_number"),
        [("linux", errno.EINVAL), ("linux", errno.EIO), ("win32", errno.EIO)],
    )
    def test_unrelated_flush_error_propagates(
        self, monkeypatch: pytest.MonkeyPatch, argv: list[str], platform: str, error_number: int
    ) -> None:
        error = OSError(error_number, "stdout failure")

        class FailingFlush(io.StringIO):
            def flush(self) -> None:
                raise error

        monkeypatch.setattr(sys, "platform", platform)
        monkeypatch.setattr(sys, "stdout", FailingFlush())
        monkeypatch.setattr(portly, "is_available", lambda port: True)
        with pytest.raises(OSError) as exc:
            main(argv)
        assert exc.value is error

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

    def test_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0
        assert "usage: portly" in capsys.readouterr().out

    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        assert "portly" in capsys.readouterr().out
