=============
Muninn-Django
=============

A Django app to add a REST API on top of your Muninn archive(s)


------------
Requirements
------------

- muninn 4.1 (including a configured archive)
- django 1.11.7
- djangorestframework (aka DRF) 3.8.2
- djangorestframework-gis 0.13
- django-filter 1.1.0 (optional)
- coreapi 2.3.3 (optional)

This package has been tested with the above mentioned versions.
When using different versions, make sure to check the `djangorestframework-gis compatibility table <https://github.com/djangonauts/django-rest-framework-gis#compatibility-with-drf-django-and-python>`_.

------------
Installation
------------

1. Add "rest_framework" and "muninn_django" to your INSTALLED_APPS setting::

    INSTALLED_APPS = [
        ...
        'rest_framework',
        'rest_framework_gis',
        'muninn_django',
    ]

2. Include the muninn-django URLconf in your project urls.py::

    url(r'^muninn/', include('muninn_django.urls')),

3. Create a django app that will contain the archive models::

    python manage.py startapp <archive>

4. Generate the archive models::

    python manage.py muninn_startapp <archive> > <archive>/models.py

4.1. Or, if the models should not be managed::

    python manage.py muninn_startapp --meta-options='{"managed": false}' <archive> > <archive>/models.py

5. Add the archive app to your INSTALLED_APPS setting::

    INSTALLED_APPS = [
        ...
        '<archive>',
    ]

6. Configure muninn-django. At a minimum, specify the models for each namespace in the archive, including ``core``::

    MUNINN = {
        '<archive>': {
            'models' : {
                'core': '<archive>.models.Core',
                'stuff': '<archive>.models.Stuff',
            },
        },
    }

7. You should restrict write access to the archive, and paginate the results. Below is a simple configuration. See DRF docs for details::

    REST_FRAMEWORK = {
        # Permissions
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
        ],

        # Pagination
        'DEFAULT_PAGINATION_CLASS': 'muninn_django.pagination.PageNumberPagination',
        'PAGE_SIZE': 100,
        'MAX_PAGE_SIZE': 1000, # specific muninn_django.pagination.PageNumberPagination

    }


----------------------
Usage
----------------------

The following examples use ``httpie``, which can be installed via pip.

Query
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- query archive for all products::

    http GET "http://127.0.0.1:8000/muninn/<archive>/"

- get metadata for a specific product::

    http GET "http://127.0.0.1:8000/muninn/<archive>/<uuid>/"

- a specific product can alternatively be accessed by product_type/product_name::

    http GET "http://127.0.0.1:8000/muninn/<archive>/<product_type>/<product_name>/"

- get all metadata for a specific product (this will query several tables)::

    http GET "http://127.0.0.1:8000/muninn/<archive>/<uuid>/?mode=extended"

- the ``mode`` parameter can also be specified in a query::

    http GET "http://127.0.0.1:8000/muninn/<archive>/?mode=extended"


Sort order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The default ordering of results is by ascending validity_start.
The sort order can be customized, using the ``ordering`` query parameter.
Custom ordering needs to be enabled, see optional configuration section below.

- sort by descending metadata_date::

    http GET "http://127.0.0.1:8000/muninn/<archive>/?ordering=-metadata_date"

- multiple fields can be specified::

    http GET "http://127.0.0.1:8000/muninn/<archive>/?ordering=-metadata_date,product_type"

- namespace fields are supported (when using the appropriate Filter in the configuration)::

    http GET "http://127.0.0.1:8000/muninn/<archive>/?ordering=-mynamespace__fieldname"


Query with filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Filtering needs to be enabled, see optional configuration section below.

- search for a specific product type::

    http GET "http://127.0.0.1:8000/muninn/<archive>/?product_type=cool"

- search for several product types::

    http GET "http://127.0.0.1:8000/muninn/<archive>/?product_type__in=cool,awesome"

- search for product updated since a date::

    http GET "http://127.0.0.1:8000/muninn/<archive>/?metadata_date__gt=2018-02-12T16:41:07"

Besides the standard `django field lookups <https://docs.djangoproject.com/en/1.11/ref/models/querysets/#field-lookups>`_, a custom lookup ``ne`` (for inequality) is available.

Create a product
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assuming that permissions is set to ``DjangoModelPermissionsOrAnonReadOnly``, replace ``user`` and ``password`` below.

