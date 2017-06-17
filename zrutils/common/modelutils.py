from django.db import models

from django.template.defaultfilters import slugify


class RowInfo(models.Model):
    """
    Common row level info across objects
    """
    at_created = models.DateTimeField(auto_now_add=True)
    at_modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def get_slugify_value(value):
    slug_value = slugify(value)
    return slug_value.replace('-', '_').upper()

