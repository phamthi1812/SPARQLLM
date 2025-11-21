"""
Rich Console UI for Logical Plan Visualization

Displays logical plans with dependency trees, cost estimates, and natural language explanations.
Provides interactive confirmation prompts for user approval.
"""

import json
from typing import Dict, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.tree import Tree
    from rich.syntax import Syntax
    from rich.prompt import Prompt
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' library not installed. Using plain text output.")
    print("Install with: pip install rich")


console = Console() if RICH_AVAILABLE else None


def display_plan(plan: dict, cost: dict, explanation: str):
    """
    Display logical plan with visualization, cost estimate, and explanation.

    Args:
        plan: Logical plan dict (conforms to logical_plan.json schema)
        cost: Cost estimate from CostEstimator
        explanation: Natural language explanation from Explainer
    """
    if not RICH_AVAILABLE:
        _display_plan_plain(plan, cost, explanation)
        return

    # Header
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Logical Plan Generated[/bold cyan]",
        border_style="cyan"
    ))

    # Natural language explanation
    console.print()
    console.print("[bold]Query Explanation:[/bold]")
    console.print(f"  {explanation}")
    console.print()

    # Cost estimate table
    cost_table = Table(show_header=False, box=None, padding=(0, 2))

    latency_s = cost['latency_ms'] / 1000
    latency_str = f"{latency_s:.1f}s" if latency_s < 60 else f"{latency_s/60:.1f}min"

    cost_table.add_row("[yellow]Estimated Latency:[/yellow]", f"[bold]{latency_str}[/bold]")
    cost_table.add_row("[yellow]Token Usage:[/yellow]", f"[bold]{cost['tokens']}[/bold] tokens")
    cost_table.add_row("[yellow]API Calls:[/yellow]", f"[bold]{cost['api_calls']}[/bold]")

    cost_usd = cost['cost_usd']
    if cost_usd < 0.01:
        cost_str = f"${cost_usd:.4f}"
    else:
        cost_str = f"${cost_usd:.2f}"
    cost_table.add_row("[yellow]Cost (USD):[/yellow]", f"[bold]{cost_str}[/bold]")

    # Add category with color
    category = cost['cost_category']
    category_colors = {'low': 'green', 'medium': 'yellow', 'high': 'red'}
    category_color = category_colors.get(category, 'white')
    cost_table.add_row(
        "[yellow]Cost Category:[/yellow]",
        f"[bold {category_color}]{category.upper()}[/bold {category_color}]"
    )

    console.print(Panel(cost_table, title="[bold yellow]Cost Estimate[/bold yellow]", border_style="yellow"))

    # Execution steps as dependency tree
    console.print()
    tree = Tree("[bold]Execution Steps[/bold]")

    # Build step nodes
    step_map = {step['id']: step for step in plan['steps']}
    step_nodes = {}
    processed = set()

    def add_step_to_tree(step_id: str, parent_node=None):
        """Recursively add step and its dependencies to tree"""
        if step_id in processed:
            return step_nodes.get(step_id)

        step = step_map[step_id]
        ggf_name = step['ggf']['name']
        operation = step['operation'].replace('_', ' ').title()

        # Build label with color coding
        label = f"[green bold]{step_id}[/green bold]: {operation} → [cyan]{ggf_name}[/cyan]"

        # Add args preview if not too long
        args = step['ggf']['args']
        if args:
            args_preview = ', '.join(f"{k}={v}" for k, v in list(args.items())[:2])
            if len(args_preview) > 50:
                args_preview = args_preview[:47] + "..."
            label += f" [dim]({args_preview})[/dim]"

        # Attach to tree
        if parent_node is None:
            node = tree.add(label)
        else:
            node = parent_node.add(label)

        step_nodes[step_id] = node
        processed.add(step_id)
        return node

    # Add steps in dependency order (topological)
    for step in plan['steps']:
        step_id = step['id']
        if step_id in processed:
            continue

        deps = step.get('depends_on', [])
        if not deps:
            # Root node
            add_step_to_tree(step_id, None)
        else:
            # Attach to first dependency
            parent_id = deps[0]
            if parent_id not in processed:
                add_step_to_tree(parent_id, None)
            parent_node = step_nodes[parent_id]
            add_step_to_tree(step_id, parent_node)

    console.print(tree)

    # Parallel execution groups (if any)
    if cost.get('parallel_groups') and len(cost['parallel_groups']) > 0:
        console.print()
        console.print("[bold]Parallel Execution Opportunities:[/bold]")
        for i, group in enumerate(cost['parallel_groups'], 1):
            group_str = ', '.join(f"[cyan]{step_id}[/cyan]" for step_id in group)
            console.print(f"  Group {i}: {group_str}")

    # Raw JSON (collapsible section)
    console.print()
    console.print("[dim]Raw Plan JSON (for debugging):[/dim]")
    syntax = Syntax(
        json.dumps(plan, indent=2),
        "json",
        theme="monokai",
        line_numbers=True,
        word_wrap=True
    )
    console.print(Panel(syntax, border_style="dim"))


