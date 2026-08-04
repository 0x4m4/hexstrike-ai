#!/usr/bin/env python3
"""HexStrike AI v6.0 - Comprehensive CLI Interface"""

import argparse
import json
import os
import requests
import sys
from typing import Dict, Any, Optional

class HexStrikeClient:
    def __init__(self, server_url: str = "http://localhost:8888", timeout: int = 300, api_key: str | None = None):
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

        key = api_key or os.environ.get("HEXSTRIKE_API_KEY", "")
        if not key:
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            if os.path.isfile(env_path):
                for line in open(env_path, encoding="utf-8"):
                    if line.strip().startswith("HEXSTRIKE_API_KEY="):
                        key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if key:
            self.session.headers["X-API-KEY"] = key

        try:
            response = self.session.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Connected to HexStrike")
        except Exception as e:
            print(f"⚠️  Server offline: {str(e)}")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.server_url}{endpoint}"
        try:
            if method == "GET":
                response = self.session.get(url, timeout=self.timeout)
            elif method == "POST":
                response = self.session.post(url, json=data, timeout=self.timeout)
            else:
                return {"error": "Unsupported method"}
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def osint_workflow(self, target: str) -> Dict:
        print(f"\n🔍 OSINT анализ: {target}\n")
        return self._make_request("POST", "/api/bugbounty/osint-workflow", {"target": target})
    
    def technology_detection(self, target: str) -> Dict:
        print(f"\n🔍 Детектирование технологий: {target}\n")
        return self._make_request("POST", "/api/intelligence/technology-detection", {"target": target})
    
    def subfinder_enum(self, domain: str) -> Dict:
        print(f"\n🔍 Перечисление поддоменов: {domain}\n")
        return self._make_request("POST", "/api/tools/subfinder", {"domain": domain})
    
    def recon_workflow(self, target: str) -> Dict:
        print(f"\n🌐 Разведка: {target}\n")
        return self._make_request("POST", "/api/bugbounty/reconnaissance-workflow", {"target": target})
    
    def vulnerability_hunting(self, target: str) -> Dict:
        print(f"\n🔐 Охота за уязвимостями: {target}\n")
        return self._make_request("POST", "/api/bugbounty/vulnerability-hunting-workflow", {"target": target})
    
    def nuclei_scan(self, target: str, templates: str = "cves") -> Dict:
        print(f"\n🔐 Nuclei сканирование: {target}\n")
        return self._make_request("POST", "/api/tools/nuclei", {"target": target, "templates": templates})
    
    def nikto_scan(self, target: str) -> Dict:
        print(f"\n🔐 Nikto сканирование: {target}\n")
        return self._make_request("POST", "/api/tools/nikto", {"target": target})
    
    def xxd_analyze(self, binary_path: str) -> Dict:
        print(f"\n🔬 Hex-dump анализ: {binary_path}\n")
        return self._make_request("POST", "/api/tools/xxd", {"file_path": binary_path})
    
    def strings_extract(self, binary_path: str) -> Dict:
        print(f"\n🔬 Извлечение строк: {binary_path}\n")
        return self._make_request("POST", "/api/tools/strings", {"file_path": binary_path})
    
    def objdump_analyze(self, binary_path: str, section: str = "all") -> Dict:
        print(f"\n🔬 Objdump анализ: {binary_path}\n")
        return self._make_request("POST", "/api/tools/objdump", {"file_path": binary_path, "section": section})
    
    def radare2_analyze(self, binary_path: str) -> Dict:
        print(f"\n🔬 Radare2 анализ: {binary_path}\n")
        return self._make_request("POST", "/api/tools/radare2", {"file_path": binary_path})
    
    def gdb_debug(self, binary_path: str, command: str = "info") -> Dict:
        print(f"\n🔬 GDB отладка: {binary_path}\n")
        return self._make_request("POST", "/api/tools/gdb", {"file_path": binary_path, "command": command})
    
    def nmap_scan(self, target: str, scan_type: str = "syn") -> Dict:
        print(f"\n🌐 Nmap сканирование: {target}\n")
        return self._make_request("POST", "/api/tools/nmap", {"target": target, "scan_type": scan_type})
    
    def masscan_scan(self, target: str, ports: str = "1-65535") -> Dict:
        print(f"\n🌐 Masscan сканирование: {target}\n")
        return self._make_request("POST", "/api/tools/masscan", {"target": target, "ports": ports})
    
    def aws_audit(self, profile: Optional[str] = None) -> Dict:
        print("\n☁️ AWS аудит\n")
        return self._make_request("POST", "/api/tools/prowler", {"profile": profile or "default"})
    
    def cloud_audit(self, cloud_type: str) -> Dict:
        print(f"\n☁️ {cloud_type.upper()} аудит\n")
        return self._make_request("POST", "/api/tools/scout-suite", {"cloud_type": cloud_type})
    
    def trivy_scan(self, target: str, scan_type: str = "image") -> Dict:
        print(f"\n☁️ Trivy сканирование: {target}\n")
        return self._make_request("POST", "/api/tools/trivy", {"target": target, "scan_type": scan_type})
    
    def comprehensive_assessment(self, target: str) -> Dict:
        print(f"\n🐛 Полный аудит: {target}\n")
        return self._make_request("POST", "/api/bugbounty/comprehensive-assessment", {"target": target})
    
    def file_upload_testing(self, target: str) -> Dict:
        print(f"\n🐛 Тест загрузки файлов: {target}\n")
        return self._make_request("POST", "/api/bugbounty/file-upload-testing", {"target": target})
    
    def business_logic_testing(self, target: str) -> Dict:
        print(f"\n🐛 Тест бизнес-логики: {target}\n")
        return self._make_request("POST", "/api/bugbounty/business-logic-workflow", {"target": target})
    
    def cache_stats(self) -> Dict:
        print("\n⚙️ Статистика кэша\n")
        return self._make_request("GET", "/api/cache/stats")
    
    def cache_clear(self) -> Dict:
        print("\n⚙️ Очистка кэша\n")
        return self._make_request("POST", "/api/cache/clear")
    
    def telemetry(self) -> Dict:
        print("\n📊 Телеметрия системы\n")
        return self._make_request("GET", "/api/telemetry")
    
    def print_result(self, result: Dict):
        if "error" in result:
            print(f"❌ Ошибка: {result['error']}")
        else:
            print(json.dumps(result, indent=2))

