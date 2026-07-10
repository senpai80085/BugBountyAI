from __future__ import annotations

from engine.scan import scan

__all__ = ["scan"]


def main() -> None:
    """
    CLI wrapper delegating to the main execution module.
    """
    from bugbounty.cli import main as cli_main
    cli_main()
