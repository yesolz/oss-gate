# v0.5.0 validation record

This release groups the policy/3 license improvements, attributed user decisions, report presentation and evidence-recording fixes into one update. It does not add a hosted backend or change third-party runtime dependency pins.

## Changes and compatibility

- Recognize additional reviewed license identifiers and distinguish missing metadata, unclassified SPDX IDs and expression failures. CC-BY-4.0 receives attribution review; MPL-2.0 remains conditional. An unreviewed identifier is not approved merely because it exists in SPDX.
- Apply optional additional license restrictions and record attributed acceptance of an exact finding without replacing the automated verdict. Reassess verified evidence offline into a new folder with source provenance.
- Preserve successful and failed DeepWiki responses with tool-recorded time. Index topic responses without rewriting them. Record agent checks with evidence/narrative hashes and archive previous checks on explicit replacement.
- Add actual bilingual report previews, a fresh packaging 26.3 allow example, clearer output paths and locked-runtime mirror troubleshooting.

Policy/3 can change a result for the same saved evidence. The historical Next 16.4.6 example changes from hold to conditional; Next 15.1.0 remains hold. Original snapshots remain unchanged and rendered reassessments identify the policy change. Existing unversioned verification files remain readable, without retroactive timestamp/hash guarantees. New hash-bound checks must be renewed after changing the checked narrative or adding a translation. Follow the bundled evidence-files.md command examples.

## Validation

The feature candidate passed 119 unittest tests on local Python 3.10 and 3.13, Ruff, both MCP adapters, generated CLI parity, 20 static pages and distribution checks. The same feature commit passed the Ubuntu 3.10/3.13, macOS 3.13 and Windows 3.13 GitHub Actions matrix. Versioned release preparation repeats the required checks before publication.

A real Codex journey collected evidence and generated both language reports. A live is-odd DeepWiki lookup reproduced Repository not found: its unchanged response was saved while the CLI still returned failure. Collection, indexing, verification recording and bilingual rendering then completed with the explanation gap retained. A cache-free installation of the frozen runtime succeeded. Release packaging is scanned for known secret patterns; this is not an independent security audit.

Claude Code accepted the candidate manifest, but the complete model-driven journey remains unverified because the existing OAuth token expired. Earlier bilingual report layouts were visually inspected in Aside; the additional is-odd report's final visual check was unavailable while the Mac was locked. These are disclosed follow-up checks, not known product defects. Independent first-user testing has not been completed.

See [the detailed validation record](policy3-validation.md) and [first-use checklist](first-use-check.md). Validation completion alone does not require a new release. Publish a patch when a discovered issue requires code or distributed behavior to change.
