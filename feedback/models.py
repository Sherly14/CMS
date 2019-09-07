# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.contrib.postgres.fields import JSONField
from zrutils.common.modelutils import RowInfo, get_slugify_value
from django.db import models
from zruser.models import ZrUser


class Feedback(RowInfo):
    feedback_json = JSONField(null=True, blank=True)
    user = models.ForeignKey(ZrUser, on_delete=models.PROTECT)

    def __str__(self):
        return self.feedback_json
