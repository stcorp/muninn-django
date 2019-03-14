#
# Copyright (C) 2018-2019 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from rest_framework import fields

from . import modelfields
from .parse import NAIVE_DATETIME_FORMATS


class NaiveDateTimeField(fields.DateTimeField):
    timezone = None
    input_formats = NAIVE_DATETIME_FORMATS


class NaiveDateTimeSerializerMixin(object):
    def __init__(self, *args, **kwargs):
        super(NaiveDateTimeSerializerMixin, self).__init__(*args, **kwargs)
        self.serializer_field_mapping[modelfields.NaiveDateTimeField] = NaiveDateTimeField
