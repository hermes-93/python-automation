"""Tests for scripts/log_analyzer.py"""
import textwrap
from pathlib import Path

import pytest

from scripts.log_analyzer import analyze, parse_line, LogStats


SAMPLE_LINES = textwrap.dedent("""\
    127.0.0.1 - - [20/Apr/2026:10:00:01 +0000] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0" 0.050
    10.0.0.1 - - [20/Apr/2026:10:00:02 +0000] "POST /api/data HTTP/1.1" 201 256 "-" "curl/7.88" 0.120
    192.168.1.5 - - [20/Apr/2026:10:00:03 +0000] "GET /missing HTTP/1.1" 404 0 "-" "bot/1.0" 0.010
    10.0.0.2 - - [20/Apr/2026:10:00:04 +0000] "GET /slow HTTP/1.1" 200 512 "-" "client/1.0" 2.500
    10.0.0.2 - - [20/Apr/2026:10:00:05 +0000] "GET /error HTTP/1.1" 500 100 "-" "client/1.0" 0.001
    127.0.0.1 - - [20/Apr/2026:10:00:06 +0000] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0" 0.045
""")


@pytest.fixture
def log_file(tmp_path):
    p = tmp_path / "access.log"
    p.write_text(SAMPLE_LINES)
    return p


def test_parse_line_nginx_format():
    line = '127.0.0.1 - - [20/Apr/2026:10:00:01 +0000] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0" 0.050'
    parsed = parse_line(line)
    assert parsed is not None
    assert parsed["ip"] == "127.0.0.1"
    assert parsed["status_int"] == 200
    assert parsed["size_int"] == 1024
    assert parsed["rt_float"] == pytest.approx(0.050)
    assert parsed["method"] == "GET"
    assert parsed["path"] == "/index.html"


def test_parse_line_combined_format():
    line = '10.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326'
    parsed = parse_line(line)
    assert parsed is not None
    assert parsed["status_int"] == 200


def test_parse_line_returns_none_for_garbage():
    assert parse_line("not a log line at all") is None
    assert parse_line("") is None


def test_analyze_total_requests(log_file):
    stats = analyze(log_file, slow_threshold=1.0)
    assert stats.total_requests == 6


def test_analyze_error_count(log_file):
    stats = analyze(log_file, slow_threshold=1.0)
    assert stats.total_errors == 2  # 404 + 500


def test_analyze_status_codes(log_file):
    stats = analyze(log_file, slow_threshold=1.0)
    assert stats.status_codes[200] == 3
    assert stats.status_codes[201] == 1
    assert stats.status_codes[404] == 1
    assert stats.status_codes[500] == 1


def test_analyze_top_ip(log_file):
    stats = analyze(log_file, slow_threshold=1.0)
    top_ip, count = stats.ip_counts.most_common(1)[0]
    assert top_ip in ("127.0.0.1", "10.0.0.2")
    assert count == 2


def test_analyze_slow_requests(log_file):
    stats = analyze(log_file, slow_threshold=1.0)
    assert len(stats.slow_requests) == 1
    rt, path, status = stats.slow_requests[0]
    assert rt == pytest.approx(2.5)
    assert path == "/slow"


def test_analyze_bytes(log_file):
    stats = analyze(log_file, slow_threshold=1.0)
    assert stats.total_bytes == 1024 + 256 + 0 + 512 + 100 + 1024


def test_analyze_no_parse_errors(log_file):
    stats = analyze(log_file, slow_threshold=1.0)
    assert stats.parse_errors == 0


def test_empty_file(tmp_path):
    p = tmp_path / "empty.log"
    p.write_text("")
    stats = analyze(p, slow_threshold=1.0)
    assert stats.total_requests == 0
