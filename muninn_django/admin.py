#
# Copyright (C) 2018-2022 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

from django.contrib import admin
from django.db.models import TextField


def custom_titled_filter(title):
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance
    return Wrapper


class CoreAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'product_type', ]
    list_filter = ['product_type', ]
    formfield_overrides = {
        TextField: {'widget': admin.widgets.AdminTextInputWidget}
    }


class LinkAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'source', ]
    list_filter = [
        'product__product_type',
        ('source__product_type', custom_titled_filter('Source product type'))
    ]


class TagAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'tag', ]


class NamespaceAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = ['get_product_name', ]
    list_filter = ['_core__product_type', ]

    def get_product_name(self, obj):
        return obj._core.product_name
    get_product_name.short_description = 'product_name'
    get_product_name.admin_order_field = '_core__product_name'
