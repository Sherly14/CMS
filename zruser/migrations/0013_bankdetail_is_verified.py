# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-08-20 10:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zruser', '0012_auto_20170819_1900'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankdetail',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
    ]
