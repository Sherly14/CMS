# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.contrib.postgres.fields import JSONField
from django.db import models

from common_utils import date_utils
from zrcommission.models import Commission
from zrmapping.models import SubDistributorMerchant, DistributorMerchant
from zrtransaction.utils.constants import TRANSACTION_STATUS
from zruser.mapping import SUBDISTRIBUTOR, DISTRIBUTOR, MERCHANT
from zruser.models import ZrUser, Beneficiary
from zrutils.common.modelutils import RowInfo, get_slugify_value

from common_utils import date_utils



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
    amount = models.DecimalField(max_digits=10, decimal_places=4, default=0.00)
    vendor_txn_id = models.CharField(max_length=128)
    txn_id = models.CharField(max_length=128)

    customer = models.CharField(max_length=256)
    beneficiary = models.CharField(max_length=256, null=True, blank=True)
    user = models.ForeignKey(to=ZrUser, related_name='transactions_list')
    transaction_request_json = JSONField(null=True, blank=True)
    transaction_response_json = JSONField(null=True, blank=True)

    additional_charges = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    is_commission_created = models.BooleanField(default=False)

    beneficiary_user = models.ForeignKey(to=Beneficiary, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.amount).quantize(Decimal("0.00"))
        super(Transaction, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Transactions'

    def __unicode__(self):
        return '%s - %s - %s' % (self.status, self.amount, self.type)

    @property
    def merchant_name(self):
        return self.user.get_full_name()
    
    @property
    def formatted_status(self):
        for status in TRANSACTION_STATUS:
            if status[0] == self.status:
                return status[1]

    @property
    def created_date(self):
        return date_utils.utc_to_ist(self.at_created).date().strftime('%d-%m-%Y')

    @property
    def created_time(self):
        return date_utils.utc_to_ist(self.at_created).strftime('%H:%M:%S')

    @property
    def distributor_name(self):
        name = ""
        distributor_instance = SubDistributorMerchant.objects.filter(merchant=self.user).first()
        if distributor_instance:
            name = distributor_instance.sub_distributor.get_full_name()
        else:
            distributor_instance = DistributorMerchant.objects.filter(merchant=self.user).first()
            if distributor_instance:
                name = distributor_instance.distributor.get_full_name()
        return name

    @property
    def commission_fee(self):
        if not self.commissions.all():
            return 'NA'

        commission = self.commissions.all().last()
        if commission.bill_payment_comm_structure:
            return commission.bill_payment_comm_structure.net_margin
        elif commission.dmt_comm_structure:
            return commission.dmt_comm_structure.customer_fee

        return 'NA'

    @property
    def commission_value(self):
        if not self.commissions.all():
            return 'NA'

        commission = self.commissions.all().last()
        if commission.bill_payment_comm_structure:
            if commission.bill_payment_comm_structure.is_chargable:
                return commission.bill_payment_comm_structure.net_margin
            else:
                return (
                    self.amount *
                    commission.bill_payment_comm_structure.net_margin
                ) / 100
        elif commission.dmt_comm_structure:
            return (
                self.amount * commission.dmt_comm_structure.customer_fee
            ) / 100

        return 'NA'

    @property
    def merchant_mobile(self):
        return self.user.mobile_no

    @property
    def sub_dist_gross_commission(self):
        comm_instance = self.commissions.filter(commission_user__role__name=SUBDISTRIBUTOR).last()
        if comm_instance:
            return comm_instance.gross_amount()
        return 'NA'

    @property
    def sub_dist_gst(self):
        comm_instance = self.commissions.filter(commission_user__role__name=SUBDISTRIBUTOR).last()
        if comm_instance:
            return comm_instance.user_gst
        return 'NA'

    @property
    def sub_dist_tds(self):
        comm_instance = self.commissions.filter(commission_user__role__name=SUBDISTRIBUTOR).last()
        if comm_instance:
            return comm_instance.user_tds
        return 'NA'

    @property
    def sub_dist_net_commission(self):
        comm_instance = self.commissions.filter(commission_user__role__name=SUBDISTRIBUTOR).last()
        if comm_instance:
            return comm_instance.net_commission
        return 'NA'

    @property
    def dist_gross_commission(self):
        comm_instance = self.commissions.filter(commission_user__role__name=DISTRIBUTOR).last()
        if comm_instance:
            return comm_instance.gross_amount()
        return 'NA'

    @property
    def dist_gst(self):
        comm_instance = self.commissions.filter(commission_user__role__name=DISTRIBUTOR).last()
        if comm_instance:
            return comm_instance.user_gst
        return 'NA'

    @property
    def dist_tds(self):
        comm_instance = self.commissions.filter(commission_user__role__name=DISTRIBUTOR).last()
        if comm_instance:
            return comm_instance.user_tds
        return 'NA'

    @property
    def dist_net_commission(self):
        comm_instance = self.commissions.filter(commission_user__role__name=DISTRIBUTOR).last()
        if comm_instance:
            return comm_instance.net_commission
        return 'NA'

    @property
    def merchant_gross_commission(self):
        comm_instance = self.commissions.filter(commission_user__role__name=MERCHANT).last()
        if comm_instance:
            return comm_instance.gross_amount()
        return 'NA'

    @property
    def merchant_gst(self):
        comm_instance = self.commissions.filter(commission_user__role__name=MERCHANT).last()
        if comm_instance:
            return comm_instance.user_gst
        return 'NA'

    @property
    def merchant_tds(self):
        comm_instance = self.commissions.filter(commission_user__role__name=MERCHANT).last()
        if comm_instance:
            return comm_instance.user_tds
        return 'NA'

    @property
    def merchant_net_commission(self):
        comm_instance = self.commissions.filter(commission_user__role__name=MERCHANT).last()
        if comm_instance:
            return comm_instance.net_commission
        return 'NA'

    @property
    def admin_net_commission(self):
        comm_instance = self.commissions.all().filter(commission_user=None).last()
        if comm_instance:
            return comm_instance.net_commission
        return 'NA'


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


class VendorZruser(RowInfo):

    vendor = models.ForeignKey(to=Vendor, related_name='user_vendor_mappings')
    user = models.ForeignKey(to=ZrUser, related_name='vendor_user_mappings')
    is_attached_to_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'RetailerTerminalMappings'

    def __unicode__(self):
        return '%s - %s' % (self.vendor, self.user)