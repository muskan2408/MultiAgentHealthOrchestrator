import argparse
import logging
import sys

from src.web import run_server
from src.cli import run_cli

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python app.py <cli|web> [-v]")
        print("cli.  Start the Terminal Assistant")
        print("web.  Start the Browser Assistant ")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="mama health AI assistant")
    parser.add_argument("mode", choices=["cli", "web"], help="Run mode: cli for terminal, web for browser UI")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show debug logs in console")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print(args.mode)
    if args.mode == "web":
        run_server()
    else:
        run_cli()

if __name__ == "__main__":
    main()
    