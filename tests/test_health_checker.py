"""Tests for scripts/health_checker.py"""
import pytest
import requests
import responses as resp_lib
from scripts.health_checker import check_endpoint, CheckResult


@resp_lib.activate
def test_healthy_endpoint():
    resp_lib.add(resp_lib.GET, "http://example.com", status=200, body="ok")
    result = check_endpoint("http://example.com")
    assert result.healthy is True
    assert result.status_code == 200
    assert result.latency_ms is not None
    assert result.error is None


@resp_lib.activate
def test_redirect_is_healthy():
    resp_lib.add(resp_lib.GET, "http://example.com", status=301, headers={"Location": "http://example.com/new"})
    resp_lib.add(resp_lib.GET, "http://example.com/new", status=200, body="ok")
    result = check_endpoint("http://example.com")
    assert result.healthy is True


@resp_lib.activate
def test_500_is_unhealthy():
    resp_lib.add(resp_lib.GET, "http://example.com", status=500)
    result = check_endpoint("http://example.com", retries=1)
    assert result.healthy is False
    assert result.status_code == 500


@resp_lib.activate
def test_404_is_unhealthy():
    resp_lib.add(resp_lib.GET, "http://example.com/missing", status=404)
    result = check_endpoint("http://example.com/missing", retries=1)
    assert result.healthy is False


@resp_lib.activate
def test_connection_error():
    resp_lib.add(resp_lib.GET, "http://down.example.com", body=requests.exceptions.ConnectionError("refused"))
    result = check_endpoint("http://down.example.com", retries=1)
    assert result.healthy is False
    assert result.error is not None


@resp_lib.activate
def test_retries_on_failure():
    resp_lib.add(resp_lib.GET, "http://flaky.example.com", body=requests.exceptions.ConnectionError("err"))
    resp_lib.add(resp_lib.GET, "http://flaky.example.com", body=requests.exceptions.ConnectionError("err"))
    resp_lib.add(resp_lib.GET, "http://flaky.example.com", status=200, body="ok")
    result = check_endpoint("http://flaky.example.com", retries=3)
    assert result.healthy is True
    assert result.attempts == 3


def test_result_dataclass_defaults():
    r = CheckResult(url="http://test.com")
    assert r.healthy is False
    assert r.status_code is None
    assert r.error is None
    assert r.attempts == 0
