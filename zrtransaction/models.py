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


class Vendor(RowInfo):

    name = models.CharField(max_length=128)

    def save(self, *args, **kwargs):
        self.name = get_slugify_value(self.name)

        super(Vendor, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Vendors'

    def __unicode__(self):
        return '%s' % self.name


class ServiceProvider(RowInfo):

    name = models.CharField(max_length=512)
    code = models.CharField(max_length=256)
    min_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    max_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    is_enabled = models.BooleanField(default=True)
    transaction_type = models.ForeignKey(to=TransactionType, null=True, blank=True)
    vendor = models.ForeignKey(to=Vendor, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.min_amount = Decimal(self.min_amount).quantize(Decimal("0.00"))
        self.max_amount = Decimal(self.max_amount).quantize(Decimal("0.00"))
        super(ServiceProvider, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'ServiceProviders'

    def __unicode__(self):
        return '%s - %s - %s' % (self.name, self.code, self.is_enabled)


class Transaction(RowInfo):

    status = models.CharField(max_length=2, choices=TRANSACTION_STATUS, default=TRANSACTION_STATUS[0][0])
    type = models.ForeignKey(to=TransactionType)
    vendor = models.ForeignKey(to=Vendor)
    service_provider = models.ForeignKey(to=ServiceProvider, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    vendor_txn_id = models.CharField(max_length=128)
    txn_id = models.CharField(max_length=128)

    customer = models.CharField(max_length=256)
    beneficiary = models.CharField(max_length=256, null=True, blank=True)
    user = models.ForeignKey(to=ZrUser, related_name='transactions_list')
    transaction_request_json = JSONField(null=True, blank=True)
    transaction_response_json = JSONField(null=True, blank=True)

    additional_charges = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    is_commission_created = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.amount).quantize(Decimal("0.00"))
        super(Transaction, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Transactions'

    def __unicode__(self):
        return '%s - %s - %s' % (self.status, self.amount, self.type)


class ServiceCircle(RowInfo):

    name = models.CharField(max_length=512)
    code = models.CharField(max_length=256)
    is_enabled = models.BooleanField(default=True)
    transaction_type = models.ForeignKey(to=TransactionType, null=True, blank=True)
    vendor = models.ForeignKey(to=Vendor, null=True, blank=True)

    class Meta:
        verbose_name_plural = 'ServiceCircles'

    def __unicode__(self):
        return '%s - %s - %s' % (self.name, self.code, self.is_enabled)
