"""Command-line entry point.

Usage:
    python -m transcript_matcher <folder-or-file> [--out OUTPUT_DIR] [options]
"""

import argparse
import logging
import sys
from pathlib import Path

import anthropic

from . import config
from .extract import extract_transcript
from .match import match_transcript
from .models import TranscriptData, TranscriptReport
from .registry import RegistryClient
from .report import write_reports

log = logging.getLogger("transcript_matcher")

SUPPORTED = {".pdf", ".docx"}


def collect_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(
        p for p in target.rglob("*")
        if p.suffix.lower() in SUPPORTED and not p.name.startswith("~")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="transcript_matcher",
        description="Parse college transcript PDFs and match institutions, courses, "
                    "and credentials against the Credential Registry.")
    parser.add_argument("target", help="Folder of transcripts (PDF/DOCX) or a single file")
    parser.add_argument("--out", default="output", help="Output directory (default: output)")
    parser.add_argument("--env", choices=["production", "sandbox"], default="production",
                        help="Credential Registry environment (default: production)")
    parser.add_argument("--model", default=config.DEFAULT_MODEL,
                        help=f"Claude model for extraction (default: {config.DEFAULT_MODEL})")
    parser.add_argument("--limit", type=int, default=0,
                        help="Only process the first N files (0 = all)")
    parser.add_argument("--extract-only", action="store_true",
                        help="Run extraction only; skip registry matching")
    parser.add_argument("--no-cache", action="store_true",
                        help="Ignore cached extractions and registry responses")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s")

    target = Path(args.target)
    if not target.exists():
        parser.error(f"Path not found: {target}")
    files = collect_files(target)
    if args.limit:
        files = files[: args.limit]
    if not files:
        parser.error("No .pdf or .docx files found.")
    log.info("Found %d transcript file(s)", len(files))

    anthropic_key = config.get_anthropic_key()
    if not anthropic_key:
        print(f"ERROR: set {config.ANTHROPIC_API_KEY_VAR} to run extraction.",
              file=sys.stderr)
        return 2
    ce_key = config.get_ce_key()
    if not args.extract_only and not ce_key:
        print(f"ERROR: set {config.CE_API_KEY_VAR} to run registry matching "
              "(or pass --extract-only).", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    cache_dir = out_dir / ".cache"
    if args.no_cache and cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            f.unlink()

    claude = anthropic.Anthropic(api_key=anthropic_key)
    registry = None
    if not args.extract_only:
        registry = RegistryClient(ce_key, environment=args.env, cache_dir=cache_dir)

    reports: list[TranscriptReport] = []
    for i, path in enumerate(files, 1):
        log.info("[%d/%d] %s", i, len(files), path.name)
        report = TranscriptReport(
            source_file=path.name,
            transcript=TranscriptData(issuing_institution="(extraction failed)"))
        try:
            report.transcript = extract_transcript(
                claude, path, cache_dir, model=args.model)
        except Exception as exc:
            log.error("Extraction failed for %s: %s", path.name, exc)
            report.errors.append(f"Extraction failed: {exc}")
            reports.append(report)
            continue

        if registry is not None:
            try:
                orgs, courses, creds, skills, errors = match_transcript(
                    registry, report.transcript)
                report.organization_matches = orgs
                report.course_matches = courses
                report.credential_matches = creds
                report.skills_profile = skills
                report.errors.extend(errors)
            except Exception as exc:
                log.error("Matching failed for %s: %s", path.name, exc)
                report.errors.append(f"Matching failed: {exc}")
        reports.append(report)

    html_path = write_reports(reports, out_dir)
    print(f"\nDone. Report: {html_path.resolve()}")
    print(f"Also wrote: {out_dir / 'results.json'} and {out_dir / 'course_matches.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
