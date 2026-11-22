# Explanation and verification files

These commands are bundled in both plugin variants. Prefix commands below with
`uv run --frozen --project "<plugin-root>" python "<plugin-root>/cli.py"`.
Select the same policy as collection; put `--policy /absolute/settings.json`
before the subcommand when applicable. Do not bypass a launch-selected policy.

## Save explanations

Use the exact review folder returned by collection. Save one response per topic:

```sh
explain owner/repo --topic overview --out /absolute/review/deepwiki.overview.json
explain owner/repo --topic communication --out /absolute/review/deepwiki.communication.json
index-explanations /absolute/review deepwiki.overview.json deepwiki.communication.json
```

Only request relevant topics. An unsuccessful `explain` exits nonzero **and saves
its failure record** when the destination is writable. Inspect the saved file
and continue with the documented gap when appropriate; do not chain explanation
commands with `&&` and accidentally skip indexing an error. No index command
turns an unsuccessful lookup into a successful explanation.

`deepwiki.<topic>.json` contains the complete adapter result, including unchanged
remote `content` and `isError`, repository, action, topic, `recorded_at` from the
system clock and `capture_kind`. `tool_response` means a remote response was
received, including error responses. `local_failure` means the adapter recorded
a policy block, timeout or another local failure; it is not a remote reply.
An upstream service can also describe a failure in text without setting
`isError`; read the content before treating it as useful coverage.

`index-explanations` creates `deepwiki.json` with schema
`oss-gate.explanation-index/1`. Its `responses` list references one to four
distinct topics for the same repository, with filenames, hashes and response/error
status. It never rewrites responses or guesses their meaning. All output paths
must be new. Gather the desired topics before creating the index.

For MCP, save the exact local-adapter JSON when the host supports it, then use
the same index command. If exact saving is unavailable, use the bundled CLI
`explain` with the same selected policy to capture the response directly. Do not
retype a failure as an original response. If shell execution is unavailable too,
retain any agent transcription separately as `deepwiki-transcription.md`, label
the limitation, and do not create a tool-response index from it. Existing legacy
single-file `deepwiki.json` remains readable and must not be relabelled as a new
tool capture.

## Record the agent's evidence check

After writing the selected language narratives and checking them against the
evidence, write a small input file, for example `check-input.json`:

```json
{
  "status": "WARN",
  "checked_fields": [
    "Names, versions, license expressions and vulnerability counts match data.json",
    "Both language narratives use the same evidence and verdict"
  ],
  "mismatches": [],
  "unresolved": ["External communication behavior has not been independently verified"]
}
```

Use only claims you actually checked. The four fields above are required;
`checked_fields`, `mismatches` and `unresolved` are arrays of nonempty strings.
At least one checked field is required. `PASS` requires empty mismatches and
unresolved lists. A grade-affecting mismatch requires `FAIL`; a coverage gap or
nonblocking unresolved point requires `WARN`. Do not mark PASS because rendering
succeeded. Do not supply a timestamp or invent an independent reviewer.

```sh
record-verification /absolute/review --input /absolute/review/check-input.json
render /absolute/review --language both
```

The writer creates `verification.json` with schema `oss-gate.verification/1`,
`kind: agent_evidence_check`, system-clock `recorded_at`, and `files_sha256`.
It verifies the sealed inputs and explanation index, then binds the check to
those files, saved explanation responses, any labelled transcription and current
`review.*.md` narratives. HTML is derived afterward and is not part of the check's
input hashes. Inspect it before delivery. `recorded_at` is the local record-save
time, not proof of when reasoning occurred or a trusted server timestamp.
The tool validates and records the agent's judgment; it does not independently
verify prose or certify the result. Local hashes detect changes relative to the
record and are not signatures against someone rewriting all local files.

Changing evidence or a narrative, or adding a translation, invalidates this
record. Recheck the changed material, update the check input and explicitly use
`record-verification ... --replace`. This archives the previous record under
`verification.previous.<sha256>.json` before replacing it. Default writes never
overwrite an existing check. A FAIL in sealed data cannot be cleared by a later
check. Run one writer per review directory. Historical unversioned verification
files remain readable; they do not gain timestamp/hash guarantees retroactively.

## Output location

Use `<workspace>/reviews` unless the user selected another location, and pass
its absolute path as `--output-root` (or MCP `output_root`). CLI omission means
`reviews` relative to the process working directory. Do not assume that an MCP
server starts in the user's workspace. Use the collection result's absolute
folder for subsequent files and include it in the final answer. If no workspace
is selected, resolve the current working directory explicitly before collection;
do not silently choose the home directory or plugin installation.
