# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from zruser.models import ZrUser
from zrutils.common.modelutils import RowInfo


class DistributorMerchant(RowInfo):

    distributor = models.ForeignKey(to=ZrUser, related_name='all_merchant_mappings')
    merchant = models.ForeignKey(to=ZrUser, related_name='distributor_mappings')
    is_attaches_to_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'DistributorMerchantMappings'

    def __unicode__(self):
        return '%s - %s' % (self.distributor, self.merchant)


class MerchantSender(RowInfo):

    merchant = models.ForeignKey(to=ZrUser, related_name='sender_mappings')
    sender = models.ForeignKey(to=ZrUser, related_name='merchant_mappings')
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'MerchantSenderMappings'

    def __unicode__(self):
        return '%s - %s' % (self.merchant, self.sender)


class SenderBeneficiary(RowInfo):

    sender = models.ForeignKey(to=ZrUser, related_name='beneficiary_mappings')
    beneficiary = models.ForeignKey(to=ZrUser, related_name='sender_mapping')
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'SenderBeneficiaryMappings'

    def __unicode__(self):
        return '%s - %s' % (self.sender, self.beneficiary)


class MerchantBeneficiary(RowInfo):

    merchant = models.ForeignKey(to=ZrUser, related_name='beneficiary_mapping')
    beneficiary = models.ForeignKey(to=ZrUser, related_name='merchant_mapping')
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'MerchantBeneficiaryMappings'

    def __unicode__(self):
        return '%s - %s' % (self.merchant, self.beneficiary)

