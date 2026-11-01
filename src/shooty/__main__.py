"""Headless CLI entry point; desktop imports are intentionally deferred."""
import argparse
from . import __version__


def main() -> int:
    parser = argparse.ArgumentParser(prog="shooty", description="Capture and annotate screenshots")
    parser.add_argument("--version", action="version", version=f"shooty {__version__}")
    parser.add_argument("command", nargs="?", choices=("capture", "open", "indicator"))
    parser.add_argument("file", nargs="?")
    args = parser.parse_args()
    if args.command is None:
        return 0
    if args.command == "open" and not args.file:
        parser.error("open requires an image file")
    if args.command == "indicator" and args.file:
        parser.error("indicator does not accept a file")
    # Keep display dependencies out of CLI help and the pure package modules.
    from .app import run
    return run(args.command, args.file)


if __name__ == "__main__":
    raise SystemExit(main())
