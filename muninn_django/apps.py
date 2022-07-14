#
# Copyright (C) 2018-2022 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from django.apps import AppConfig

from . import settings

class MuninnDjangoConfig(AppConfig):
    name = 'muninn_django'
    
    def ready(self):
        settings.patch_defaults()
