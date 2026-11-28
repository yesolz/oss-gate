"""Resolved identities, offline imports and failure modes that must never approve."""

import copy
import inspect
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins/oss-gate"))
sys.path.insert(0, str(ROOT / "tests"))
import legacy_server
from core import api, containers, jvm, swift
from core.repo_inputs import object_json
from core.repo_review import discover, collect_repository, evaluate_repository
from core.repo_render import GAPS, render_repository
from core.settings import policy_scope, guard_request, PolicyBlocked
from core.snapshot import verify
from test_repository_go_cargo import write, codes

DIGEST = "sha256:" + "a" * 64
IMAGE = "docker.io/library/alpine@" + DIGEST
POM = '<project xmlns="http://maven.apache.org/POM/4.0.0"><groupId>org.example</groupId><artifactId>app</artifactId><version>1.0-SNAPSHOT</version></project>'
TREE = {
    "groupId": "org.example",
    "artifactId": "app",
    "version": "1.0-SNAPSHOT",
    "children": [
        {
            "groupId": "org.apache.commons",
            "artifactId": "commons-lang3",
            "version": "3.12.0",
            "scope": "compile",
            "children": [
                {
                    "groupId": "org.jetbrains.kotlin",
                    "artifactId": "kotlin-stdlib",
                    "version": "1.9.0",
                    "scope": "runtime",
                }
            ],
        }
    ],
}
SWIFT_URL = "https://github.com/apple/swift-nio-http2"
PINS = {
    "version": 3,
    "originHash": "context",
    "pins": [
        {
            "identity": "swift-nio-http2",
            "kind": "remoteSourceControl",
            "location": SWIFT_URL + ".git",
            "state": {"version": "1.19.0", "revision": "b" * 40},
        }
    ],
}
TRIVY = {
    "SchemaVersion": 2,
    "ArtifactType": "container_image",
    "ArtifactName": "alpine:latest",
    "CreatedAt": "2026-11-20T00:00:00Z",
    "Trivy": {"Version": "0.67.0"},
    "Metadata": {
        "ImageID": "sha256:" + "c" * 64,
        "RepoDigests": [IMAGE],
        "ImageConfig": {"config": {"Env": ["SECRET=must-not-leak"]}},
    },
    "Results": [
        {
            "Class": "os-pkgs",
            "Type": "alpine",
            "Target": "alpine:latest",
            "Packages": [{"Name": "libcrypto3", "Version": "3.3.3-r0", "Licenses": ["Apache-2.0"]}],
            "Vulnerabilities": [
                {
                    "VulnerabilityID": "CVE-2025-0001",
                    "PkgName": "libcrypto3",
                    "InstalledVersion": "3.3.3-r0",
                    "FixedVersion": "3.3.3-r1",
                    "Severity": "HIGH",
                    "CVSS": {"nvd": {"V3Score": 8.1}},
                    "Description": "<script>ignored</script>",
                }
            ],
        }
    ],
}
GRYPE = {
    "descriptor": {"name": "grype", "version": "0.100.0", "configuration": {"secret": "must-not-leak"}},
    "source": {"type": "image", "target": {"repoDigests": [IMAGE], "manifestDigest": DIGEST}},
    "matches": [
        {
            "artifact": {"name": "libcrypto3", "version": "3.3.3-r0", "type": "apk", "licenses": ["Apache-2.0"]},
            "vulnerability": {
                "id": "CVE-2025-0001",
                "namespace": "alpine:distro:alpine:3.20",
                "severity": "High",
                "cvss": [{"metrics": {"baseScore": 8.1}}],
                "fix": {"versions": ["3.3.3-r1"]},
            },
        }
    ],
}


