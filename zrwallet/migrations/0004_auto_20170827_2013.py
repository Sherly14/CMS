# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-08-27 20:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zrwallet', '0003_wallettransactions'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='wallettransactions',
            options={'verbose_name_plural': 'WalletTransactions'},
        ),
        migrations.RemoveField(
            model_name='wallettransactions',
            name='dmt_final_balance',
        ),
        migrations.RemoveField(
            model_name='wallettransactions',
            name='dmt_initial_balance',
        ),
        migrations.RemoveField(
            model_name='wallettransactions',
            name='non_dmt_final_balance',
        ),
        migrations.RemoveField(
            model_name='wallettransactions',
            name='non_dmt_initial_balance',
        ),
        migrations.AddField(
            model_name='wallettransactions',
            name='dmt_balance',
            field=models.DecimalField(decimal_places=3, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name='wallettransactions',
            name='non_dmt_balance',
            field=models.DecimalField(decimal_places=3, default=0.0, max_digits=10),
        ),
    ]
