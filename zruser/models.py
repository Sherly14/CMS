# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.db import models

from zruser.utils.constants import KYC_APPROVAL_CHOICES, GENDER_CHOICES
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

    mobile_no = models.BigIntegerField(unique=True, null=False, blank=False)
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
    pan_no = models.CharField(max_length=10, null=True, blank=True)
    gstin = models.CharField(max_length=20, null=True, blank=True)

    def save(self, *args, **kwargs):
        # self.pass_word = make_password(self.pass_word)

        super(ZrUser, self).save(*args, **kwargs)

    def check_password(self, password):
        return check_password(password, self.pass_word)

    def get_full_name(self):
        return '%s - (%s)' % (self.first_name, self.last_name)

    class Meta:
        verbose_name_plural = 'ZrUsers'

    def __unicode__(self):
        return '%s - (%s)' % (self.mobile_no, self.first_name)


class KYCDetail(RowInfo):

    type = models.ForeignKey(to=KYCDocumentType, related_name='all_kyc_details')
    document_id = models.CharField(max_length=50, null=True)
    document_link = models.CharField(max_length=512)
    for_user = models.ForeignKey(to=ZrUser, related_name='kyc_details')
    approval_status = models.CharField(max_length=2, choices=KYC_APPROVAL_CHOICES, default=KYC_APPROVAL_CHOICES[0][0])
    by_approved = models.ForeignKey(to=ZrAdminUser, related_name='attached_kyc_details', null=True)
    role = models.ForeignKey(to=UserRole, related_name='submitted_kyc_details')

    class Meta:
        verbose_name_plural = 'KYCDetails'

    def __unicode__(self):
        return '%s - (%s)' % (self.type, self.for_user)


class BankDetail(RowInfo):
    account_no = models.CharField(max_length=20)
    IFSC_code = models.CharField(max_length=20)
    account_name = models.CharField(max_length=128)
    bank_name = models.CharField(max_length=20, null=True, blank=True)
    bank_city = models.CharField(max_length=256, null=True, blank=True)
    for_user = models.ForeignKey(to=ZrUser, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'BankDetails'

    def __unicode__(self):
        return '%s - (%s)' % (self.account_no, self.IFSC_code)


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
