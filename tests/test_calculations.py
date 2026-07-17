import sys
import time
import types

import pytest

import libfaketimefs_ctl
from libfaketimefs_ctl import (
    Command,
    calculate_fake_time,
    calculate_offset,
    calculate_status,
    format_command,
)
from libfaketimefs_ctl.cli import parse_timestamp, parse_timestamp_and_rate


@pytest.mark.parametrize("now,expected", [(0, 0), (1, 2), (5, 10), (6, 11.0)])
def test_calculate_fake_time_ramp(now, expected):
    assert calculate_fake_time((0, 0, 10, 2), now=now) == expected


@pytest.mark.parametrize("now,expected", [(0, 0), (1, 1), (5, 5), (6, 5.0)])
def test_calculate_offset_ramp(now, expected):
    assert calculate_offset((0, 0, 10, 2), now=now) == expected


def test_calculate_status_moving_then_idle():
    # calculate_status compares against the real current time.
    now = int(time.time())
    moving = Command(ref=now, time1=now, time2=now + 10_000, rate=2)
    idle = Command(ref=now - 10_000, time1=now - 10_000, time2=now - 5_000, rate=1)
    assert calculate_status(moving) == 'MOVING'
    assert calculate_status(idle) == 'IDLE'


def test_format_command():
    assert format_command(Command(1, 2, 3, 4)) == '1 2 3 4'


def test_parse_timestamp_absolute():
    assert parse_timestamp('2018-03-27') == pytest.approx(
        parse_timestamp('2018-03-27'), abs=0
    )
    assert isinstance(parse_timestamp('2018-03-27'), int)


def test_parse_timestamp_and_rate():
    ts, rate = parse_timestamp_and_rate('2018-03-27 30')
    assert isinstance(ts, int)
    assert rate == 30


def test_parse_timestamp_and_rate_rejects_low_rate():
    with pytest.raises(ValueError):
        parse_timestamp_and_rate('2018-03-27 0')


def test_dynamodb_client_defaults_to_aws(monkeypatch):
    created = {}

    def fake_client(service, **kwargs):
        created['service'] = service
        created['kwargs'] = kwargs
        return object()

    monkeypatch.delenv('LIBFAKETIMEFS_DYNAMODB_ENDPOINT_URL', raising=False)
    monkeypatch.setattr(libfaketimefs_ctl, '_dynamodb', None)
    monkeypatch.setitem(
        sys.modules,
        'boto3',
        types.SimpleNamespace(client=fake_client),
    )
    monkeypatch.setitem(
        sys.modules,
        'libfaketimefs_botocore',
        types.SimpleNamespace(patch_botocore=lambda: None),
    )

    libfaketimefs_ctl.get_dynamodb()

    assert created == {'service': 'dynamodb', 'kwargs': {}}


def test_dynamodb_client_uses_configured_local_endpoint(monkeypatch):
    created = {}

    def fake_client(service, **kwargs):
        created['service'] = service
        created['kwargs'] = kwargs
        return object()

    monkeypatch.setenv(
        'LIBFAKETIMEFS_DYNAMODB_ENDPOINT_URL',
        'http://localhost:8000',
    )
    monkeypatch.setattr(libfaketimefs_ctl, '_dynamodb', None)
    monkeypatch.setitem(
        sys.modules,
        'boto3',
        types.SimpleNamespace(client=fake_client),
    )
    monkeypatch.setitem(
        sys.modules,
        'libfaketimefs_botocore',
        types.SimpleNamespace(patch_botocore=lambda: None),
    )

    libfaketimefs_ctl.get_dynamodb()

    assert created == {
        'service': 'dynamodb',
        'kwargs': {'endpoint_url': 'http://localhost:8000'},
    }
