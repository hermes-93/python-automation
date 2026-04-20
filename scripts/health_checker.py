#!/usr/bin/env python3
"""HTTP endpoint health checker with retries, latency tracking, and rich reporting."""

import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import click
import requests
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 2


@dataclass
class CheckResult:
    url: str
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    healthy: bool = False
    error: Optional[str] = None
    attempts: int = 0


def check_endpoint(url: str, timeout: int = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES) -> CheckResult:
    result = CheckResult(url=url)

    for attempt in range(1, retries + 1):
        result.attempts = attempt
        try:
            start = time.perf_counter()
            resp = requests.get(url, timeout=timeout, allow_redirects=True)
            elapsed = (time.perf_counter() - start) * 1000
            result.status_code = resp.status_code
            result.latency_ms = round(elapsed, 2)
            result.healthy = 200 <= resp.status_code < 400
            result.error = None
            return result
        except requests.exceptions.ConnectionError as e:
            result.error = f"Connection error: {e}"
        except requests.exceptions.Timeout:
            result.error = f"Timeout after {timeout}s"
        except requests.exceptions.RequestException as e:
            result.error = str(e)

        if attempt < retries:
            time.sleep(DEFAULT_RETRY_DELAY)

    result.healthy = False
    return result


def run_checks(urls: list[str], timeout: int, retries: int) -> list[CheckResult]:
    results = []
    for url in urls:
        with console.status(f"Checking {url}..."):
            result = check_endpoint(url, timeout=timeout, retries=retries)
        results.append(result)
    return results


def print_report(results: list[CheckResult]) -> int:
    table = Table(title="Health Check Report", box=box.ROUNDED, show_lines=True)
    table.add_column("URL", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center", width=10)
    table.add_column("HTTP", justify="center", width=6)
    table.add_column("Latency", justify="right", width=10)
    table.add_column("Attempts", justify="center", width=8)
    table.add_column("Error", style="red")

    failed = 0
    for r in results:
        status = "[green]UP[/green]" if r.healthy else "[red]DOWN[/red]"
        http = str(r.status_code) if r.status_code else "—"
        latency = f"{r.latency_ms:.1f} ms" if r.latency_ms else "—"
        error = r.error or ""
        if not r.healthy:
            failed += 1
        table.add_row(r.url, status, http, latency, str(r.attempts), error)

    console.print(table)

    total = len(results)
    ok = total - failed
    console.print(f"\n[bold]Summary:[/bold] {ok}/{total} healthy", end="")
    if failed:
        console.print(f"  [red]({failed} down)[/red]")
    else:
        console.print("  [green]✓ All OK[/green]")

    return failed


@click.command()
@click.argument("urls", nargs=-1, required=True)
@click.option("--timeout", "-t", default=DEFAULT_TIMEOUT, show_default=True, help="Request timeout in seconds")
@click.option("--retries", "-r", default=DEFAULT_RETRIES, show_default=True, help="Number of retry attempts")
@click.option("--fail-fast", is_flag=True, help="Exit 1 on first failure")
def main(urls, timeout, retries, fail_fast):
    """Check health of HTTP endpoints.

    Examples:\n
        python health_checker.py https://github.com https://google.com\n
        python health_checker.py --timeout 5 --retries 2 https://myapp.example.com
    """
    results = run_checks(list(urls), timeout=timeout, retries=retries)
    failed = print_report(results)

    if fail_fast and failed:
        sys.exit(1)
    if failed:
        sys.exit(2)


if __name__ == "__main__":
    main()
