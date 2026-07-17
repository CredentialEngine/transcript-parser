"""Generate HTML, JSON, and CSV reports from match results."""

import csv
import html
import json
from datetime import datetime
from pathlib import Path

from .models import MatchResult, TranscriptReport

CONF_COLORS = {"high": "#1a7f37", "medium": "#9a6700", "low": "#bc4c00", "none": "#cf222e"}


def _badge(r: MatchResult) -> str:
    color = CONF_COLORS.get(r.confidence, "#57606a")
    label = f"{r.confidence} ({r.score:.2f})" if r.score else r.confidence
    return (f'<span style="background:{color};color:#fff;border-radius:10px;'
            f'padding:2px 8px;font-size:12px;white-space:nowrap">{label}</span>')


def _match_cell(r: MatchResult) -> str:
    if r.best is None:
        return f'<em>{html.escape(r.detail or "no candidate found")}</em>'
    name = html.escape(r.best.name or "(unnamed)")
    code = f" <code>{html.escape(r.best.coded_notation)}</code>" if r.best.coded_notation else ""
    typ = html.escape((r.best.ctdl_type or "").replace("ceterms:", ""))
    link = f'<a href="{html.escape(r.best.uri)}" target="_blank">{name}</a>' if r.best.uri else name
    return f"{link}{code} <small style='color:#57606a'>{typ}</small>"


