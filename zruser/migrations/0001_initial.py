# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-06-25 17:36
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('account_no', models.CharField(max_length=20)),
                ('IFSC_code', models.CharField(max_length=20)),
                ('account_name', models.CharField(max_length=128)),
                ('bank_name', models.CharField(blank=True, max_length=20, null=True)),
                ('bank_city', models.CharField(blank=True, max_length=256, null=True)),
            ],
            options={
                'verbose_name_plural': 'BankDetails',
            },
        ),
        migrations.CreateModel(
            name='KYCDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('document_id', models.CharField(max_length=20)),
                ('document_link', models.CharField(max_length=512)),
                ('approval_status', models.CharField(choices=[(b'I', b'In Process'), (b'A', b'Approved'), (b'R', b'Rejected')], default=b'I', max_length=2)),
            ],
            options={
                'verbose_name_plural': 'KYCDetails',
            },
        ),
        migrations.CreateModel(
            name='KYCDocumentType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=128)),
            ],
            options={
                'verbose_name_plural': 'KYCDocumentTypes',
            },
        ),
        migrations.CreateModel(
            name='OTPDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('challengeId', models.CharField(max_length=64)),
                ('mobile_no', models.BigIntegerField(unique=True)),
                ('expiry', models.DateTimeField(auto_now=True)),
                ('otp', models.CharField(max_length=64)),
            ],
            options={
                'verbose_name_plural': 'OTPDetails',
            },
        ),
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=128, unique=True)),
            ],
            options={
                'verbose_name_plural': 'UserRoles',
            },
        ),
        migrations.CreateModel(
            name='ZrAdminUser',
            fields=[
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('id', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='zr_admin_user', serialize=False, to=settings.AUTH_USER_MODEL)),
                ('mobile_no', models.BigIntegerField(blank=True, null=True)),
                ('gender', models.CharField(blank=True, choices=[(b'M', b'Male'), (b'F', b'Female'), (b'O', b'Others')], max_length=2, null=True)),
                ('city', models.CharField(blank=True, max_length=256, null=True)),
                ('state', models.CharField(blank=True, max_length=256, null=True)),
                ('pincode', models.IntegerField(blank=True, null=True)),
                ('address', models.CharField(blank=True, max_length=512, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admin_users', to='zruser.UserRole')),
            ],
            options={
                'verbose_name_plural': 'ZrAdminUser',
            },
        ),
        migrations.CreateModel(
            name='ZrUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('at_created', models.DateTimeField(auto_now_add=True)),
                ('at_modified', models.DateTimeField(auto_now=True)),
                ('mobile_no', models.BigIntegerField(unique=True)),
                ('first_name', models.CharField(max_length=128)),
                ('last_name', models.CharField(blank=True, max_length=128, null=True)),
                ('pass_word', models.CharField(blank=True, max_length=256, null=True)),
                ('email', models.EmailField(blank=True, max_length=64, null=True)),
                ('gender', models.CharField(blank=True, choices=[(b'M', b'Male'), (b'F', b'Female'), (b'O', b'Others')], max_length=2, null=True)),
                ('city', models.CharField(blank=True, max_length=256, null=True)),
                ('state', models.CharField(blank=True, max_length=256, null=True)),
                ('pincode', models.IntegerField(blank=True, null=True)),
                ('address_line_1', models.CharField(blank=True, max_length=512, null=True)),
                ('address_line_2', models.CharField(blank=True, max_length=512, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('is_kyc_verified', models.BooleanField(default=False)),
                ('is_mobile_verified', models.BooleanField(default=False)),
                ('business_name', models.CharField(blank=True, max_length=256, null=True)),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zr_users', to='zruser.UserRole')),
            ],
            options={
                'verbose_name_plural': 'ZrUsers',
            },
        ),
        migrations.AddField(
            model_name='otpdetail',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='all_otps', to='zruser.ZrUser'),
        ),
        migrations.AddField(
            model_name='kycdetail',
            name='by_approved',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attached_kyc_details', to='zruser.ZrAdminUser'),
        ),
        migrations.AddField(
            model_name='kycdetail',
            name='for_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kyc_details', to='zruser.ZrUser'),
        ),
        migrations.AddField(
            model_name='kycdetail',
            name='role',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submitted_kyc_details', to='zruser.UserRole'),
        ),
        migrations.AddField(
            model_name='kycdetail',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='all_kyc_details', to='zruser.KYCDocumentType'),
        ),
        migrations.AddField(
            model_name='bankdetail',
            name='for_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='zruser.ZrUser'),
        ),
    ]
