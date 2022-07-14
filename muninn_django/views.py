#
# Copyright (C) 2018-2022 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

import logging
from copy import copy

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404

from .serializers import ProductSerializerFactory
from .errors import BadRequest
try:
    from .filters import ProductFilterFactory
except:
    ProductFilterFactory = None


logger = logging.getLogger(__name__)


class ProductViewSetFactory(object):
    @classmethod
    def get(cls, archive, queryset):
        body = {}
        body['__module__'] = '%s.%s' % (__name__, archive)
        body['muninn_archive'] = archive
        body['queryset'] = queryset
        if ProductFilterFactory:
            body['filter_class'] = ProductFilterFactory.get(archive, queryset.model)

        newclass = type('ProductViewSet', (ProductViewSet, ), body)
        return newclass


class ProductViewSet(viewsets.ModelViewSet):
    '''
    added query parameters:
        - mode: for GET requests, use serializer defined in settings
    '''
    muninn_archive = None
    filter_class = None

    def get_queryset(self):
        queryset = self.queryset

        # validate query params, raise if unsupported param used
        # muninn-django
        valid_params = ['mode', 'format', 'ordering', ]
        # pagination
        if self.pagination_class:
            for name in dir(self.pagination_class):
                if name.endswith('_query_param'):
                    valid_params.append(getattr(self.paginator, name))
        # filters
        if self.filter_class:
            valid_params += list(self.filter_class.get_filters().keys())
        for name in self.request.GET.keys():
            if name not in valid_params:
                raise BadRequest('Invalid query param: "%s"' % name)

        # django query optimization
        meta = self.get_serializer_class().Meta
        queryset = queryset.select_related(*meta.select_related)
        if meta.prefetch_related:
            queryset = queryset.prefetch_related(*meta.prefetch_related)

        return queryset

    def get_object(self):
        if 'product_type' in self.kwargs and 'product_name' in self.kwargs:
            # use product_type/product_name to lookup object
            queryset = self.filter_queryset(self.get_queryset())
            filter_kwargs = {
                'product_type': self.kwargs['product_type'],
                'product_name': self.kwargs['product_name'],
            }
            obj = get_object_or_404(queryset, **filter_kwargs)
            self.check_object_permissions(self.request, obj)
            return obj
        else:
            # use the primary key to lookup object
            return super(ProductViewSet, self).get_object()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            # for GET, the serializer depends on the `mode` parameter
            mode = self.request.query_params.get('mode', 'default')
            try:
                serializer_class = ProductSerializerFactory.get(self.muninn_archive, mode=mode)
            except Exception as e:
                logger.exception(e)
                raise BadRequest('Invalid value for query param "%s": "%s"' % ('mode', mode))
        else:
            # other methods always use the "Complete" serializer (so that custom namespaces are properly handled)
            serializer_class = ProductSerializerFactory.get(self.muninn_archive, base_class_path='muninn_django.serializers.ProductCompleteSerializer')
        return serializer_class

    def _get_partial_validated_data(self, request, item):
        serializer = self.get_serializer(self.get_object(), data={item: request.data}, partial=True)
        serializer.is_valid(raise_exception=True)
        result = serializer.validated_data[item]
        return result

    @action(methods=['post'], detail=True)
    def tag(self, request, pk=None):
        '''Add tags'''
        instance = self.get_object()
        tags_data = self._get_partial_validated_data(request, 'tags')
        existing = [tag.tag for tag in instance.tags.all()]
        for tag in tags_data:
            if tag not in existing:
                instance.tags.create(tag=tag)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def untag(self, request, pk=None):
        '''Remove tags'''
        instance = self.get_object()
        tags_data = self._get_partial_validated_data(request, 'tags')
        for tag in instance.tags.all():
            if tag.tag in tags_data:
                tag.delete()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def link(self, request, pk=None):
        '''Add source products'''
        instance = self.get_object()
        source_products = self._get_partial_validated_data(request, 'source_products')
        existing = list(instance.source_products.all())
        for source in source_products:
            if source not in existing:
                instance.source_links.create(source=source)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(methods=['post'], detail=True)
    def unlink(self, request, pk=None):
        '''Remove source products'''
        instance = self.get_object()
        source_products = self._get_partial_validated_data(request, 'source_products')
        for link in instance.source_links.all():
            if link.source in source_products:
                link.delete()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
