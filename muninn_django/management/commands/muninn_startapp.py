#
# Copyright (C) 2018-2020 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from django.core.management.base import BaseCommand, CommandError
from django.template import Template, Context
import muninn


TYPES_MAPPING = {
    'long': 'models.BigIntegerField',
    'integer': 'models.IntegerField',
    'real': 'models.FloatField',
    'boolean': 'models.BooleanField',
    'text': 'models.TextField',
    'timestamp': 'NaiveDateTimeField',
    'uuid': 'models.UUIDField',
    'geometry': 'models.GeometryField',
}

TEMPLATE = '''
from __future__ import unicode_literals

from django.contrib.gis.db import models
from muninn_django import models as muninn_models
from muninn_django.naiveutcdatetime.modelfields import NaiveDateTimeField
# from django.contrib.gis.db.models import GeometryField, PolygonField
# import django.contrib.gis.db.backends


class Core(muninn_models.Core):
    class Meta(muninn_models.Core.Meta):
        db_table = '{{table_prefix}}core'
{{meta_options}}

class Tag(muninn_models.Tag):
    class Meta(muninn_models.Tag.Meta):
        db_table = '{{table_prefix}}tag'
{{meta_options}}

class Link(muninn_models.Link):
    class Meta(muninn_models.Link.Meta):
        db_table = '{{table_prefix}}link'
{{meta_options}}
{% for ns in namespaces %}
class {{ns.name_camel_case}}(models.Model):
    _core = models.OneToOneField(Core, models.CASCADE, db_column='uuid', related_name='{{ns.name}}', primary_key=True)
{% for field in ns.fields %}
{% if field.code == 'geometry' %}
    {{field.name}} = {{field.type}}(geography=True{% if field.optional %}, blank=True, null=True{% endif %})
{% else %}
    {{field.name}} = {{field.type}}({% if field.optional %}blank=True, null=True{% endif %})
{% endif %}
{% endfor %}

    class Meta:
        db_table = '{{table_prefix}}{{ns.name}}'
        verbose_name_plural = '{{ns.name}}'
{{meta_options}}
{% endfor %}
'''

import json
class Command(BaseCommand):
    help = 'Creates models.py for a muninn archive'

    def add_arguments(self, parser):
        parser.add_argument('archive', type=str)
        parser.add_argument('--meta-options', type=json.loads,
                            help='''JSON dictionary of options that will be added to all models' Meta. Example: {"managed": false}''')

    def handle(self, *args, **options):
        # get table_prefix
        archive_name = options['archive']
        config = muninn._read_archive_config_file(muninn._locate_archive_config_file(archive_name))
        backend = config['archive']['backend']
        table_prefix = config[backend].get('table_prefix', '')
        if options['meta_options']:
            meta_options = '\n'.join(['        %s = %s' % (k, repr(v)) for k, v in options['meta_options'].items()]) + '\n'
        else:
            meta_options = ''
        context = {
            'table_prefix': table_prefix,
            'namespaces': [],
            'meta_options': meta_options,
        }

        with muninn.open(archive_name) as archive:
            for namespace in archive.namespaces():
                if namespace != 'core':
                    namespace_schema = archive.namespace_schema(namespace)
                    # name_camel_case = namespace_schema.__name__
                    ns_context = {
                        'name': namespace,
                        'name_camel_case': namespace.capitalize(),
                        'fields': [],
                    }
                    for name in sorted(namespace_schema):
                        field = namespace_schema[name]
                        field_name = field.name()
                        if field.__module__ != 'muninn.schema':
                            field_name = '%s.%s' % (field.__module__, field.name())
                        field_type = TYPES_MAPPING.get(field_name, None)
                        optional = namespace_schema.is_optional(name)
                        if field_type:
                            ns_context['fields'].append({'code': field_name, 'name': name, 'type': field_type, 'optional': optional})
                    context['namespaces'].append(ns_context)

        template = Template(TEMPLATE)
        result = template.render(Context(context))
        #TODO: create a file instead of printing to stdout
        print(result)
        #TODO: print simple instructions, including default MUNINN setting to add to settings.py
