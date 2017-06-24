# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.db import models

from zrpayment.utils.constants import PAYMENT_REQUEST_STATUS
from zruser.models import ZrUser
from zrutils.common.modelutils import RowInfo, get_slugify_value


# Create your models here.

class PaymentMode(RowInfo):

    name = models.CharField(max_length=64)

    def save(self, *args, **kwargs):
        self.name = get_slugify_value(self.name)

        super(PaymentMode, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'PaymentModes'

    def __unicode__(self):
        return '%s' % self.name


class MerchantPaymentRequest(RowInfo):

    merchant = models.ForeignKey(to=ZrUser, related_name='merchant_payment_requests')
    distributor = models.ForeignKey(to=ZrUser, related_name='distributor_payment_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    dmt_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    non_dmt_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    merchant_payment_mode = models.ForeignKey(to=PaymentMode, related_name='merchant_requests')
    merchant_ref_no = models.CharField(max_length=20, null=True, blank=True)

    distributor_payment_mode = models.ForeignKey(to=PaymentMode, related_name='distributor_requests',
                                                 null=True, blank=True)
    distributor_ref_no = models.CharField(max_length=20, null=True, blank=True)
    merchant_status = models.CharField(max_length=2, choices=PAYMENT_REQUEST_STATUS, null=True, blank=True)
    distributor_status = models.CharField(max_length=2, choices=PAYMENT_REQUEST_STATUS, null=True, blank=True)

    comments = models.TextField(max_length=1024, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.amount).quantize(Decimal("0.00"))
        self.dmt_amount = Decimal(self.amount).quantize(Decimal("0.00"))
        self.non_dmt_amount = Decimal(self.amount).quantize(Decimal("0.00"))

        super(MerchantPaymentRequest, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'PaymentRequests'

    def __unicode__(self):
        return '%s - %s - %s' % (self.merchant, self.distributor, self.amount)


