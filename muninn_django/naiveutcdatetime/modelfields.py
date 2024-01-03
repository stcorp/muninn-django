#
# Copyright (C) 2018-2022 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

import datetime

from django.db import models
from django.core import exceptions
from django.utils.translation import gettext_lazy as _

from .parse import parse_datetime


class NaiveDateTimeField(models.DateTimeField):
    # Inheriting from DateTimeField makes django rest framework into using the correct data types
    default_error_messages = {
        'invalid': _("'%(value)s' value has an invalid format. It must be in "
                     "YYYY-MM-DD HH:MM:ss[.uuuuuu] format."),
        'invalid_date': _("'%(value)s' value has the correct format "
                          "(YYYY-MM-DD) but it is an invalid date."),
        'invalid_datetime': _("'%(value)s' value has the correct format "
                              "(YYYY-MM-DD HH:MM:ss[.uuuuuu]) "
                              "but it is an invalid date/time."),
    }
    description = _("Date (with time, without timezone)")

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)

        try:
            parsed = parse_datetime(value)
            if parsed is not None:
                return parsed
        except ValueError:
            raise exceptions.ValidationError(
                self.error_messages['invalid_datetime'],
                code='invalid_datetime',
                params={'value': value},
            )

        raise exceptions.ValidationError(
            self.error_messages['invalid'],
            code='invalid',
            params={'value': value},
        )

    def pre_save(self, model_instance, add):
        if self.auto_now or (self.auto_now_add and add):
            value = datetime.datetime.now()
            setattr(model_instance, self.attname, value)
            return value
        else:
            return super(NaiveDateTimeField, self).pre_save(model_instance, add)

    def get_prep_value(self, value):
        # Bypass DateTimeField for this one.
        # Calling super().get_prep_value would raise warnings about using naive datetimes if USE_TZ=True
        value = models.Field.get_prep_value(self, value)
        return self.to_python(value)