::

    echo '{"archive_date": "2013-01-29T00:00:00", "archive_path": "/tmp/...", "physical_name":"product_0001.hdf", "product_name":"product_0001", "product_type": "simple", "tags": ["public"]}' | http -a user:password POST "http://127.0.0.1:8000/muninn/<archive>/"


Update a product
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assuming the product you want to edit has UUID "aa892e17-45e9-4624-a37c-f3acebace68c"

- edit fields (note that providing ``tags`` and ``source_products`` will replace the full list; see below for incremental updates for those lists)::

    echo '{"active": "False", "tags": ["deprecated"], "validity_stop": "2018-01-26T08:51:57.999999", "stuff": {"stuff_1": "Hellow", "stuff_2": -1}}' | http -a user:password PATCH "http://127.0.0.1:8000/muninn/<archive>/aa892e17-45e9-4624-a37c-f3acebace68c/"

- add tag::

    echo '["public", "highlight"]' | http -a user:password POST "http://127.0.0.1:8000/muninn/<archive>/aa892e17-45e9-4624-a37c-f3acebace68c/tag/"

- remove tag::

    echo '["deprecated"]' | http -a user:password POST "http://127.0.0.1:8000/muninn/<archive>/aa892e17-45e9-4624-a37c-f3acebace68c/untag/"

- add source::

    echo '["ddc8d012-2846-46a0-91fd-0143baaee2f8"]' | http -a user:password POST "http://127.0.0.1:8000/muninn/<archive>/aa892e17-45e9-4624-a37c-f3acebace68c/link/"

- remove source::

    echo '["ddc8d012-2846-46a0-91fd-0143baaee2f8"]' | http -a user:password POST "http://127.0.0.1:8000/muninn/<archive>/aa892e17-45e9-4624-a37c-f3acebace68c/unlink/"


Delete a product
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Note that by default, the product is not removed from the filesystem. If that is not the intended behaviour, see optional configuration section below::

    http -a user:password DELETE http://127.0.0.1:8000/muninn/<archive>/aa892e17-45e9-4624-a37c-f3acebace68c/


Schema
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If `Core API <http://www.coreapi.org/>`_ is installed, the schema is available::

    http http://127.0.0.1:8000/muninn/schema/


----------------------
Optional configuration
----------------------

Multiple archives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To add another archive, simply repeat the installation steps above. The top level keys in the MUNINN setting define the name of each archive.


Custom URLs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The default configuration::

    url(r'^muninn/', include('muninn_django.urls')),

adds all archives under a common URL path ``muninn``, so the URLs for each archive will be ``muninn/archive1/``, ``muninn/archive2/``, etc.

To customize, this behaviour, create a ``<archive>/urls.py``::

    from django.conf.urls import url, include
    from muninn_django.routers import MuninnRouter

    router = MuninnRouter()
    router.register_muninn('<archive>', prefix='data')
    urlpatterns = [
        url(r'^', include(router.urls))
    ]

and use that in the project urls.py::

    url(r'^api/', include('<archive>.urls')),

In this example, the URL path for this archive will be ``api/data/``.
Note the prefix can be omitted, in which case the URL path will be ``api/`` (might make sense if there is a single archive).
In that case, the following shortand can be used in the project urls.py (no need for a separate <archive>/urls.py)::

    url(r'^api/', include(MuninnRouter('<archive>').urls)),


Custom serializers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
By default, two serializers are defined:
    - ``default`` returns just the ``core`` namespace fields.
    - ``extended`` returns the full metadata: all namespaces, tags and source products.

The serializer is chosen through the ``mode`` request parameter.

If you want to customize serializers, you'll have to specify the ``serializers`` key in the archive ``MUNINN`` setting. Below is the default configuration::

    MUNINN = {
        '<archive>': {
            ...
            'serializers' : {
                'default': 'muninn_django.serializers.ProductCoreSerializer',
                'extended': 'muninn_django.serializers.ProductCompleteSerializer',
            },
        },
    }


Disable fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
By default, all namespace fields are available. To disable some fields across all serializers, use::

    MUNINN = {
        '<archive>': {
            ...
            'disabled_fields': {
                'core': ['active', 'archive_date', 'archive_path', ],
            },
        },
    }


