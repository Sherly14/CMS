import re

from django import forms
from zruser.models import ZrAdminUser, ZrUser
from zrpayment.models import  PaymentRequest
from zrwallet.models import Wallet

class TopupForm(forms.ModelForm):

    class Meta:
        model = PaymentRequest
        fields = ['amount', 'dmt_amount', 'non_dmt_amount',
        'to_user', 'from_user','document',
        'payment_mode','from_account_no', 'to_account_no',
        'from_bank', 'to_bank', 'payment_type', 'comments']

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        merchant_id = self.data['to_user']
        payment_type = self.data['type']
        wallet = Wallet.objects.all().filter(merchant_id=merchant_id).fi
        if payment_type == "DMT":
            if int(wallet.dmt_balance) < int(amount) :
                raise forms.ValidationError('Amount Should be less than or equal to  your DMT Balance %s' % str(wallet.dmt_balance))

        if int(amount) <= 0:
            raise forms.ValidationError('Amount Should be greater than 0')

        return amount

