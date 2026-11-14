"""Read-only checks of pushable history and tracked text; never prints secrets."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    # App-owned refs/codex/* may retain local recovery trees. They are not
    # branch/tag histories and are never included in a normal branch push.
    objects = git("rev-list", "--objects", "--branches", "--tags", "--remotes")
    result = subprocess.run(["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)"],
                            cwd=ROOT, input=objects, capture_output=True, check=True)
    oversized, largest = [], 0
    for line in result.stdout.decode().splitlines():
        parts = line.split(" ", 3)
        if len(parts) >= 3 and parts[1] == "blob":
            size = int(parts[2])
            largest = max(largest, size)
            if size > 100 * 1024 * 1024:
                oversized.append((parts[3] if len(parts) > 3 else parts[0], size))
    assert not oversized, f"Oversized reachable history blobs: {oversized}"
    patterns = re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{32,}")
    findings = []
    tracked = git("ls-files", "-z").decode().split("\0")
    for name in filter(None, tracked):
        path = ROOT / name
        if path.is_file() and path.stat().st_size < 5 * 1024 * 1024 and patterns.search(path.read_bytes()):
            findings.append(name)
        assert not name.startswith(("DL_FIRE", ".venv/", "node_modules/", ".aws/")), name
        assert path.name != ".env", name
    assert not findings, f"Potential credential patterns in files (values withheld): {findings}"
    print(f"PASS: no branch/tag/remote-history blob >100 MiB; largest {largest:,} bytes; no supported credential patterns in tracked files.")
    print("Credential-pattern scanning is heuristic; no credentials were found, not a proof of absence.")


if __name__ == "__main__":
    main()
