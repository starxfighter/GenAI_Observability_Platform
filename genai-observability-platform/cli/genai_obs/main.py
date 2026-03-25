"""
GenAI Observability CLI - Main Entry Point
"""
import click
from typing import Optional
import json

from .config import Config, get_config
from .commands import agents, traces, alerts, api_keys, metrics


@click.group()
@click.option('--profile', '-p', default='default', help='Configuration profile to use')
@click.option('--endpoint', '-e', help='API endpoint URL (overrides config)')
@click.option('--output', '-o', type=click.Choice(['json', 'table', 'text']), default='table', help='Output format')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx: click.Context, profile: str, endpoint: Optional[str], output: str, verbose: bool):
    """
    GenAI Observability Platform CLI

    Manage agents, traces, alerts, and more from the command line.

    Examples:

        # List all agents
        genai-obs agents list

        # Get trace details
        genai-obs traces get <trace-id>

        # Create an API key
        genai-obs api-keys create --agent my-agent --name "Production Key"
    """
    ctx.ensure_object(dict)

    # Load configuration
    config = get_config(profile)
    if endpoint:
        config.endpoint = endpoint

    ctx.obj['config'] = config
    ctx.obj['output'] = output
    ctx.obj['verbose'] = verbose


# Register command groups
cli.add_command(agents.agents)
cli.add_command(traces.traces)
cli.add_command(alerts.alerts)
cli.add_command(api_keys.api_keys)
cli.add_command(metrics.metrics)


@cli.command()
@click.pass_context
def configure(ctx: click.Context):
    """
    Configure CLI settings interactively.
    """
    click.echo("GenAI Observability CLI Configuration\n")

    endpoint = click.prompt("API Endpoint", default="https://api.observability.example.com")
    api_key = click.prompt("API Key", hide_input=True)
    default_output = click.prompt("Default output format", type=click.Choice(['json', 'table', 'text']), default='table')

    config = Config(
        endpoint=endpoint,
        api_key=api_key,
        default_output=default_output
    )
    config.save()

    click.echo("\nConfiguration saved successfully!")


@cli.command()
@click.pass_context
def version(ctx: click.Context):
    """
    Show CLI version.
    """
    from . import __version__
    click.echo(f"genai-obs version {__version__}")


@cli.command()
@click.pass_context
def status(ctx: click.Context):
    """
    Check API connection status.
    """
    config = ctx.obj['config']

    click.echo(f"Endpoint: {config.endpoint}")

    try:
        from .client import APIClient
        client = APIClient(config)
        health = client.get("/health")

        click.echo(f"Status: {click.style('Connected', fg='green')}")
        click.echo(f"API Version: {health.get('version', 'unknown')}")
        click.echo(f"Environment: {health.get('environment', 'unknown')}")
    except Exception as e:
        click.echo(f"Status: {click.style('Error', fg='red')}")
        click.echo(f"Error: {str(e)}")


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == '__main__':
    main()
