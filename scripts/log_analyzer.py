#!/usr/bin/env python3
"""Nginx/application log analyzer — parse access logs, report top IPs, status codes, slow requests."""

import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

NGINX_PATTERN = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) '
    r'"[^"]*" "(?P<ua>[^"]*)"'
    r'(?: (?P<rt>[\d.]+))?'
)

COMBINED_PATTERN = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" '
    r'(?P<status>\d{3}) (?P<size>\d+|-)'
)


@dataclass
class LogStats:
    total_requests: int = 0
    total_errors: int = 0
    total_bytes: int = 0
    status_codes: Counter = field(default_factory=Counter)
    ip_counts: Counter = field(default_factory=Counter)
    path_counts: Counter = field(default_factory=Counter)
    method_counts: Counter = field(default_factory=Counter)
    slow_requests: list = field(default_factory=list)
    parse_errors: int = 0


def parse_line(line: str) -> Optional[dict]:
    for pat in (NGINX_PATTERN, COMBINED_PATTERN):
        m = pat.match(line)
        if m:
            d = m.groupdict()
            d["status_int"] = int(d["status"])
            d["size_int"] = int(d["size"]) if d["size"] != "-" else 0
            d["rt_float"] = float(d["rt"]) if d.get("rt") else None
            return d
    return None


def analyze(path: Path, slow_threshold: float) -> LogStats:
    stats = LogStats()

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parsed = parse_line(line)
            if not parsed:
                stats.parse_errors += 1
                continue

            stats.total_requests += 1
            stats.status_codes[parsed["status_int"]] += 1
            stats.ip_counts[parsed["ip"]] += 1
            stats.path_counts[parsed["path"]] += 1
            stats.method_counts[parsed.get("method", "?")] += 1
            stats.total_bytes += parsed["size_int"]

            if parsed["status_int"] >= 400:
                stats.total_errors += 1

            if parsed.get("rt_float") and parsed["rt_float"] >= slow_threshold:
                stats.slow_requests.append((parsed["rt_float"], parsed.get("path", "?"), parsed["status_int"]))

    stats.slow_requests.sort(reverse=True)
    return stats


def _status_color(code: int) -> str:
    if code < 300:
        return "green"
    if code < 400:
        return "yellow"
    return "red"


def print_report(stats: LogStats, top_n: int, slow_threshold: float) -> None:
    error_rate = (stats.total_errors / stats.total_requests * 100) if stats.total_requests else 0
    size_mb = stats.total_bytes / 1024 / 1024

    summary = (
        f"[bold]Total requests:[/bold] {stats.total_requests:,}  "
        f"[bold]Errors:[/bold] [{'red' if error_rate > 5 else 'green'}]{stats.total_errors:,} ({error_rate:.1f}%)[/]  "
        f"[bold]Traffic:[/bold] {size_mb:.1f} MB  "
        f"[bold]Parse errors:[/bold] {stats.parse_errors}"
    )
    console.print(Panel(summary, title="Summary"))

    # Status codes
    t = Table(title="Status Codes", box=box.SIMPLE)
    t.add_column("Code", style="cyan", width=6)
    t.add_column("Count", justify="right")
    t.add_column("Pct", justify="right")
    for code, cnt in sorted(stats.status_codes.items()):
        pct = cnt / stats.total_requests * 100
        color = _status_color(code)
        t.add_row(f"[{color}]{code}[/{color}]", f"{cnt:,}", f"{pct:.1f}%")
    console.print(t)

    # HTTP methods
    t2 = Table(title="HTTP Methods", box=box.SIMPLE)
    t2.add_column("Method", style="cyan")
    t2.add_column("Count", justify="right")
    for method, cnt in stats.method_counts.most_common():
        t2.add_row(method, f"{cnt:,}")
    console.print(t2)

    # Top IPs
    t3 = Table(title=f"Top {top_n} IPs", box=box.SIMPLE)
    t3.add_column("IP", style="cyan")
    t3.add_column("Requests", justify="right")
    for ip, cnt in stats.ip_counts.most_common(top_n):
        t3.add_row(ip, f"{cnt:,}")
    console.print(t3)

    # Top paths
    t4 = Table(title=f"Top {top_n} Paths", box=box.SIMPLE)
    t4.add_column("Path", style="cyan")
    t4.add_column("Requests", justify="right")
    for path, cnt in stats.path_counts.most_common(top_n):
        t4.add_row(path[:80], f"{cnt:,}")
    console.print(t4)

    # Slow requests
    if stats.slow_requests:
        t5 = Table(title=f"Slow Requests (>{slow_threshold}s)", box=box.SIMPLE)
        t5.add_column("Response Time", style="red", justify="right")
        t5.add_column("Path")
        t5.add_column("Status", justify="center")
        for rt, path, status in stats.slow_requests[:top_n]:
            t5.add_row(f"{rt:.3f}s", path[:80], str(status))
        console.print(t5)


@click.command()
@click.argument("logfile", type=click.Path(exists=True, path_type=Path))
@click.option("--top", "-n", default=10, show_default=True, help="Number of top entries to show")
@click.option("--slow-threshold", default=1.0, show_default=True, help="Slow request threshold in seconds")
def main(logfile: Path, top: int, slow_threshold: float) -> None:
    """Analyze Nginx/Apache access logs.

    Supports combined log format with optional $request_time field.

    Examples:\n
        python log_analyzer.py /var/log/nginx/access.log\n
        python log_analyzer.py access.log --top 20 --slow-threshold 2.0
    """
    console.print(f"Analyzing [cyan]{logfile}[/cyan]...\n")
    stats = analyze(logfile, slow_threshold)

    if stats.total_requests == 0:
        console.print("[red]No parseable log lines found.[/red]")
        sys.exit(1)

    print_report(stats, top_n=top, slow_threshold=slow_threshold)


if __name__ == "__main__":
    main()
