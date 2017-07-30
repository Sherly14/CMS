from django import forms
from django.contrib.auth import authenticate
from zruser.models import ZrAdminUser, ZrUser


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


class MerchantForm(forms.ModelForm):

    def clean(self):
        print

    class Meta:
        model = ZrUser
        fields = ['mobile_no', 'first_name', 'last_name', 'email', 'gender', 'city', 'state', 'pincode']


class DistributorForm(forms.ModelForm):

    class Meta:
        model = ZrAdminUser
        fields = ['mobile_no', 'gender', 'city', 'state', 'pincode']
