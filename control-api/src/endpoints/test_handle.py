# test_mqtt_stream_handler.py
import json
from mqtt_stream import handle_message


def test_staff_access_on():
    payload = json.dumps({
        "command": "staff_access", "room_no": "27.03.05",
        "status": "on", "sent_at": "2026-07-06T04:58:30Z",
    })
    event = handle_message("staff_access/on/27.03.05", payload)
    assert event.kind == "staff_access"
    assert event.data == {"room_no": "27.03.05", "status": "on"}


def test_update_schedule_triggers_refresh_on_replace():
    payload = json.dumps({"status": "replace", "update": "2026-07-06"})
    event = handle_message("update_schedule", payload)
    assert event.data["should_refresh"] is True


def test_update_schedule_no_refresh_on_unknown_status():
    payload = json.dumps({"status": "noop", "update": "2026-07-06"})
    event = handle_message("update_schedule", payload)
    assert event.data["should_refresh"] is False


def test_mq_update_schedule_cancel_triggers_refresh():
    payload = json.dumps({"status": "cancel_schedule", "date": "2026-07-06"})
    event = handle_message("mq_update_schedule", payload)
    assert event.data["should_refresh"] is True


def test_schedule_item_from_array_payload():
    payload = json.dumps([{"id": 1, "coursecode": "CS101"}])
    event = handle_message("send_message/qr", payload)
    assert event.kind == "schedule_item"
    assert event.data["item"]["coursecode"] == "CS101"


def test_invalid_json_returns_error_event():
    event = handle_message("staff_access/on/27.03.05", "{not json")
    assert event.kind == "error"
    assert "Invalid JSON" in event.data["message"]


def test_unrecognized_topic_falls_through_to_unknown():
    payload = json.dumps({"foo": "bar"})
    event = handle_message("some/other/topic", payload)
    assert event.kind == "unknown"