def main():
    parser = argparse.ArgumentParser(description="HexStrike AI v6.0 CLI")
    parser.add_argument("--server", default="http://localhost:8888")
    parser.add_argument("--json", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    
    osint = subparsers.add_parser("osint-workflow")
    osint.add_argument("target")
    
    tech = subparsers.add_parser("technology-detect")
    tech.add_argument("target")
    
    sub = subparsers.add_parser("subfinder-enum")
    sub.add_argument("domain")
    
    recon = subparsers.add_parser("recon-workflow")
    recon.add_argument("target")
    
    vuln = subparsers.add_parser("vulnerability-hunt")
    vuln.add_argument("target")
    
    nuclei = subparsers.add_parser("nuclei-scan")
    nuclei.add_argument("target")
    nuclei.add_argument("--templates", default="cves")
    
    nikto = subparsers.add_parser("nikto-scan")
    nikto.add_argument("target")
    
    xxd = subparsers.add_parser("xxd-analyze")
    xxd.add_argument("binary")
    
    strings = subparsers.add_parser("strings-extract")
    strings.add_argument("binary")
    
    objdump = subparsers.add_parser("objdump-analyze")
    objdump.add_argument("binary")
    objdump.add_argument("--section", default="all")
    
    radare2 = subparsers.add_parser("radare2-analyze")
    radare2.add_argument("binary")
    
    gdb = subparsers.add_parser("gdb-debug")
    gdb.add_argument("binary")
    gdb.add_argument("--command", default="info")
    
    nmap = subparsers.add_parser("nmap-scan")
    nmap.add_argument("target")
    nmap.add_argument("--type", default="syn")
    
    masscan = subparsers.add_parser("masscan-scan")
    masscan.add_argument("target")
    masscan.add_argument("--ports", default="1-65535")
    
    aws = subparsers.add_parser("aws-audit")
    aws.add_argument("--profile", default=None)
    
    cloud = subparsers.add_parser("cloud-audit")
    cloud.add_argument("cloud_type", choices=["aws", "azure", "gcp"])
    
    trivy = subparsers.add_parser("trivy-scan")
    trivy.add_argument("target")
    trivy.add_argument("--type", dest="scan_type", default="image")
    
    comp = subparsers.add_parser("comprehensive-assessment")
    comp.add_argument("target")
    
    upload = subparsers.add_parser("file-upload-test")
    upload.add_argument("target")
    
    business = subparsers.add_parser("business-logic-test")
    business.add_argument("target")
    
    subparsers.add_parser("cache-stats")
    subparsers.add_parser("cache-clear")
    subparsers.add_parser("telemetry")

    llm = subparsers.add_parser("llm", help="Local LLM: llama-server (:8080) > ollama (:11434)")
    llm_sub = llm.add_subparsers(dest="llm_cmd")
    llm_sub.add_parser("connect", help="Detect LLM, write .env, defense handshake")
    llm_sub.add_parser("status", help="Show provider status")
    llm_hs = llm_sub.add_parser("handshake", help="Defense-prompted handshake")
    llm_hs.add_argument("--probe", choices=("models", "chat", "both"), default="both")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    # Local LLM routes (no HexStrike API server required)
    if args.command == "llm":
        root = os.path.dirname(os.path.abspath(__file__))
        src = os.path.join(root, "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from hexstrike.llm.provider import LocalLlmProvider, resolve_llm_config, write_env_llm_block

        cfg = resolve_llm_config()
        provider = LocalLlmProvider(cfg)
        if args.llm_cmd == "status":
            st = provider.status()
            print(json.dumps(st, indent=2))
            sys.exit(0 if st.get("selected_provider_reachable") else 1)
        if args.llm_cmd == "connect":
            from pathlib import Path as _Path
            env_path = _Path(root) / ".env"
            write_env_llm_block(env_path, cfg)
            provider = LocalLlmProvider(resolve_llm_config())
            report = provider.handshake(probe="both")
            report["env_written"] = str(env_path)
            print(json.dumps(report, indent=2))
            sys.exit(0 if report.get("llm", {}).get("selected_provider_reachable") else 1)
        if args.llm_cmd == "handshake":
            report = provider.handshake(probe=getattr(args, "probe", "both"))
            print(json.dumps(report, indent=2))
            sys.exit(0 if report.get("llm", {}).get("selected_provider_reachable") else 1)
        print("usage: hexstrike_cli.py llm {connect|status|handshake}", file=sys.stderr)
        sys.exit(2)
    
    client = HexStrikeClient(args.server)
    result = None
    
    try:
        if args.command == "osint-workflow":
            result = client.osint_workflow(args.target)
        elif args.command == "technology-detect":
            result = client.technology_detection(args.target)
        elif args.command == "subfinder-enum":
            result = client.subfinder_enum(args.domain)
        elif args.command == "recon-workflow":
            result = client.recon_workflow(args.target)
        elif args.command == "vulnerability-hunt":
            result = client.vulnerability_hunting(args.target)
        elif args.command == "nuclei-scan":
            result = client.nuclei_scan(args.target, args.templates)
        elif args.command == "nikto-scan":
            result = client.nikto_scan(args.target)
        elif args.command == "xxd-analyze":
            result = client.xxd_analyze(args.binary)
        elif args.command == "strings-extract":
            result = client.strings_extract(args.binary)
        elif args.command == "objdump-analyze":
            result = client.objdump_analyze(args.binary, args.section)
        elif args.command == "radare2-analyze":
            result = client.radare2_analyze(args.binary)
        elif args.command == "gdb-debug":
            result = client.gdb_debug(args.binary, args.command)
        elif args.command == "nmap-scan":
            result = client.nmap_scan(args.target, args.type)
        elif args.command == "masscan-scan":
            result = client.masscan_scan(args.target, args.ports)
        elif args.command == "aws-audit":
            result = client.aws_audit(args.profile)
        elif args.command == "cloud-audit":
            result = client.cloud_audit(args.cloud_type)
        elif args.command == "trivy-scan":
            result = client.trivy_scan(args.target, args.scan_type)
        elif args.command == "comprehensive-assessment":
            result = client.comprehensive_assessment(args.target)
        elif args.command == "file-upload-test":
            result = client.file_upload_testing(args.target)
        elif args.command == "business-logic-test":
            result = client.business_logic_testing(args.target)
        elif args.command == "cache-stats":
            result = client.cache_stats()
        elif args.command == "cache-clear":
            result = client.cache_clear()
        elif args.command == "telemetry":
            result = client.telemetry()
        
        if result:
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                client.print_result(result)
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Отмено")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
