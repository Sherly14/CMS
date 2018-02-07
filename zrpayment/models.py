# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from decimal import Decimal

from django.db import models
from django.contrib.postgres.fields import JSONField

from zruser.models import ZrUser, Bank
from zrutils.common.modelutils import RowInfo, get_slugify_value
from zrtransaction import models as zr_transaction_models

PAYMENT_REQUEST_STATUS = (
    (0, 'Submitted'),
    (1, 'Approved'),
    (2, 'Rejected'),
    (3, 'Refund')
)



PAYMENT_REQUEST_TYPE = (
    (0, 'Credit'),
    (1, 'Commission'),
    (2, 'Topup'),
)


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
    """
    For payment request from merchant or distributor
    """

    merchant = models.ForeignKey(to=ZrUser, related_name='merchant_payment_requests')
    supervisor = models.ForeignKey(to=ZrUser, related_name='distributor_payment_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    dmt_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    non_dmt_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    merchant_payment_mode = models.ForeignKey(to=PaymentMode, related_name='merchant_requests')
    merchant_ref_no = models.CharField(max_length=20, null=True, blank=True)

    distributor_payment_mode = models.ForeignKey(to=PaymentMode, related_name='distributor_requests',
                                                 null=True, blank=True)
    distributor_ref_no = models.CharField(max_length=20, null=True, blank=True)

    is_supervisor_approved = models.NullBooleanField()
    is_admin_approved = models.NullBooleanField()
    comments = models.TextField(max_length=1024, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.amount).quantize(Decimal("0.00"))
        self.dmt_amount = Decimal(self.amount).quantize(Decimal("0.00"))
        self.non_dmt_amount = Decimal(self.amount).quantize(Decimal("0.00"))

        super(MerchantPaymentRequest, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'PaymentRequests'

    def __unicode__(self):
        return '%s - %s - %s' % (self.merchant, self.supervisor, self.amount)


class PaymentRequest(RowInfo):
    """
    For payment request from merchant or distributor
    """
    from_user = models.ForeignKey(to=ZrUser, related_name='payment_requester',
                                  help_text="Who generates request of payment")
    to_user = models.ForeignKey(to=ZrUser, related_name='payment_request_supervisor')
    amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    dmt_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)
    non_dmt_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.00)

    to_bank = models.ForeignKey(to=Bank, related_name='to_bank')
    to_account_no = models.CharField(max_length=30)

    from_bank = models.ForeignKey(to=Bank)
    from_account_no = models.CharField(max_length=30)

    payment_mode = models.ForeignKey(to=PaymentMode, related_name='payment_request_mode')
    ref_no = models.CharField(max_length=30, null=True, blank=True)
    document = models.CharField(max_length=512, blank=True)

    comments = models.TextField(max_length=1024, null=True, blank=True)
    reject_comments = models.TextField(max_length=1024, null=True, blank=True)
    status = models.PositiveSmallIntegerField(choices=PAYMENT_REQUEST_STATUS, default=0, null=True, blank=True)
    payment_type = models.PositiveSmallIntegerField(choices=PAYMENT_REQUEST_TYPE, default=0, null=True, blank=True)

    @property
    def request_type(self):
        _type = "DMT"
        if self.non_dmt_amount:
            _type = "Non DMT"
        return _type

    def save(self, *args, **kwargs):
        self.amount = Decimal(self.amount).quantize(Decimal("0.00"))
        self.dmt_amount = Decimal(self.dmt_amount).quantize(Decimal("0.00"))
        self.non_dmt_amount = Decimal(self.non_dmt_amount).quantize(Decimal("0.00"))

        super(PaymentRequest, self).save(*args, **kwargs)

    def get_status(self):
        if self.status == 0:
            return "Pending"
        elif self.status == 1:
            return "Accepted"
        elif self.status == 3:
            return "Refund"
        else:
            return "Rejected"

    class Meta:
        verbose_name_plural = 'PaymentRequests'

    def __unicode__(self):
        return '%s - %s - %s' % (self.from_user, self.to_user, self.amount)


class Payments(RowInfo):
    PENDING = 'Pending'
    SUCCESS = 'Success'
    FAILURE = 'Failure'
    REFUND_PENDING = 'Refund Pending'
    REFUNDED = 'Refunded'
    EXPIRED = 'Expired'
    SPAM = 'Spam'

    payment_status = (
        ('P', PENDING),
        ('S', SUCCESS),
        ('F', FAILURE),
        ('RP', REFUND_PENDING),
        ('R', REFUNDED),
        ('E', EXPIRED),
        ('SP', SPAM),
    )
    status = models.CharField(choices=payment_status, max_length=3, default=payment_status[0][0])
    vendor = models.ForeignKey(to='zrtransaction.Vendor', null=True, blank=True)
    mode = models.ForeignKey(PaymentMode)
    amount = models.DecimalField(decimal_places=3, default=0.00, max_digits=10)
    txn_id = models.CharField(max_length=128)
    vendor_txn_id = models.CharField(max_length=128)
    customer = models.CharField(max_length=256)
    user = models.ForeignKey(ZrUser)
    transaction_request_json = JSONField(default={})
    transaction_response_json = JSONField(default={})
    additional_charges = models.DecimalField(decimal_places=3, default=0.00, max_digits=10)
    is_settled = models.BooleanField(default=False)

    @property
    def settled(self):
        if self.is_settled:
            return "Yes"
        return "No"

    def __unicode__(self):
        return 'status=%s / amount=%s / pk=%s' % (
            self.status,
            self.amount,
            self.pk
        )
