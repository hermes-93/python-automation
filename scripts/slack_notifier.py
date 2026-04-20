#!/usr/bin/env python3
"""Send structured alerts and notifications to Slack via incoming webhooks."""

import json
import os
import sys
from enum import Enum

import click
import requests
from rich.console import Console

console = Console()


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


SEVERITY_CONFIG = {
    Severity.INFO: {"color": "#36a64f", "emoji": ":information_source:"},
    Severity.WARNING: {"color": "#ffa500", "emoji": ":warning:"},
    Severity.ERROR: {"color": "#e01e5a", "emoji": ":x:"},
    Severity.CRITICAL: {"color": "#7c0000", "emoji": ":rotating_light:"},
}


def build_payload(
    title: str,
    message: str,
    severity: Severity,
    source: str = "",
    fields: dict | None = None,
) -> dict:
    cfg = SEVERITY_CONFIG[severity]
    attachment = {
        "color": cfg["color"],
        "title": f"{cfg['emoji']} {title}",
        "text": message,
        "footer": source or "python-automation",
        "ts": __import__("time").time(),
    }
    if fields:
        attachment["fields"] = [
            {"title": k, "value": v, "short": True}
            for k, v in fields.items()
        ]
    return {"attachments": [attachment]}


def send(webhook_url: str, payload: dict, timeout: int = 10) -> bool:
    try:
        resp = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        if resp.status_code == 200 and resp.text == "ok":
            return True
        console.print(f"[red]Slack API error: {resp.status_code} {resp.text}[/red]")
        return False
    except requests.RequestException as e:
        console.print(f"[red]Request failed: {e}[/red]")
        return False


@click.command()
@click.argument("title")
@click.argument("message")
@click.option(
    "--severity", "-s",
    type=click.Choice([s.value for s in Severity]),
    default=Severity.INFO.value,
    show_default=True,
)
@click.option("--source", default="", help="Source system name shown in footer")
@click.option("--field", "-f", multiple=True, metavar="KEY=VALUE", help="Extra fields (repeatable)")
@click.option(
    "--webhook-url",
    envvar="SLACK_WEBHOOK_URL",
    required=True,
    help="Slack incoming webhook URL (or set SLACK_WEBHOOK_URL env var)",
)
def main(title, message, severity, source, field, webhook_url):
    """Send a notification to Slack.

    Examples:\n
        python slack_notifier.py "Deploy Complete" "v2.1.0 deployed to prod" -s info\n
        python slack_notifier.py "DB Down" "Postgres unreachable" -s critical -f host=db01 -f env=prod\n
        SLACK_WEBHOOK_URL=https://... python slack_notifier.py "Test" "Hello"
    """
    fields = {}
    for f in field:
        if "=" in f:
            k, v = f.split("=", 1)
            fields[k] = v
        else:
            console.print(f"[yellow]Ignoring malformed field: {f!r} (expected KEY=VALUE)[/yellow]")

    payload = build_payload(
        title=title,
        message=message,
        severity=Severity(severity),
        source=source,
        fields=fields or None,
    )

    console.print(f"Sending [bold]{severity}[/bold] alert to Slack...")
    ok = send(webhook_url, payload)

    if ok:
        console.print("[green]Sent successfully.[/green]")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
