#
# Copyright (C) 2018-2022 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from django.conf import settings
from django.conf.urls import url, include

from .routers import MuninnRouter

router = MuninnRouter()

for archive_name in settings.MUNINN.keys():
    router.register_muninn(archive_name, prefix=archive_name)

urlpatterns = [
    url(r'^', include(router.urls))
]

# CORE API
try:
    import coreapi
    from rest_framework.schemas import get_schema_view
    schema_view = get_schema_view(title='MUNINN API')
    urlpatterns += [ 
        url(r'^schema/$', schema_view),
    ]
except:
    pass
