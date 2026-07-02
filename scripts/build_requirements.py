"""Rebuild requirements.txt from the installed venv's dependency graph.

The runtime requirements are DERIVED, not hand-maintained: this keeps the file
minimal (no dead ML/vector deps) and guaranteed to cover every real import.

Strategy:
1. Statically scan LIVE code (services/core/utils/config/worker) for every
   top-level import, EXCLUDING known-dead files (embedding/vector/chunking/sprint).
2. Map each imported top-level module to its providing distribution.
3. Compute the transitive dependency closure over installed metadata.
4. Emit a minimal requirements.txt pinned to installed versions.

Usage (run inside the project venv that has the app's deps installed):
    python scripts/build_requirements.py            # dry-run report
    python scripts/build_requirements.py --write     # overwrite requirements.txt
"""
import ast
import sys
import re
from pathlib import Path
from importlib import metadata

ROOT = Path(__file__).resolve().parent.parent

# Files that belong to the abandoned embedding / vector-search / sprint feature.
# Nothing on the runtime path (backend app / worker) imports these.
DEAD_FILES = {
    "utils/ai/embedding_helper.py",
    "utils/ai/chunking_helper.py",
    "utils/database/vectordb_helper.py",
}
# Directories to scan as "live" runtime code.
LIVE_DIRS = ["services", "core", "utils", "config", "worker"]

STDLIB = set(sys.stdlib_module_names)
LOCAL_PKGS = {"services", "core", "utils", "config", "worker", "backend", "frontend", "tests", "scripts", "database"}


def find_dead_sprint_files():
    """Locate any *sprint_data_service* modules — treat as dead too."""
    dead = set()
    for p in ROOT.rglob("*sprint_data_service*.py"):
        rel = p.relative_to(ROOT).as_posix()
        if not rel.startswith((".venv", "tests", "scripts")):
            dead.add(rel)
    return dead


def top_level_imports(py_file):
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:  # ignore relative imports
                mods.add(node.module.split(".")[0])
    return mods


def main():
    dead = DEAD_FILES | find_dead_sprint_files()
    print("=== Dead files excluded from scan ===")
    for d in sorted(dead):
        print("  ", d)

    # 1. collect live imports
    live_imports = set()
    scanned = 0
    for d in LIVE_DIRS:
        for py in (ROOT / d).rglob("*.py"):
            rel = py.relative_to(ROOT).as_posix()
            if rel in dead:
                continue
            scanned += 1
            live_imports |= top_level_imports(py)

    # 2. filter to third-party
    third_party = sorted(
        m for m in live_imports
        if m not in STDLIB and m not in LOCAL_PKGS and not m.startswith("_")
    )
    print(f"\n=== Scanned {scanned} live files. Third-party top-level imports ===")
    print("  ", third_party)

    # 3. map module -> distribution
    pkg_dist = metadata.packages_distributions()
    root_dists = set()
    unmapped = []
    for mod in third_party:
        dists = pkg_dist.get(mod)
        if dists:
            root_dists.update(dists)
        else:
            unmapped.append(mod)
    print("\n=== Unmapped modules (no installed dist provides them) ===")
    print("  ", unmapped or "(none)")

    # The bare `import google` (from `from google import genai`) maps to EVERY
    # installed google-* namespace package. Only the new SDK (google-genai) is
    # actually used; drop the rest as roots and let the closure re-add whatever
    # google-genai genuinely requires.
    root_dists = {
        d for d in root_dists
        if not (d.lower().startswith("google") and d.lower() != "google-genai")
    }

    # psycopg needs the binary extra + pool; make sure they're roots
    for forced in ("psycopg", "psycopg-binary", "psycopg-pool"):
        try:
            metadata.version(forced)
            root_dists.add(forced)
        except metadata.PackageNotFoundError:
            pass

    print("\n=== Direct (root) distributions ===")
    for r in sorted(root_dists, key=str.lower):
        print("  ", r)

    # 4. transitive closure
    def norm(name):
        return re.split(r"[<>=!;\[\s]", name.strip())[0].lower().replace("_", "-")

    installed = {norm(d.metadata["Name"]): d.metadata["Name"] for d in metadata.distributions()}

    closure = set()
    stack = [norm(r) for r in root_dists]
    while stack:
        cur = stack.pop()
        if cur in closure or cur not in installed:
            continue
        closure.add(cur)
        try:
            reqs = metadata.requires(installed[cur]) or []
        except metadata.PackageNotFoundError:
            reqs = []
        for req in reqs:
            # skip optional (extra) deps
            if "extra ==" in req:
                continue
            dep = norm(req)
            if dep and dep not in closure:
                stack.append(dep)

    print(f"\n=== Closure size: {len(closure)} distributions ===")

    # 5. emit
    lines = []
    for name in sorted(closure):
        real = installed.get(name)
        if not real:
            continue
        ver = metadata.version(real)
        lines.append(f"{real}=={ver}")

    print("\n=== Proposed requirements.txt ===")
    print("\n".join(lines))

    # compare with current
    current = set()
    for ln in (ROOT / "requirements.txt").read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            current.add(norm(ln))
    proposed = {norm(l) for l in lines}
    print("\n=== REMOVED (in current, not in proposed) ===")
    print("  ", sorted(current - proposed))
    print("\n=== ADDED (in proposed, not in current) ===")
    print("  ", sorted(proposed - current))

    if "--write" in sys.argv:
        header = (
            "# Runtime dependencies for QA-Assistant backend + worker.\n"
            "# Auto-derived from the live-app dependency closure (no dead ML/vector deps).\n"
            "# Regenerate: python scripts/build_requirements.py --write\n"
        )
        (ROOT / "requirements.txt").write_text(header + "\n".join(lines) + "\n")
        print("\n*** requirements.txt WRITTEN ***")


if __name__ == "__main__":
    main()
