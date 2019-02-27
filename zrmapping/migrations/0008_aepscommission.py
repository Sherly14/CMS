# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2019-03-05 16:58
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('zruser', '0034_zruser_user_code'),
        ('zrmapping', '0007_retailerterminal'),
    ]

    operations = [
        migrations.CreateModel(
            name='AEPSCommission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('aeps_commission_structure_set', models.IntegerField()),
                ('is_active', models.BooleanField(default=False)),
                ('distributor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dist_aeps_comm_mappings', to='zruser.ZrUser')),
                ('merchant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='merc_aeps_comm_mappings', to='zruser.ZrUser')),
            ],
            options={
                'verbose_name_plural': 'AEPSCommissionMappings',
            },
        ),
    ]
