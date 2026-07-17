"""Data models for extracted transcript content and registry match results."""

from typing import List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Extraction models (what Claude pulls out of a transcript PDF)
# ---------------------------------------------------------------------------

class CourseEntry(BaseModel):
    subject_code: Optional[str] = None      # e.g. "ENGL"
    course_number: Optional[str] = None     # e.g. "1A", "1030"
    title: str                              # e.g. "College Composition and Reading"
    credits_attempted: Optional[float] = None
    credits_earned: Optional[float] = None
    grade: Optional[str] = None             # e.g. "A", "B+", "CR", "W"
    term: Optional[str] = None              # e.g. "2019 Fall", "Spring 2021"
    term_start_date: Optional[str] = None   # ISO 8601 if printed on the transcript
    term_end_date: Optional[str] = None
    level: Optional[str] = None             # "undergraduate" | "graduate" | other
    is_transfer: bool = False               # taken at another institution and transferred in
    taught_at: Optional[str] = None         # institution/campus that actually taught it,
                                            # if different from the issuing institution


class DegreeAward(BaseModel):
    name: str                               # e.g. "Associate of Science"
    major: Optional[str] = None
    date_awarded: Optional[str] = None      # as printed; ISO 8601 when possible
    honors: Optional[str] = None
    institution: Optional[str] = None       # awarding institution if not the issuer


class TranscriptData(BaseModel):
    issuing_institution: str                # the school that produced the transcript
    institution_location: Optional[str] = None   # city/state if printed
    institution_system: Optional[str] = None     # district or system, e.g. "Peralta CCD"
    transcript_date: Optional[str] = None        # date issued/printed
    student_level: Optional[str] = None          # "undergraduate" | "graduate" | mixed
    transfer_institutions: List[str] = []
    degrees: List[DegreeAward] = []
    courses: List[CourseEntry] = []
    parsing_notes: Optional[str] = None          # anything ambiguous or unreadable


# ---------------------------------------------------------------------------
# Match result models (transcript entity vs. Credential Registry record)
# ---------------------------------------------------------------------------

class Skill(BaseModel):
    """A competency linked to a matched registry record (ceterms:teaches /
    ceterms:assesses alignment)."""
    name: Optional[str] = None              # None until resolved, if URI-only
    description: Optional[str] = None
    framework: Optional[str] = None         # competency framework name
    uri: Optional[str] = None               # target competency resource URI
    source: Optional[str] = None            # "teaches" | "assesses"


class SkillSummary(BaseModel):
    """One deduplicated skill in a transcript-level skills profile."""
    name: str
    framework: Optional[str] = None
    uri: Optional[str] = None
    source_courses: List[str] = []          # which matched courses teach it


class RegistryCandidate(BaseModel):
    uri: str                                # @id of the registry resource
    ctid: Optional[str] = None
    ctdl_type: Optional[str] = None
    name: Optional[str] = None
    coded_notation: Optional[str] = None
    score: float = 0.0                      # 0..1 similarity score


class MatchResult(BaseModel):
    kind: str                               # "organization" | "course" | "credential"
    query_text: str                         # what we searched for (name / code + title)
    matched: bool = False
    confidence: str = "none"                # "high" | "medium" | "low" | "none"
    score: float = 0.0
    best: Optional[RegistryCandidate] = None
    runners_up: List[RegistryCandidate] = []
    detail: Optional[str] = None            # human-readable explanation
    skills: List[Skill] = []                # competencies on the matched record


class TranscriptReport(BaseModel):
    source_file: str
    transcript: TranscriptData
    organization_matches: List[MatchResult] = []   # issuer + transfer institutions
    course_matches: List[MatchResult] = []
    credential_matches: List[MatchResult] = []
    skills_profile: List[SkillSummary] = []        # deduped across all matches
    errors: List[str] = []
