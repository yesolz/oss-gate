# Report template

Write each document entirely in its selected language, except exact identifiers, source quotes and code. Use the following sections, translating headings naturally. Use the length the decision needs. Prefer short, connected paragraphs and explain technical terms through their practical effect. Do not repeat the same disclaimer in every section or pad an incomplete review. Keep exact details in evidence tables and sources.

# <package> <version>: adoption review

Start with one blockquote containing three short paragraphs, before collection metadata. Use clear, approachable language; in Korean prefer polite explanations such as "확인이 필요해요" or "먼저 확인하세요" over repeated audit-style declarations. Use natural labels in the selected language: **Decision / Why / Next step**, or **결론 / 이유 / 지금 할 일**. Keep each paragraph to one or two sentences.

> **Decision:** State the exact target and the computed outcome. For supplemental runtime analysis, explicitly label this as a recommendation, not an automated verdict.
>
> **Why:** Explain what the software does and the specific finding that drives the decision in plain language. State any coverage gap that materially limits this conclusion.
>
> **Next step:** Name the most useful action the reader can take now, with an exact version or setting only when supported. Do not imply that a proposed fix has already been verified in their environment.

If `additional_policy` is present, distinguish its effective outcome from `base_overall` and explain its findings. Otherwise omit additional-policy sections.

After the opening, record snapshot date, ecosystem, repository, policy version, verdict and verification status. The renderer places this context separately from the opening summary. Keep detailed counts, full advisory IDs, hashes and collection mechanics in the relevant sections below. These instructions affect presentation, never the computed policy or preserved evidence.

## 1. Decision and scope

An area/status/reason table for license, known vulnerabilities, dependencies and maintenance. State that this is a screening aid, not legal advice or a security guarantee. Explain the actual target and graph version. Separate observation from interpretation.

## 2. What the software does

Its purpose, main capabilities, intended use and architecture. Explain a concrete request/data flow. Attribute DeepWiki material as AI-generated and not pinned to the reviewed version.

## 3. External communication and configuration

What leaves the environment, destinations, telemetry evidence, credentials, relevant settings and defaults. A lack of evidence is not proof of no telemetry. Do not reproduce secrets.

## 4. License review

The package license and dependency license table with exact versions, categories and paths. Explain the specific review questions raised by the observed licenses, including unknown metadata, OR choices, AND obligations or exceptions. Avoid universal conclusions about legal compliance.

## 5. Known vulnerabilities

Canonical advisory groups, aliases, affected packages, scores, publication dates, matching affected/fixed ranges and sources. Explain what an advisory means and whether applicability has been established. Zero findings means no known records returned within the measured scope.

## 6. Dependencies

Graph source and version, direct/transitive counts, role of each direct dependency and relevant paths. Include omitted extras, unresolved ranges, truncation, query failures and differences from a user's lockfile.

## 7. Maintenance

Scorecard date, scores and unevaluated checks. Maintenance signals, release history and security-reporting process with sources. Stars are context, not proof of trust. Do not treat -1 as a scored zero.

## 8. Adoption actions

Specific actions arising from the evidence: package/version, configuration, owner or decision required, and supporting source. Separate a suggested action from a verified remediation.

## 9. Unknowns and limitations

Missing/unindexed/stale sources, mismatched versions, unverified claims, scope limits, alias or severity gaps and all coverage flags. Explain why a prior-version graph cannot establish safety for the requested version.

## 10. Evidence and verification

Map claims to saved evidence and original URLs. Explain how to verify the snapshot hashes. Summarize factual review, mismatches and status. Do not claim that an agent's self-check is an independent audit.
