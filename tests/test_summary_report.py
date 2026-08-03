"""Regression tests for summary report input normalization (#146)."""

from hexstrike_report_utils import normalize_summary_report_inputs


def test_null_execution_time_becomes_zero():
    out = normalize_summary_report_inputs(
        {"target": "127.0.0.1", "execution_time": None, "tools_used": ["nmap"], "vulnerabilities": []}
    )
    assert out["execution_time"] == 0.0


def test_tools_used_string_is_split():
    out = normalize_summary_report_inputs({"tools_used": "nmap, nuclei"})
    assert out["tools_used"] == ["nmap", "nuclei"]


def test_non_dict_vulnerability_entries():
    out = normalize_summary_report_inputs({"vulnerabilities": ["open port 443"]})
    assert out["vulnerabilities"][0]["severity"] == "info"
