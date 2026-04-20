# python-automation

DevOps automation scripts in Python — health checking, log analysis, Docker cleanup, Slack notifications, and AWS inventory. Each script is standalone and production-ready.

[![CI](https://github.com/hermes-93/python-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/hermes-93/python-automation/actions/workflows/ci.yml)
[![Security](https://github.com/hermes-93/python-automation/actions/workflows/security.yml/badge.svg)](https://github.com/hermes-93/python-automation/actions/workflows/security.yml)

## Scripts

| Script | Purpose |
|---|---|
| `health_checker.py` | HTTP endpoint health check with retries and rich table output |
| `log_analyzer.py` | Parse Nginx/Apache access logs — top IPs, paths, slow requests |
| `docker_cleanup.py` | Remove stopped containers, dangling images, unused volumes/networks |
| `slack_notifier.py` | Send structured alerts to Slack via incoming webhook |
| `aws_inventory.py` | List EC2, S3, RDS resources with tabular output and JSON export |

## Quick Start

```bash
git clone https://github.com/hermes-93/python-automation.git
cd python-automation
pip install -r requirements.txt
```

## Usage

### Health Checker

```bash
python scripts/health_checker.py https://github.com https://google.com

# With custom timeout and retries
python scripts/health_checker.py --timeout 5 --retries 2 https://myapp.example.com

# Exit 1 on any failure (for CI/alerting)
python scripts/health_checker.py --fail-fast https://api.example.com/health
```

Output:
```
╭────────────────────────────────────────────────────────────────╮
│ URL              │ Status │ HTTP │ Latency │ Attempts │ Error   │
├────────────────────────────────────────────────────────────────┤
│ https://github.. │   UP   │  200 │ 234.5ms │    1     │         │
│ https://google.. │   UP   │  200 │ 112.3ms │    1     │         │
╰────────────────────────────────────────────────────────────────╯
Summary: 2/2 healthy  ✓ All OK
```

### Log Analyzer

```bash
python scripts/log_analyzer.py /var/log/nginx/access.log

# Show top 20 entries, flag slow requests over 2s
python scripts/log_analyzer.py access.log --top 20 --slow-threshold 2.0

# Analyze sample bundled log
python scripts/log_analyzer.py examples/sample.log
```

Output includes: summary panel, status code breakdown, HTTP methods, top IPs, top paths, slow requests.

### Docker Cleanup

```bash
# Dry run — see what would be removed
python scripts/docker_cleanup.py --dry-run

# Full cleanup (containers + images + volumes + networks)
python scripts/docker_cleanup.py

# Only clean containers and images
python scripts/docker_cleanup.py --no-volumes --no-networks
```

### Slack Notifier

```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK

# Info notification
python scripts/slack_notifier.py "Deploy Complete" "v2.1.0 deployed to prod" -s info

# Critical alert with extra fields
python scripts/slack_notifier.py "Database Down" "Postgres unreachable" \
  -s critical \
  -f host=db01.prod \
  -f env=production \
  --source my-service
```

Severity levels: `info`, `warning`, `error`, `critical`

### AWS Inventory

```bash
# Requires AWS credentials (env vars or ~/.aws/credentials)

# List all resources in us-east-1
python scripts/aws_inventory.py

# Different region, save to JSON
python scripts/aws_inventory.py --region eu-west-1 --output-json inventory.json

# Only EC2 and RDS, skip S3
python scripts/aws_inventory.py --no-s3
```

## Running Tests

```bash
pip install -r requirements-dev.txt
make test

# Or directly
python -m pytest tests/ -v --cov=scripts --cov-report=term-missing
```

Test coverage: ~35 tests across health_checker, log_analyzer, and slack_notifier.

## CI/CD

```
push / PR
   │
   ├── lint          → flake8 (max 120 chars)
   ├── test (3.11)   → pytest + coverage
   ├── test (3.12)   → pytest + coverage + codecov
   ├── integration-health → real HTTP checks (github.com, google.com)
   └── integration-log    → analyze examples/sample.log
```

Security (weekly + on push to main):
- **Bandit** — static analysis for Python security issues
- **Safety** — dependency vulnerability scan
- **Semgrep** — secrets and Python pattern scan

## Project Structure

```
python-automation/
├── scripts/
│   ├── health_checker.py   # HTTP health check with retries
│   ├── log_analyzer.py     # Nginx log parsing and reporting
│   ├── docker_cleanup.py   # Docker resource cleanup
│   ├── slack_notifier.py   # Slack webhook notifications
│   └── aws_inventory.py    # AWS EC2/S3/RDS inventory
├── tests/
│   ├── test_health_checker.py   # 7 tests
│   ├── test_log_analyzer.py     # 11 tests
│   └── test_slack_notifier.py   # 9 tests
├── examples/
│   └── sample.log          # Sample Nginx access log for demo
├── requirements.txt
├── requirements-dev.txt
├── Makefile
└── .github/workflows/
    ├── ci.yml              # lint + test matrix + integration
    └── security.yml        # bandit + safety + semgrep
```

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP requests (health_checker, slack_notifier) |
| `boto3` | AWS SDK (aws_inventory) |
| `docker` | Docker SDK for Python (docker_cleanup) |
| `rich` | Beautiful terminal output (all scripts) |
| `click` | CLI argument parsing (all scripts) |