class JVM(unittest.TestCase):
    def test_maven_tree_preserves_direct_transitive_scope_and_mutable_root(self):
        result = jvm.analyze({"pom.xml": POM, "dependency-tree.json": json.dumps(TREE)})
        self.assertEqual(len(result["packages"]), 2)
        self.assertEqual(result["packages"][0]["name"], "org.apache.commons:commons-lang3")
        self.assertEqual(result["packages"][1]["direct_uses"], [])
        self.assertEqual(len(result["projects"][0]["dependency_edges"]), 2)
        self.assertEqual(codes(result), {"jvm_build_configuration_unverified"})

    def test_gradle_kotlin_configuration_and_legacy_paths(self):
        inputs = {
            "app/build.gradle.kts": 'error("must never execute")',
            "app/gradle.lockfile": "org.jetbrains.kotlin:kotlin-stdlib:1.9.0=compileClasspath,runtimeClasspath\nempty=test\n",
            "app/buildscript-gradle.lockfile": "org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.0=classpath\nempty=\n",
            "other/build.gradle": "// executable manifest",
            "other/gradle/dependency-locks/runtimeClasspath.lockfile": "org.jetbrains.kotlin:kotlin-stdlib:1.8.0\n",
        }
        result = jvm.analyze(inputs)
        self.assertEqual(len(result["packages"]), 3)
        self.assertEqual(len(result["projects"]), 2)
        self.assertEqual(
            len(next(p for p in result["projects"] if p["path"] == "app/build.gradle.kts")["lockfiles"]), 2
        )
        by_version = {p["version"]: p for p in result["packages"]}
        self.assertEqual(by_version["1.8.0"]["projects"], ["other/build.gradle"])
        self.assertEqual(by_version["1.8.0"]["configurations"], ["runtimeClasspath"])
        self.assertTrue(all(not p["direct_uses"] for p in result["packages"]))
        self.assertIn("jvm_dependency_edges_unverified", codes(result))

    def test_gradle_dynamic_snapshot_duplicate_and_empty_conflicts_reject(self):
        for text in (
            "a:b:1.+=runtime\nempty=",
            "a:b:1-SNAPSHOT=runtime\nempty=",
            "a:b:1=runtime\nempty=runtime",
            "a:b:1=runtime",
            "a:b:1=runtime\na:b:1=test\nempty=",
            "a:b:${version}=runtime\nempty=",
        ):
            with self.subTest(text=text):
                r = jvm.analyze({"gradle.lockfile": text})
                self.assertFalse(r["packages"])
                self.assertIn("jvm_resolution_invalid", codes(r))

    def test_maven_verbose_omitted_nodes_are_not_selected_dependencies(self):
        tree = copy.deepcopy(TREE)
        omitted = copy.deepcopy(tree["children"][0])
        omitted.update(version="0.1", included="false", omittedReason="conflict", winnerVersion="3.12.0")
        tree["children"].append(omitted)
        result = jvm.analyze({"pom.xml": POM, "dependency-tree.json": json.dumps(tree)})
        self.assertEqual(len(result["packages"]), 2)
        self.assertNotIn("0.1", [p["version"] for p in result["packages"]])
        self.assertIn("jvm_omitted_nodes", codes(result))
        omitted["included"] = "true"
        self.assertIn("jvm_resolution_invalid", codes(jvm.analyze({"dependency-tree.json": json.dumps(tree)})))

    def test_snapshot_system_dependencies_and_variants_never_approve(self):
        tree = copy.deepcopy(TREE)
        tree["children"] += [
            {"groupId": "private", "artifactId": "local", "version": "1.0", "scope": "system"},
            {"groupId": "public", "artifactId": "changing", "version": "1-SNAPSHOT"},
        ]
        tree["children"][0]["classifier"] = "linux-x86_64"
        r = jvm.analyze({"pom.xml": POM, "dependency-tree.json": json.dumps(tree)})
        self.assertEqual(len(r["packages"]), 2)
        self.assertTrue({"jvm_variant_unverified", "jvm_local_artifact", "jvm_version_unresolved"} <= codes(r))

    def test_pom_entities_and_identity_mismatch_remain_unverified(self):
        for pom in (
            '<!DOCTYPE project [<!ENTITY x SYSTEM "file:///etc/passwd">]><project>&x;</project>',
            POM.replace("org.example", "private.other"),
            "<broken",
        ):
            r = jvm.analyze({"pom.xml": pom, "dependency-tree.json": json.dumps(TREE)})
            self.assertIn("jvm_manifest_identity_unverified", codes(r))
        self.assertIn("jvm_resolved_input_missing", codes(jvm.analyze({"pom.xml": POM})))


