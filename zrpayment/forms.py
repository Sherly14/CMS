import re

from django import forms
from zruser.models import ZrAdminUser, ZrUser
from zrpayment.models import  PaymentRequest
from zrwallet.models import Wallet

class TopupForm(forms.ModelForm):

    class Meta:
        model = PaymentRequest
        fields = ['amount', 'dmt_amount', 'non_dmt_amount',
        'to_user', 'from_user','document','status',
        'payment_mode','from_account_no', 'to_account_no',
        'from_bank', 'to_bank', 'payment_type', 'comments']

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        merchant_id = self.data['to_user']
        payment_type = self.data['type']
        wallets = Wallet.objects.all().filter(merchant_id=merchant_id)
        if not wallets:
            raise forms.ValidationError(
                'You dont have any wallet')
        elif payment_type == "DMT" and  int(wallets[0].dmt_balance) < int(amount) :
            raise forms.ValidationError('Amount Should be less than or equal to  your DMT Balance %s' % str(wallets[0].dmt_balance))
        elif payment_type == "NONDMT" and int(wallets[0].non_dmt_balance) < int(amount):
            raise forms.ValidationError(
                'Amount Should be less than or equal to  your Non DMT Balance %s' % str(wallets[0].non_dmt_balance))

        if int(amount) <= 0:
            raise forms.ValidationError('Amount Should be greater than 0')

        return amount

