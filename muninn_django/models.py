#
# Copyright (C) 2018 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function, unicode_literals

import uuid
import os

from django.contrib.gis.db import models
from muninn_django.naiveutcdatetime.modelfields import NaiveDateTimeField


class Core(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField()
    hash = models.TextField(blank=True, null=True)
    size = models.BigIntegerField(blank=True, null=True)
    metadata_date = NaiveDateTimeField()
    archive_date = NaiveDateTimeField(blank=True, null=True)
    archive_path = models.TextField(blank=True, null=True)
    product_type = models.TextField()
    product_name = models.TextField()
    physical_name = models.TextField()
    validity_start = NaiveDateTimeField(blank=True, null=True)
    validity_stop = NaiveDateTimeField(blank=True, null=True)
    creation_date = NaiveDateTimeField(blank=True, null=True)
    remote_url = models.TextField(blank=True, null=True)
    footprint = models.GeometryField(geography=True, blank=True, null=True)

    source_products = models.ManyToManyField('self', symmetrical=False, related_name='derived_products', through='Link', through_fields=('product', 'source'),)

    def product_path(self):
        if self.archive_path is None:
            return None
        else:
            return os.path.join(self.archive_path, self.physical_name)

    def _repr(self):
        return '%s - %s' % (self.product_type, self.product_name)

    def __str__(self):
        # python 3
        return self._repr()

    def __unicode__(self):
        # python 2
        return self._repr()

    class Meta:
        abstract = True
        unique_together = (('product_type', 'product_name'), ('archive_path', 'physical_name'),)
        ordering = ('validity_start', )
        verbose_name_plural = 'core'


class Tag(models.Model):
    product = models.ForeignKey('Core', models.CASCADE, db_column='uuid', related_name='tags')
    tag = models.TextField()

    def _repr(self):
        return self.tag

    def __str__(self):
        # python 3
        return self._repr()

    def __unicode__(self):
        # python 2
        return self._repr()

    class Meta:
        abstract = True
        unique_together = (('product', 'tag'),)


class Link(models.Model):
    product = models.ForeignKey('Core', models.CASCADE, db_column='uuid', related_name='source_links')
    source = models.ForeignKey('Core', models.CASCADE, db_column='source_uuid', related_name='+')

    class Meta:
        abstract = True
        unique_together = (('product', 'source'),)
