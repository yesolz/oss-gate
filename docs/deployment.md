# Static demo deployment and prototype retirement

Build with `uv run --frozen python scripts/build_site.py`. The output is `site/generated`, containing plain HTML/CSS and public example downloads. Serve that directory on GitHub Pages or another static host. There is no review input, API handler, model key, database or background worker.

For GitHub Pages, configure the repository's Pages source as GitHub Actions, then run the Pages workflow from the intended published commit. Confirm the deployment URL, both language pages, all example links and downloads. A committed workflow alone is not evidence of a live deployment.

The public repository contains the standalone plugin and static demo. Historical workshop deployment source is maintained separately and is not part of this repository. The workshop used a temporary account supplied by its organizers; its cleanup status has not been independently verified.

GitHub repository changes do not terminate AWS resources. For organizer-provided temporary accounts, follow the workshop cleanup policy. For deployments in an account you manage, verify the exact resources and retained data before removing them. No cloud teardown was performed as part of this release.
