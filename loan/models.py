from django.db import models
from django.contrib.postgres.fields import JSONField
from zrpayment.models import PaymentRequest

from django.contrib.auth.models import User
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


class UserProfile(RowInfo):
    user = models.OneToOneField(ZrUser, on_delete=models.PROTECT)
    first_name = models.CharField(max_length=200, blank=True, null=True)
    last_name = models.CharField(max_length=200, blank=True, null=True)
    father_name = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=100, blank=True, null=True)
    alternate_phone_number = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    aadhaar_number = models.CharField(max_length=15, blank=True, null=True)
    aadhaar_photo_front = models.CharField(max_length=512, blank=True)
    aadhaar_photo_back = models.CharField(max_length=512, blank=True)
    pan_number = models.CharField(max_length=15, blank=True, null=True)
    profile_photo = models.CharField(max_length=512, blank=True)
    pan_card_photo = models.CharField(max_length=512, blank=True)
    gender = models.CharField(max_length=5, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    pincode = models.CharField(max_length=15, blank=True, null=True)
    uid = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    locality = models.CharField(max_length=512, blank=True, null=True)
    street_address = models.CharField(max_length=512, blank=True, null=True)
    date_joined = models.DateField(blank=True, null=True)

    def save(self, *args, **kwargs):
        uuid_number = uuid.uuid4()
        if self.uid is None:
            self.uid = str(uuid_number.int)[:10]
        super(UserProfile, self).save(*args, **kwargs)

    def __getitem__(self, item):
        return getattr(self, item)

    def __str__(self):
        return self.first_name


class DailyTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.user.first_name


class RequestLog(RowInfo):
    request_type = models.CharField(max_length=10, blank=True, null=True,
                                    choices=REQUEST_CHOICES)
    url = models.CharField(max_length=200, blank=True, null=True)
    user = models.ForeignKey(ZrUser, on_delete=models.PROTECT)
    response = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.url


class UserHappyOffer(RowInfo):
    user = models.ForeignKey(ZrUser, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cohort_uid = models.CharField(max_length=50)
    kyc_status = models.CharField(max_length=15)
    tenure = models.CharField(max_length=15)
    pq_response = JSONField(null=True, blank=True)
    calculated_on = models.DateField()

    def __str__(self):
        return self.user.first_name


class UserHappyLoan(RowInfo):
    user = models.ForeignKey(ZrUser, on_delete=models.PROTECT)
    loan_uid = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_request = models.ForeignKey(to=PaymentRequest, related_name='happyloan')
    status = models.CharField(max_length=30)
    response = JSONField(null=True, blank=True)
    disbursed_on = models.DateField()

    def __str__(self):
        return self.user.first_name


class UserHappyRepayment(RowInfo):
    user = models.ForeignKey(ZrUser, on_delete=models.PROTECT)
    repayments_request_ref = models.CharField(max_length=50)
    loan_uid = models.CharField(max_length=50)
    amount_repaid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15)

    def __str__(self):
        return '%s - (%s)' % (self.user, self.amount_repaid)
