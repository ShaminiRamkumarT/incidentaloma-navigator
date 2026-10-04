"""LLM extractor: Claude reads the report and returns structured findings (Pydantic-validated).

The model only extracts what the report says. The guideline decision stays in the
deterministic engine (guidelines.py), so every recommendation remains auditable.
Requires ANTHROPIC_API_KEY (or another credential the Anthropic SDK can find).
"""
import anthropic

from .schema import ReportExtraction

MODEL = "claude-opus-5-5"

SYSTEM = """You extract incidental renal and adrenal lesions from CT radiology reports into a fixed schema.

Rules:
- One Finding per distinct renal or adrenal lesion. Ignore stones, hydronephrosis, normal organs and other organs.
- Use the FINDINGS section for imaging features and the IMPRESSION/recommendation text for stated_actions and reported_category.
- size_cm is the largest dimension, converted to cm.
- Put each attenuation value in unenhanced_hu (non-contrast) or enhanced_hu (any post-contrast phase); for a single-phase
  exam, use the exam technique to decide.
- composition: "cystic" if the report calls the lesion a cyst/cystic anywhere, "solid" if it calls it solid, otherwise "indeterminate".
- septa_count: use the number given; "few" = 2; any vaguer plural quantity = 4.
- stated_actions: only what the radiologist recommended for that lesion.
  IMAGING_SURVEILLANCE = interval follow-up imaging; CHARACTERIZATION_IMAGING = dedicated imaging to characterize the lesion now;
  SPECIALIST_REFERRAL = referral to a specialist, surgeon or multidisciplinary team;
  HORMONAL_WORKUP = any hormonal, biochemical or endocrine testing;
  NO_FOLLOWUP only when the report explicitly says no follow-up/no further imaging. Leave empty if nothing is recommended.
- Never infer values the report does not state; use null."""

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def extract(text: str) -> ReportExtraction:
    response = _get_client().messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"<report>\n{text}\n</report>"}],
        output_format=ReportExtraction,
        # Server-side fallback if a safety classifier declines the request.
        extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
        extra_body={"fallbacks": "default"},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Model declined the request: {response.stop_details}")
    if response.parsed_output is None:
        raise RuntimeError(f"No structured output (stop_reason={response.stop_reason})")
    return response.parsed_output
