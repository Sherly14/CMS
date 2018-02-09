# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import boto3
from django.conf import settings as dj_settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.db import models

from common_utils import email_utils
from zruser.utils.constants import KYC_APPROVAL_CHOICES, GENDER_CHOICES, BANK_ACCOUNT_TYPES, BANK_CHANNEL_TYPES
from zrutils.common.modelutils import RowInfo, get_slugify_value


# Create your models here.

class UserRole(RowInfo):
    name = models.CharField(max_length=128, unique=True)

    def save(self, *args, **kwargs):
        self.name = get_slugify_value(self.name)

        super(UserRole, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'UserRoles'

    def __unicode__(self):
        return self.name


class BusinesssType(RowInfo):
    name = models.CharField(max_length=256)
    code = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    @staticmethod
    def get_business_types_form_choices():
        business_types = []
        for business_type in BusinesssType.objects.all():
            business_types.append(
                (business_type, business_type)
            )

        return business_types

    class Meta:
        verbose_name_plural = 'BusinessTypes'

    def __unicode__(self):
        return self.name


class KYCDocumentType(RowInfo):
    name = models.CharField(max_length=128)

    @staticmethod
    def get_document_types_form_choices():
        kyc_doc_types = []
        for doc_type in KYCDocumentType.objects.all():
            kyc_doc_types.append(
                (doc_type, doc_type,)
            )

        return kyc_doc_types

    class Meta:
        verbose_name_plural = 'KYCDocumentTypes'

    def __unicode__(self):
        return self.name


class ZrAdminUser(RowInfo):
    id = models.OneToOneField(to=User, related_name='zr_admin_user', primary_key=True)
    mobile_no = models.BigIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, null=True, blank=True)
    city = models.CharField(max_length=256, null=True, blank=True)
    state = models.CharField(max_length=256, null=True, blank=True)
    pincode = models.IntegerField(null=True, blank=True)
    address = models.CharField(max_length=512, null=True, blank=True)
    role = models.ForeignKey(to=UserRole, related_name='admin_users')
    is_active = models.BooleanField(default=True)
    zr_user = models.OneToOneField(to='zruser.ZrUser', related_name='zr_user', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'ZrAdminUser'

    def __unicode__(self):
        return '%s - (%s)' % (self.id.username, self.mobile_no)


class ZrUser(RowInfo):
    mobile_no = models.BigIntegerField(
        unique=True, null=False, blank=False,
    )
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128, null=True, blank=True)
    pass_word = models.CharField(max_length=256, null=True, blank=True)
    email = models.EmailField(max_length=64, null=True, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, null=True, blank=True)
    role = models.ForeignKey(to=UserRole, related_name='zr_users')

    city = models.CharField(max_length=256, null=True, blank=True)
    state = models.CharField(max_length=256, null=True, blank=True)
    pincode = models.IntegerField(null=True, blank=True)
    address_line_1 = models.CharField(max_length=512, null=True, blank=True)
    address_line_2 = models.CharField(max_length=512, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_kyc_verified = models.BooleanField(default=False)
    is_mobile_verified = models.BooleanField(default=False)
    business_name = models.CharField(max_length=256, null=True, blank=True)
    residence_address = models.CharField(max_length=256, null=True, blank=True)
    pan_no = models.CharField(max_length=10, null=True, blank=True)
    gstin = models.CharField(max_length=20, null=True, blank=True)

    UPIID = models.CharField(max_length=256, null=True, blank=True)
    business_type = models.ForeignKey(to=BusinesssType, related_name='business_type', null=True, blank=True)

    def save(self, *args, **kwargs):
        # self.pass_word = make_password(self.pass_word)

        super(ZrUser, self).save(*args, **kwargs)

    def check_password(self, password):
        return check_password(password, self.pass_word)

    def get_full_name(self):
        if self.last_name:
            return '%s %s' % (self.first_name, self.last_name)
        else:
            return self.first_name

    @property
    def full_name(self):
        return self.get_full_name()

    def send_welcome_email(self, password):
        portal_url = None
        if self.role.name == 'MERCHANT':
            portal_url = 'zrupee.com'
        else:
            portal_url = 'cms.zrupee.com'

        email_utils.send_email(
            'Hello and welcome To Zrupee!',
            self.email,
            'user_welcome_email',
            {
                'username': self.mobile_no,
                'password': password,
                'portal_url': portal_url
            },
            is_html=True
        )

    class Meta:
        verbose_name_plural = 'ZrUsers'

    def __unicode__(self):
        return '%s - (%s)' % (self.mobile_no, self.first_name)


class KYCDetail(RowInfo):
    type = models.ForeignKey(to=KYCDocumentType, related_name='all_kyc_details')
    document_id = models.CharField(max_length=50, null=True, blank=True)
    document_link = models.CharField(max_length=512)
    for_user = models.ForeignKey(to=ZrUser, related_name='kyc_details')
    approval_status = models.CharField(max_length=2, choices=KYC_APPROVAL_CHOICES, default=KYC_APPROVAL_CHOICES[0][0])
    by_approved = models.ForeignKey(to=ZrAdminUser, related_name='attached_kyc_details', null=True, blank=True)
    role = models.ForeignKey(to=UserRole, related_name='submitted_kyc_details')

    class Meta:
        verbose_name_plural = 'KYCDetails'

    def get_download_url(self):
        s3 = boto3.client(
            's3', aws_access_key_id=dj_settings.S3_AWS_SEC_KEY_ID,
            aws_secret_access_key=dj_settings.S3_AWS_SEC_KEY_SECRET,
            region_name='ap-south-1'
        )
        generated_url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': 'zrupee-kyc-documents',
                'Key': self.document_id
            }
        )

        return generated_url

    def __unicode__(self):
        return '%s - (%s)' % (self.type, self.for_user)


