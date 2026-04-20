#!/usr/bin/env python3
"""AWS resource inventory: EC2, S3, RDS — with rich tabular output and optional JSON export."""

import json
import sys
from datetime import timezone

import boto3
import click
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def get_client(service: str, region: str):
    return boto3.client(service, region_name=region)


def list_ec2(region: str) -> list[dict]:
    ec2 = get_client("ec2", region)
    instances = []
    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for inst in reservation["Instances"]:
                name = next(
                    (t["Value"] for t in inst.get("Tags", []) if t["Key"] == "Name"),
                    "—",
                )
                instances.append({
                    "id": inst["InstanceId"],
                    "name": name,
                    "type": inst["InstanceType"],
                    "state": inst["State"]["Name"],
                    "az": inst["Placement"]["AvailabilityZone"],
                    "private_ip": inst.get("PrivateIpAddress", "—"),
                    "public_ip": inst.get("PublicIpAddress", "—"),
                })
    return instances


def list_s3() -> list[dict]:
    s3 = boto3.client("s3")
    buckets = []
    response = s3.list_buckets()
    for b in response.get("Buckets", []):
        try:
            location = s3.get_bucket_location(Bucket=b["Name"])
            region = location["LocationConstraint"] or "us-east-1"
        except ClientError:
            region = "—"
        buckets.append({
            "name": b["Name"],
            "region": region,
            "created": b["CreationDate"].astimezone(timezone.utc).strftime("%Y-%m-%d"),
        })
    return buckets


def list_rds(region: str) -> list[dict]:
    rds = get_client("rds", region)
    instances = []
    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page["DBInstances"]:
            instances.append({
                "id": db["DBInstanceIdentifier"],
                "engine": f"{db['Engine']} {db['EngineVersion']}",
                "class": db["DBInstanceClass"],
                "status": db["DBInstanceStatus"],
                "az": db["AvailabilityZone"],
                "multi_az": db["MultiAZ"],
                "storage_gb": db["AllocatedStorage"],
            })
    return instances


def print_ec2(instances: list[dict]) -> None:
    if not instances:
        console.print("[dim]  No EC2 instances found.[/dim]")
        return
    t = Table(title=f"EC2 Instances ({len(instances)})", box=box.ROUNDED)
    t.add_column("ID", style="cyan")
    t.add_column("Name")
    t.add_column("Type")
    t.add_column("State")
    t.add_column("AZ")
    t.add_column("Private IP")
    t.add_column("Public IP")
    for i in instances:
        state_color = "green" if i["state"] == "running" else "red"
        t.add_row(
            i["id"], i["name"], i["type"],
            f"[{state_color}]{i['state']}[/{state_color}]",
            i["az"], i["private_ip"], i["public_ip"],
        )
    console.print(t)


def print_s3(buckets: list[dict]) -> None:
    if not buckets:
        console.print("[dim]  No S3 buckets found.[/dim]")
        return
    t = Table(title=f"S3 Buckets ({len(buckets)})", box=box.ROUNDED)
    t.add_column("Name", style="cyan")
    t.add_column("Region")
    t.add_column("Created")
    for b in buckets:
        t.add_row(b["name"], b["region"], b["created"])
    console.print(t)


def print_rds(instances: list[dict]) -> None:
    if not instances:
        console.print("[dim]  No RDS instances found.[/dim]")
        return
    t = Table(title=f"RDS Instances ({len(instances)})", box=box.ROUNDED)
    t.add_column("ID", style="cyan")
    t.add_column("Engine")
    t.add_column("Class")
    t.add_column("Status")
    t.add_column("AZ")
    t.add_column("Multi-AZ", justify="center")
    t.add_column("Storage")
    for db in instances:
        status_color = "green" if db["status"] == "available" else "yellow"
        t.add_row(
            db["id"], db["engine"], db["class"],
            f"[{status_color}]{db['status']}[/{status_color}]",
            db["az"], "✓" if db["multi_az"] else "✗",
            f"{db['storage_gb']} GB",
        )
    console.print(t)


@click.command()
@click.option("--region", "-r", default="us-east-1", show_default=True, envvar="AWS_DEFAULT_REGION")
@click.option("--ec2/--no-ec2", default=True)
@click.option("--s3/--no-s3", default=True)
@click.option("--rds/--no-rds", default=True)
@click.option("--output-json", type=click.Path(), help="Save full inventory to JSON file")
def main(region, ec2, s3, rds, output_json):
    """List AWS resources across EC2, S3, and RDS.

    Requires AWS credentials (env vars or ~/.aws/credentials).

    Examples:\n
        python aws_inventory.py --region eu-west-1\n
        python aws_inventory.py --no-s3 --output-json inventory.json
    """
    inventory = {}

    try:
        if ec2:
            console.rule("[bold]EC2")
            instances = list_ec2(region)
            print_ec2(instances)
            inventory["ec2"] = instances

        if s3:
            console.rule("[bold]S3")
            buckets = list_s3()
            print_s3(buckets)
            inventory["s3"] = buckets

        if rds:
            console.rule("[bold]RDS")
            db_instances = list_rds(region)
            print_rds(db_instances)
            inventory["rds"] = db_instances

    except NoCredentialsError:
        console.print("[red]No AWS credentials found. Set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY or configure ~/.aws/credentials[/red]")
        sys.exit(1)
    except ClientError as e:
        console.print(f"[red]AWS API error: {e}[/red]")
        sys.exit(1)

    if output_json:
        with open(output_json, "w") as f:
            json.dump(inventory, f, indent=2, default=str)
        console.print(f"\n[green]Inventory saved to {output_json}[/green]")


if __name__ == "__main__":
    main()
