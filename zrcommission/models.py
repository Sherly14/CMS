# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.db import models

from zrcommission.utils.constants import COMMISSION_CHOICES
from zrtransaction.models import Transaction, TransactionType, Vendor
from zruser.models import ZrUser
from zrutils.common.modelutils import RowInfo


# Create your models here.

class Commission(RowInfo):

    transaction = models.ForeignKey(to=Transaction, related_name='commissions')
    merchant = models.ForeignKey(to=ZrUser, null=True, blank=True, related_name='merchant_commission')
    distributor = models.ForeignKey(to=ZrUser, null=True, blank=True, related_name='distributor_commission')
    merchant_commission = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    distributor_commission = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    zrupee_commission = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    government_tax = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    def save(self, *args, **kwargs):
        self.distributor_commission = Decimal(self.distributor_commission).quantize(Decimal("0.00"))
        self.merchant_commission = Decimal(self.merchant_commission).quantize(Decimal("0.00"))
        self.zrupee_commission = Decimal(self.zrupee_commission).quantize(Decimal("0.00"))
        self.government_tax = Decimal(self.government_tax).quantize(Decimal("0.00"))

        super(Commission, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Commissions'

    def __unicode__(self):
        return '%s - zrupee_commission com%s' % (self.transaction, self.zrupee_commission)


class CommissionStructure(RowInfo):

    distributor = models.ForeignKey(to=ZrUser, related_name='commission_structures')
    transaction_type = models.ForeignKey(to=TransactionType)
    transaction_vendor = models.ForeignKey(to=Vendor)
    commission_type = models.CharField(max_length=2, choices=COMMISSION_CHOICES)
    for_distributor = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    for_merchant = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)
    for_zrupee = models.DecimalField(max_digits=3, decimal_places=3, default=0.00)

    def save(self, *args, **kwargs):
        self.for_merchant = Decimal(self.for_merchant).quantize(Decimal("0.00"))
        self.for_distributor = Decimal(self.for_distributor).quantize(Decimal("0.00"))
        self.for_zrupee = Decimal(self.for_zrupee).quantize(Decimal("0.00"))

        super(CommissionStructure, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'CommissionStructures'

    def __unicode__(self):
        return '%s - distributor_commission %s' % (self.distributor, self.for_zrupee)
