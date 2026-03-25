"""
Agent management commands
"""
import click
from typing import Optional

from ..client import APIClient, APIError
from ..output import format_output, print_success, print_error, format_status


@click.group()
def agents():
    """Manage agents."""
    pass


@agents.command('list')
@click.option('--team', help='Filter by team ID')
@click.option('--status', type=click.Choice(['active', 'inactive', 'all']), default='active', help='Filter by status')
@click.option('--limit', default=50, help='Maximum number of results')
@click.pass_context
def list_agents(ctx: click.Context, team: Optional[str], status: str, limit: int):
    """List all agents."""
    config = ctx.obj['config']
    client = APIClient(config)

    params = {'limit': limit}
    if team:
        params['team_id'] = team
    if status != 'all':
        params['is_active'] = status == 'active'

    try:
        result = client.get('/api/v1/agents', params=params)
        agents_list = result.get('items', result) if isinstance(result, dict) else result

        # Format for display
        display_data = []
        for agent in agents_list:
            display_data.append({
                'agent_id': agent.get('agent_id'),
                'name': agent.get('name'),
                'framework': agent.get('framework', '-'),
                'environment': agent.get('environment', '-'),
                'status': format_status('active' if agent.get('is_active') else 'inactive')
            })

        output = format_output(display_data, ctx.obj['output'],
                              columns=['agent_id', 'name', 'framework', 'environment', 'status'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to list agents: {e.message}")
        raise SystemExit(1)


@agents.command('get')
@click.argument('agent_id')
@click.pass_context
def get_agent(ctx: click.Context, agent_id: str):
    """Get agent details."""
    config = ctx.obj['config']
    client = APIClient(config)

    try:
        result = client.get(f'/api/v1/agents/{agent_id}')
        output = format_output(result, ctx.obj['output'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to get agent: {e.message}")
        raise SystemExit(1)


@agents.command('register')
@click.option('--id', 'agent_id', required=True, help='Unique agent ID')
@click.option('--name', required=True, help='Agent display name')
@click.option('--description', help='Agent description')
@click.option('--team', 'team_id', help='Team ID')
@click.option('--project', 'project_id', help='Project ID')
@click.option('--framework', help='Agent framework (langchain, crewai, custom)')
@click.option('--environment', default='dev', help='Environment (dev, staging, prod)')
@click.pass_context
def register_agent(ctx: click.Context, agent_id: str, name: str, description: Optional[str],
                   team_id: Optional[str], project_id: Optional[str], framework: Optional[str],
                   environment: str):
    """Register a new agent."""
    config = ctx.obj['config']
    client = APIClient(config)

    data = {
        'agent_id': agent_id,
        'name': name,
        'environment': environment
    }
    if description:
        data['description'] = description
    if team_id:
        data['team_id'] = team_id
    if project_id:
        data['project_id'] = project_id
    if framework:
        data['framework'] = framework

    try:
        result = client.post('/api/v1/agents', data=data)
        print_success(f"Agent '{agent_id}' registered successfully")

        output = format_output(result, ctx.obj['output'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to register agent: {e.message}")
        raise SystemExit(1)


@agents.command('update')
@click.argument('agent_id')
@click.option('--name', help='New display name')
@click.option('--description', help='New description')
@click.option('--framework', help='New framework')
@click.option('--active/--inactive', default=None, help='Set active status')
@click.pass_context
def update_agent(ctx: click.Context, agent_id: str, name: Optional[str],
                 description: Optional[str], framework: Optional[str], active: Optional[bool]):
    """Update an agent."""
    config = ctx.obj['config']
    client = APIClient(config)

    data = {}
    if name:
        data['name'] = name
    if description:
        data['description'] = description
    if framework:
        data['framework'] = framework
    if active is not None:
        data['is_active'] = active

    if not data:
        print_error("No updates specified")
        raise SystemExit(1)

    try:
        result = client.patch(f'/api/v1/agents/{agent_id}', data=data)
        print_success(f"Agent '{agent_id}' updated successfully")

    except APIError as e:
        print_error(f"Failed to update agent: {e.message}")
        raise SystemExit(1)


@agents.command('delete')
@click.argument('agent_id')
@click.option('--force', is_flag=True, help='Skip confirmation')
@click.pass_context
def delete_agent(ctx: click.Context, agent_id: str, force: bool):
    """Delete an agent."""
    if not force:
        if not click.confirm(f"Are you sure you want to delete agent '{agent_id}'?"):
            click.echo("Aborted")
            return

    config = ctx.obj['config']
    client = APIClient(config)

    try:
        client.delete(f'/api/v1/agents/{agent_id}')
        print_success(f"Agent '{agent_id}' deleted successfully")

    except APIError as e:
        print_error(f"Failed to delete agent: {e.message}")
        raise SystemExit(1)


@agents.command('metrics')
@click.argument('agent_id')
@click.option('--period', default='24h', help='Time period (1h, 24h, 7d, 30d)')
@click.pass_context
def agent_metrics(ctx: click.Context, agent_id: str, period: str):
    """Get agent metrics summary."""
    config = ctx.obj['config']
    client = APIClient(config)

    try:
        result = client.get(f'/api/v1/agents/{agent_id}/metrics', params={'period': period})
        output = format_output(result, ctx.obj['output'])
        click.echo(output)

    except APIError as e:
        print_error(f"Failed to get metrics: {e.message}")
        raise SystemExit(1)
