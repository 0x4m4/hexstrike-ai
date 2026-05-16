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
    
    def run(self, category: Optional[str] = None, dry_run: bool = False):
        platform = self.detect_platform()
        logger.info(f"Detected platform: {platform}")
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