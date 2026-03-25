"""
Alert management commands
"""
import click
from typing import Optional

from ..client import APIClient, APIError
from ..output import format_output, print_success, print_error, format_severity, format_status


@click.group()
def alerts():
    """Manage alerts and alert rules."""
    pass


@alerts.command('list')
@click.option('--status', type=click.Choice(['open', 'acknowledged', 'resolved', 'all']), default='open', help='Filter by status')
@click.option('--severity', type=click.Choice(['critical', 'high', 'medium', 'low', 'all']), default='all', help='Filter by severity')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--limit', default=20, help='Maximum results')
@click.pass_context
def list_alerts(ctx: click.Context, status: str, severity: str, agent_id: Optional[str], limit: int):
    """List alerts."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {'limit': limit}
    if status != 'all':
        params['status'] = status
    if severity != 'all':
        params['severity'] = severity
    if agent_id:
        params['agent_id'] = agent_id

    try:
        result = client.get('/api/v1/alerts', params=params)
        alerts_list = result.get('items', result) if isinstance(result, dict) else result

        display_data = []
        for alert in alerts_list:
            display_data.append({
                'id': alert.get('alert_id', '')[:8],
                'severity': format_severity(alert.get('severity', 'medium')),
                'title': alert.get('title', '-')[:40],
                'agent': alert.get('agent_id', '-'),
                'status': format_status(alert.get('status', 'open')),
                'time': alert.get('triggered_at', '-')[:16]
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=['id', 'severity', 'title', 'agent', 'status', 'time'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to list alerts: {e.message}")
        raise SystemExit(1)


@alerts.command('get')
@click.argument('alert_id')
@click.pass_context
def get_alert(ctx: click.Context, alert_id: str):
    """Get alert details."""
    config = ctx.obj['config']
    client = APIClient(config)

    try:
        result = client.get(f'/api/v1/alerts/{alert_id}')

        # Format for display
        click.echo(f"\nAlert: {result.get('alert_id')}")
        click.echo(f"Title: {result.get('title')}")
        click.echo(f"Severity: {format_severity(result.get('severity', 'medium'))}")
        click.echo(f"Status: {format_status(result.get('status', 'open'))}")
        click.echo(f"Agent: {result.get('agent_id')}")
        click.echo(f"Triggered: {result.get('triggered_at')}")
        click.echo(f"\nDescription:\n{result.get('description', '-')}")

        # Investigation results
        investigation = result.get('investigation')
        if investigation:
            click.echo(f"\n{click.style('AI Investigation:', bold=True)}")
            click.echo(f"Root Cause: {investigation.get('root_cause', '-')}")
            click.echo(f"Recommendation: {investigation.get('recommendation', '-')}")

        # Trace link
        if result.get('trace_id'):
            click.echo(f"\nTrace: {result.get('trace_id')}")

    except APIError as e:
        print_error(f"Failed to get alert: {e.message}")
        raise SystemExit(1)


@alerts.command('ack')
@click.argument('alert_id')
@click.option('--note', help='Acknowledgment note')
@click.pass_context
def acknowledge_alert(ctx: click.Context, alert_id: str, note: Optional[str]):
    """Acknowledge an alert."""
    config = ctx.obj['config']
    client = APIClient(config)

    data = {'status': 'acknowledged'}
    if note:
        data['note'] = note

    try:
        client.patch(f'/api/v1/alerts/{alert_id}', data=data)
        print_success(f"Alert {alert_id} acknowledged")

    except APIError as e:
        print_error(f"Failed to acknowledge alert: {e.message}")
        raise SystemExit(1)


@alerts.command('resolve')
@click.argument('alert_id')
@click.option('--note', help='Resolution note')
@click.pass_context
def resolve_alert(ctx: click.Context, alert_id: str, note: Optional[str]):
    """Resolve an alert."""
    config = ctx.obj['config']
    client = APIClient(config)

    data = {'status': 'resolved'}
    if note:
        data['resolution_note'] = note

    try:
        client.patch(f'/api/v1/alerts/{alert_id}', data=data)
        print_success(f"Alert {alert_id} resolved")

    except APIError as e:
        print_error(f"Failed to resolve alert: {e.message}")
        raise SystemExit(1)


# Alert Rules subcommands
@alerts.group('rules')
def rules():
    """Manage alert rules."""
    pass


@rules.command('list')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--enabled/--disabled', default=None, help='Filter by enabled status')
@click.pass_context
def list_rules(ctx: click.Context, agent_id: Optional[str], enabled: Optional[bool]):
    """List alert rules."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {}
    if agent_id:
        params['agent_id'] = agent_id
    if enabled is not None:
        params['is_enabled'] = enabled

    try:
        result = client.get('/api/v1/alerts/rules', params=params)
        rules_list = result.get('items', result) if isinstance(result, dict) else result

        display_data = []
        for rule in rules_list:
            display_data.append({
                'id': rule.get('rule_id', '')[:8],
                'name': rule.get('name', '-'),
                'type': rule.get('rule_type', '-'),
                'severity': format_severity(rule.get('severity', 'medium')),
                'enabled': format_status('active' if rule.get('is_enabled') else 'inactive')
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=['id', 'name', 'type', 'severity', 'enabled'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to list rules: {e.message}")
        raise SystemExit(1)


@rules.command('create')
@click.option('--name', required=True, help='Rule name')
@click.option('--type', 'rule_type', required=True,
              type=click.Choice(['error_rate', 'latency', 'token_usage', 'anomaly']),
              help='Rule type')
@click.option('--agent', 'agent_id', help='Target agent ID')
@click.option('--severity', default='medium',
              type=click.Choice(['critical', 'high', 'medium', 'low']),
              help='Alert severity')
@click.option('--threshold', type=float, help='Threshold value')
@click.option('--window', default=300, help='Evaluation window in seconds')
@click.pass_context
def create_rule(ctx: click.Context, name: str, rule_type: str, agent_id: Optional[str],
                severity: str, threshold: Optional[float], window: int):
    """Create an alert rule."""
    config = ctx.obj['config']
    client = APIClient(config)

    data = {
        'name': name,
        'rule_type': rule_type,
        'severity': severity,
        'conditions': {
            'window_seconds': window
        }
    }

    if agent_id:
        data['agent_id'] = agent_id

    if threshold:
        data['conditions']['threshold'] = threshold

    # Set default thresholds by rule type
    if not threshold:
        defaults = {
            'error_rate': 0.05,  # 5%
            'latency': 5000,     # 5000ms
            'token_usage': 100000,  # 100K tokens
            'anomaly': 2.0       # 2 std deviations
        }
        data['conditions']['threshold'] = defaults.get(rule_type, 1.0)

    try:
        result = client.post('/api/v1/alerts/rules', data=data)
        print_success(f"Alert rule '{name}' created")
        click.echo(f"Rule ID: {result.get('rule_id')}")

    except APIError as e:
        print_error(f"Failed to create rule: {e.message}")
        raise SystemExit(1)


@rules.command('enable')
@click.argument('rule_id')
@click.pass_context
def enable_rule(ctx: click.Context, rule_id: str):
    """Enable an alert rule."""
    config = ctx.obj['config']
    client = APIClient(config)

    try:
        client.patch(f'/api/v1/alerts/rules/{rule_id}', data={'is_enabled': True})
        print_success(f"Rule {rule_id} enabled")

    except APIError as e:
        print_error(f"Failed to enable rule: {e.message}")
        raise SystemExit(1)


@rules.command('disable')
@click.argument('rule_id')
@click.pass_context
def disable_rule(ctx: click.Context, rule_id: str):
    """Disable an alert rule."""
    config = ctx.obj['config']
    client = APIClient(config)

    try:
        client.patch(f'/api/v1/alerts/rules/{rule_id}', data={'is_enabled': False})
        print_success(f"Rule {rule_id} disabled")

    except APIError as e:
        print_error(f"Failed to disable rule: {e.message}")
        raise SystemExit(1)


@rules.command('delete')
@click.argument('rule_id')
@click.option('--force', is_flag=True, help='Skip confirmation')
@click.pass_context
def delete_rule(ctx: click.Context, rule_id: str, force: bool):
    """Delete an alert rule."""
    if not force:
        if not click.confirm(f"Are you sure you want to delete rule '{rule_id}'?"):
            click.echo("Aborted")
            return

    config = ctx.obj['config']
    client = APIClient(config)

    try:
        client.delete(f'/api/v1/alerts/rules/{rule_id}')
        print_success(f"Rule {rule_id} deleted")

    except APIError as e:
        print_error(f"Failed to delete rule: {e.message}")
        raise SystemExit(1)
