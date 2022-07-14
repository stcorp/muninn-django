#
# Copyright (C) 2018-2022 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from datetime import datetime

from django.utils.timezone import make_aware
from django.conf import settings
from django.contrib.gis import forms
from django.utils.encoding import force_str
# from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django_filters import rest_framework as filters

from .parse import parse_datetime


def handle_timezone(value, is_dst=None):
    if settings.USE_TZ and timezone.is_naive(value):
        return make_aware(value, timezone.utc, False)
    elif not settings.USE_TZ and timezone.is_aware(value):
        return timezone.make_naive(value, timezone.utc)
    return value


class NaiveUtcIsoDateTimeField(forms.DateTimeField):
    ISO_8601 = 'iso-8601'
    input_formats = [ISO_8601]

    def strptime(self, value, format):
        value = force_str(value)

        if format == self.ISO_8601:
            parsed = parse_datetime(value)
            if parsed is None:  # Continue with other formats if doesn't match
                raise ValueError
            return handle_timezone(parsed)
        return super(NaiveUtcIsoDateTimeField, self).strptime(value, format)


class NaiveUtcIsoDateTimeFilter(filters.DateTimeFilter):
    field_class = NaiveUtcIsoDateTimeField
