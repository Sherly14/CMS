# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-10-07 13:29
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('zrwallet', '0008_auto_20171007_1227'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wallettransactions',
            name='log_type',
        ),
    ]
