from __future__ import annotations

import subprocess


def main() -> int:
    """Build entrypoint for Cloudflare CI (`uv run build`)."""
    completed = subprocess.run(["pywrangler", "sync"], check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