class Swift(unittest.TestCase):
    def test_versions_one_two_three_and_xcode_locations(self):
        for version in (1, 2, 3):
            data = copy.deepcopy(PINS)
            data["version"] = version
            if version == 1:
                pin = data.pop("pins")[0]
                data["object"] = {
                    "pins": [{"package": pin["identity"], "repositoryURL": pin["location"], "state": pin["state"]}]
                }
            result = swift.analyze(
                {"App.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved": json.dumps(data)}
            )
            self.assertEqual(result["packages"][0]["name"], SWIFT_URL.removeprefix("https://"))
            self.assertEqual(result["packages"][0]["revision"], "b" * 40)
            self.assertEqual(result["packages"][0]["direct_uses"], [])
            self.assertIn("swift_manifest_resolution_unverified", codes(result))

    def test_branch_registry_local_and_credential_sources_never_query(self):
        for change in (
            {"state": {"branch": "main", "revision": "a" * 40}},
            {"kind": "registry"},
            {"location": "https://user:must-not-leak@github.com/org/pkg"},
            {"location": "../local"},
            {"location": "https://github.com/org/pkg?token=must-not-leak"},
        ):
            data = copy.deepcopy(PINS)
            data["pins"][0].update(change)
            result = swift.analyze({"Package.resolved": json.dumps(data)})
            self.assertFalse(result["packages"])
            self.assertTrue(result["coverage_gaps"])
            self.assertNotIn("must-not-leak", json.dumps(result))

    def test_duplicate_and_future_pins_are_rejected(self):
        for data in ({**PINS, "version": 4}, {**PINS, "pins": PINS["pins"] * 2}, {"version": 2, "pins": [True]}):
            result = swift.analyze({"Package.resolved": json.dumps(data)})
            self.assertFalse(result["packages"])
            self.assertIn("swift_resolution_invalid", codes(result))

    def test_unknown_revision_preserved_as_gap_and_manifest_not_executed(self):
        data = copy.deepcopy(PINS)
        data["pins"][0]["state"].pop("revision")
        result = swift.analyze({"Package.resolved": json.dumps(data), "Package.swift": 'fatalError("not executed")'})
        self.assertIn("swift_revision_unverified", codes(result))
        self.assertEqual(result["packages"][0]["projects"], ["Package.swift"])
        self.assertIn("swift_resolved_input_missing", codes(swift.analyze({"Package.swift": "code"})))


