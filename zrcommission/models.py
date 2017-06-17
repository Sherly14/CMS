# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.db import models

from zrtransaction.models import Transaction


# Create your models here.

class Commission(models.Model):

    transaction = models.ForeignKey(to=Transaction)
    beneficiary_commission = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    merchant_commission = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    zrupee_commission = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    government_tax = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    def save(self, *args, **kwargs):
        self.beneficiary_commission = Decimal(self.beneficiary_commission).quantize(Decimal("0.00"))
        self.merchant_commission = Decimal(self.merchant_commission).quantize(Decimal("0.00"))
        self.zrupee_commission = Decimal(self.zrupee_commission).quantize(Decimal("0.00"))
        self.government_tax = Decimal(self.government_tax).quantize(Decimal("0.00"))

        super(Commission, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Commissions'

    def __unicode__(self):
        return '%s - %s' % (self.transaction, self.zrupee_commission)
