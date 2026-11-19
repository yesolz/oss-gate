# v0.2.2 validation record

Reviewed on 2026-11-20 (Asia/Seoul). This patch preserves unknown CVSS v3 severity when an upstream zero has no corroborating zero-impact vector. It adds no dependencies, scoring system, hosted service or policy rule.

## Correction

The [initial Codex user test](codex-e2e-validation.md) found that missing CVSS v3 data could appear as severity `none`. The corrected normalizer keeps that uncertainty, recovers scores from valid vectors and preserves genuine zero-impact scores. One regression method covers six representative cases. Unknown severity continues to limit the existing deterministic policy.

## Candidate installation and user journeys

The release archive was extracted and installed through Codex's marketplace commands. Only the extracted marketplace name changed to isolate the installation; all 28 plugin files matched the candidate source byte for byte. Fresh ephemeral sessions used natural-language requests, the configured model and existing ChatGPT login, with `--approve-for-me`. No expected verdicts were supplied and no target package or runtime was installed or executed.

An initial attempt with both marketplace versions installed selected the older MCP server despite selecting the new skill. That attempt was excluded. The public plugin installation was temporarily removed, and all three clean runs were checked against the 0.2.2 MCP process path. This is a test-harness limitation, not evidence that the older server passed candidate validation.

### Next.js: an October fix is not a current clean bill of health

The English request compared npm next 16.4.0 and 16.4.1 against the [October 14 security update](https://nextjs.org/blog/nextjs-security-update-october-14-2026), including CVE-2026-96889.

- Collection succeeded separately for both versions. The root advisory count changed from five to two; the remaining advisories postdated the October fix.
- All observed absent CVSS v3 values remained unknown, exercising the corrected behavior through the installed MCP server. Both policies remained `hold`, including license-review blockers; vulnerability and maintenance limitations were retained.
- The supplemental source comparison distinguished a higher minimum Sharp dependency from the freshly resolved graph: both graphs already resolved Sharp 0.35.5. A graph-only comparison would hide that difference.

### PHP2Shell: native runtime scope remains explicit

The Korean request compared PHP runtimes 8.4.26 and 8.4.27 for CVE-2026-109618 and CVE-2026-109619, using the [official PHP release archive](https://www.php.net/archive/2026.php#2026-10-21-5) and upstream advisory/source evidence.

The model rejected unrelated package candidates and used a scoped manual runtime assessment. It did not fabricate a collector snapshot or automatic policy verdict. The evidence distinguished the two fixes in 8.4.27 from subsequent security fixes in 8.4.28, so fixing PHP2Shell did not automatically approve an outdated runtime for new adoption.

### LiteLLM: a removed version cannot become an approval

The Korean request asked about PyPI litellm 1.107.0 and a supply-chain concern. The publisher's [incident report](https://docs.litellm.ai/blog/security-incident-oct-21-2026) identifies this compromised version, but that fact was not supplied as an expected answer.

The exact-version collector returned `version_not_found`: the package existed in PyPI, while the requested version and deps.dev version lookup returned 404. The session preserved the original diagnostic response, hashes and a Korean explanation, stopped without substituting another version, and explicitly withheld vulnerability, license and policy conclusions. It did not produce a normal HTML adoption report or independently complete the incident investigation. This validates honest failure handling, not malware detection or full supply-chain incident coverage.

## Engineering checks

- All 38 unittest methods pass against the extracted candidate, including the retained 177 legacy assertions and the new severity cases.
- MCP stdio initialization, all six tool definitions and error round-trip smoke checks pass.
- Ruff, Git whitespace checks and static distribution validation pass. The bilingual demo contains 18 HTML pages with no live input forms.
- Both lockfiles retain the exact dependency versions from 0.2.1. The locked plugin runtime audit covers 31 packages and reports no known vulnerabilities at review time.
- Git-history and extracted-archive secret scans report no matches. These detector results do not guarantee the absence of every possible secret.
- Candidate CI passes on Ubuntu Python 3.10 and 3.13, macOS Intel Python 3.13, and Windows Python 3.13. Final publication checks and artifact digests belong to the GitHub release record.

## Boundaries and reproduction

These are bounded Codex CLI user journeys, not exploit executions or exhaustive security certification. Claude's complete conversation and desktop approval UX were not retested. Aside visual inspection was unavailable because the Mac was locked; HTML received static checks. Report layout is unchanged and the tracked example HTML differs only in generator version.

Follow [CONTRIBUTING](../CONTRIBUTING.md) for deterministic checks and build the release with `uv run --frozen python scripts/package_release.py`. Local prompts, transcripts, reports and scan results remain in the ignored `verification-local/release-v0.2.2/` directory. They are not published as fixtures or included in the release archive.
