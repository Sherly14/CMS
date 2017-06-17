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


class PaymentRequest(RowInfo):

    merchant = models.ForeignKey(to=ZrUser, related_name='merchant_payment_requests')
    distributor = models.ForeignKey(to=ZrUser, related_name='distributor_payment_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    merchant_payment_mode = models.ForeignKey(to=PaymentMode, related_name='merchant_requests')
    merchant_ref_no = models.CharField(max_length=20)

    distributor_payment_mode = models.ForeignKey(to=PaymentMode, related_name='distributor_requests')
    distributor_ref_no = models.CharField(max_length=20)

    merchant_status = models.CharField(max_length=2, choices=PAYMENT_REQUEST_STATUS)
    distributor_status = models.CharField(max_length=2, choices=PAYMENT_REQUEST_STATUS)

    comments = models.TextField(max_length=1024)

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.amount).quantize(Decimal("0.00"))

        super(PaymentRequest, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'PaymentRequests'

    def __unicode__(self):
        return '%s - %s - %s' % (self.merchant_id, self.distributor_id, self.amount)


