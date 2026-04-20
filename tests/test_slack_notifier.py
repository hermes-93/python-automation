"""Tests for scripts/slack_notifier.py"""
import json
import pytest
import responses as resp_lib

from scripts.slack_notifier import build_payload, send, Severity


def test_build_payload_info():
    payload = build_payload("Deploy OK", "v1.0.0 deployed", Severity.INFO)
    assert "attachments" in payload
    att = payload["attachments"][0]
    assert "Deploy OK" in att["title"]
    assert att["color"] == "#36a64f"
    assert "v1.0.0 deployed" in att["text"]


def test_build_payload_critical():
    payload = build_payload("CRITICAL", "DB down", Severity.CRITICAL)
    att = payload["attachments"][0]
    assert att["color"] == "#7c0000"
    assert ":rotating_light:" in att["title"]


def test_build_payload_with_fields():
    fields = {"host": "db01", "env": "prod"}
    payload = build_payload("Alert", "msg", Severity.WARNING, fields=fields)
    att = payload["attachments"][0]
    assert "fields" in att
    field_titles = {f["title"] for f in att["fields"]}
    assert field_titles == {"host", "env"}


def test_build_payload_with_source():
    payload = build_payload("Test", "msg", Severity.INFO, source="my-service")
    att = payload["attachments"][0]
    assert att["footer"] == "my-service"


def test_build_payload_default_source():
    payload = build_payload("Test", "msg", Severity.INFO)
    att = payload["attachments"][0]
    assert att["footer"] == "python-automation"


@resp_lib.activate
def test_send_success():
    resp_lib.add(resp_lib.POST, "https://hooks.slack.com/test", body="ok", status=200)
    payload = build_payload("Test", "msg", Severity.INFO)
    result = send("https://hooks.slack.com/test", payload)
    assert result is True


@resp_lib.activate
def test_send_failure_non_200():
    resp_lib.add(resp_lib.POST, "https://hooks.slack.com/test", status=403, body="Forbidden")
    payload = build_payload("Test", "msg", Severity.INFO)
    result = send("https://hooks.slack.com/test", payload)
    assert result is False


@resp_lib.activate
def test_send_request_body_is_json():
    captured = {}

    def callback(request):
        captured["body"] = json.loads(request.body)
        return 200, {}, "ok"

    resp_lib.add_callback(resp_lib.POST, "https://hooks.slack.com/test", callback=callback)
    payload = build_payload("Title", "Msg", Severity.ERROR)
    send("https://hooks.slack.com/test", payload)
    assert "attachments" in captured["body"]


def test_severity_values():
    assert Severity.INFO.value == "info"
    assert Severity.WARNING.value == "warning"
    assert Severity.ERROR.value == "error"
    assert Severity.CRITICAL.value == "critical"
