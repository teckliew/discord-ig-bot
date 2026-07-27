"""
Single-run entry point for GitHub Actions.
Runs one check-and-post cycle then exits (no infinite loop) — the schedule
in .github/workflows/poll-instagram.yml is what makes this "continuous".
"""

import sys

from main import load_state, run_once, log

if __name__ == "__main__":
    state = load_state()
    log.info("Running single check (GitHub Actions mode)")
    state, success = run_once(state)
    if not success:
        log.error("Check failed, exiting with error code so the alert step fires")
        sys.exit(1)
    log.info("Check complete, exiting")
