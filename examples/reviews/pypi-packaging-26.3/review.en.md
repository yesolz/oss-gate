# packaging 26.3: a small building block for Python tooling

## Decision and scope

**Allow under OSS Gate policy/3 for the measured package scope.** The exact PyPI version has recognized license metadata, no returned known advisories, a matching graph with no package dependencies, and an 8.8 Scorecard signal. Keep the applicable license notices and test the APIs your project needs.

## What the software does

If your tool needs to compare Python versions or interpret dependency requirements, packaging provides shared implementations instead of making each project write its own parser. Its [official documentation](https://packaging.pypa.io/en/stable/) covers versions, requirements, environment markers and compatibility tags. This overview is documentation-based; DeepWiki was not used for this example.

## License and dependencies

The recorded expression is `Apache-2.0 OR BSD-2-Clause`. The screening selects an available permissive branch and preserves that choice. Confirm the license option and notices for your use. The returned graph contains only the root package: zero direct and zero transitive package dependencies. This does not inventory a Python installation or build tools.

## Vulnerabilities and maintenance

The 2026-11-22 snapshot returned no advisories from the queried services. That is a dated observation, not a guarantee. The Scorecard overall is 8.8, dated 2026-08-24; it is older than this collection and is not a real-time maintenance assessment.

## Adoption actions

Pin and test the intended version, retain the chosen license terms, and refresh the review when the version or relevant advisories change. API metadata cannot establish every runtime behavior. External communication was not independently inspected; no claim that the package never communicates externally is made.

## Evidence

This example was collected with the local policy/3 candidate. `data.json`, `api-responses.json` and `evidence-sha256.json` preserve the normalized results, original responses and integrity hashes. The possible verdict was obtained without custom policy overrides or acceptance records. The automatic verdict remains separate from this explanatory narrative.
