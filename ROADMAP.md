# Roadmap: Transcript Matcher → CE/AACRAO Transcript Parser Vision

Gap analysis of the current tool against "Transcript Parser: Translating
Academic Records into Skills and Opportunities" (CE + AACRAO + Anthropic
write-up), and a phased plan to close it.

## Where the current tool already delivers on the vision

| Write-up requirement | Status |
|---|---|
| Read any transcript (PDF incl. scanned, varied layouts) | ✅ Claude extraction, one code path; validated on 39 real samples |
| Identify courses' globally unique CTIDs | ✅ Course → CTID matching via org catalog (code + title similarity) |
| Credits, grades, terms, institutions, degrees | ✅ Extracted with structured schema |
| Confidence scoring / communicating certainty | ✅ high/medium/low/none bands + runner-up candidates in report |
| Traceability | ✅ Every match links to the registry resource URI/CTID |
| Uses existing Registry course-catalog data | ✅ Search API (subClassOf LOP, dual owned/offered queries) |

## Gaps between current design and the vision

1. **Skills are the point — and we don't return them yet.** The write-up's
   core promise is transcripts → *skills profiles*. We stop at the course
   CTID; we never fetch `ceterms:teaches` → competency data.
2. **PII posture is inverted.** Current design deliberately strips learner
   PII. The vision requires learner identity + transcript-only data
   (semester GPA, cumulative GPA, milestones) in a normative structure for
   downstream processing.
3. **Academic summary data is not captured.** Term/cumulative GPA, academic
   standing, honors/dean's list milestones exist in `parsing_notes` prose at
   best, not as structured fields.
4. **Input formats.** No image (photographed transcript) or plain-text
   input; no PESC XML / EDI (SPEEDE) — the machine-readable formats AACRAO
   institutions actually exchange.
5. **No conversational access.** The vision is "AI-enabled natural language
   conversations"; today it's a batch CLI.
6. **No gap analysis.** "How close am I to a credential?" requires comparing
   matched courses against `ceterms:requires` condition profiles on
   registry credentials.
7. **No trust/verification layer.** Nothing checks PDF digital signatures,
   issuer authenticity against the registry, or verifiable-credential
   packaging.
8. **Confidence is heuristic, not calibrated.** Bands are hand-tuned
   thresholds; registrar-grade transfer-credit decisions need measured
   precision on a labeled golden set.

## Phase 1 — Skills output + richer extraction (the demo-able core)

*The minimum needed for the write-up's headline story to be true.*

- **Skills retrieval:** for each matched course/credential, fetch linked
  competencies (`ceterms:teaches` → CTDL-ASN frameworks) via the Search API's
  Description Sets / RelatedItems, or per-resource graph fetch. Add a
  `skills` section per matched course and an aggregated **skills profile**
  per transcript (deduped competencies with source-course traceability).
- **Extraction schema additions:** per-term GPA and credit totals,
  cumulative GPA, academic standing, honors/dean's list/milestones,
  enrollment status, catalog year if printed.
- **PII mode:** `--pii include|exclude` (default exclude, preserving current
  FERPA-safe behavior). When included, learner name/DOB/student ID go into a
  clearly separated `learner` block.
- **Normative output structure:** define the JSON schema for the full result
  (learner block + registry-matched data + transcript-only data). Candidate
  anchors: CTDL JSON-LD for registry entities; review AACRAO/PESC field
  naming for the transcript-only block. (Write-up marks this TBD — needs a
  working session with Deb/Mike/Mark.)
- **Image + text input:** accept JPG/PNG (Claude vision) and .txt.

## Phase 2 — Registrar-grade quality

- **Golden dataset & calibration:** hand-label correct matches for the 39
  sample transcripts (org/course/credential level). Add an eval script that
  reports precision/recall per confidence band; tune thresholds against it.
  This is the substance behind the write-up's "expert guidance for
  confidence scoring" ask.
- **Review workflow:** report flags low/medium matches for human
  confirmation; accept/reject feeds back into the golden set.
- **PESC XML / EDI SPEEDE ingestion:** deterministic parsers (no LLM cost,
  no extraction uncertainty) for institutions that can supply them.
- **Registry coverage report:** per-institution counts of courses/credentials
  found vs. transcript needs — doubles as an internal CE data-quality tool
  showing exactly where Registry course coverage is missing.
- **Collections traversal:** follow `ceterms:Collection` membership where
  orgs publish courses inside collections.

## Phase 3 — Conversational and pathway intelligence

- **MCP server** wrapping the pipeline (`parse_transcript`,
  `match_to_registry`, `get_skills_profile`, `credential_gap_analysis`) so
  Claude (claude.ai, Claude Code, or a custom app) can converse over any
  transcript. This is the shortest path to "natural language conversations."
- **Credential gap analysis:** compare a learner's matched courses/credits
  against `ceterms:requires` condition profiles of candidate credentials at
  matched institutions → "you appear to be N credits from X" (with the
  caveat language registrars require).
- **Batch mode at scale:** Anthropic Batches API (~50% cost reduction) for
  bulk institutional runs; per-run token/cost reporting.

## Phase 4 — Trust and verification

- **Document authenticity:** detect and validate PDF digital signatures
  (Parchment/NSC-style signed transcripts); surface signer identity.
- **Issuer verification:** cross-check the signing/issuing institution
  against its Registry record — CE as trust registry (write-up's PKI
  question). Scope investigation first; this is research, not a feature yet.
- **Verifiable credential packaging:** optional W3C VC output of the parsed
  + matched result for downstream wallets/CLRs.

## Cross-cutting (every phase)

- **Privacy/FERPA framing:** document the data path (PDF → Anthropic API,
  no training on API data; local caching; retention). Decide whether
  zero-data-retention or a BAA-style arrangement is needed before
  non-redacted production use — aligns with the write-up's privacy ask.
- **Known registry data realities to communicate, not code around:**
  many institutions have no published course data (the tool now reports
  this explicitly); learning opportunities are inconsistently typed
  (handled via subClassOf); some orgs exist only at district or campus
  level (handled via name-variant search, verify on next full run).
