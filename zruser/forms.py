import re

from django import forms
from django.contrib.auth import authenticate
from zruser.models import ZrAdminUser, ZrUser, BankDetail


class LoginForm(forms.Form):
    username = forms.CharField(max_length=255, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if not user or not user.is_active:
            raise forms.ValidationError("Sorry, that login was invalid. Please try again.")
        return self.cleaned_data

    def login(self, request):
        print request
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        return user


class MerchantDistributorForm(forms.ModelForm):
    mobile_no = forms.CharField(widget=forms.TextInput(attrs={'type': 'tel'}))
    pincode = forms.CharField(widget=forms.TextInput())

    def clean_mobile_no(self):
        mobile_no = self.cleaned_data['mobile_no']
        if ZrUser.objects.filter(mobile_no=mobile_no).count():
            raise forms.ValidationError('Mobile number already exist')

        if not mobile_no.isdigit():
            raise forms.ValidationError('Invalid mobile number')

        return mobile_no

    def clean(self):
        form_data = self.cleaned_data

    class Meta:
        model = ZrUser
        fields = [
            'mobile_no', 'first_name', 'last_name', 'email', 'gender', 'city',
            'state', 'pincode', 'address_line_1', 'address_line_2',
            'business_name', 'pan_no'
        ]


class BankDetailForm(forms.ModelForm):
    class Meta:
        model = BankDetail
        fields = [
            'account_no', 'IFSC_code', 'account_name', 'bank_name',
            'bank_city'
        ]


class DistributorForm(forms.ModelForm):

    class Meta:
        model = ZrAdminUser
        fields = ['mobile_no', 'gender', 'city', 'state', 'pincode']
