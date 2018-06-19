#
# Copyright (C) 2018 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

import logging
from copy import copy

from django.conf import settings
from django.utils.module_loading import import_string
from django.db.models import fields as django_fields
from django.db.models import Lookup
from django.core.exceptions import FieldDoesNotExist
from rest_framework.filters import OrderingFilter
from django_filters import rest_framework as filters
from django.contrib.gis.db.models import GeometryField
from rest_framework_gis.filters import GeometryFilter

from muninn_django.naiveutcdatetime.modelfields import NaiveDateTimeField
from muninn_django.naiveutcdatetime.forms import NaiveUtcIsoDateTimeFilter


logger = logging.getLogger(__name__)


@django_fields.Field.register_lookup
class NotEqual(Lookup):
    '''django "__ne" custom lookup'''
    lookup_name = 'ne'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return '%s <> %s' % (lhs, rhs), params


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class ProductFilter(filters.FilterSet):

    # `in` implicitly supports `exact` :)
    # `distinct=True` is required to remove duplicates that the underlying inner join produces
    tag = CharInFilter(name='tags__tag', lookup_expr='in', distinct=True)

    source_product = filters.CharFilter(name='source_products__uuid', lookup_expr='exact')
    derived_product = filters.CharFilter(name='derived_products__uuid', lookup_expr='exact')

    class Meta(object):
        model = None  # to be overriden
        filter_overrides = {
            NaiveDateTimeField: {
                'filter_class': NaiveUtcIsoDateTimeFilter,
            },
            GeometryField: {
                'filter_class': GeometryFilter,
            }
        }


def _get_filters(model_class, preffix=None, disabled_lookups=None):
    result = {}
    for field in model_class._meta.fields:
        if isinstance(field, GeometryField):
            # disable lookups on geography fields, because
            # 1. django sqlite backend will match null fields with everything (fixed in django 2.0)
            #   see https://code.djangoproject.com/ticket/28380
            # 2. django postgres backend does not support basic functions when geography=True, e.g. ST_Contains
            #   see https://docs.djangoproject.com/en/1.11/ref/contrib/gis/model-api/#geography-type
            continue
        filter_def = list(type(field).get_lookups().keys())
        if filter_def and field.name != '_core':
            name = '%s__%s' % (preffix, field.name) if preffix else field.name
            filter_def = [x for x in filter_def if not x in disabled_lookups]
            result[name] = filter_def

    return result


class ProductFilterFactory(object):
    @classmethod
    def get(cls, archive, model_class):
        name = 'ProductFilter'

        disabled_lookups = settings.MUNINN[archive].get('disabled_lookups', [])
        meta_fields = _get_filters(model_class, disabled_lookups=disabled_lookups)
        for ns, ns_class_path in settings.MUNINN[archive]['models'].items():
            if ns != 'core':
                ns_class = import_string(ns_class_path)
                meta_fields.update(_get_filters(ns_class, preffix=ns, disabled_lookups=disabled_lookups))

        meta_body = {}
        meta_body['__module__'] = '%s.%s.%s' % (__name__, archive, name)
        meta_body['model'] = model_class
        meta_body['fields'] = meta_fields
        meta_class = type('Meta', (ProductFilter.Meta, ), meta_body)

        body = {}
        body['__module__'] = '%s.%s' % (__name__, archive)
        body['Meta'] = meta_class
        newclass = type(name, (ProductFilter, ), body)

        return newclass


class RelatedOrderingFilter(OrderingFilter):
    """

    See: https://github.com/encode/django-rest-framework/issues/1005

    Extends OrderingFilter to support ordering by fields in related models
    using the Django ORM __ notation
    """
    def is_valid_field(self, model, field):
        """
        Return true if the field exists within the model (or in the related
        model specified using the Django ORM __ notation)
        """
        components = field.split('__', 1)
        try:
            field = model._meta.get_field(components[0])

            if isinstance(field, django_fields.reverse_related.OneToOneRel):
                return self.is_valid_field(field.related_model, components[1])

            # reverse relation
            if isinstance(field, django_fields.reverse_related.ForeignObjectRel):
                return self.is_valid_field(field.model, components[1])

            # foreign key
            if field.remote_field and len(components) == 2:
                return self.is_valid_field(field.related_model, components[1])
            return True
        except FieldDoesNotExist:
            return False

    def remove_invalid_fields(self, queryset, fields, ordering, view):
        return [term for term in fields
                if self.is_valid_field(queryset.model, term.lstrip('-'))]
