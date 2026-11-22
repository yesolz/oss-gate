# Requests adoption proposal

Evidence date: 2026-11-17 · Proposal example · Verification: **WARN**

> This proposal uses a historical Requests 2.34.2 snapshot. It does not document an actual team's approval, production environment, legal response or current security posture.

## 1. Context and intended users

Assume a Python service needs to call external HTTP APIs. A “backend API team” is an illustrative audience, not a verified organizational requirement. Requests 2.34.2 is conditional under policy v3. The outstanding adoption question is certifi@2026.10.23, its MPL-2.0 obligations, and the actual modifications/distribution. [Evidence 1, 2]

The package itself declares Apache-2.0. The saved graph has four direct dependencies, certifi, charset-normalizer, idna and urllib3, and no transitive dependencies. It has not been established that this graph matches any particular service's installed environment. [Evidence 2]

## 2. Proposed adoption conditions

**Check the environment.** Review the actual runtime and lockfile. Historical versions are Requests 2.34.2, certifi 2026.10.23, charset-normalizer 3.5.2, idna 3.20.0 and urllib3 2.8.0. This is a comparison baseline, not a present-day installation recommendation. Review a different version or extras configuration as a new environment. [Evidence 2, 3]

**Record a license decision.** Determine whether certifi files are modified, whether the CA bundle is redistributed, and which artifacts are shipped. Record a human decision about the applicable MPL-2.0 obligations. This proposal would make that decision a prerequisite for production adoption; it does not assume a legal review has already happened. [Evidence 1, 2]

**Review operational settings.** Keep TLS verification enabled and inspect proxy/CA settings, `.netrc` and `trust_env` in the deployment environment. Client-key files need separate secret-storage and permission review. These are review questions derived from the old wiki narrative, not operational settings tested here. [Evidence 3]

**Review optional features.** Reassess the dependency scope before enabling extras that add PySocks, chardet or other packages. Treat version changes, extras changes, new advisories and distribution changes as triggers for another review. [Evidence 3]

## 3. Expected outcomes and measurement

| Measure | Saved baseline | Proposed target | How to check |
|---|---|---|---|
| Known advisories | 0 for Requests and the four queried dependencies | No unresolved high-severity item in a fresh decision-time review | Compare the new snapshot and actual lockfile |
| certifi license decision | No recorded decision | Human decision before production adoption | Review record or ticket |
| Disabled TLS verification in the actual environment | Unmeasured | 0 unapproved disabling cases | Code/configuration review |
| Additional unreviewed dependencies | Unmeasured | Review when changed | Compare lockfile diffs with evidence |

Targets are proposals, not achieved results. Owners, budget, schedule and alternative-package comparisons are not set. No competing package was investigated, so this document does not claim Requests is superior to all alternatives.

## 4. Risks and limitations

The Scorecard is 8.2 but dates to 2026-08-24. Branch-Protection is unevaluated (-1), and the Vulnerabilities check is missing. The original agent check was WARN, with some wiki claims, including redirect authentication-header behavior, not reproduced. The wiki is not version-pinned. [Evidence 1, 2, 3]

Flask's source snapshot from the periodic report is absent and excluded from totals. The old document's complete portfolio result is therefore not used as verified evidence for this proposal. [Evidence 4]

## 5. Evidence and verification

| Number | Source | Use |
|---|---|---|
| 1 | [Requests review](../reviews/psf-requests-2.34.2/review.en.md) | Verdict, actions and limitations |
| 2 | [data.json](../reviews/psf-requests-2.34.2/data.json) | Versions, licenses, graph and Scorecard |
| 3 | Software, configuration and dependency sections of the same review | Questions derived from AI-generated wiki explanations |
| 4 | [Periodic report](../periodic/2026-11-python-web.en.md) | Available coverage and missing evidence |

Verification is WARN. Proposals are separated from evidence and numerical claims are checked against saved data, but the real environment, legal obligations and current vulnerability state have not been freshly verified. Use the [hash manifest](../snapshot-sha256.json) to check source integrity.
