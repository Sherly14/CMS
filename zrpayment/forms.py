import re

from django import forms
from zruser.models import ZrAdminUser, ZrUser
from zrpayment.models import  PaymentRequest

class TopupForm(forms.ModelForm):

    class Meta:
        model = PaymentRequest
        fields = ['from_user', 'to_user', 'amount', 'dmt_amount', 'non_dmt_amount', 'payment_type']
