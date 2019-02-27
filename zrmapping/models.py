# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from zruser.models import ZrUser, Sender, Beneficiary, ZrTerminal
from zrutils.common.modelutils import RowInfo
from zrcommission.models import AEPSCommissionStructure


class DistributorMerchant(RowInfo):

    distributor = models.ForeignKey(to=ZrUser, related_name='all_merchant_mappings')
    merchant = models.ForeignKey(to=ZrUser, related_name='distributor_mappings')
    is_attached_to_admin = models.BooleanField(default=False)
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
    eko_sender_id = models.CharField(max_length=255, null=True, blank=True)
    eko_beneficiary_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'SenderBeneficiary'

    def __unicode__(self):
        return '%s - %s' % (self.sender, self.beneficiary)


class SenderBeneficiaryMapping(RowInfo):

    sender = models.ForeignKey(to=Sender, related_name='all_sender_beneficiary_mappings')
    beneficiary = models.ForeignKey(to=Beneficiary, related_name='all_beneficiary_sender_mappings')
    is_active = models.BooleanField(default=False)
    eko_sender_id = models.CharField(max_length=255, null=True, blank=True)
    eko_beneficiary_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'SenderBeneficiaryMapping'

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


class SubDistributorMerchant(RowInfo):

    sub_distributor = models.ForeignKey(to=ZrUser, related_name='merchant_sub_mappings')
    merchant = models.ForeignKey(to=ZrUser, related_name='sub_distributor_mappings')
    is_attached_to_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'SubDistributorMerchantMappings'

    def __unicode__(self):
        return '%s - %s' % (self.sub_distributor, self.merchant)


class DistributorSubDistributor(RowInfo):

    distributor = models.ForeignKey(to=ZrUser, related_name='sub_dist_dist_mappings')
    sub_distributor = models.ForeignKey(to=ZrUser, related_name='dist_sub_dist_mappings')
    is_attached_to_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'DistributorSubDistributorMappings'

    def __unicode__(self):
        return '%s - %s' % (self.distributor, self.sub_distributor)


class RetailerTerminal(RowInfo):

    retailer = models.ForeignKey(to=ZrUser, related_name='terminal_retailer_mappings')
    terminal = models.ForeignKey(to=ZrTerminal, related_name='retailer_terminal_mappings')
    is_attached_to_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'RetailerTerminalMappings'

    def __unicode__(self):
        return '%s - %s' % (self.retailer, self.terminal)


class AEPSCommission(RowInfo):
    distributor = models.ForeignKey(to=ZrUser, related_name='dist_aeps_comm_mappings', null=True, blank=False)
    merchant = models.ForeignKey(to=ZrUser, related_name='merc_aeps_comm_mappings', null=True, blank=True)
    aeps_commission_structure = models.ForeignKey(to=AEPSCommissionStructure, related_name='aeps_comm_mappings', null=True, blank=False)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'AEPSCommissionMappings'

    def __unicode__(self):
        return '%s: %s - %s' % (self.pk, self.distributor, self.merchant)
