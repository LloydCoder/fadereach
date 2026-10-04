# Intelligence Model

## Evidence hierarchy

FadeReach separates:

Observation → Evidence → Signal → Interpretation → Hypothesis → Action → Outcome.

An observation is what was seen. Evidence is a provenance-bearing artifact supporting an observation. A signal is a normalized meaningful change. An interpretation/hypothesis is reasoning over evidence. An action is a controlled execution. An outcome is what actually happened.

## Required provenance

Evidence should preserve source, observed time, retrieval time, source location/reference, extraction method and confidence/quality metadata where available.

## No hallucinated authority

AI-generated reasoning MUST NOT overwrite source facts. Unknown remains unknown. Missing evidence is not evidence of absence.

## Why-now

An outbound recommendation should explain:
- account/ICP fit
- observable trigger
- evidence
- likely buyer/problem hypothesis
- offer/angle
- confidence and uncertainty
- proposed action

## Learning

Outcome data feeds experiment and revenue attribution. The system should distinguish correlation from causation and avoid treating a single successful campaign as universal proof.