# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-08-31 15:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zrcommission', '0011_auto_20170831_1518'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billpaycommissionstructure',
            name='net_margin',
            field=models.DecimalField(decimal_places=3, default=0.0, max_digits=5),
        ),
    ]
