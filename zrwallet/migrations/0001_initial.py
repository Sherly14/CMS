# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-24 10:23
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('zruser', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('dmt_balance', models.DecimalField(decimal_places=3, default=0.0, max_digits=10)),
                ('non_dmt_balance', models.DecimalField(decimal_places=3, default=0.0, max_digits=10)),
                ('merchant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='zruser.ZrUser')),
            ],
            options={
                'verbose_name_plural': 'Wallets',
            },
        ),
    ]
