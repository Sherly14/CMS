# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-17 16:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Commission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('beneficiary_commission', models.DecimalField(decimal_places=3, default=0.0, max_digits=10)),
                ('merchant_commission', models.DecimalField(decimal_places=3, default=0.0, max_digits=10)),
                ('zrupee_commission', models.DecimalField(decimal_places=3, default=0.0, max_digits=10)),
                ('government_tax', models.DecimalField(decimal_places=3, default=0.0, max_digits=10)),
            ],
            options={
                'verbose_name_plural': 'Commissions',
            },
        ),
    ]
