# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.postgres.fields import JSONField
from zrutils.common.modelutils import RowInfo, get_slugify_value
from django.db import models


class Feedback(RowInfo):
    feedback_json = JSONField(null=True, blank=True)

    def __str__(self):
        return self.feedback_json
