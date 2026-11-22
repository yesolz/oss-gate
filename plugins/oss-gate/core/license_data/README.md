# License data

`spdx.json` extracts only license/exception identifier strings from SPDX License List Data v3.29.0. Source URLs, catalog version and original-file SHA-256 values are recorded. No upstream license text or editorial description is bundled or relicensed. These identifiers identify the applicable texts; they are not an approval list.

`reviewed.json` is OSS Gate's screening classification with primary-source links and notes. The six added permissive identifiers retain notice/redistribution obligations; BSD-3-Clause-Clear grants no patent rights. CC-BY-4.0 requires attribution review and is conditional. Older entries retain policy/2 classifications rather than claiming a comprehensive new legal review.

To update: retrieve licenses.json and exceptions.json from an explicit SPDX release tag, record their hashes, extract the sorted identifier arrays, and review the diff. Never update the catalog at runtime or infer permissiveness from a prefix or membership. Classification changes require expression/false-approval tests and an explicit policy revision.
