# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from decimal import Decimal

from django.db import models

from zrtransaction.models import Transaction
from zruser.models import ZrUser
from zrutils.common.modelutils import RowInfo


# Create your models here.

class Wallet(RowInfo):

    # Merchant field is invalid name. It should be user because it can be for all
    # distributors, merchants and sub distributors
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


# Create your models here.

class WalletTransactions(RowInfo):
    TRANSACTION = 'transaction'
    BALANCE = 'balance'
    REFUND_DECR = 'refund_decrement'
    REFUND_INC = 'refund_increment'
    LOG_TYPES = (
        (TRANSACTION, 'Transaction'),
        (BALANCE, 'Balance'),
        (REFUND_DECR, 'Refund'),
        (REFUND_INC, 'Refund increment')
    )

    log_type = models.CharField(
        max_length=20,
        default=TRANSACTION,
        choices=LOG_TYPES
    )
    wallet = models.ForeignKey(to=Wallet, related_name='transactions')
    transaction = models.ForeignKey(
        to=Transaction, related_name='transaction_logs',
        null=True, blank=True
    )
    payment_request = models.ForeignKey(
        to='zrpayment.PaymentRequest',
        null=True, blank=True
    )
    dmt_balance = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    non_dmt_balance = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    is_success = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'WalletTransactions'

    def __unicode__(self):
        return '%s' % (self.wallet)

    def save(self, *args, **kwargs):
        self.dmt_balance = Decimal(self.dmt_balance).quantize(Decimal("0.00"))
        self.non_dmt_balance = Decimal(self.non_dmt_balance).quantize(Decimal("0.00"))

        super(WalletTransactions, self).save(*args, **kwargs)
