"""Create an isolated Hermes profile and install Pandora-AEO skill."""
from __future__ import annotations
import argparse
import shutil
import subprocess
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap an isolated Hermes AEO profile.")
    parser.add_argument("--profile", default="aeo-lab")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    hermes = shutil.which("hermes")
    if not hermes:
        parser.error("hermes executable was not found on PATH")
    skill = args.repo / "optional-skills" / "aeo-audit"
    if not (skill / "SKILL.md").is_file():
        parser.error(f"skill not found: {skill / 'SKILL.md'}")
    command = [hermes, "profile", "create", args.profile, "--description", "Audita sitios web, mide AEO y genera assets con evidencia."]
    if args.dry_run:
        print(" ".join(command))
        print(f"Copy {skill} into the new profile's skills directory after creation.")
        return 0
    subprocess.run(command, check=True)
    config_path = subprocess.check_output([hermes, "-p", args.profile, "config", "path"], text=True).strip()
    profile_home = Path(config_path).parent
    destination = profile_home / "skills" / "aeo-audit"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill, destination)
    print(f"Profile created: {args.profile}")
    print(f"Skill installed: {destination / 'SKILL.md'}")
    print("Next: run hermes doctor, configure the model, and verify a no-write audit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
