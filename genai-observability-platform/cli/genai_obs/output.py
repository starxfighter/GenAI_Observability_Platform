"""
Output formatting utilities for CLI
"""
import json
import click
from typing import Any, List, Optional
from datetime import datetime


def format_output(data: Any, format: str = 'table', columns: Optional[List[str]] = None) -> str:
    """
    Format data for output.

    Args:
        data: Data to format (dict, list, or primitive)
        format: Output format ('json', 'table', 'text')
        columns: Column names for table format

    Returns:
        Formatted string
    """
    if format == 'json':
        return json.dumps(data, indent=2, default=str)
    elif format == 'table':
        return format_table(data, columns)
    else:
        return format_text(data)


def format_table(data: Any, columns: Optional[List[str]] = None) -> str:
    """Format data as a table."""
    if isinstance(data, dict):
        # Single item - format as key-value pairs
        lines = []
        max_key_len = max(len(str(k)) for k in data.keys()) if data else 0
        for key, value in data.items():
            formatted_value = format_value(value)
            lines.append(f"{key:<{max_key_len}}  {formatted_value}")
        return '\n'.join(lines)

    elif isinstance(data, list):
        if not data:
            return "No results"

        # List of items - format as table
        if columns is None:
            # Auto-detect columns from first item
            if isinstance(data[0], dict):
                columns = list(data[0].keys())
            else:
                columns = ['value']

        # Calculate column widths
        widths = {col: len(col) for col in columns}
        for item in data:
            if isinstance(item, dict):
                for col in columns:
                    val = str(item.get(col, ''))[:50]  # Truncate long values
                    widths[col] = max(widths[col], len(val))
            else:
                widths['value'] = max(widths['value'], len(str(item)))

        # Build header
        header = '  '.join(col.upper().ljust(widths[col]) for col in columns)
        separator = '  '.join('-' * widths[col] for col in columns)

        # Build rows
        rows = []
        for item in data:
            if isinstance(item, dict):
                row = '  '.join(
                    str(item.get(col, ''))[:50].ljust(widths[col])
                    for col in columns
                )
            else:
                row = str(item)
            rows.append(row)

        return f"{header}\n{separator}\n" + '\n'.join(rows)

    else:
        return str(data)


def format_text(data: Any) -> str:
    """Format data as plain text."""
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            lines.append(f"{key}: {format_value(value)}")
        return '\n'.join(lines)
    elif isinstance(data, list):
        return '\n'.join(format_value(item) for item in data)
    else:
        return str(data)


def format_value(value: Any) -> str:
    """Format a single value."""
    if value is None:
        return '-'
    elif isinstance(value, bool):
        return click.style('Yes', fg='green') if value else click.style('No', fg='red')
    elif isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, (list, dict)):
        return json.dumps(value, default=str)
    else:
        return str(value)


def print_success(message: str):
    """Print a success message."""
    click.echo(click.style(f"✓ {message}", fg='green'))


def print_error(message: str):
    """Print an error message."""
    click.echo(click.style(f"✗ {message}", fg='red'), err=True)


def print_warning(message: str):
    """Print a warning message."""
    click.echo(click.style(f"⚠ {message}", fg='yellow'))


def print_info(message: str):
    """Print an info message."""
    click.echo(click.style(f"ℹ {message}", fg='blue'))


def format_duration(ms: int) -> str:
    """Format duration in milliseconds to human-readable string."""
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    elif ms < 3600000:
        return f"{ms/60000:.1f}m"
    else:
        return f"{ms/3600000:.1f}h"


def format_tokens(count: int) -> str:
    """Format token count."""
    if count < 1000:
        return str(count)
    elif count < 1000000:
        return f"{count/1000:.1f}K"
    else:
        return f"{count/1000000:.1f}M"


def format_cost(amount: float) -> str:
    """Format cost in USD."""
    if amount < 0.01:
        return f"${amount:.4f}"
    elif amount < 1:
        return f"${amount:.3f}"
    else:
        return f"${amount:.2f}"


def format_severity(severity: str) -> str:
    """Format severity with color."""
    colors = {
        'critical': 'red',
        'high': 'red',
        'medium': 'yellow',
        'low': 'green',
        'info': 'blue'
    }
    color = colors.get(severity.lower(), 'white')
    return click.style(severity.upper(), fg=color)


def format_status(status: str) -> str:
    """Format status with color."""
    colors = {
        'success': 'green',
        'error': 'red',
        'running': 'blue',
        'pending': 'yellow',
        'active': 'green',
        'inactive': 'red',
        'open': 'yellow',
        'resolved': 'green',
        'acknowledged': 'blue'
    }
    color = colors.get(status.lower(), 'white')
    return click.style(status, fg=color)
