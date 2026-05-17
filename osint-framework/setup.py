from setuptools import setup, find_packages
setup(
    name="osint-framework",
    version="1.0.0",
    packages=find_packages(),
    entry_points={"console_scripts": ["osint-cli=cli.main:cli"]},
)
