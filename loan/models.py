from django.db import models
from django.contrib.postgres.fields import JSONField
from zrpayment.models import PaymentRequest

import uuid
from zruser.models import ZrUser
from zrutils.common.modelutils import RowInfo, get_slugify_value


# Create your models here.
GENDER_CHOICES = (
    (u'M', u'Male'),
    (u'F', u'Female'),
    (u'O', u'Other'),
)

ZR_LOAN_STATUS_CHOICES = (
    (u'P', u'Pending'),
    (u'A', u'Approved'),
    (u'R', u'Rejected'),
    (u'R', u'Repaid'),
)

REQUEST_CHOICES = (
    (u'cc', u'Create Cohort'),
    (u'pq', u'Pre Qualifications'),
    (u'cl', u'Create Loan'),
    (u'ld', u'Loan Disbursal'),
    (u'ldc', u'Loan Disbursal Confirmation'),
    (u'pa', u'Payment Advice'),
    (u'pu', u'Payment Upload'),
)


class RequestLog(RowInfo):
    request_type = models.CharField(max_length=10, blank=True, null=True,
                                    choices=REQUEST_CHOICES)
    url = models.CharField(max_length=200, blank=True, null=True)
    user = models.ForeignKey(ZrUser, on_delete=models.PROTECT)
    response = JSONField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.url


class HappyOffer(RowInfo):
    user = models.ForeignKey(ZrUser, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cohort_uid = models.CharField(max_length=50)
    kyc_status = models.CharField(max_length=15)
    tenure = models.CharField(max_length=15)
    pq_response = JSONField(null=True, blank=True)
    calculated_on = models.DateField()

    def __str__(self):
        return self.user.first_name


class HappyLoan(RowInfo):
    user = models.ForeignKey(ZrUser, on_delete=models.PROTECT)
    loan_uid = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_request = models.ForeignKey(to=PaymentRequest, related_name='happy_loan')
    status = models.CharField(max_length=30)
    response = JSONField(null=True, blank=True)
    disbursed_on = models.DateField()

    def __str__(self):
        return self.user.first_name


class HappyRepayment(RowInfo):
    user = models.ForeignKey(ZrUser, on_delete=models.PROTECT)
    repayments_request_ref = models.CharField(max_length=50)
    loan_uid = models.CharField(max_length=50)
    amount_repaid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_request = models.ForeignKey(to=PaymentRequest, related_name='happy_repayment')
    status = models.CharField(max_length=15)

    def __str__(self):
        return '%s - (%s)' % (self.user, self.amount_repaid)