class Containers(unittest.TestCase):
    def test_scanner_rfc3339_nanoseconds_are_preserved_on_all_runtimes(self):
        for suffix in (".1Z", ".000000005Z", ".12345678+09:00", "Z"):
            report = copy.deepcopy(TRIVY)
            report["CreatedAt"] = "2021-08-25T12:20:30" + suffix
            result = containers.analyze({"trivy.json": json.dumps(report)})
            self.assertEqual(result["container_scans"][0]["created_at"], report["CreatedAt"])
        for value in ("2021-02-30T00:00:00Z", "2021-08-25T12:20:30", "2021-08-25T12:20:30.1234567890Z"):
            report["CreatedAt"] = value
            self.assertFalse(containers.analyze({"trivy.json": json.dumps(report)})["container_scans"])

    def test_grype_unspecified_scanner_metadata_keeps_findings(self):
        data = copy.deepcopy(GRYPE)
        data["descriptor"].update(version="[not provided]", timestamp="")
        result = containers.analyze({"grype.json": json.dumps(data)})
        scan = result["container_scans"][0]
        self.assertIsNone(scan["scanner_version"])
        self.assertIsNone(scan["created_at"])
        self.assertEqual(scan["overall"], "hold")

    def test_trivy_digest_findings_and_credentials_are_sanitized(self):
        r = containers.analyze(
            {"Dockerfile": "FROM alpine@" + DIGEST + " AS build\nFROM build\n", "trivy.json": json.dumps(TRIVY)}
        )
        scan = r["container_scans"][0]
        self.assertEqual(scan["overall"], "hold")
        self.assertEqual(scan["findings"][0]["fixed_versions"], ["3.3.3-r1"])
        self.assertEqual(r["container_images"][0]["matched_reports"], ["trivy.json"])
        self.assertEqual(len(r["container_images"]), 1)
        self.assertNotIn("must-not-leak", json.dumps(r))
        self.assertIn("container_final_image_unverified", codes(r))

    def test_tag_or_other_digest_never_matches_image(self):
        for reference in ("alpine:latest", "alpine@sha256:" + "d" * 64):
            r = containers.analyze(
                {"compose.yaml": "services:\n  app:\n    image: " + reference, "trivy.json": json.dumps(TRIVY)}
            )
            self.assertEqual(r["container_images"][0]["matched_reports"], [])
            self.assertIn("container_scan_missing", codes(r))

    def test_grype_ignored_high_severity_is_not_silently_dropped(self):
        data = copy.deepcopy(GRYPE)
        data["ignoredMatches"] = data.pop("matches")
        data["matches"] = []
        r = containers.analyze({"grype.json": json.dumps(data)})
        scan = r["container_scans"][0]
        self.assertEqual(scan["overall"], "hold")
        self.assertEqual(scan["ignored_count"], 1)
        self.assertTrue(scan["findings"][0]["suppressed"])
        self.assertIn("container_suppressed_findings", codes(r))
        self.assertNotIn("must-not-leak", json.dumps(r))

    def test_zero_unknown_and_score_only_findings_stay_conservative(self):
        for severity, score, expected in (
            (None, None, "conditional"),
            ("low", 9.1, "hold"),
            ("Critical", None, "hold"),
        ):
            data = copy.deepcopy(GRYPE)
            vuln = data["matches"][0]["vulnerability"]
            vuln["severity"], vuln["cvss"] = severity, [{"metrics": {"baseScore": score}}]
            self.assertEqual(
                containers.analyze({"grype.json": json.dumps(data)})["container_scans"][0]["overall"], expected
            )
        data["matches"] = []
        result = containers.analyze({"grype.json": json.dumps(data)})
        self.assertEqual(result["container_scans"][0]["overall"], "conditional")
        self.assertIn("container_licenses_unverified", codes(result))

    def test_different_distro_namespaces_and_versions_are_not_cve_deduplicated(self):
        data = copy.deepcopy(GRYPE)
        data["matches"] *= 2
        data["matches"][1] = copy.deepcopy(data["matches"][1])
        data["matches"][1]["vulnerability"]["namespace"] = "other:distro"
        r = containers.analyze({"grype.json": json.dumps(data)})
        self.assertEqual(len(r["container_scans"][0]["findings"]), 2)

    def test_compose_anchors_dynamic_and_malformed_inputs_never_clean(self):
        cases = {
            "compose.yml": 'services:\n  app: &app {image: "alpine"}\n  copy: *app\n',
            "Dockerfile": "ARG BASE=alpine\nFROM ${BASE}\n",
        }
        for source, text in cases.items():
            self.assertTrue(containers.analyze({source: text})["coverage_gaps"])
        for value in ("https://user:secret@host/x", "host/repo@sha256:short", "../image", "alpine;curl"):
            self.assertIsNone(containers.image_reference(value))

    def test_malformed_foreign_reports_and_limits_reject(self):
        reports = [
            dict(TRIVY, SchemaVersion=3),
            dict(TRIVY, ArtifactType="filesystem"),
            dict(TRIVY, Results="none"),
            dict(TRIVY, Results=[True]),
        ]
        for data in reports:
            r = containers.analyze({"trivy.json": json.dumps(data)})
            self.assertFalse(r["container_scans"])
            self.assertIn("container_input_invalid", codes(r))
        with patch.object(containers, "MAX_ITEMS", 0):
            self.assertFalse(containers.analyze({"trivy.json": json.dumps(TRIVY)})["container_scans"])


