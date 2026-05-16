#!/usr/bin/env python3
"""OSINT Tool Installation Script - Installs all OSINT tools from the catalog"""

import os
import sys
import json
import subprocess
import click
from pathlib import Path
from typing import Optional
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / 'config'
TOOLS_DIR = BASE_DIR / 'tools'

class OSINTInstaller:
    def __init__(self, config_path: Path = None):
        self.config_path = config_path or CONFIG_DIR / 'catalog-links.json'
        self.load_config()
    
    def load_config(self):
        with open(self.config_path) as f:
            self.catalog = json.load(f)
        logger.info(f"Loaded {self.catalog['total']} catalog items")
    
    def detect_platform(self) -> str:
        """Detect operating system"""
        import platform
        system = platform.system()
        if system == "Linux":
            if Path("/etc/kali-version").exists():
                return "kali"
            return "ubuntu"
        elif system == "Darwin":
            return "macos"
        return "unknown"
    
    def get_tool_installation_info(self):
        """Return installation info for known tools"""
        return {
            'sherlock': {'type': 'github', 'url': 'https://github.com/sherlock-project/sherlock', 'method': 'pip', 'category': 'username'},
            'maigret': {'type': 'github', 'url': 'https://github.com/soxoj/maigret', 'method': 'pip', 'category': 'username'},
            'blackbird': {'type': 'github', 'url': 'https://github.com/p1ngul1n0/blackbird', 'method': 'pip', 'category': 'username'},
            'whatsmyname': {'type': 'github', 'url': 'https://github.com/WebBreacher/WhatsMyName', 'method': 'manual', 'category': 'username'},
            'holehe': {'type': 'github', 'url': 'https://github.com/megadose/holehe', 'method': 'pip', 'category': 'email'},
            'ghunt': {'type': 'github', 'url': 'https://github.com/mhpn/Google_Hacking', 'method': 'pip', 'category': 'email'},
            'spiderfoot': {'type': 'github', 'url': 'https://github.com/smicallef/spiderfoot', 'method': 'pip', 'category': 'recon'},
            'recon-ng': {'type': 'github', 'url': 'https://github.com/lanmaster53/recon-ng', 'method': 'pip', 'category': 'recon'},
            'theharvester': {'type': 'github', 'url': 'https://github.com/edge-security/theHarvester', 'method': 'pip', 'category': 'recon'},
            'snscrape': {'type': 'github', 'url': 'https://github.com/justinpark/snscrape', 'method': 'pip', 'category': 'social'},
            'instaloader': {'type': 'pypi', 'package': 'instaloader', 'method': 'pip', 'category': 'social'},
            'twint': {'type': 'github', 'url': 'https://github.com/twintproject/twint', 'method': 'pip', 'category': 'social'},
        }

    def install_github_repo(self, url, target_dir):
        """Clone GitHub repo"""
        try:
            repo_name = url.split('/')[-1].replace('.git', '')
            target_path = target_dir / repo_name
            result = subprocess.run(['git', 'clone', '--depth', '1', url, str(target_path)], capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                logger.info(f"Cloned {repo_name}")
                if (target_path / 'setup.py').exists() or (target_path / 'pyproject.toml').exists():
                    subprocess.run([sys.executable, '-m', 'pip', 'install', str(target_path)], capture_output=True)
                elif (target_path / 'requirements.txt').exists():
                    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(target_path / 'requirements.txt')], capture_output=True)
                return True
            else:
                logger.error(f"Failed to clone {url}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error installing {url}: {e}")
            return False

    def install_pypi_package(self, package, target_dir):
        """Install Python package from PyPI"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', package, '--target', str(target_dir)], capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                logger.info(f"Installed {package}")
                return True
            else:
                logger.error(f"Failed to install {package}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error installing {package}: {e}")
            return False
    
    def run(self, category: Optional[str] = None, dry_run: bool = False):
        platform = self.detect_platform()
        logger.info(f"Detected platform: {platform}")
        
        tool_info = self.get_tool_installation_info()
        logger.info(f"Found {len(tool_info)} known tools to install")
        
        for tool_name, info in tool_info.items():
            if dry_run:
                logger.info(f"DRY RUN: Would install {tool_name}")
                continue
            
            category_dir = TOOLS_DIR / info['category']
            category_dir.mkdir(parents=True, exist_ok=True)
            
            if info['type'] == 'github':
                self.install_github_repo(info['url'], category_dir)
            elif info['type'] == 'pypi':
                self.install_pypi_package(info['package'], category_dir)
            elif info['type'] == 'system':
                logger.info(f"System package {info['package']} needs manual install")
        
        logger.info("Installation complete!")

@click.command()
@click.option("--category", "-c", help="Install specific category")
@click.option("--dry-run", "-d", is_flag=True, help="Test without making changes")
@click.option("--list-categories", "-l", is_flag=True, help="List available categories")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def main(category: Optional[str], dry_run: bool, list_categories: bool, verbose: bool):
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    installer = OSINTInstaller()
    if list_categories:
        categories = list(installer.catalog["by_section"].keys())
        click.echo("Available categories:")
        for c in sorted(categories):
            count = len(installer.catalog["by_section"][c])
            click.echo(f"  - {c}: {count} items")
        return
    installer.run(category=category, dry_run=dry_run)

if __name__ == "__main__":
    main()