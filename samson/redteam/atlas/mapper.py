"""MITRE ATLAS taxonomy mapper (ADR-003)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from samson.core.config import SamsonSettings, get_settings
from samson.core.errors import ConfigurationError, ToolExecutionError
from samson.redteam.schemas import ATLASEntry, ATLASMapRequest, ATLASMapResult

logger = logging.getLogger(__name__)


class AtlasMapper:
    def __init__(self, settings: SamsonSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._taxonomy = self._load_taxonomy(self._settings.atlas_taxonomy_path)

    @staticmethod
    def _load_taxonomy(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise ConfigurationError(f"ATLAS taxonomy not found: {path}", path=str(path))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ConfigurationError(f"Invalid ATLAS taxonomy: {path}", error=str(exc)) from exc
        if not isinstance(data, dict) or "techniques" not in data:
            raise ConfigurationError("ATLAS taxonomy must contain techniques array")
        return data

    def map_artifact(self, req: ATLASMapRequest) -> ATLASMapResult:
        corpus = json.dumps(req.artifact, ensure_ascii=False).lower()
        scored: list[tuple[float, dict[str, Any]]] = []
        for technique in self._taxonomy.get("techniques") or []:
            if not isinstance(technique, dict):
                continue
            score = self._score_technique(corpus, technique)
            if score > 0:
                scored.append((score, technique))
        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[: req.top_k]

        techniques: list[ATLASEntry] = []
        mitigations: set[str] = set()
        for score, technique in top:
            techniques.append(
                ATLASEntry(
                    atlas_id=str(technique["atlas_id"]),
                    name=str(technique.get("name") or ""),
                    description=str(technique.get("description") or ""),
                    confidence=min(score, 1.0),
                    evidence=self._extract_evidence(corpus, technique),
                )
            )
            for m in technique.get("mitigations") or []:
                mitigations.add(str(m))

        avg_confidence = sum(t.confidence for t in techniques) / max(len(techniques), 1)
        return ATLASMapResult(
            request_id=req.request_id,
            tactics=[],
            techniques=techniques,
            mitigations=sorted(mitigations),
            confidence=avg_confidence,
            taxonomy_version=str(self._taxonomy.get("version") or "unknown"),
        )

    @staticmethod
    def _score_technique(corpus: str, technique: dict[str, Any]) -> float:
        keywords = [str(k).lower() for k in technique.get("keywords") or []]
        if not keywords:
            return 0.0
        hits = sum(1 for kw in keywords if kw in corpus)
        name = str(technique.get("name") or "").lower()
        if name and name in corpus:
            hits += 2
        return hits / (len(keywords) + 2)

    @staticmethod
    def _extract_evidence(corpus: str, technique: dict[str, Any]) -> str:
        keywords = [str(k).lower() for k in technique.get("keywords") or []]
        for kw in keywords:
            match = re.search(rf".{{0,60}}{re.escape(kw)}.{{0,60}}", corpus)
            if match:
                return match.group(0).strip()
        return str(technique.get("description") or "")[:160]
