from __future__ import annotations

import sys

from app.bootstrap import bootstrap


def main() -> None:
    print("[MAIN] Bootstrap start...")

    orchestrator = bootstrap()

    print("[MAIN] Bootstrap OK")

    commands = sys.argv[1:]
    if not commands:
        print("[MAIN] No command provided")
        return

    if len(commands) == 1 and commands[0].lower() == "shell":
        _run_interactive_shell(orchestrator)
        return

    command = " ".join(commands)

    print(f"[MAIN] Running command: {command}")

    orchestrator.handle_command(command)

    print(f"[MAIN] {command} finished")


def _run_interactive_shell(orchestrator) -> None:
    print("[MAIN] Interactive shell started")
    print("[MAIN] Type commands, or 'exit' to quit")

    while True:
        try:
            raw = input("mcgiver-ai> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("[MAIN] Shell interrupted")
            _shutdown_runtime(orchestrator)
            break

        if not raw:
            continue

        lowered = raw.lower()

        if lowered in {"exit", "quit"}:
            print("[MAIN] Shell exit requested")
            _shutdown_runtime(orchestrator)
            break

        if lowered == "help":
            _print_shell_help()
            continue

        try:
            print(f"[MAIN] Running command: {raw}")
            orchestrator.handle_command(raw)
            print(f"[MAIN] {raw} finished")
        except Exception as exc:
            print(f"[MAIN] Shell error: {exc}")


def _shutdown_runtime(orchestrator) -> None:
    try:
        orchestrator.handle_command("scheduler_stop")
    except Exception:
        pass

    print("[MAIN] Runtime shutdown complete")


def _print_shell_help() -> None:
    print("AVAILABLE COMMANDS")
    print("-" * 72)
    print("scan_market")
    print("show_trades")
    print("show_trades status prepared")
    print("show_trades pair GBPJPY")
    print("show_trades timeframe M5")
    print("show_trades limit 3")
    print("show_trades_summary")
    print("show_trade_stats")
    print("cleanup_prepared_duplicates")
    print("mark_submitted <trade_id>")
    print("mark_open <trade_id>")
    print("mark_closed <trade_id> <exit_price> <pnl>")
    print("mark_rejected <trade_id> <reason>")
    print("mark_cancelled <trade_id> <reason>")
    print("paper_submit <trade_id>")
    print("paper_open <trade_id>")
    print("paper_close <trade_id> <exit_price> <pnl>")
    print("paper_reject <trade_id> <reason>")
    print("paper_cancel <trade_id> <reason>")
    print("paper_full_cycle <trade_id> <exit_price> <pnl>")
    print("scheduler_start <interval_seconds>")
    print("scheduler_start <interval_seconds> paper")
    print("scheduler_status")
    print("scheduler_run_once")
    print("scheduler_stop")
    print("help")
    print("exit")


if __name__ == "__main__":
    main()