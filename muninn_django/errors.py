#
# Copyright (C) 2018-2022 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from rest_framework.exceptions import APIException


class BadRequest(APIException):
    status_code = 400
