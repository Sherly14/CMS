# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.contrib.postgres.fields import JSONField
from django.db import models

from zrtransaction.utils.constants import TRANSACTION_STATUS
from zruser.models import ZrUser
from zrutils.common.modelutils import RowInfo, get_slugify_value


# Create your models here.

class TransactionType(RowInfo):

    name = models.CharField(max_length=128)

    def save(self, *args, **kwargs):
        self.name = get_slugify_value(self.name)

        super(TransactionType, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'TransactionTypes'

    def __unicode__(self):
        return '%s' % self.name


class Transaction(RowInfo):

    status = models.CharField(max_length=2, choices=TRANSACTION_STATUS, default=TRANSACTION_STATUS[0][0])
    type = models.ForeignKey(to=TransactionType)
    amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    third_party_txn_id = models.CharField(max_length=128)

    beneficiary = models.ForeignKey(to=ZrUser, related_name='all_transactions')
    merchant = models.ForeignKey(to=ZrUser, related_name='transactions_list')
    transaction_json = JSONField()

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.amount).quantize(Decimal("0.00"))
        super(Transaction, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Transactions'

    def __unicode__(self):
        return '%s - %s - %s' % (self.status, self.amount, self.type)
