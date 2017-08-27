# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.db import models

from zrcommission.utils.constants import COMMISSION_CHOICES
from zrtransaction.models import Transaction, TransactionType, Vendor, ServiceProvider
from zruser.models import ZrUser
from zrutils.common.modelutils import RowInfo


# Create your models here.

class Commission(RowInfo):

    transaction = models.ForeignKey(to=Transaction, related_name='commissions')

    commission_user = models.ForeignKey(to=ZrUser, null=True, blank=True, related_name='all_commissions')
    # distributor = models.ForeignKey(to=ZrUser, null=True, blank=True, related_name='distributor_commissions')
    # sub_distributor = models.ForeignKey(to=ZrUser, null=True, blank=True, related_name='sub_distributor_commissions')

    user_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # distributor_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # sub_distributor_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    user_tds = models.DecimalField(max_digits=10, decimal_places=4, default=0.00)
    # distributor_tds = models.DecimalField(max_digits=10, decimal_places=4, default=0.00)
    # sub_distributor_tds = models.DecimalField(max_digits=10, decimal_places=4, default=0.00)

    user_gst = models.DecimalField(max_digits=10, decimal_places=4, default=0.00)
    # distributor_gst = models.DecimalField(max_digits=10, decimal_places=4, default=0.00)
    # sub_distributor_gst = models.DecimalField(max_digits=10, decimal_places=4, default=0.00)
    net_commission = models.DecimalField(max_digits=10, decimal_places=4, default=0.00)
    # zrupee_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        self.user_commission = Decimal(self.user_commission).quantize(Decimal("0.00"))
        # self.distributor_commission = Decimal(self.merchant_commission).quantize(Decimal("0.00"))
        # self.sub_distributor_commission = Decimal(self.zrupee_commission).quantize(Decimal("0.00"))

        # self.zrupee_commission = Decimal(self.zrupee_commission).quantize(Decimal("0.00"))

        self.user_tds = Decimal(self.user_tds).quantize(Decimal("0.0000"))
        # self.distributor_tds = Decimal(self.distributor_tds).quantize(Decimal("0.0000"))
        # self.sub_distributor_tds = Decimal(self.sub_distributor_tds).quantize(Decimal("0.0000"))

        self.user_gst = Decimal(self.user_gst).quantize(Decimal("0.0000"))
        # self.distributor_gst = Decimal(self.distributor_gst).quantize(Decimal("0.0000"))
        # self.sub_distributor_gst = Decimal(self.sub_distributor_gst).quantize(Decimal("0.0000"))

        super(Commission, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Commissions'

    def __unicode__(self):
        return '%s - zrupee_commission com%s' % (self.transaction, self.net_commission)


class BillPayCommissionStructure(RowInfo):

    distributor = models.ForeignKey(to=ZrUser, related_name='commission_structures')
    transaction_type = models.ForeignKey(to=TransactionType)
    transaction_vendor = models.ForeignKey(to=Vendor)
    service_provider = models.ForeignKey(to=ServiceProvider)
    commission_type = models.CharField(max_length=2, choices=COMMISSION_CHOICES)
    net_margin = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    commission_for_zrupee = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    commission_for_distributor = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    commission_for_sub_distributor = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    commission_for_merchant = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    tds_value = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    is_chargable = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.commission_for_zrupee = Decimal(self.commission_for_zrupee).quantize(Decimal("0.00"))
        self.commission_for_distributor = Decimal(self.commission_for_distributor).quantize(Decimal("0.00"))
        self.commission_for_merchant = Decimal(self.commission_for_merchant).quantize(Decimal("0.00"))
        self.commission_for_sub_distributor = Decimal(self.commission_for_sub_distributor).quantize(Decimal("0.00"))

        super(BillPayCommissionStructure, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'BillPayCommissionStructure'

    def __unicode__(self):
        return '%s - distributor_commission %s' % (self.distributor, self.for_zrupee)


class DMTCommissionStructure(RowInfo):

    distributor = models.ForeignKey(to=ZrUser, related_name='dmt_commission_structures')
    transaction_type = models.ForeignKey(to=TransactionType)
    transaction_vendor = models.ForeignKey(to=Vendor)
    service_provider = models.ForeignKey(to=ServiceProvider)
    commission_type = models.CharField(max_length=2, choices=COMMISSION_CHOICES)
    net_margin = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    commission_for_zrupee = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    commission_for_distributor = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    commission_for_sub_distributor = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    commission_for_merchant = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    tds_value = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    gst_value = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    is_chargable = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.commission_for_zrupee = Decimal(self.commission_for_zrupee).quantize(Decimal("0.00"))
        self.commission_for_distributor = Decimal(self.commission_for_distributor).quantize(Decimal("0.00"))
        self.commission_for_merchant = Decimal(self.commission_for_merchant).quantize(Decimal("0.00"))
        self.commission_for_sub_distributor = Decimal(self.commission_for_sub_distributor).quantize(Decimal("0.00"))

        super(DMTCommissionStructure, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'DMTCommissionStructure'

    def __unicode__(self):
        return '%s - net margin %s' % (self.distributor, self.net_margin)

