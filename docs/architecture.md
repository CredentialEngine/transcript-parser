# How the Transcript Parser Works

The parser turns a transcript document into Registry-linked data: matched
institutions, courses, and credentials (with CTIDs and confidence ratings) and
a skills profile built from the competencies those courses teach.

**The LLM does exactly one job: reading the transcript.** Claude is called once
per transcript to turn the document into structured data (plus, rarely, one
repair call if its JSON fails validation). Everything after that, including
Registry search, matching, confidence scoring, and skills retrieval, is
deterministic code calling the Credential Registry. Same inputs, same outputs.

## Sequence diagram (one transcript)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant CLI as Parser (CLI)
    participant Cache as Local cache<br/>(output/.cache)
    participant Claude as Claude API<br/>(LLM)
    participant Search as Registry Search API<br/>(API key)
    participant Res as Registry resources<br/>(public, no key)

    User->>CLI: python -m transcript_matcher <folder>

    rect rgb(255, 243, 224)
    Note over CLI,Claude: Stage 1: Extraction (the only LLM step)
    CLI->>Cache: Extraction cached for this file hash?
    alt Cache hit
        Cache-->>CLI: Structured transcript data ($0, no LLM call)
    else Cache miss
        CLI->>Claude: LLM CALL: PDF (or DOCX text) + extraction prompt + JSON schema
        Claude-->>CLI: JSON: institutions, courses, credits, grades, terms, degrees
        CLI->>CLI: Validate JSON against schema (Pydantic)
        opt Validation fails (rare)
            CLI->>Claude: LLM REPAIR CALL: invalid JSON + validation error
            Claude-->>CLI: Corrected JSON
        end
        CLI->>Cache: Save extraction
    end
    end

    rect rgb(227, 242, 253)
    Note over CLI,Search: Stage 2: Match institutions (issuer + transfer schools)
    loop Name variants until a strong match (exact, then contains, then full text)
        CLI->>Search: Organization search by name / alternateName
        Search-->>CLI: Candidate organizations
    end
    CLI->>CLI: Score candidates, assign confidence (high / medium / low / none)
    end

    rect rgb(232, 245, 233)
    Note over CLI,Search: Stage 3: Match courses and credentials
    CLI->>Search: All courses / learning opportunities owned or offered by matched org
    Search-->>CLI: Institution course catalog (paginated, cached)
    CLI->>CLI: Match each transcript course by course code + title, score confidence
    CLI->>Search: All credentials owned or offered by matched org
    Search-->>CLI: Institution credentials (cached)
    CLI->>CLI: Match each degree awarded, score confidence
    end

    rect rgb(243, 229, 245)
    Note over CLI,Res: Stage 4: Skills profile
    CLI->>CLI: Read competencies (ceterms:teaches) on each matched record
    opt Competency given only as a URI
        CLI->>Res: GET competency record
        Res-->>CLI: Competency name and framework (cached)
    end
    CLI->>CLI: Deduplicate into a skills profile, each skill traced to its source courses
    end

    CLI-->>User: report.html, results.json, course_matches.csv, skills.csv
```

## What each participant is

| Participant | Role | Cost |
|---|---|---|
| **Claude API** | Reads the transcript (PDF, including scanned pages, or DOCX) into structured data. The only AI step. | About $0.12 for a typical 4 page transcript; $0 when cached |
| **Registry Search API** | Finds organizations, course catalogs, and credentials. Requires a Credential Engine API key. | No Anthropic cost |
| **Registry resources** | Public CTDL records, fetched only to resolve competency names referenced by URI. | Free, no key |
| **Local cache** | Stores extractions (by file hash) and Registry responses so re-runs skip repeated work. | n/a |

## Key design points

- **One LLM call per transcript, then deterministic.** Matching decisions are
  inspectable code, not model judgments, which makes results reproducible and
  explainable to registrars. See [confidence.md](confidence.md) for how scores
  are computed.
- **Catalog download, then local matching.** Courses are matched against the
  institution's full Registry catalog in memory rather than one API call per
  course, keeping Registry traffic to a handful of calls per transcript.
- **Skills are linked data, not inference.** Competencies come directly from
  the matched Registry records. The LLM never guesses skills.
- **Coverage is visible.** When a matched institution has no course records in
  the Registry, the report says so explicitly instead of reporting a failed
  match.

Code map: extraction in [`extract.py`](../transcript_matcher/extract.py),
Registry queries in [`registry.py`](../transcript_matcher/registry.py),
matching, scoring, and skills in [`match.py`](../transcript_matcher/match.py),
outputs in [`report.py`](../transcript_matcher/report.py).
