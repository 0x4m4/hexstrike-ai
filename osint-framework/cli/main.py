import click
import requests
import json

API_BASE = "http://localhost:8000/api/v1"

@click.group()
def cli():
    """OSINT Automation Framework CLI"""
    pass

@cli.command()
@click.argument("target")
@click.option("--tools", "-t", multiple=True, help="Tools to use")
def search(target, tools):
    """Run an OSINT search"""
    tool_list = list(tools) if tools else ["maigret", "sherlock"]
    try:
        response = requests.post(f"{API_BASE}/search", json={
            "target": target,
            "tools": tool_list
        })
        click.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.argument("tool_name")
@click.argument("target")
def run_tool(tool_name, target):
    """Run a specific tool directly"""
    try:
        response = requests.post(f"{API_BASE}/tools/{tool_name}/run?target={target}")
        click.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
def list_tools():
    """List available OSINT tools"""
    try:
        response = requests.get(f"{API_BASE}/tools")
        for tool in response.json()["tools"]:
            click.echo(f"{tool['name']} ({tool['category']}): {tool['description']}")
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
def history():
    """Show search history"""
    try:
        response = requests.get(f"{API_BASE}/history")
        click.echo(json.dumps(response.json(), indent=2))
    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == "__main__":
    cli()