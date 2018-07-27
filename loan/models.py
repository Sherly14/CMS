from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.
GENDER_CHOICES = (
    (u'M', u'Male'),
    (u'F', u'Female'),
    (u'O', u'Other'),
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


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    first_name = models.CharField(max_length=200, blank=True, null=True)
    last_name = models.CharField(max_length=200, blank=True, null=True)
    phone_number = models.CharField(max_length=100, blank=True, null=True)
    alternate_phone_number = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    aadhaar_number = models.CharField(max_length=15, blank=True, null=True)
    aadhaar_photo_front = models.ImageField(upload_to="aadhaar_front/", blank=True, null=True)
    aadhaar_photo_back = models.ImageField(upload_to="aadhaar_back/", blank=True, null=True)
    pan_number = models.CharField(max_length=15, blank=True, null=True)
    profile_photo = models.ImageField(upload_to="profile/", blank=True, null=True)
    pancard_photo = models.ImageField(upload_to="pancard/", blank=True, null=True)
    gender = models.CharField(max_length=5, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    pincode = models.CharField(max_length=15, blank=True, null=True)
    uid = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    date_joined = models.DateField(blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        uuid_number = uuid.uuid4()
        if self.uid is None:
            self.uid = str(uuid_number.int)[:10]
        super(UserProfile, self).save(*args, **kwargs)

    def __str__(self):
        return self.first_name


class DailyTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.first_name


class RequestLog(models.Model):
    request_type = models.CharField(max_length=10, blank=True, null=True,
                                    choices=REQUEST_CHOICES)
    url = models.CharField(max_length=200, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    response = models.TextField(blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.url


class UserHappyOffer(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    calculated_on = models.DateField()
    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.first_name


class Project(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True)
    slug = models.SlugField(unique=True)
    api_doc_shared = models.BooleanField(default=False)
    api_demo_given = models.BooleanField(default=False)
    physical_meeting = models.BooleanField(default=False)
    uat_release = models.BooleanField(default=False)
    risk_parameters_asked_santosh = models.BooleanField(default=False)
    risk_parameters_set_uat = models.BooleanField(default=False)
    risk_parameters_verified = models.BooleanField(default=False)

    contract_created_uat = models.BooleanField(default=False)
    product_created_uat = models.BooleanField(default=False)
    product_parameters_verified = models.BooleanField(default=False)
    cohort_step_completed = models.BooleanField(default=False)
    cohort_step_verified = models.BooleanField(default=False)
    loan_step_completed = models.BooleanField(default=False)
    loan_step_verified = models.BooleanField(default=False)
    repayment_step_completed = models.BooleanField(default=False)
    repayment_step_verified = models.BooleanField(default=False)

    uat_loan_numbers_verified = models.BooleanField(default=False)
    uat_demo_taken = models.BooleanField(default=False)
    data_migrated = models.BooleanField(default=False)

    contract_created_live = models.BooleanField(default=False)
    product_created_live = models.BooleanField(default=False)
    risk_parameters_set_live = models.BooleanField(default=False)
    live_credentials_released = models.BooleanField(default=False)
    screenshots_taken = models.BooleanField(default=False)

    live_loan_tested = models.BooleanField(default=False)
    marketing_call = models.BooleanField(default=False)

    date_added = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
