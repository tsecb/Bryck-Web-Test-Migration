"""Windows-side remote control for running the web shipment suite on a Linux
test-runner machine over SSH - no manual `ssh`/password prompts needed.

Credentials are read from environment variables ONLY. Never hardcode a host,
username, or password in this file, and never commit them anywhere:

    WS_REMOTE_HOST       e.g. 192.168.6.36
    WS_REMOTE_USER       e.g. bryck
    WS_REMOTE_KEY_PATH   path to a private key file (preferred over a password)
    WS_REMOTE_PASSWORD   password auth, only if a key isn't set up yet
    WS_REMOTE_DIR        project directory on the remote machine
                         (default: ~/Bryck-Web-Test-Migration)

Set them for the current PowerShell session before running, e.g.:
    $env:WS_REMOTE_HOST = "192.168.6.36"
    $env:WS_REMOTE_USER = "bryck"
    $env:WS_REMOTE_PASSWORD = "<real password>"   # or WS_REMOTE_KEY_PATH instead

Subcommands:
    trigger   Kill any existing "web-test" screen session on the remote
              machine and start a fresh run (scripts/run_in_screen.sh), which
              itself archives the previous run's results before starting.
    status    Show remote screen-session state and tail the latest runner log.
    fetch     Download the latest single-file HTML report to
              reports/web/fetched/ on this machine.

Usage:
    python scripts/remote_control.py trigger
    python scripts/remote_control.py trigger --markers shipment
    python scripts/remote_control.py status
    python scripts/remote_control.py fetch
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import paramiko


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _load_private_key(key_path: str):
    """Try each supported key type since paramiko has no single "auto" loader."""
    last_error: Exception | None = None
    for key_cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey, paramiko.DSSKey):
        try:
            return key_cls.from_private_key_file(key_path)
        except paramiko.SSHException as exc:
            last_error = exc
    raise SystemExit(f"Could not load private key '{key_path}' as any supported type: {last_error}")


def _connect() -> paramiko.SSHClient:
    host = _require_env("WS_REMOTE_HOST")
    user = _require_env("WS_REMOTE_USER")
    key_path = os.environ.get("WS_REMOTE_KEY_PATH")
    password = os.environ.get("WS_REMOTE_PASSWORD")
    if not key_path and not password:
        raise SystemExit("Set WS_REMOTE_KEY_PATH (preferred) or WS_REMOTE_PASSWORD before running.")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict = {"username": user, "timeout": 20, "look_for_keys": False, "allow_agent": False}
    if key_path:
        connect_kwargs["pkey"] = _load_private_key(key_path)
    else:
        connect_kwargs["password"] = password
    ssh.connect(host, **connect_kwargs)
    return ssh


def _remote_dir() -> str:
    return os.environ.get("WS_REMOTE_DIR", "~/Bryck-Web-Test-Migration")


def _run(ssh: paramiko.SSHClient, command: str, timeout: int = 60) -> tuple[int, str, str]:
    _, stdout, stderr = ssh.exec_command(command, timeout=timeout)
    rc = stdout.channel.recv_exit_status()
    return rc, stdout.read().decode(errors="replace").strip(), stderr.read().decode(errors="replace").strip()


def cmd_trigger(args: argparse.Namespace) -> int:
    ssh = _connect()
    try:
        remote_dir = _remote_dir()
        extra = " ".join(args.extra or [])
        command = f"cd {remote_dir} && chmod +x scripts/run_in_screen.sh && ./scripts/run_in_screen.sh {extra}"
        print(f"==> {command}")
        rc, out, err = _run(ssh, command, timeout=30)
        print(out)
        if err:
            print(err, file=sys.stderr)
        return rc
    finally:
        ssh.close()


def cmd_status(args: argparse.Namespace) -> int:
    ssh = _connect()
    try:
        remote_dir = _remote_dir()
        _, sessions, _ = _run(ssh, "screen -ls 2>/dev/null || true")
        print("Screen sessions:\n" + (sessions or "(none)"))

        _, latest_log, _ = _run(ssh, f"ls -t {remote_dir}/logs/web/runner_*.log 2>/dev/null | head -1")
        if latest_log:
            _, tail_out, _ = _run(ssh, f"tail -n 40 {latest_log}")
            print(f"\n--- tail -n 40 {latest_log} ---\n{tail_out}")
        else:
            print("\nNo runner logs found yet.")
        return 0
    finally:
        ssh.close()


def cmd_fetch(args: argparse.Namespace) -> int:
    ssh = _connect()
    try:
        remote_dir = _remote_dir()
        _, remote_report, _ = _run(
            ssh, f"ls -t {remote_dir}/reports/web/allure-report-web-*.html 2>/dev/null | head -1"
        )
        if not remote_report:
            print("No single-file HTML report found on the remote machine yet.")
            return 1

        sftp = ssh.open_sftp()
        try:
            local_dir = Path("reports/web/fetched")
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / Path(remote_report).name
            sftp.get(remote_report, str(local_path))
        finally:
            sftp.close()

        print(f"Fetched: {local_path}")
        return 0
    finally:
        ssh.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remote control for the web shipment suite")
    subparsers = parser.add_subparsers(dest="command", required=True)

    trigger_parser = subparsers.add_parser("trigger", help="Kill any existing screen session and start a fresh run")
    trigger_parser.add_argument(
        "extra", nargs=argparse.REMAINDER, help="Args forwarded to run_tests.py, e.g. --markers shipment"
    )
    trigger_parser.set_defaults(func=cmd_trigger)

    status_parser = subparsers.add_parser("status", help="Show screen session state and tail the latest runner log")
    status_parser.set_defaults(func=cmd_status)

    fetch_parser = subparsers.add_parser("fetch", help="Download the latest single-file HTML report")
    fetch_parser.set_defaults(func=cmd_fetch)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
