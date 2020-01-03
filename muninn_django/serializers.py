#
# Copyright (C) 2018-2020 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from datetime import datetime

from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework import serializers

from muninn_django.naiveutcdatetime.serializers import NaiveDateTimeSerializerMixin
from .errors import BadRequest


class NamespaceSerializerFactory(object):
    # factory cache
    _dynamic_namespace_serializers = {}

    @classmethod
    def get(cls, archive, namespace):
        model_class = import_string(settings.MUNINN[archive]['models'][namespace])
        name = model_class._meta.object_name + 'NamespaceSerializer'
        disabled_fields = tuple(settings.MUNINN[archive].get('disabled_fields', {}).get(namespace, ()))

        # check factory cache
        cache_key = '%s.%s.%s' % (__name__, archive, name)
        if cache_key in cls._dynamic_namespace_serializers:
            return cls._dynamic_namespace_serializers[cache_key]

        # Meta class
        class NamespaceMeta:
            model = model_class
            exclude = ('_core', ) + disabled_fields

        # bake class
        body = {}
        body['Meta'] = NamespaceMeta
        body['__module__'] = '%s.%s' % (__name__, archive)
        newclass = type(name, (NaiveDateTimeSerializerMixin, serializers.ModelSerializer, ), body)

        # keep class in factory cache
        cls._dynamic_namespace_serializers[cache_key] = newclass
        return newclass


class ProductSerializerFactory(object):
    # factory cache
    _dynamic_product_serializers = {}

    @classmethod
    def get(cls, archive, base_class_path=None, mode='default'):

        if not base_class_path:
            base_class_path = settings.MUNINN[archive]['serializers'][mode]
        base_class = import_string(base_class_path)
        model_class = import_string(settings.MUNINN[archive]['models']['core'])
        name = base_class_path[base_class_path.rfind('.')+1:]
        disabled_fields = tuple(settings.MUNINN[archive].get('disabled_fields', {}).get('core', ()))
        wants_tags = 'tags' in base_class._declared_fields.keys()
        wants_source_products = not (hasattr(base_class.Meta, 'exclude') and 'source_products' in base_class.Meta.exclude)

        # check factory cache
        cache_key = '%s.%s.%s' % (__name__, archive, name)
        if cache_key in cls._dynamic_product_serializers:
            return cls._dynamic_product_serializers[cache_key]

        # build list of custom namespaces
        muninn_namespaces = getattr(base_class.Meta, 'muninn_namespaces', None)
        if not muninn_namespaces:
            muninn_namespaces = settings.MUNINN[archive]['models'].keys()
        muninn_namespaces = list(muninn_namespaces)
        if 'core' in muninn_namespaces:
            muninn_namespaces.remove('core')

        # define query optimization
        prefetch_related = []
        if wants_tags:
            prefetch_related.append('tags')
        if wants_source_products:
            prefetch_related.append('source_products')

        # bake Meta class
        meta_body = {}
        meta_body['__module__'] = '%s.%s.%s' % (__name__, archive, name)
        meta_body['model'] = model_class
        meta_body['read_only_fields'] = ('metadata_date', )
        meta_body['exclude'] = getattr(base_class.Meta, 'exclude', ()) + disabled_fields
        meta_body['muninn_namespaces'] = muninn_namespaces
        meta_body['select_related'] = muninn_namespaces
        meta_body['prefetch_related'] = prefetch_related
        meta_class = type('Meta', (base_class.Meta, ), meta_body)

        # bake class
        body = {}
        body['__module__'] = '%s.%s' % (__name__, archive)
        body['Meta'] = meta_class
        if wants_source_products:
            # This allows our many-to-many relationship to become writable, see https://stackoverflow.com/questions/48624793/
            body['source_products'] = serializers.PrimaryKeyRelatedField(
                many=True,
                required=False,
                queryset=model_class.objects.all(),
                # style={'base_template': 'input.html'}, # avoids loading all products in the Browsable API
                style={'base_template': 'list_field.html'}, # disable field in the Browsable API
            )
        # custom namespaces
        for ns in muninn_namespaces:
            body[ns] = NamespaceSerializerFactory.get(archive, ns)(many=False, required=False)
        newclass = type(name, (base_class, ), body)

        
        # keep class in factory cache
        cls._dynamic_product_serializers[cache_key] = newclass
        return newclass


class TagField(serializers.ListField):
    '''Serializer field for list of product tags'''
    child = serializers.CharField()
    def to_representation(self, obj):
        return [tag.tag for tag in obj.all()]


class ProductCompleteSerializer(serializers.ModelSerializer):
    '''
    Serializer that returns the complete set of metadata (core, links, tags, and custom namespaces).
    Should always be used for write operations.
    '''
    tags = TagField(required=False)

    class Meta(object):
        model = None  # will be set by ProductSerializerFactory
        exclude = ()
        muninn_namespaces = ()  # will be set to all namespaces by ProductSerializerFactory

    def _extract_namespace_data(self, validated_data):
        unvalidated_data = self.context['request'].data
        result = {}
        for ns in self.Meta.muninn_namespaces:
            result[ns] = validated_data.pop(ns, None)
            if not result[ns] and unvalidated_data.get(ns, None):
                raise BadRequest("namespace '%s' provided to an endpoint that does not accept it" % ns)
        return result

    def create(self, validated_data):
        # extract nested data
        ns_data = self._extract_namespace_data(validated_data)
        tags_data = validated_data.pop('tags', [])
        source_products = validated_data.pop('source_products', [])

        # set metadata_date
        if not 'active' in validated_data:
            validated_data['active'] = True
        validated_data['metadata_date'] = datetime.utcnow()

        # create instance
        instance = super(ProductCompleteSerializer, self).create(validated_data)

        # add tags
        for tag in tags_data:
            instance.tags.create(tag=tag)

        # add sources
        for source in source_products:
            instance.source_links.create(source=source)

        # create custom namespaces
        for ns, data in ns_data.items():
            if data is not None:
                serializer_class = self.fields[ns]
                ns_data[ns]['_core'] = instance
                serializer_class.create(ns_data[ns])

        return instance

    def update(self, instance, validated_data):
        # extract nested data
        ns_data = self._extract_namespace_data(validated_data)
        tags_data = validated_data.pop('tags', None)
        source_products = validated_data.pop('source_products', None)

        # set metadata_date
        validated_data['metadata_date'] = datetime.utcnow()

        # update instance
        instance = super(ProductCompleteSerializer, self).update(instance, validated_data)

        # update tags
        if tags_data is not None:
            existing = [tag.tag for tag in instance.tags.all()]
            for tag in instance.tags.all():
                if tag.tag not in tags_data:
                    tag.delete()
            for tag in tags_data:
                if tag not in existing:
                    instance.tags.create(tag=tag)

        # update sources
        if source_products is not None:
            existing = list(instance.source_products.all())
            for link in instance.source_links.all():
                if link.source not in source_products:
                    link.delete()
            for source in source_products:
                if source not in existing:
                    instance.source_links.create(source=source)

        # update custom namespaces
        for ns, data in ns_data.items():
            if data is not None:
                serializer_class = self.fields[ns]
                ns_instance = getattr(instance, ns, None)
                if ns_instance:
                    serializer_class.update(ns_instance, data)
                else:
                    data['_core'] = instance
                    serializer_class.create(data)

        return instance


class ProductCoreSerializer(serializers.ModelSerializer):
    '''Serializer that returns just the core metadata'''
    class Meta(object):
        exclude = ('source_products', )
        muninn_namespaces = ('core', )
