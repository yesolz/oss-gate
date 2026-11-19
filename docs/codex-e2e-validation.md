# Codex end-to-end validation

Tested on 2026-11-20 (Asia/Seoul) using the public OSS Gate 0.2.1 marketplace installation, Codex CLI 0.163.0-alpha.11 and the existing ChatGPT login. The configured model was gpt-6.1-sol. These are model-driven user journeys, separate from the deterministic regression suite.

## Installation and execution

Installed with the documented commands:

```sh
codex plugin marketplace add yesolz/oss-gate
codex plugin add oss-gate@oss-gate
```

Fresh ephemeral Codex sessions received natural-language requests in empty output directories. The model selected the installed `oss-review` skill and called the installed MCP tools itself. No expected verdict or report text was supplied. The reviewed packages and runtimes were not installed or executed.

The first two noninteractive attempts used an approval policy of `never`. MCP calls required approval and stopped before collection; neither attempt fabricated a completed review. The successful runs used Codex's `--approve-for-me` mode. No persistent approval settings were changed. This validates the CLI flow with automatic approval review, not an approval-free interactive desktop flow.

## Brotli comparison

The request asked for separate Korean adoption reviews of PyPI brotli 1.2.0 and 1.2.1, evidence for CVE-2026-111497, the fix difference, original data and HTML.

- Both `collect_review` calls and DeepWiki calls completed. Each version has its own immutable snapshot, original API responses, Korean narrative, standalone HTML and verification record.
- Version 1.2.0 produced `hold`, with GHSA and PYSEC aliases grouped into one vulnerability at CVSS 3.1 9.8.
- Version 1.2.1 produced no known advisory matches in the measured scope. Its overall verdict remained `conditional` because of the dated Scorecard score of 6.4, rather than claiming complete safety.
- The reports matched the fix to PyPI brotli 1.2.1, distinguished other branches and brotlicffi, and retained source disagreements and native/build dependency limitations.
- An independent review found no material narrative discrepancy. Both policies recomputed identically, sealed and supplemental hashes matched, and HTML had no broken local links or external resource dependencies.
- Both verification records remain `WARN`: source limitations and unverified deployment artifacts are explicit. The Mac was locked, so Aside visual inspection could not be completed. HTML was checked statically only.

## Node.js runtime boundary

A separate request asked about Node.js runtime 22.23.3, the same CVE, and whether 22.23.4 fixes it.

The model rejected unrelated deps.dev repository package candidates and did not substitute an npm package for the runtime. It used official advisories, releases and tagged source to write a scoped runtime review. It explicitly withheld the package collector's automatic policy verdict and distinguished its own evidence-based recommendation.

The [22.23.4 release](https://nodejs.org/en/blog/release/v22.23.4) and [security announcement](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases) support the fix. The model also compared the tagged decoder source: both releases still identify bundled Brotli as 1.1.0, while 22.23.4 contains the backported fix. A version-string-only comparison would miss that distinction. This is not a test of full native-runtime vulnerability coverage or an exploit reproduction.

## Defect found and local correction

The live records exposed a normalization defect: deps.dev returned `cvss3Score: 0` and an empty vector for CVE-2026-111497 and PYSEC-2026-4322, while OSV supplied no CVSS v3 vector. Version 0.2.1 labelled these individual records as severity `none`. The Brotli group still correctly used the GHSA score of 9.8, and both generated narratives explicitly refused to interpret the individual zero as safety.

The correction treats an uncorroborated zero as unknown, uses a valid available CVSS v3 vector when possible, and preserves a genuine zero-impact vector. Invalid numeric scores also fall back to the vector. It does not add CVSS v4 scoring or change the policy.

All 38 unittest methods, Ruff, MCP stdio smoke checks and distribution checks pass. A fresh live lookup after the correction returned unknown CVSS v3 severity for the CVE/PYSEC records and preserved the GHSA score of 9.8. The original installed version and collected evidence were not modified to disguise the defect. This correction is separate from the published 0.2.1 release.

## Remaining limits

This exercise covers two Codex CLI requests in Korean, not every model, language or ecosystem. Claude's complete model-driven flow, desktop approval UX and current report visuals remain unverified here. Model-generated supplemental investigation and runtime recommendations must remain distinguishable from deterministic package evidence and policy output. Local transcripts and generated reports are retained under the ignored `verification-local/codex-user-test/` directory, not published as release fixtures.
