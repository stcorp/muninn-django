#
# Copyright (C) 2018 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from rest_framework.permissions import BasePermission, SAFE_METHODS


class ReadOnly(BasePermission):
    """
    A read-only request.
    """
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS

