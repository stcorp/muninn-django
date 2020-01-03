#
# Copyright (C) 2018-2020 S[&]T, The Netherlands.
#

from __future__ import absolute_import, division, print_function

import os
import tempfile
import shutil
from functools import partial

from django.conf import settings
from django.utils.module_loading import import_string
from django.db.models.signals import post_delete

from .errors import BadRequest


# lifted from muninn/utils.py
class TemporaryDirectory(object):
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def __enter__(self):
        self._path = tempfile.mkdtemp(*self._args, **self._kwargs)
        return self._path

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self._path)
        return False

# adapted from muninn/archive.py
def remove_file(archive_root, sender, instance, **kwargs):
    if archive_root is None:
        return
    product_path = instance.product_path()
    if product_path is None:
        return
    product_path = os.path.join(archive_root, product_path)
    if not os.path.lexists(product_path):
        return

    # Remove the data associated with the product from disk.
    try:
        with TemporaryDirectory(prefix=".remove-", suffix="-%s" % instance.uuid.hex,
                                dir=os.path.dirname(product_path)) as tmp_path:

            # Move product into the temporary directory. When the temporary directory will be removed at the end of
            # this scope, the product will be removed along with it.
            assert(instance.physical_name == os.path.basename(product_path))
            try:
                os.rename(product_path, os.path.join(tmp_path, os.path.basename(product_path)))
            except EnvironmentError as _error:
                raise

    except EnvironmentError as _error:
        raise BadRequest("unable to remove product '%s' (%s) [%s]" % (instance.product_name, instance.uuid, _error))


def django_signals_connect(archive):
    config = settings.MUNINN[archive]
    archive_root = config.get('root')
    model_class = import_string(config['models']['core'])
    if archive_root is not None:
        post_delete.connect(partial(remove_file, archive_root), sender=model_class, weak=False)
