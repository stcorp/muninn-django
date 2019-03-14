#
# Copyright (C) 2018-2019 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from copy import copy

from django.conf import settings


DEFAULT_SERIALIZERS = {
    'default': 'muninn_django.serializers.ProductCoreSerializer',
    'extended': 'muninn_django.serializers.ProductCompleteSerializer',
}

def patch_defaults():
    muninn_settings = getattr(settings, 'MUNINN')
    for name, archive_settings in muninn_settings.items():
        if 'serializers' not in archive_settings:
            archive_settings['serializers'] = copy(DEFAULT_SERIALIZERS)
