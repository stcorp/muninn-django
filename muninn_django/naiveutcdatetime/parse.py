#
# Copyright (C) 2018-2020 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

import datetime

NAIVE_DATE_FORMATS = [
    '%Y-%m-%d',
    '%Y%m%d',
]

NAIVE_DATETIME_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S',
    '%Y%m%dT%H%M%S.%f', '%Y%m%dT%H%M%S',
] + NAIVE_DATE_FORMATS


def parse_date(value):
    result = None
    for fmt in NAIVE_DATE_FORMATS:
        try:
            result = datetime.datetime.strptime(value, fmt).date()
        except:
            continue
        if result:
            break
    return result


def parse_datetime(value):
    result = None
    for fmt in NAIVE_DATETIME_FORMATS:
        try:
            result = datetime.datetime.strptime(value, fmt)
        except:
            continue
        if result:
            break
    return result
