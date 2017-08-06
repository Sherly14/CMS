# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from decimal import Decimal

from django.db import models

from zruser.models import ZrUser
from zrutils.common.modelutils import RowInfo


# Create your models here.

class Wallet(RowInfo):

    merchant = models.OneToOneField(to=ZrUser, related_name='wallet', primary_key=True)
    dmt_balance = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    non_dmt_balance = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    class Meta:
        verbose_name_plural = 'Wallets'

    def get_total_balance(self):
        return self.dmt_balance + self.non_dmt_balance

    def __unicode__(self):
        return '%s - %s' % (self.merchant, self.get_total_balance())

    def save(self, *args, **kwargs):
        self.dmt_balance = Decimal(self.dmt_balance).quantize(Decimal("0.00"))
        self.non_dmt_balance = Decimal(self.non_dmt_balance).quantize(Decimal("0.00"))

        super(Wallet, self).save(*args, **kwargs)
