"""Input normalization for summary report generation (#146)."""

from typing import Any, Dict, List


def normalize_summary_report_inputs(results: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce JSON payloads so summary report formatting never raises."""

    def _coerce_vulns(raw: Any) -> List[dict]:
        items = raw if isinstance(raw, list) else []
        normalized: List[dict] = []
        for item in items:
            if isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append({"severity": "info", "detail": str(item)})
        return normalized

    def _coerce_tools(raw: Any) -> List[str]:
        if isinstance(raw, list):
            return [str(t).strip() for t in raw if str(t).strip()]
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(",") if t.strip()]
        if raw is None:
            return []
        return [str(raw)]

    try:
        execution_time = float(results.get("execution_time") or 0)
    except (TypeError, ValueError):
        execution_time = 0.0

    return {
        "target": str(results.get("target") or "Unknown")[:60],
        "execution_time": execution_time,
        "tools_used": _coerce_tools(results.get("tools_used")),
        "vulnerabilities": _coerce_vulns(results.get("vulnerabilities")),
    }
