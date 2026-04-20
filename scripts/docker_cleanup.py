#!/usr/bin/env python3
"""Docker resource cleanup: stopped containers, dangling images, unused volumes and networks."""

import sys

import click
import docker
from docker.errors import DockerException
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def get_client() -> docker.DockerClient:
    try:
        client = docker.from_env()
        client.ping()
        return client
    except DockerException as e:
        console.print(f"[red]Cannot connect to Docker daemon: {e}[/red]")
        sys.exit(1)


def _fmt_size(n_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} TB"


def remove_stopped_containers(client: docker.DockerClient, dry_run: bool) -> int:
    stopped = client.containers.list(filters={"status": "exited"})
    stopped += client.containers.list(filters={"status": "created"})

    if not stopped:
        console.print("[dim]  No stopped containers.[/dim]")
        return 0

    table = Table(box=box.SIMPLE)
    table.add_column("Container ID", style="cyan")
    table.add_column("Name")
    table.add_column("Image")
    table.add_column("Status")

    for c in stopped:
        table.add_row(c.short_id, c.name, c.image.tags[0] if c.image.tags else "<none>", c.status)

    console.print(table)

    if not dry_run:
        for c in stopped:
            c.remove(force=False)
        console.print(f"[green]Removed {len(stopped)} containers.[/green]")
    else:
        console.print(f"[yellow][dry-run] Would remove {len(stopped)} containers.[/yellow]")

    return len(stopped)


def remove_dangling_images(client: docker.DockerClient, dry_run: bool) -> tuple[int, int]:
    dangling = client.images.list(filters={"dangling": True})

    if not dangling:
        console.print("[dim]  No dangling images.[/dim]")
        return 0, 0

    total_size = sum(img.attrs.get("Size", 0) for img in dangling)

    console.print(f"  Found {len(dangling)} dangling images ({_fmt_size(total_size)})")

    if not dry_run:
        for img in dangling:
            try:
                client.images.remove(img.id, force=False)
            except Exception as e:
                console.print(f"  [yellow]Skip {img.short_id}: {e}[/yellow]")
        console.print(f"[green]Removed {len(dangling)} images ({_fmt_size(total_size)} freed).[/green]")
    else:
        console.print(f"[yellow][dry-run] Would remove {len(dangling)} images ({_fmt_size(total_size)}).[/yellow]")

    return len(dangling), total_size


def remove_unused_volumes(client: docker.DockerClient, dry_run: bool) -> int:
    volumes = client.volumes.list(filters={"dangling": True})

    if not volumes:
        console.print("[dim]  No unused volumes.[/dim]")
        return 0

    console.print(f"  Found {len(volumes)} unused volumes")

    if not dry_run:
        for v in volumes:
            try:
                v.remove()
            except Exception as e:
                console.print(f"  [yellow]Skip {v.name}: {e}[/yellow]")
        console.print(f"[green]Removed {len(volumes)} volumes.[/green]")
    else:
        console.print(f"[yellow][dry-run] Would remove {len(volumes)} volumes.[/yellow]")

    return len(volumes)


def remove_unused_networks(client: docker.DockerClient, dry_run: bool) -> int:
    networks = client.networks.list()
    built_in = {"bridge", "host", "none"}
    unused = []
    for net in networks:
        if net.name in built_in:
            continue
        net.reload()
        if not net.containers:
            unused.append(net)

    if not unused:
        console.print("[dim]  No unused custom networks.[/dim]")
        return 0

    console.print(f"  Found {len(unused)} unused networks")

    if not dry_run:
        for net in unused:
            try:
                net.remove()
            except Exception as e:
                console.print(f"  [yellow]Skip {net.name}: {e}[/yellow]")
        console.print(f"[green]Removed {len(unused)} networks.[/green]")
    else:
        console.print(f"[yellow][dry-run] Would remove {len(unused)} networks.[/yellow]")

    return len(unused)


@click.command()
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be removed without deleting")
@click.option("--containers/--no-containers", default=True, show_default=True)
@click.option("--images/--no-images", default=True, show_default=True)
@click.option("--volumes/--no-volumes", default=True, show_default=True)
@click.option("--networks/--no-networks", default=True, show_default=True)
def main(dry_run, containers, images, volumes, networks):
    """Clean up unused Docker resources.

    Examples:\n
        python docker_cleanup.py\n
        python docker_cleanup.py --dry-run\n
        python docker_cleanup.py --no-volumes --no-networks
    """
    client = get_client()

    if dry_run:
        console.print("[yellow]DRY RUN — nothing will be deleted[/yellow]\n")

    if containers:
        console.rule("[bold]Stopped Containers")
        remove_stopped_containers(client, dry_run)

    if images:
        console.rule("[bold]Dangling Images")
        remove_dangling_images(client, dry_run)

    if volumes:
        console.rule("[bold]Unused Volumes")
        remove_unused_volumes(client, dry_run)

    if networks:
        console.rule("[bold]Unused Networks")
        remove_unused_networks(client, dry_run)

    console.print("\n[bold green]Cleanup complete.[/bold green]")


if __name__ == "__main__":
    main()