def _display_plan_plain(plan: dict, cost: dict, explanation: str):
    """Fallback plain text display when Rich not available"""
    print("\n" + "=" * 80)
    print("LOGICAL PLAN GENERATED")
    print("=" * 80)

    print(f"\nExplanation: {explanation}\n")

    print("Cost Estimate:")
    print(f"  Latency: {cost['latency_ms']/1000:.1f}s")
    print(f"  Tokens: {cost['tokens']}")
    print(f"  API Calls: {cost['api_calls']}")
    print(f"  Cost: ${cost['cost_usd']:.4f}")
    print(f"  Category: {cost['cost_category'].upper()}\n")

    print("Steps:")
    for step in plan['steps']:
        print(f"  {step['id']}: {step['operation']} -> {step['ggf']['name']}")
        if step.get('depends_on'):
            print(f"    depends on: {', '.join(step['depends_on'])}")

    print("\nRaw JSON:")
    print(json.dumps(plan, indent=2))
    print("=" * 80 + "\n")


def prompt_user_confirmation() -> str:
    """
    Prompt user to approve, reject, edit, or quit.

    Returns:
        'approve', 'reject', 'edit', or 'quit'
    """
    if not RICH_AVAILABLE:
        return _prompt_user_confirmation_plain()

    console.print()
    console.print(Panel.fit(
        "[bold cyan]Review the plan above and choose an action[/bold cyan]",
        border_style="cyan"
    ))

    console.print()
    console.print("  [bold green]y[/bold green] - Approve and execute")
    console.print("  [bold red]n[/bold red] - Reject and regenerate")
    console.print("  [bold yellow]e[/bold yellow] - Edit plan manually")
    console.print("  [bold dim]q[/bold dim] - Quit without executing")
    console.print()

    choice = Prompt.ask(
        "[bold cyan]Your choice[/bold cyan]",
        choices=["y", "n", "e", "q"],
        default="y"
    ).lower().strip()

    action_map = {
        'y': 'approve',
        'n': 'reject',
        'e': 'edit',
        'q': 'quit'
    }

    return action_map[choice]


def _prompt_user_confirmation_plain() -> str:
    """Fallback plain text confirmation prompt"""
    print("\nActions:")
    print("  y - Approve and execute")
    print("  n - Reject and regenerate")
    print("  e - Edit plan manually")
    print("  q - Quit")

    while True:
        choice = input("Your choice [y/n/e/q]: ").lower().strip()
        if choice in ['y', 'n', 'e', 'q']:
            return {'y': 'approve', 'n': 'reject', 'e': 'edit', 'q': 'quit'}[choice]
        print("Invalid choice. Please enter y, n, e, or q.")


def display_error(message: str, error_type: str = "error"):
    """
    Display error message with formatting.

    Args:
        message: Error message to display
        error_type: 'error', 'warning', or 'info'
    """
    if not RICH_AVAILABLE:
        print(f"\n[{error_type.upper()}] {message}\n")
        return

    colors = {
        'error': 'red',
        'warning': 'yellow',
        'info': 'blue'
    }
    color = colors.get(error_type, 'white')

    console.print()
    console.print(Panel(
        f"[bold]{message}[/bold]",
        title=f"[{color}]{error_type.upper()}[/{color}]",
        border_style=color
    ))


def display_success(message: str):
    """Display success message"""
    if not RICH_AVAILABLE:
        print(f"\n[SUCCESS] {message}\n")
        return

    console.print()
    console.print(Panel(
        f"[bold]{message}[/bold]",
        title="[green]SUCCESS[/green]",
        border_style="green"
    ))
