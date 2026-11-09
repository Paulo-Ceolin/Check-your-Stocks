import argparse

from tracker.cli import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Crypto & Stock Portfolio Tracker")
    parser.add_argument("--gui", action="store_true", help="Launch the desktop widget")
    args = parser.parse_args()
    if not args.gui:
        run()
        return
    try:
        from ui.app import launch
    except ImportError as exc:
        print(
            "The desktop widget requires CustomTkinter and matplotlib. "
            "Install them with: python -m pip install -r requirements.txt"
        )
        print(f"Import detail: {exc}")
        return
    launch()


if __name__ == "__main__":
    main()
