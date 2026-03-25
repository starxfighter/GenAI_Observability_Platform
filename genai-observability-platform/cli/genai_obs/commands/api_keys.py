"""
API Key management commands
"""
import click
from typing import Optional

from ..client import APIClient, APIError
from ..output import format_output, print_success, print_error, format_status


@click.group('api-keys')
def api_keys():
    """Manage API keys."""
    pass


@api_keys.command('list')
@click.option('--agent', 'agent_id', help='Filter by agent ID')
@click.option('--active/--all', default=True, help='Show only active keys')
@click.pass_context
def list_keys(ctx: click.Context, agent_id: Optional[str], active: bool):
    """List API keys."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {}
    if agent_id:
        params['agent_id'] = agent_id
    if active:
        params['is_active'] = True

    try:
        result = client.get('/api/v1/api-keys', params=params)
        keys_list = result.get('items', result) if isinstance(result, dict) else result

        display_data = []
        for key in keys_list:
            display_data.append({
                'prefix': key.get('key_prefix', '-'),
                'name': key.get('name', '-'),
                'agent': key.get('agent_id', '-'),
                'status': format_status('active' if key.get('is_active') else 'inactive'),
                'last_used': key.get('last_used_at', 'Never')[:16] if key.get('last_used_at') else 'Never',
                'created': key.get('created_at', '-')[:10]
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=['prefix', 'name', 'agent', 'status', 'last_used', 'created'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to list API keys: {e.message}")
        raise SystemExit(1)


@api_keys.command('create')
@click.option('--name', required=True, help='Key name/description')
@click.option('--agent', 'agent_id', required=True, help='Agent ID this key is for')
@click.option('--expires', help='Expiration date (YYYY-MM-DD) or days (e.g., "30d")')
@click.option('--scopes', multiple=True, default=['write:events', 'read:traces'],
              help='Permission scopes')
@click.pass_context
def create_key(ctx: click.Context, name: str, agent_id: str,
               expires: Optional[str], scopes: tuple):
    """Create a new API key."""
    config = ctx.obj['config']
    client = APIClient(config)

    data = {
        'name': name,
        'agent_id': agent_id,
        'scopes': list(scopes)
    }

    if expires:
        if expires.endswith('d'):
            from datetime import datetime, timedelta
            days = int(expires[:-1])
            data['expires_at'] = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
        else:
            data['expires_at'] = expires + 'T00:00:00Z'

    try:
        result = client.post('/api/v1/api-keys', data=data)

        print_success("API key created successfully")
        click.echo()
        click.echo(click.style("IMPORTANT: Save this key now. It won't be shown again!", fg='yellow', bold=True))
        click.echo()
        click.echo(f"API Key: {click.style(result.get('api_key', 'N/A'), fg='green', bold=True)}")
        click.echo(f"Key ID: {result.get('key_id')}")
        click.echo(f"Prefix: {result.get('key_prefix')}")
        click.echo()

    except APIError as e:
        print_error(f"Failed to create API key: {e.message}")
        raise SystemExit(1)


@api_keys.command('revoke')
@click.argument('key_id')
@click.option('--force', is_flag=True, help='Skip confirmation')
@click.pass_context
def revoke_key(ctx: click.Context, key_id: str, force: bool):
    """Revoke an API key."""
    if not force:
        if not click.confirm(f"Are you sure you want to revoke API key '{key_id}'? This cannot be undone."):
            click.echo("Aborted")
            return

    config = ctx.obj['config']
    client = APIClient(config)

    try:
        client.delete(f'/api/v1/api-keys/{key_id}')
        print_success(f"API key {key_id} revoked")

    except APIError as e:
        print_error(f"Failed to revoke API key: {e.message}")
        raise SystemExit(1)


@api_keys.command('rotate')
@click.argument('key_id')
@click.option('--grace-period', default=24, help='Hours to keep old key active (default: 24)')
@click.pass_context
def rotate_key(ctx: click.Context, key_id: str, grace_period: int):
    """Rotate an API key (create new, schedule old for deletion)."""
    config = ctx.obj['config']
    client = APIClient(config)

    try:
        result = client.post(f'/api/v1/api-keys/{key_id}/rotate', data={
            'grace_period_hours': grace_period
        })

        print_success("API key rotated successfully")
        click.echo()
        click.echo(click.style("IMPORTANT: Save this new key now. It won't be shown again!", fg='yellow', bold=True))
        click.echo()
        click.echo(f"New API Key: {click.style(result.get('api_key', 'N/A'), fg='green', bold=True)}")
        click.echo(f"New Key ID: {result.get('key_id')}")
        click.echo(f"Old key will be revoked in {grace_period} hours")
        click.echo()

    except APIError as e:
        print_error(f"Failed to rotate API key: {e.message}")
        raise SystemExit(1)


@api_keys.command('test')
@click.option('--key', 'api_key', help='API key to test (uses configured key if not provided)')
@click.pass_context
def test_key(ctx: click.Context, api_key: Optional[str]):
    """Test an API key."""
    config = ctx.obj['config']

    if api_key:
        # Use provided key
        from ..config import Config
        test_config = Config(
            endpoint=config.endpoint,
            api_key=api_key,
            timeout=config.timeout
        )
        client = APIClient(test_config)
    else:
        client = APIClient(config)

    try:
        result = client.get('/api/v1/auth/validate')

        print_success("API key is valid")
        click.echo(f"Agent: {result.get('agent_id', '-')}")
        click.echo(f"Scopes: {', '.join(result.get('scopes', []))}")
        if result.get('expires_at'):
            click.echo(f"Expires: {result.get('expires_at')}")

    except APIError as e:
        if e.status_code == 401:
            print_error("API key is invalid or expired")
        else:
            print_error(f"Failed to validate API key: {e.message}")
        raise SystemExit(1)
