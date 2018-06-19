#
# Copyright (C) 2018 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.routers import DefaultRouter, Route

from . import views


class MuninnRouter(DefaultRouter):
    def __init__(self, muninn_archive=None, *args, **kwargs):
        '''
        `muninn_archive` specifies an archive (defined in the settings) that will be registered automatically.
        Use as a shorthand for use cases whre there is only one archive to be served under a URL path.
        '''
        super(MuninnRouter, self).__init__(*args, **kwargs)
        # Add detail route that understands `product_type/product_name`
        route_kwargs = {
            'url': u'^{prefix}/(?P<product_type>[^/.]+)/(?P<product_name>[^/.]+){trailing_slash}$',
            'mapping': {
                u'put': u'update',
                u'delete': u'destroy',
                u'patch': u'partial_update',
                u'get': u'retrieve'},
            'name': u'{basename}-detail',
            'detail': True,
            'initkwargs': {u'suffix': u'Instance'}
        }
        try:
            product_name_route = Route(**route_kwargs)
        except TypeError:
            # DRF below 1.8:
            del route_kwargs['detail']
            product_name_route = Route(**route_kwargs)
        self.routes.append(product_name_route)

        if muninn_archive:
            self.register_muninn(muninn_archive, prefix='')

    def register_muninn(self, archive, prefix=''):
        '''
        Register a router for a muninn archive according to the settings.
        '''
        config = settings.MUNINN[archive]
        view_class = import_string(config['view']) if 'view' in config else None
        if not view_class:
            model_class = import_string(config['models']['core'])
            queryset = model_class.objects.all()
            view_class = views.ProductViewSetFactory.get(archive, queryset, )
        self.register(prefix, view_class, base_name=archive)