def _table(rows: list[str], headers: list[str]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    return (f'<table><thead><tr>{head}</tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def _summary_counts(results: list[MatchResult]) -> dict:
    return {
        "total": len(results),
        "matched": sum(1 for r in results if r.matched),
        "high": sum(1 for r in results if r.confidence == "high"),
        "medium": sum(1 for r in results if r.confidence == "medium"),
        "low": sum(1 for r in results if r.confidence == "low"),
        "none": sum(1 for r in results if r.confidence == "none"),
    }


def write_reports(reports: list[TranscriptReport], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- JSON (full fidelity) ----
    (out_dir / "results.json").write_text(
        json.dumps([r.model_dump() for r in reports], indent=2), encoding="utf-8")

    # ---- CSV of course matches ----
    with (out_dir / "course_matches.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_file", "institution", "course", "matched", "confidence",
                    "score", "registry_name", "registry_code", "registry_ctid",
                    "registry_uri"])
        for rep in reports:
            for r in rep.course_matches:
                w.writerow([
                    rep.source_file, rep.transcript.issuing_institution, r.query_text,
                    r.matched, r.confidence, r.score,
                    r.best.name if r.best else "", r.best.coded_notation if r.best else "",
                    r.best.ctid if r.best else "", r.best.uri if r.best else "",
                ])

    # ---- CSV of the skills profiles ----
    with (out_dir / "skills.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_file", "institution", "skill", "framework",
                    "registry_uri", "source_courses"])
        for rep in reports:
            for s in rep.skills_profile:
                w.writerow([rep.source_file, rep.transcript.issuing_institution,
                            s.name, s.framework or "", s.uri or "",
                            "; ".join(s.source_courses)])

    # ---- HTML ----
    sections = []
    grand = {"orgs": [], "courses": [], "creds": []}
    total_skills = 0
    for rep in reports:
        t = rep.transcript
        grand["orgs"].extend(rep.organization_matches)
        grand["courses"].extend(rep.course_matches)
        grand["creds"].extend(rep.credential_matches)
        total_skills += len(rep.skills_profile)

        org_rows = [
            f"<tr><td>{html.escape(r.query_text)}</td><td>{_match_cell(r)}</td>"
            f"<td>{_badge(r)}</td></tr>"
            for r in rep.organization_matches]
        cred_rows = [
            f"<tr><td>{html.escape(r.query_text)}</td><td>{_match_cell(r)}</td>"
            f"<td>{_badge(r)}</td></tr>"
            for r in rep.credential_matches]
        course_rows = []
        for course, r in zip(t.courses, rep.course_matches):
            when = course.term or course.term_start_date or ""
            course_rows.append(
                f"<tr><td>{html.escape(r.query_text)}</td>"
                f"<td>{html.escape(when)}</td>"
                f"<td>{html.escape(course.grade or '')}</td>"
                f"<td>{'transfer' if course.is_transfer else ''}</td>"
                f"<td>{_match_cell(r)}</td><td>{_badge(r)}</td></tr>")

        skills_rows = []
        for s in rep.skills_profile:
            name_cell = (f'<a href="{html.escape(s.uri)}" target="_blank">'
                         f'{html.escape(s.name)}</a>' if s.uri else html.escape(s.name))
            skills_rows.append(
                f"<tr><td>{name_cell}</td>"
                f"<td>{html.escape(s.framework or '')}</td>"
                f"<td>{html.escape('; '.join(s.source_courses))}</td></tr>")
        skills_html = (
            f"<h4>Skills profile ({len(rep.skills_profile)} unique competencies)</h4>"
            + _table(skills_rows, ["Skill / competency", "Framework", "From course(s)"])
            if skills_rows else
            "<h4>Skills profile</h4><p><em>No competency data linked to the "
            "matched registry records.</em></p>")

        cc = _summary_counts(rep.course_matches)
        degrees = "".join(
            f"<li>{html.escape(d.name)}"
            + (f" — {html.escape(d.major)}" if d.major else "")
            + (f" ({html.escape(d.date_awarded)})" if d.date_awarded else "") + "</li>"
            for d in t.degrees) or "<li><em>none listed</em></li>"
        errors = "".join(f"<li>{html.escape(e)}</li>" for e in rep.errors)
        notes = (f"<p><strong>Parsing notes:</strong> {html.escape(t.parsing_notes)}</p>"
                 if t.parsing_notes else "")

        sections.append(f"""
<details open>
<summary><strong>{html.escape(rep.source_file)}</strong> —
  {html.escape(t.issuing_institution)}
  <small>({cc['matched']}/{cc['total']} courses matched)</small></summary>
<div class="body">
  <p><strong>Transcript date:</strong> {html.escape(t.transcript_date or 'n/a')}
     &nbsp;|&nbsp; <strong>Location:</strong> {html.escape(t.institution_location or 'n/a')}
     &nbsp;|&nbsp; <strong>System/District:</strong> {html.escape(t.institution_system or 'n/a')}</p>
  <p><strong>Degrees awarded:</strong></p><ul>{degrees}</ul>
  {notes}
  <h4>Institutions</h4>
  {_table(org_rows, ["Institution on transcript", "Registry match", "Confidence"])}
  <h4>Credentials awarded</h4>
  {_table(cred_rows, ["Degree on transcript", "Registry match", "Confidence"]) if cred_rows else "<p><em>none</em></p>"}
  <h4>Courses ({cc['total']}) — {cc['high']} high, {cc['medium']} medium, {cc['low']} low, {cc['none']} unmatched</h4>
  {_table(course_rows, ["Course on transcript", "Term", "Grade", "", "Registry match", "Confidence"])}
  {skills_html}
  {f'<h4>Errors</h4><ul>{errors}</ul>' if errors else ''}
</div>
</details>""")

    def stat_block(label: str, results: list[MatchResult]) -> str:
        c = _summary_counts(results)
        pct = (100 * c["matched"] // c["total"]) if c["total"] else 0
        return (f'<div class="stat"><div class="n">{c["matched"]}/{c["total"]}</div>'
                f'<div class="l">{label} matched ({pct}%)</div></div>')

    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Credential Registry Transcript Match Report</title>
<style>
 body {{ font-family: Segoe UI, system-ui, sans-serif; margin: 24px auto; max-width: 1200px;
        color: #1f2328; }}
 table {{ border-collapse: collapse; width: 100%; margin: 8px 0 20px; font-size: 14px; }}
 th, td {{ border: 1px solid #d0d7de; padding: 5px 9px; text-align: left; vertical-align: top; }}
 th {{ background: #f6f8fa; }}
 details {{ border: 1px solid #d0d7de; border-radius: 8px; margin: 14px 0; }}
 summary {{ padding: 10px 14px; cursor: pointer; background: #f6f8fa; border-radius: 8px; }}
 .body {{ padding: 6px 16px 14px; }}
 .stats {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 18px 0; }}
 .stat {{ border: 1px solid #d0d7de; border-radius: 8px; padding: 12px 20px; }}
 .stat .n {{ font-size: 26px; font-weight: 700; }}
 .stat .l {{ color: #57606a; font-size: 13px; }}
 code {{ background: #f6f8fa; padding: 1px 5px; border-radius: 4px; }}
</style></head><body>
<h1>Credential Registry Transcript Match Report</h1>
<p>Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · {len(reports)} transcript(s)</p>
<div class="stats">
  {stat_block("institutions", grand["orgs"])}
  {stat_block("courses", grand["courses"])}
  {stat_block("credentials", grand["creds"])}
  <div class="stat"><div class="n">{total_skills}</div>
    <div class="l">unique skills identified</div></div>
</div>
{''.join(sections)}
</body></html>"""

    html_path = out_dir / "report.html"
    html_path.write_text(page, encoding="utf-8")
    return html_path
