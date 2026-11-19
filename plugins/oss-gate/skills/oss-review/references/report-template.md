# Report template

Write each document entirely in its selected language, except exact identifiers, source quotes and code. Use the following sections, translating headings naturally. Aim for a substantive 1,500 to 3,000 words when the evidence supports it; never pad an incomplete review with invented facts.

# <package> <version>: adoption review

Snapshot date, ecosystem, repository, policy version, verdict and verification status.

> Summarize what it does, why this verdict follows, and what must happen before adoption in three short paragraphs. State important coverage gaps here.

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
