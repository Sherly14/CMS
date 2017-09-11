# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal, getcontext, Context

from django.db import models

from zrcommission.utils.constants import COMMISSION_CHOICES
from zruser.models import ZrUser
from zrmapping import models as zr_mappings
from zrutils.common.modelutils import RowInfo


class Commission(RowInfo):

    transaction = models.ForeignKey(to='zrtransaction.Transaction', related_name='commissions')

    bill_payment_comm_structure = models.ForeignKey(
        to='zrcommission.BillPayCommissionStructure', related_name='bill_pay_commissions', null=True
    )
    dmt_comm_structure = models.ForeignKey(
        to='zrcommission.DMTCommissionStructure', related_name='dmt_commissions', null=True
    )

    commission_user = models.ForeignKey(to=ZrUser, null=True, blank=True, related_name='all_commissions')
    # distributor = models.ForeignKey(to=ZrUser, null=True, blank=True, related_name='distributor_commissions')
    # sub_distributor = models.ForeignKey(to=ZrUser, null=True, blank=True, related_name='sub_distributor_commissions')

    user_commission = models.DecimalField(max_digits=10, decimal_places=4, default=0.00)
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

    def gross_amount(self):
        return self.net_commission - (self.user_gst + self.user_tds)

    def save(self, *args, **kwargs):
        self.user_commission = Decimal(self.user_commission).quantize(Decimal("0.0000"), context=Context(prec=10))
        # self.distributor_commission = Decimal(self.merchant_commission).quantize(Decimal("0.00"))
        # self.sub_distributor_commission = Decimal(self.zrupee_commission).quantize(Decimal("0.00"))

        # self.zrupee_commission = Decimal(self.zrupee_commission).quantize(Decimal("0.00"))

        self.user_tds = Decimal(self.user_tds).quantize(Decimal("0.0000"), context=Context(prec=10))
        # self.distributor_tds = Decimal(self.distributor_tds).quantize(Decimal("0.0000"))
        # self.sub_distributor_tds = Decimal(self.sub_distributor_tds).quantize(Decimal("0.0000"))

        self.user_gst = Decimal(self.user_gst).quantize(Decimal("0.0000"), context=Context(prec=10))
        # self.distributor_gst = Decimal(self.distributor_gst).quantize(Decimal("0.0000"))
        # self.sub_distributor_gst = Decimal(self.sub_distributor_gst).quantize(Decimal("0.0000"))

        super(Commission, self).save(*args, **kwargs)

    def get_commission_without_comm(self):
        return '%.2f' % (float(self.net_commission) - float(self.user_tds))

    def get_merchant_commission(self):
        comm = Commission.objects.filter(
            transaction=self.transaction, commission_user__role__name='MERCHANT'
        ).last()
        if comm:
            return comm.net_commission
        else:
            return None

    class Meta:
        verbose_name_plural = 'Commissions'

    def __unicode__(self):
        return '%s - zrupee_commission com%s' % (self.transaction, self.net_commission)


class BillPayCommissionStructure(RowInfo):
    distributor = models.ForeignKey(to=ZrUser, related_name='commission_structures', null=True, blank=True)
    service_provider = models.ForeignKey(to='zrtransaction.ServiceProvider', related_name='bill_commission_structure')
    commission_type = models.CharField(max_length=2, choices=COMMISSION_CHOICES)
    net_margin = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    commission_for_zrupee = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    commission_for_distributor = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    commission_for_sub_distributor = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    commission_for_merchant = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    gst_value = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    tds_value = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    is_chargable = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # self.commission_for_zrupee = Decimal(
        #     self.commission_for_zrupee
        # ).quantize(Decimal("0.000"), context=Context(prec=10))
        # self.commission_for_distributor = Decimal(
        #     self.commission_for_distributor
        # ).quantize(Decimal("0.000"), context=Context(prec=10))
        # self.commission_for_merchant = Decimal(
        #     self.commission_for_merchant
        # ).quantize(Decimal("0.000"), context=Context(prec=10))
        # self.commission_for_sub_distributor = Decimal(
        #     self.commission_for_sub_distributor
        # ).quantize(Decimal("0.00"), context=Context(prec=10))

        super(BillPayCommissionStructure, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'BillPayCommissionStructure'

    def __unicode__(self):
        return '%s - net_margin %s' % (self.distributor, self.net_margin)


class DMTCommissionStructure(RowInfo):
    distributor = models.ForeignKey(
        to=ZrUser,
        related_name='dmt_commission_structures',
        null=True,
        blank=True
    )
    commission_type = models.CharField(max_length=2, choices=COMMISSION_CHOICES)
    transaction_vendor = models.ForeignKey(to='zrtransaction.Vendor')
    min_charge = models.DecimalField(max_digits=7, decimal_places=4, default=10.00)
    minimum_amount = models.DecimalField(max_digits=8, decimal_places=4, default=0.00)
    maximum_amount = models.DecimalField(max_digits=8, decimal_places=4, default=0.00)
    customer_fee = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    commission_for_zrupee = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    commission_for_distributor = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    commission_for_sub_distributor = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    commission_for_merchant = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    tds_value = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    gst_value = models.DecimalField(max_digits=7, decimal_places=4, default=0.00)
    is_enabled = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.commission_for_zrupee = Decimal(self.commission_for_zrupee).quantize(Decimal("0.00"))
        self.commission_for_distributor = Decimal(self.commission_for_distributor).quantize(Decimal("0.00"))
        self.commission_for_merchant = Decimal(self.commission_for_merchant).quantize(Decimal("0.00"))
        self.commission_for_sub_distributor = Decimal(self.commission_for_sub_distributor).quantize(Decimal("0.00"))

        super(DMTCommissionStructure, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'DMTCommissionStructure'

    def __unicode__(self):
        return '%s - net margin %s' % (self.transaction_vendor, self.customer_fee)
