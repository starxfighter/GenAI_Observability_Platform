"""
Metrics commands
"""
import click
from typing import Optional

from ..client import APIClient, APIError
from ..output import (format_output, print_success, print_error, format_duration,
                      format_tokens, format_cost)


@click.group()
def metrics():
    """View metrics and analytics."""
    pass


@metrics.command('summary')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--period', default='24h', help='Time period (1h, 24h, 7d, 30d)')
@click.pass_context
def summary(ctx: click.Context, agent_id: Optional[str], period: str):
    """Show metrics summary."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {'period': period}
    if agent_id:
        params['agent_id'] = agent_id

    try:
        result = client.get('/api/v1/metrics/summary', params=params)

        click.echo(f"\n{'='*50}")
        click.echo(f"Metrics Summary ({period})")
        click.echo(f"{'='*50}\n")

        # Trace metrics
        click.echo(click.style("Traces", bold=True))
        click.echo(f"  Total Traces: {result.get('total_traces', 0):,}")
        click.echo(f"  Success Rate: {result.get('success_rate', 0)*100:.1f}%")
        click.echo(f"  Error Rate: {result.get('error_rate', 0)*100:.1f}%")
        click.echo()

        # Latency metrics
        click.echo(click.style("Latency", bold=True))
        click.echo(f"  P50: {format_duration(result.get('p50_latency_ms', 0))}")
        click.echo(f"  P95: {format_duration(result.get('p95_latency_ms', 0))}")
        click.echo(f"  P99: {format_duration(result.get('p99_latency_ms', 0))}")
        click.echo()

        # Token metrics
        click.echo(click.style("Token Usage", bold=True))
        click.echo(f"  Total Tokens: {format_tokens(result.get('total_tokens', 0))}")
        click.echo(f"  Prompt Tokens: {format_tokens(result.get('prompt_tokens', 0))}")
        click.echo(f"  Completion Tokens: {format_tokens(result.get('completion_tokens', 0))}")
        click.echo()

        # Cost metrics
        click.echo(click.style("Cost", bold=True))
        click.echo(f"  Total Cost: {format_cost(result.get('total_cost_usd', 0))}")
        click.echo(f"  Avg Cost/Trace: {format_cost(result.get('avg_cost_per_trace', 0))}")
        click.echo()

    except APIError as e:
        print_error(f"Failed to get metrics summary: {e.message}")
        raise SystemExit(1)


@metrics.command('tokens')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--model', help='Filter by model')
@click.option('--period', default='24h', help='Time period')
@click.option('--group-by', type=click.Choice(['agent', 'model', 'hour', 'day']), default='model')
@click.pass_context
def token_usage(ctx: click.Context, agent_id: Optional[str], model: Optional[str],
                period: str, group_by: str):
    """Show token usage breakdown."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {'period': period, 'group_by': group_by}
    if agent_id:
        params['agent_id'] = agent_id
    if model:
        params['model'] = model

    try:
        result = client.get('/api/v1/metrics/tokens', params=params)
        data = result.get('data', result) if isinstance(result, dict) else result

        display_data = []
        for item in data:
            display_data.append({
                group_by: item.get(group_by, '-'),
                'prompt': format_tokens(item.get('prompt_tokens', 0)),
                'completion': format_tokens(item.get('completion_tokens', 0)),
                'total': format_tokens(item.get('total_tokens', 0)),
                'cost': format_cost(item.get('cost_usd', 0))
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=[group_by, 'prompt', 'completion', 'total', 'cost'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to get token metrics: {e.message}")
        raise SystemExit(1)


@metrics.command('latency')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--period', default='24h', help='Time period')
@click.option('--interval', default='1h', help='Aggregation interval')
@click.pass_context
def latency(ctx: click.Context, agent_id: Optional[str], period: str, interval: str):
    """Show latency metrics over time."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {'period': period, 'interval': interval}
    if agent_id:
        params['agent_id'] = agent_id

    try:
        result = client.get('/api/v1/metrics/latency', params=params)
        data = result.get('data', result) if isinstance(result, dict) else result

        display_data = []
        for item in data:
            display_data.append({
                'time': item.get('timestamp', '-')[:16],
                'p50': format_duration(item.get('p50_ms', 0)),
                'p95': format_duration(item.get('p95_ms', 0)),
                'p99': format_duration(item.get('p99_ms', 0)),
                'requests': item.get('request_count', 0)
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=['time', 'p50', 'p95', 'p99', 'requests'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to get latency metrics: {e.message}")
        raise SystemExit(1)


@metrics.command('errors')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--period', default='24h', help='Time period')
@click.option('--top', default=10, help='Number of top error types to show')
@click.pass_context
def error_breakdown(ctx: click.Context, agent_id: Optional[str], period: str, top: int):
    """Show error breakdown by type."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {'period': period, 'limit': top}
    if agent_id:
        params['agent_id'] = agent_id

    try:
        result = client.get('/api/v1/metrics/errors', params=params)
        data = result.get('data', result) if isinstance(result, dict) else result

        click.echo(f"\nTop {top} Error Types ({period})\n")

        display_data = []
        for item in data:
            display_data.append({
                'error_type': item.get('error_type', '-')[:30],
                'count': item.get('count', 0),
                'percentage': f"{item.get('percentage', 0):.1f}%",
                'agents': item.get('affected_agents', 0)
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=['error_type', 'count', 'percentage', 'agents'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to get error metrics: {e.message}")
        raise SystemExit(1)


@metrics.command('cost')
@click.option('--period', default='30d', help='Time period')
@click.option('--group-by', type=click.Choice(['agent', 'team', 'project', 'cost_center', 'day']),
              default='agent', help='Group by')
@click.pass_context
def cost_breakdown(ctx: click.Context, period: str, group_by: str):
    """Show cost breakdown."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {'period': period, 'group_by': group_by}

    try:
        result = client.get('/api/v1/metrics/cost', params=params)
        data = result.get('data', result) if isinstance(result, dict) else result

        # Calculate total
        total_cost = sum(item.get('cost_usd', 0) for item in data)

        click.echo(f"\nCost Breakdown by {group_by.replace('_', ' ').title()} ({period})")
        click.echo(f"Total: {format_cost(total_cost)}\n")

        display_data = []
        for item in data:
            cost = item.get('cost_usd', 0)
            display_data.append({
                group_by: item.get(group_by, '-'),
                'cost': format_cost(cost),
                'percentage': f"{(cost/total_cost*100) if total_cost > 0 else 0:.1f}%",
                'tokens': format_tokens(item.get('total_tokens', 0))
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=[group_by, 'cost', 'percentage', 'tokens'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to get cost metrics: {e.message}")
        raise SystemExit(1)


@metrics.command('tools')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--period', default='24h', help='Time period')
@click.pass_context
def tool_metrics(ctx: click.Context, agent_id: Optional[str], period: str):
    """Show tool usage metrics."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {'period': period}
    if agent_id:
        params['agent_id'] = agent_id

    try:
        result = client.get('/api/v1/metrics/tools', params=params)
        data = result.get('data', result) if isinstance(result, dict) else result

        click.echo(f"\nTool Usage ({period})\n")

        display_data = []
        for item in data:
            success_rate = item.get('success_rate', 0)
            display_data.append({
                'tool': item.get('tool_name', '-'),
                'calls': item.get('invocation_count', 0),
                'success': click.style(f"{success_rate*100:.1f}%",
                                      fg='green' if success_rate > 0.95 else 'yellow' if success_rate > 0.8 else 'red'),
                'avg_time': format_duration(item.get('avg_duration_ms', 0)),
                'p95_time': format_duration(item.get('p95_duration_ms', 0))
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=['tool', 'calls', 'success', 'avg_time', 'p95_time'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to get tool metrics: {e.message}")
        raise SystemExit(1)
