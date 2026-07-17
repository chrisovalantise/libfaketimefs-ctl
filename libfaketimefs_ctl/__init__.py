from __future__ import print_function

import boto3
import collections
import datetime
import libfaketimefs_botocore
import os
import time


libfaketimefs_botocore.patch_botocore()

FAKETIME_REALTIME_FILE = os.environ.get('FAKETIME_REALTIME_FILE')
DYNAMODB_ENDPOINT_URL = os.environ.get('LIBFAKETIMEFS_DYNAMODB_ENDPOINT_URL')

Command = collections.namedtuple('Command', 'ref, time1, time2, rate')

dynamodb_kwargs = {}
if DYNAMODB_ENDPOINT_URL:
    dynamodb_kwargs['endpoint_url'] = DYNAMODB_ENDPOINT_URL

dynamodb = boto3.client('dynamodb', **dynamodb_kwargs)


def calculate_fake_time(command, now=None):
    """
    Calculates the fake time from a command and the real time.

    >>> cmd = (0, 0, 10, 2)
    >>> calculate_fake_time(cmd, now=0)
    0
    >>> calculate_fake_time(cmd, now=1)
    2
    >>> calculate_fake_time(cmd, now=5)
    10
    >>> calculate_fake_time(cmd, now=6)
    11.0

    >>> cmd = (0, 10, 20, 2)
    >>> calculate_fake_time(cmd, now=0)
    10
    >>> calculate_fake_time(cmd, now=1)
    12
    >>> calculate_fake_time(cmd, now=5)
    20
    >>> calculate_fake_time(cmd, now=6)
    21.0

    """

    if now is None:
        now = get_time()

    offset = calculate_offset(command, now)

    return now + offset


def calculate_offset(command, now=None):
    """
    Calculates the offset from a command and the real time.

    >>> cmd = (0, 0, 10, 2)
    >>> calculate_offset(cmd, now=0)
    0
    >>> calculate_offset(cmd, now=1)
    1
    >>> calculate_offset(cmd, now=5)
    5
    >>> calculate_offset(cmd, now=6)
    5.0

    >>> cmd = (0, 10, 20, 2)
    >>> calculate_offset(cmd, now=0)
    10
    >>> calculate_offset(cmd, now=1)
    11
    >>> calculate_offset(cmd, now=5)
    15
    >>> calculate_offset(cmd, now=6)
    15.0

    """

    ref, time1, time2, rate = command

    # The starting point of fast forwarding is already in the future
    # if time1 is ahead of when the command was issued (ref time).
    initial_offset = time1 - ref

    # There is a window of time where it will be fast forwarding.
    # Calculate that and also how much real time that would take.
    window_fast = time2 - time1
    window_real = window_fast / float(rate)

    # Get how much real time has passed since the command was issued.
    if now is None:
        now = get_time()
    elapsed = now - ref

    # Discard any time elapsed after the fast forwarding end point,
    # because the offset should stop increasing at that point.
    if elapsed > window_real:
        elapsed = window_real

    # Now calculate the offset. Use the intial offset and the fast
    # forwaded time. Subtract the amount of time it has been fast
    # forwarding because that is already included in the fast amount.
    elapsed_fast = elapsed * rate
    return initial_offset + elapsed_fast - elapsed


def calculate_status(command):
    if calculate_fake_time(command) < command.time2:
        return 'MOVING'
    else:
        return 'IDLE'


def format_command(command):
    return '{} {} {} {}'.format(*command)


def get_time():
    if FAKETIME_REALTIME_FILE:
        with open(FAKETIME_REALTIME_FILE) as open_file:
            return float(open_file.read())
    else:
        return time.time()


def read_command(table):
    response = dynamodb.get_item(
        TableName=table,
        Key={
            'Id': {
                'S': 'command',
            }
        }
    )
    item = response.get('Item')
    if item:
        value = item['Value']['S']
        return Command(*(int(v) for v in value.split(' ')))


def read_commands(table):
    last_command = None
    while True:
        command = read_command(table)
        if command and command != last_command:
            yield command
            last_command = command
        time.sleep(1)


def log_command(command):
    command_string = format_command(command)
    print('[{}] {}'.format(datetime.datetime.now(), command_string))


def send_command(command, table):
    log_command(command)
    dynamodb.put_item(
        TableName=table,
        Item={
            'Id': {
                'S': 'command',
            },
            'Value': {
                'S': format_command(command),
            },
        }
    )


def write_command(command, path):
    log_command(command)
    command_string = format_command(command)
    with open(path, 'w') as open_file:
        open_file.write(command_string)
