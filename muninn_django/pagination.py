#
# Copyright (C) 2018-2019 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from django.conf import settings
from rest_framework import pagination

class PageNumberPagination(pagination.PageNumberPagination):

    def __new__(cls, *args, **kwargs):
        max_page_size = settings.REST_FRAMEWORK.get('MAX_PAGE_SIZE')
        if max_page_size:
            cls.max_page_size = max_page_size
            cls.page_size_query_param = settings.REST_FRAMEWORK.get('PAGE_SIZE_QUERY_PARAM', 'page_size')
        return super(PageNumberPagination, cls).__new__(cls, *args, **kwargs)
