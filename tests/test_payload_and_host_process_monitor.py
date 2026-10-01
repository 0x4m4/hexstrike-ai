import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import psutil

import hexstrike_server


class PayloadGenerationTests(unittest.TestCase):
    def test_cyclic_payload_matches_legacy_content_at_boundaries_and_sizes(self):
        test_client = hexstrike_server.app.test_client()
        sizes = [0, 1, 25, 26, 27, 51, 1024, 1025, 8193]

        for size in sizes:
            with self.subTest(size=size):
                captured = {}

                def create_file(filename, content, *args, **kwargs):
                    captured["filename"] = filename
                    captured["content"] = content
                    return {"success": True}

                with patch.object(hexstrike_server.file_manager, "create_file", create_file):
                    response = test_client.post(
                        "/api/payloads/generate",
                        json={"type": "cyclic", "size": size, "filename": "pattern.txt"},
                    )

                expected = "".join(
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[index % 26]
                    for index in range(size)
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(captured["content"], expected)
                self.assertEqual(len(captured["content"]), size)
                self.assertEqual(response.get_json()["payload_info"]["size"], size)


class HostProcessMonitorTests(unittest.TestCase):
    @staticmethod
    def make_process(pid, name, executable=None, error=None):
        process = Mock()
        process.info = {"pid": pid, "name": name}
        if error:
            process.exe.side_effect = error
        else:
            process.exe.return_value = executable
        return process

    def test_collector_reports_heuristic_indicators_without_duplicate_unavailable_flag(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            executable_path = os.path.join(temp_directory, "actual.exe")
            with open(executable_path, "w", encoding="utf-8") as executable_file:
                executable_file.write("")
            missing_path = os.path.join(temp_directory, "gone.exe")
            processes = [
                self.make_process(1, "different", executable_path),
                self.make_process(2, "gone", missing_path),
                self.make_process(3, "protected", error=psutil.AccessDenied(pid=3)),
            ]

            with patch.object(
                hexstrike_server.psutil, "process_iter", return_value=processes
            ):
                with patch.object(
                    hexstrike_server.tempfile, "gettempdir", return_value=temp_directory
                ):
                    with patch.object(hexstrike_server.os, "access", return_value=True):
                        result = hexstrike_server.collect_host_processes()

        findings = {
            process["pid"]: {finding["indicator"] for finding in process["findings"]}
            for process in result
        }
        self.assertEqual(
            findings[1],
            {"process_name_mismatch", "executable_in_writable_temp"},
        )
        self.assertIn("executable_path_missing", findings[2])
        self.assertEqual(findings[3], {"executable_inaccessible"})

    def test_host_monitor_route_is_read_only_and_labels_findings_as_indicators(self):
        with patch.object(hexstrike_server, "collect_host_processes", return_value=[]):
            response = hexstrike_server.app.test_client().get("/api/processes/host-monitor")

        self.assertEqual(response.status_code, 200)
        self.assertIn("not malware verdicts", response.get_json()["notice"])
        self.assertEqual(response.get_json()["processes"], [])
        route = hexstrike_server.app.url_map._rules_by_endpoint["monitor_host_processes"][0]
        self.assertEqual(route.methods, {"GET", "HEAD", "OPTIONS"})


if __name__ == "__main__":
    unittest.main()
