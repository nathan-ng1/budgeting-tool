"""Commands for building the Retail Edition (Issue #252). Run from the repo root
with the `retail-build` dependency group synced:

    python -m retail_build version [--tag vX.Y.Z]   print the Version being built
    python -m retail_build build   [--output-dir D] compile, then check the bundle
    python -m retail_build smoke   [--output-dir D] launch the build and check it

The workflow (`.github/workflows/retail-windows-build.yml`) runs these after
`npm run build` and `python -m dashboard.build_info`.
"""

import argparse
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from retail_build import bundle_check, plan, smoke

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "retail-build"
REPORT_NAME = "compilation-report.xml"


def project_version(pyproject: Path = REPO_ROOT / "pyproject.toml") -> str:
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]


def check_tag(tag: str, version: str) -> None:
    """A release build must carry the Version its tag names (spec #236: one tag, one Version)."""
    if tag.removeprefix("v") != version:
        raise SystemExit(f"Tag {tag} does not match the Version in pyproject.toml ({version}).")


def build(output_dir: Path) -> None:
    version = project_version()
    for needed in (plan.STATIC_DIR / "index.html", plan.BUILD_INFO_FILE):
        if not (SRC / needed).is_file():
            raise SystemExit(
                f"src/{needed.as_posix()} is missing: run `npm run build` in frontend/ "
                "and `python -m dashboard.build_info` first."
            )
    output_dir.mkdir(parents=True, exist_ok=True)
    report = output_dir / REPORT_NAME
    args = plan.nuitka_args(src=SRC, output_dir=output_dir, version=version, report=report)
    subprocess.run([sys.executable, "-m", "nuitka", *args], check=True)

    problems = bundle_check.problems(report, plan.dist_dir(output_dir))
    if problems:
        raise SystemExit("The build is not a Retail build:\n- " + "\n- ".join(problems))
    print(f"Built {plan.dist_dir(output_dir)} (v{version}); no Collaborator-only package is in it.")


def run_smoke(output_dir: Path) -> None:
    executable = plan.executable_path(output_dir)
    if not executable.is_file():
        raise SystemExit(f"{executable} does not exist: build first.")
    with tempfile.TemporaryDirectory(prefix="retail-smoke-") as workdir:
        try:
            smoke.run_smoke([str(executable)], workdir=Path(workdir), expected_version=project_version())
        except smoke.SmokeFailure as failure:
            raise SystemExit(f"Smoke test failed: {failure}")
    print("Smoke test passed.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="retail_build")
    commands = parser.add_subparsers(dest="command", required=True)
    version = commands.add_parser("version")
    version.add_argument("--tag", help="fail unless this tag (vX.Y.Z) matches pyproject.toml's version")
    for name in ("build", "smoke"):
        commands.add_parser(name).add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    if args.command == "version":
        if args.tag:
            check_tag(args.tag, project_version())
        print(project_version())
    elif args.command == "build":
        build(args.output_dir)
    else:
        run_smoke(args.output_dir)


if __name__ == "__main__":
    main()
