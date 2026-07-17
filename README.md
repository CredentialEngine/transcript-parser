# Transcript Parser: Translating Academic Records into Skills and Opportunities

An AI-powered transcript parser that reads college transcripts, extracts the
institutions, courses, credits, grades, and degrees they contain, and maps
them to CTDL records in the **Credential Registry** — returning globally
unique identifiers (CTIDs) and the linked data behind them, including the
skills and competencies each course teaches.

37 million Americans have completed college courses without earning a
credential. Their transcripts are static records of learning that employers
and institutions cannot easily interpret. By connecting transcript contents
to the Credential Registry's transparent, machine-actionable descriptions,
this tool turns academic records into dynamic skills profiles — supporting
skills-based hiring, faster transfer credit evaluation, and clearer paths
back to credential completion.

A collaboration of **Credential Engine** and **AACRAO**.

## What it does

Given a folder of transcripts (PDF, including scanned documents), the parser:

1. **Extracts** the issuing institution, transfer institutions, every course
   (subject, number, title, credits, grade, term, level, transfer status),
   degrees awarded, and transcript dates — using Claude with a structured
   schema. Learner PII is excluded by default.
2. **Matches institutions** to Registry organizations, handling
   abbreviations, campus qualifiers, and district/system naming.
3. **Matches courses and credentials** to the institution's published
   Registry records (courses, learning opportunities, programs, degrees) by
   course code and title similarity, with a confidence rating on every match.
4. **Builds a skills profile**: competencies linked to matched courses
   (`ceterms:teaches`) are retrieved, deduplicated, and traced back to the
   courses that taught them.
5. **Reports** everything as an HTML report (matches, non-matches,
   confidence, skills), plus JSON and CSV for downstream processing —
   including which institutions have no published Registry data, a useful
   view of Registry coverage.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:ANTHROPIC_API_KEY = "<Anthropic API key>"
$env:CE_REGISTRY_API_KEY = "<Credential Registry Search API key>"

python -m transcript_matcher <folder-of-transcripts> --out output
```

Open `output/report.html` for the match report. Useful flags: `--limit N`
(first N files), `--extract-only` (no Registry key needed), `--env sandbox`
(sandbox Registry), `--model` (default `claude-opus-4-8`).

`python -m transcript_matcher.probe "<institution name>"` tests organization
matching directly.

## Privacy

Transcripts contain FERPA-protected information. Extraction is instructed to
discard learner PII (names, IDs, birth dates), and no transcript documents or
run outputs belong in this repository. Note that transcript files are
transmitted to the Anthropic API for extraction; confirm current
data-handling policy before processing non-redacted documents.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the phased plan: richer academic data and
PII-inclusive normative output, calibrated confidence scoring for registrar
use, conversational access via MCP, credential gap analysis, and transcript
verification/trust.
