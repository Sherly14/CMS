import re

from django import forms
from django.contrib.auth import authenticate
from zruser.models import ZrAdminUser, ZrUser, BankDetail, KYCDocumentType


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
    mobile_no = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'tel'}),
        max_length=10,
        min_length=10
    )
    pincode = forms.CharField(widget=forms.TextInput())
    email = forms.EmailField(max_length=255, required=True)

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        if ' ' in first_name:
            raise forms.ValidationError('Space not allowed')
        if re.findall(r'[0-9]+', first_name):
            raise forms.ValidationError('Numbers not allowed')

        return first_name

    def clean_pan_no(self):
        pan_no = self.cleaned_data['pan_no']
        if pan_no:
            return pan_no.upper()
        else:
            raise forms.ValidationError('PAN number is compulsory')

        return pan_no

    def clean_mobile_no(self):
        mobile_no = self.cleaned_data['mobile_no']
        if ZrUser.objects.filter(mobile_no=mobile_no).count():
            raise forms.ValidationError('Mobile number already exist')

        if not mobile_no.isdigit():
            raise forms.ValidationError('Invalid mobile number')

        return mobile_no

    def clean_residence_address(self):
        residence_addr = self.cleaned_data['residence_address']
        if not residence_addr:
            raise forms.ValidationError('Field value cannot be empty')

        return residence_addr

    def __init__(self, *args, **kwargs):
        if kwargs.get('merchant'):
            self.Meta.fields.append('upi_id')
            _ = kwargs.pop('upi_id')

        super(MerchantDistributorForm, self).__init__(
            *args, **kwargs
        )

    class Meta:
        model = ZrUser
        fields = [
            'id', 'mobile_no', 'first_name', 'last_name', 'email', 'gender', 'city',
            'state', 'pincode', 'address_line_1', 'address_line_2',
            'business_name', 'pan_no', 'gstin', 'UPIID', 'residence_address', 'business_type'
        ]


class UpdateMerchantDistributorForm(forms.ModelForm):
    email = forms.EmailField(max_length=255, required=True)
    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        if ' ' in first_name:
            raise forms.ValidationError('Space not allowed')
        if re.findall(r'[0-9]+', first_name):
            raise forms.ValidationError('Numbers not allowed')

        return first_name


    def __init__(self, *args, **kwargs):
        if kwargs.get('merchant'):
            self.Meta.fields.append('upi_id')
            _ = kwargs.pop('upi_id')

        super(UpdateMerchantDistributorForm, self).__init__(
            *args, **kwargs
        )

    class Meta:
        model = ZrUser
        fields = [
           'first_name', 'last_name', 'email'
        ]

class BankDetailForm(forms.ModelForm):
    class Meta:
        model = BankDetail
        fields = [
            'account_no', 'IFSC_code', 'account_name', 'bank_name',
            'bank_city', 'account_type'
        ]


class DistributorForm(forms.ModelForm):

    class Meta:
        model = ZrAdminUser
        fields = ['mobile_no', 'gender', 'city', 'state', 'pincode']
