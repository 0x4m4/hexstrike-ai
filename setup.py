from setuptools import setup

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
  name='hexstrike-ai',
  version='0.1.0',
  author='0x4m4',
  scripts=[
    'hexstrike_server.py',
    'hexstrike_mcp.py',
  ],
)

