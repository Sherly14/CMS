# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('zruser', '0034_zruser_user_code'),
        ('zrmapping', '0008_aepscommission'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserBeneficiary',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=False)),
                ('beneficiary', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='beneficiary_user_mappings', to='zruser.Beneficiary')),
                ('merchant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_beneficiary_mappings', to='zruser.ZrUser'))
            ],
            options={
                'verbose_name_plural': 'UserBeneficiaryMappings',
            },
        ),
    ]