class Integration(unittest.TestCase):
    def test_maven_swift_queries_are_distinct_and_swift_never_hits_depsdev(self):
        fixture = {legacy_server.QB: legacy_server.qb_echo(())}
        for name, version in (
            ("org.apache.commons:commons-lang3", "3.12.0"),
            ("org.jetbrains.kotlin:kotlin-stdlib", "1.9.0"),
        ):
            fixture[legacy_server.VER("maven", name, version)] = {
                "versionKey": {"system": "MAVEN", "name": name, "version": version},
                "licenses": ["Apache-2.0"],
            }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write(
                root, {"pom.xml": POM, "dependency-tree.json": json.dumps(TREE), "Package.resolved": json.dumps(PINS)}
            )
            with legacy_server.fake(fixture) as fake:
                result = collect_repository(root, str(Path(tmp) / "out"), True)
            self.assertEqual(result["summary"]["vulnerability_queries_complete"], 3)
            self.assertEqual(result["summary"]["license_metadata_available"], 2)
            self.assertEqual(result["verdict"], "hold")  # Existing license policy holds missing Swift metadata.
            query = next(c[2] for c in fake.calls if c[1] == legacy_server.QB)
            self.assertEqual({q["package"]["ecosystem"] for q in query["queries"]}, {"Maven", "SwiftURL"})
            swift_query = next(q for q in query["queries"] if q["package"]["ecosystem"] == "SwiftURL")
            self.assertEqual(swift_query["package"]["name"], "github.com/apple/swift-nio-http2")
            self.assertFalse(any("/systems/swift" in c[1] for c in fake.calls))
            data = json.loads(Path(result["data"]).read_text(encoding="utf-8"))
            self.assertIn("swift_license_source_unavailable", codes(data["verdict"]))
            self.assertEqual(data["verdict"], evaluate_repository(data))

    def test_swift_allowlist_and_host_restrictions_apply_before_network(self):
        config = {
            "schema": "oss-gate.settings/1",
            "name": "Restricted",
            "version": "1",
            "network": {
                "allow_identifiers": ["swift:https://github.com/apple/*"],
                "services": ["osv"],
                "allowed_repository_hosts": ["github.com"],
            },
        }
        body = {"package": {"ecosystem": "SwiftURL", "name": SWIFT_URL}, "version": "1.19.0"}
        with policy_scope(config):
            guard_request(api.OSV_BASE + "/query", body)
            with self.assertRaises(PolicyBlocked):
                guard_request(
                    api.OSV_BASE + "/query",
                    {**body, "package": {"ecosystem": "SwiftURL", "name": "https://private.example/secret"}},
                )
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp) / "repo", {"Package.resolved": json.dumps(PINS)})
            with policy_scope(config), legacy_server.fake({legacy_server.QB: legacy_server.qb_echo(())}):
                result = collect_repository(Path(tmp) / "repo", str(Path(tmp) / "out"))
            self.assertEqual(result["summary"]["vulnerability_queries_complete"], 1)

    def test_container_only_collection_is_offline_sealed_and_renderable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            write(
                root,
                {"scan.trivy.json": json.dumps(TRIVY), "compose.yaml": 'services:\n  app:\n    image: "' + IMAGE + '"'},
            )
            with (
                patch.object(api, "_post", side_effect=AssertionError("network")),
                patch.object(api, "_get", side_effect=AssertionError("network")),
            ):
                result = collect_repository(root, str(Path(tmp) / "out"))
            self.assertEqual(result["verdict"], "hold")
            self.assertEqual(result["summary"]["packages"], 0)
            self.assertEqual(result["summary"]["container_imported_findings"], 1)
            folder = Path(result["folder"])
            verify(folder)
            saved = json.loads((folder / "data.json").read_text(encoding="utf-8"))
            source_hash = next(f["sha256"] for f in saved["inventory"]["files"] if f["path"] == "scan.trivy.json")
            self.assertEqual(saved["verdict"]["container_scans"][0]["input_sha256"], source_hash)
            self.assertEqual(json.loads((folder / "api-responses.json").read_text(encoding="utf-8")), [])
            render_repository(folder, "both")
            for lang in ("ko", "en"):
                html = (folder / f"report.{lang}.html").read_text(encoding="utf-8")
                self.assertIn("CVE-2025-0001", html)
                self.assertIn(DIGEST, html)
                self.assertIn(source_hash, html)
                self.assertNotIn("must-not-leak", html)
                self.assertNotIn("<script>ignored</script>", html)

    def test_container_license_restrictions_and_additional_policy_are_applied(self):
        data = copy.deepcopy(TRIVY)
        data["Results"][0]["Vulnerabilities"] = []
        config = {
            "schema": "oss-gate.settings/1",
            "name": "No Apache",
            "version": "1",
            "network": {"services": []},
            "review": {"license_restrictions": {"Apache-2.0": "hold"}, "require_communication_review": True},
        }
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp) / "repo", {"trivy.json": json.dumps(data)})
            with policy_scope(config):
                result = collect_repository(Path(tmp) / "repo", str(Path(tmp) / "out"))
            self.assertEqual(result["verdict"], "hold")
            saved = json.loads(Path(result["data"]).read_text(encoding="utf-8"))
            verdict = saved["verdict"]["container_scans"][0]["packages"][0]["verdict"]
            self.assertIn("communication_unverified", verdict["coverage_gaps"])
            render_repository(result["folder"], "both")
            self.assertIn("selected_license_restriction", [f["code"] for f in verdict["findings"]])
            self.assertIn("communication_unverified", codes(saved["verdict"]))

    def test_container_license_evidence_is_bound_to_import_and_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, hashes = Path(tmp) / "repo", []
            for field, value in (
                ("original", None),
                ("image", "docker.io/library/other@" + DIGEST),
                ("time", "2026-11-21T00:00:00Z"),
            ):
                report = copy.deepcopy(TRIVY)
                if field == "image":
                    report["Metadata"]["RepoDigests"] = [value]
                elif field == "time":
                    report["CreatedAt"] = value
                write(root, {"trivy.json": json.dumps(report)})
                result = collect_repository(root, str(Path(tmp) / "out"))
                saved = json.loads(Path(result["data"]).read_text(encoding="utf-8"))
                review = saved["verdict"]["container_scans"][0]["packages"][0]["verdict"]["license_reviews"][0]
                hashes.append(review["finding_sha256"])
            self.assertEqual(len(set(hashes)), 3)

    def test_import_files_are_hashed_and_symlinks_not_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(
                root,
                {
                    "build.gradle.kts": "code",
                    "gradle/dependency-locks/runtimeClasspath.lockfile": "a:b:1.0\n",
                    "trivy.json": json.dumps(TRIVY),
                },
            )
            (root / "Package.resolved").symlink_to(root / "private-missing")
            result = discover(root)
            self.assertTrue(any(p["system"] == "maven" for p in result["packages"]))
            self.assertIn("file_unreadable_or_limited", codes(result))
            self.assertTrue(all(len(f["sha256"]) == 64 for f in result["files"] if f["status"] != "unreadable"))

    def test_bounded_json_and_all_new_gap_translations(self):
        for text in (
            '{"a":1,"a":2}',
            '{"a":NaN}',
            '{"a":1e999}',
            "[" + "[]" + "]",
            '{"a":' + "[" * 70 + "0" + "]" * 70 + "}",
        ):
            with self.assertRaises(ValueError):
                object_json(text)
        for module in (jvm, swift, containers):
            for code in re.findall(r'gap\(result, "([a-z_]+)"', inspect.getsource(module)):
                self.assertIn(code, GAPS)
                self.assertEqual(len(GAPS[code]), 2)


if __name__ == "__main__":
    unittest.main()