Sorting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To enable sorting, add ``rest_framework.filters.OrderingFilter`` to ``DEFAULT_FILTER_BACKENDS`` setting::

    REST_FRAMEWORK = {
    ...
        # Filtering
        'DEFAULT_FILTER_BACKENDS': (
            'muninn_django.filters.RelatedOrderingFilter',

``RelatedOrderingFilter`` extends the built-in filter to support ordering by fields in related models, using the Django ORM __ notation. If you don't care about that, you stick to the built-in filter::

    REST_FRAMEWORK = {
    ...
        # Filtering
        'DEFAULT_FILTER_BACKENDS': (
            'rest_framework.filters.OrderingFilter', 


Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To enable filtering:

1. Install ``django-filter`` and instruct DRF to use it::

    REST_FRAMEWORK = {
    ...
        # Filtering
        'DEFAULT_FILTER_BACKENDS': (
            'django_filters.rest_framework.DjangoFilterBackend', 

2. Add it to the INSTALLED_APPS setting. It is necessary for the browsable API::

    INSTALLED_APPS = [
        ...
        'django_filters',
    ]

3. Optionally, disable some lookups for a particular archive::

    MUNINN = {
        '<archive>': {
            ...
            'disabled_lookups' : ['search', 'regex', 'iregex', ],
        },
    }


Remove products from filesystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Add a ``root`` setting to the archive configuration::

    MUNINN = {
        '<archive>': {
            'root' : '/path/to/archive/root',
            ...
        },
    }

2. Edit/add an AppConfig instance in ``<archive>/apps.py``::

    from django.apps import AppConfig
    from muninn_django.signals import django_signals_connect

    class MyAppConfig(AppConfig):
        name = '<archive>'
        def ready(self):
            django_signals_connect('<archive>')

3. Make sure this AppConfig is in use, either by specifying it in ``INSTALLED_APPS``::

    INSTALLED_APPS = [
        ...
        '<archive>.apps.MyAppConfig',
    ]

or making it the default in ``<archive>/__init.py``::

    default_app_config = '<archive>.apps.MyAppConfig'


Custom behaviour
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If the default behaviour doesn't suit you, you'll have to

1. write your own ViewSet class::

    class ProductViewSet(muninn_django.views.ProductViewSet):
        muninn_archive = '<archive>'
        queryset = Core.objects.all()

2. configure it::

    MUNINN = {
        '<archive>': {
            ...
            'view': '<archive>.views.ProductViewSet',
        },
    }

(Non-exhaustive) list of possible customizations:
    - custom filtering (see DRF docs)

    - specify permission classes for a specific archive in a multi-archive deployment (see DRF docs)

    - constrain the queryset to exclude partially ingested products::

        queryset = Core.objects.filter(active=True)

    - constrain the queryset if a user is not authenticated::

        def get_queryset(self):
            queryset = super(ProductViewSet, self).get_queryset()

            # only logged-in users have access to all product types
            user = self.request.user
            if not user.is_authenticated:
                queryset = queryset.filter(product_type__in=PUBLIC_PRODUCT_TYPES)

            return queryset


Database Migrations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can use django migrations to handle changes in the muninn namespaces. Note that:
    - the initial tables must be created by ``muninn-prepare``
    - muninn-django will ignore Geometry data types, to add such a field you'll have to issue the SQL command manually

1. Initialize the migrations::

    python manage.py makemigrations <archive>
    python manage.py migrate --fake-initial <archive>

2. Update models.py to match the desired state of the database (if the muninn definition has already been updated, you should be able to use ``muninn_startapp``)

3. Apply migrations as usual in django::

    python manage.py makemigrations <archive>
    python manage.py migrate <archive>


--------------
CAVEATS
--------------

custom namespace restrictions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Custom namespace names are restricted: can't use core namespace field names.
Reason: django model mapping

core namespace restrictions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

(Future) core namespace field names are restricted: can't use the following:
    - tag
    - source_product
    - derived_product
    - mode

Reason: the names are used as GET parameters, and would clash with filtering

Writable data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``metadata_date`` is defined as read-only; its value is set whenever there is a write access.
All other fields are writable.

Geometry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Geometry data types are not fully supported. The API supports reading and writing, but not query filtering. This notably affects ``core.footprint``.


---------------
Troubleshooting
---------------

Sqlite database settings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Under python 3, using the default engine ``django.db.backends.sqlite3`` works, but under python 2 that will fail for write operations. Use ``django.contrib.gis.db.backends.spatialite`` instead. You might also have to set SPATIALITE_LIBRARY_PATH::

    SPATIALITE_LIBRARY_PATH = 'mod_spatialite'
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.spatialite',
            ...

