"""
Trace management commands
"""
import click
from typing import Optional
from datetime import datetime, timedelta

from ..client import APIClient, APIError
from ..output import format_output, print_success, print_error, format_status, format_duration


@click.group()
def traces():
    """View and search traces."""
    pass


@traces.command('list')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--status', type=click.Choice(['success', 'error', 'all']), default='all', help='Filter by status')
@click.option('--since', help='Start time (ISO format or relative like "1h", "24h", "7d")')
@click.option('--until', help='End time (ISO format)')
@click.option('--limit', default=20, help='Maximum number of results')
@click.pass_context
def list_traces(ctx: click.Context, agent_id: Optional[str], status: str,
                since: Optional[str], until: Optional[str], limit: int):
    """List recent traces."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {'limit': limit}
    if agent_id:
        params['agent_id'] = agent_id
    if status != 'all':
        params['status'] = status
    if since:
        params['start_time'] = parse_time(since)
    if until:
        params['end_time'] = until

    try:
        result = client.get('/api/v1/traces', params=params)
        traces_list = result.get('items', result) if isinstance(result, dict) else result

        # Format for display
        display_data = []
        for trace in traces_list:
            display_data.append({
                'trace_id': trace.get('trace_id', '')[:16] + '...',
                'agent': trace.get('agent_id', '-'),
                'name': trace.get('root_span_name', '-')[:30],
                'duration': format_duration(trace.get('duration_ms', 0)),
                'status': format_status(trace.get('status', 'unknown')),
                'time': trace.get('start_time', '-')[:19]
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=['trace_id', 'agent', 'name', 'duration', 'status', 'time'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to list traces: {e.message}")
        raise SystemExit(1)


@traces.command('get')
@click.argument('trace_id')
@click.option('--spans/--no-spans', default=True, help='Include span details')
@click.pass_context
def get_trace(ctx: click.Context, trace_id: str, spans: bool):
    """Get trace details."""
    config = ctx.obj['config']
    client = APIClient(config)

    try:
        result = client.get(f'/api/v1/traces/{trace_id}', params={'include_spans': spans})
        output = format_output(result, ctx.obj['output'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to get trace: {e.message}")
        raise SystemExit(1)


@traces.command('search')
@click.argument('query')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--since', default='24h', help='Search window (default: 24h)')
@click.option('--limit', default=20, help='Maximum results')
@click.pass_context
def search_traces(ctx: click.Context, query: str, agent_id: Optional[str],
                  since: str, limit: int):
    """Search traces by content."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {
        'q': query,
        'limit': limit,
        'start_time': parse_time(since)
    }
    if agent_id:
        params['agent_id'] = agent_id

    try:
        result = client.get('/api/v1/traces/search', params=params)
        traces_list = result.get('items', result) if isinstance(result, dict) else result

        click.echo(f"Found {len(traces_list)} traces matching '{query}'\n")

        display_data = []
        for trace in traces_list:
            display_data.append({
                'trace_id': trace.get('trace_id', '')[:16] + '...',
                'agent': trace.get('agent_id', '-'),
                'status': format_status(trace.get('status', 'unknown')),
                'time': trace.get('start_time', '-')[:19]
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=['trace_id', 'agent', 'status', 'time'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to search traces: {e.message}")
        raise SystemExit(1)


@traces.command('timeline')
@click.argument('trace_id')
@click.pass_context
def trace_timeline(ctx: click.Context, trace_id: str):
    """Show trace timeline visualization."""
    config = ctx.obj['config']
    client = APIClient(config)

    try:
        result = client.get(f'/api/v1/traces/{trace_id}', params={'include_spans': True})
        spans = result.get('spans', [])

        if not spans:
            click.echo("No spans found in trace")
            return

        # Sort by start time
        spans.sort(key=lambda s: s.get('start_time', ''))

        # Find the trace start time
        trace_start = datetime.fromisoformat(spans[0]['start_time'].replace('Z', '+00:00'))

        click.echo(f"\nTrace: {trace_id}")
        click.echo(f"Status: {format_status(result.get('status', 'unknown'))}")
        click.echo(f"Duration: {format_duration(result.get('duration_ms', 0))}")
        click.echo("\nTimeline:\n")

        for span in spans:
            span_start = datetime.fromisoformat(span['start_time'].replace('Z', '+00:00'))
            offset_ms = int((span_start - trace_start).total_seconds() * 1000)
            duration_ms = span.get('duration_ms', 0)

            # Calculate indent based on depth
            depth = span.get('depth', 0)
            indent = "  " * depth

            # Status indicator
            status = span.get('status', 'unknown')
            if status == 'error':
                indicator = click.style('✗', fg='red')
            elif status == 'success':
                indicator = click.style('✓', fg='green')
            else:
                indicator = click.style('○', fg='yellow')

            # Format line
            name = span.get('name', 'unnamed')[:40]
            span_type = span.get('span_type', '')

            click.echo(f"{indent}{indicator} {name} ({span_type})")
            click.echo(f"{indent}  +{offset_ms}ms | {format_duration(duration_ms)}")

            # Show error if present
            if span.get('error'):
                error_msg = span['error'].get('message', 'Unknown error')[:60]
                click.echo(f"{indent}  {click.style(f'Error: {error_msg}', fg='red')}")

    except APIError as e:
        print_error(f"Failed to get trace: {e.message}")
        raise SystemExit(1)


@traces.command('errors')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--since', default='24h', help='Time window')
@click.option('--limit', default=20, help='Maximum results')
@click.pass_context
def list_errors(ctx: click.Context, agent_id: Optional[str], since: str, limit: int):
    """List traces with errors."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {
        'status': 'error',
        'limit': limit,
        'start_time': parse_time(since)
    }
    if agent_id:
        params['agent_id'] = agent_id

    try:
        result = client.get('/api/v1/traces', params=params)
        traces_list = result.get('items', result) if isinstance(result, dict) else result

        click.echo(f"Found {len(traces_list)} traces with errors\n")

        for trace in traces_list:
            click.echo(f"Trace: {trace.get('trace_id')}")
            click.echo(f"  Agent: {trace.get('agent_id')}")
            click.echo(f"  Time: {trace.get('start_time')}")
            if trace.get('error'):
                click.echo(f"  Error: {click.style(trace['error'].get('message', 'Unknown'), fg='red')}")
            click.echo()

    except APIError as e:
        print_error(f"Failed to list errors: {e.message}")
        raise SystemExit(1)


def parse_time(time_str: str) -> str:
    """Parse time string to ISO format."""
    # Check for relative time
    if time_str.endswith('h'):
        hours = int(time_str[:-1])
        return (datetime.utcnow() - timedelta(hours=hours)).isoformat() + 'Z'
    elif time_str.endswith('d'):
        days = int(time_str[:-1])
        return (datetime.utcnow() - timedelta(days=days)).isoformat() + 'Z'
    elif time_str.endswith('m'):
        minutes = int(time_str[:-1])
        return (datetime.utcnow() - timedelta(minutes=minutes)).isoformat() + 'Z'
    else:
        # Assume ISO format
        return time_str