class BankDetail(RowInfo):
    account_no = models.CharField(max_length=20)
    account_type = models.CharField(max_length=2, choices=BANK_ACCOUNT_TYPES)
    channel = models.IntegerField(choices=BANK_CHANNEL_TYPES, default=BANK_CHANNEL_TYPES[1][0])
    IFSC_code = models.CharField(max_length=20)
    account_name = models.CharField(max_length=128)
    bank_name = models.CharField(max_length=20, null=True, blank=True)
    bank_city = models.CharField(max_length=256, null=True, blank=True)
    for_user = models.ForeignKey(to=ZrUser, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'BankDetails'

    def __unicode__(self):
        return '%s - (%s)' % (self.account_no, self.IFSC_code)


class Bank(RowInfo):
    bank_name = models.CharField(max_length=128)
    bank_code = models.CharField(max_length=16)
    eko_bank_id = models.CharField(max_length=64)
    account_length = models.IntegerField(default=0)
    ifsc_code = models.CharField(max_length=16, null=True, blank=True)
    is_master_ifsc = models.BooleanField(default=False)
    ifsc_formula = models.IntegerField(default=0)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Banks'

    def __unicode__(self):
        return '%s - (%s)' % (self.bank_name, self.bank_code)


class Sender(RowInfo):
    mobile_no = models.BigIntegerField(unique=True, null=False, blank=False)
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128, null=True, blank=True)
    email = models.EmailField(max_length=64, null=True, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, null=True, blank=True)

    city = models.CharField(max_length=256, null=True, blank=True)
    state = models.CharField(max_length=256, null=True, blank=True)
    pin_code = models.IntegerField(null=True, blank=True)
    address_line_1 = models.CharField(max_length=512, null=True, blank=True)
    address_line_2 = models.CharField(max_length=512, null=True, blank=True)

    is_user_active = models.BooleanField(default=True)
    is_mobile_verified = models.BooleanField(default=False)
    is_kyc_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Senders'

    def __unicode__(self):
        return '%s - (%s)' % (self.mobile_no, self.first_name)


class Beneficiary(RowInfo):
    mobile_no = models.BigIntegerField()
    first_name = models.CharField(max_length=128)
    last_name = models.CharField(max_length=128, null=True, blank=True)
    email = models.EmailField(max_length=64, null=True, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER_CHOICES, null=True, blank=True)

    city = models.CharField(max_length=256, null=True, blank=True)
    state = models.CharField(max_length=256, null=True, blank=True)
    pin_code = models.IntegerField(null=True, blank=True)
    address_line_1 = models.CharField(max_length=512, null=True, blank=True)
    address_line_2 = models.CharField(max_length=512, null=True, blank=True)

    account_no = models.CharField(max_length=20)
    bank = models.ForeignKey(to=Bank, related_name='beneficiaries_from_bank')
    channel = models.IntegerField(choices=BANK_CHANNEL_TYPES, default=BANK_CHANNEL_TYPES[1][0])
    IFSC_code = models.CharField(max_length=20)
    account_name = models.CharField(max_length=128)

    is_bank_account_verified = models.BooleanField(default=False)
    is_user_active = models.BooleanField(default=True)
    is_mobile_verified = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Beneficiaries'
        unique_together = ('account_no', 'bank')

    def __unicode__(self):
        return '%s - (%s)' % (self.mobile_no, self.first_name)


class SenderKYCDetail(RowInfo):
    type = models.ForeignKey(to=KYCDocumentType, related_name='all_sender_kyc_details')
    document_id = models.CharField(max_length=50, null=True, blank=True)
    document_link = models.CharField(max_length=512)
    for_sender = models.ForeignKey(to=Sender, related_name='sender_kyc_details')
    approval_status = models.CharField(max_length=2, choices=KYC_APPROVAL_CHOICES, default=KYC_APPROVAL_CHOICES[0][0])
    by_approved = models.ForeignKey(to=ZrAdminUser, related_name='attached_sender_kyc_details', null=True, blank=True)

    class Meta:
        verbose_name_plural = 'SenderKYCDetail'

    def __unicode__(self):
        return '%s - (%s)' % (self.type, self.for_sender)


class OTPDetail(RowInfo):
    challengeId = models.CharField(max_length=64)
    user = models.ForeignKey(to=ZrUser, related_name='all_otps')
    mobile_no = models.BigIntegerField()
    expiry = models.DateTimeField()
    otp = models.CharField(max_length=64)

    class Meta:
        verbose_name_plural = 'OTPDetails'

    def __unicode__(self):
        return '%s - (%s)' % (self.otp, self.mobile_no)


class MerchantLead(RowInfo):
    name = models.CharField(max_length=128)
    email = models.EmailField(max_length=64)
    mobile_no = models.BigIntegerField(unique=True)

    class Meta:
        verbose_name_plural = 'MerchantLead'

    def __unicode__(self):
        return '%s - (%s)' % (self.name, self.mobile_no)
