# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import login
from django.shortcuts import render
from django.views.generic import CreateView, DetailView, ListView

from zruser.forms import LoginForm, MerchantForm, DistributorForm
from zruser.models import ZrUser

MERCHANT = 'MERCHANT'
DISTRIBUTOR = 'DISTRIBUTOR'
BENEFICIARY = 'BENEFICIARY'


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.POST and form.is_valid():
        user = form.login(request)
        if user:
            login(request, user)
            return render(request, 'user_profile.html')
    return render(request, 'login.html', {'login_form': form})


class MerchantCreateView(CreateView):
    template_name = 'zruser/add_merchant.html'
    form_class = MerchantForm
    queryset = ZrUser.objects.filter(role__name=MERCHANT)
    context_object_name = 'merchant_list'


class MerchantDetailView(DetailView):
    template_name = 'zruser/merchant_detail.html'
    queryset = ZrUser.objects.filter(role__name=MERCHANT)
    context_object_name = 'merchant'


class MerchantListView(ListView):
    template_name = 'zruser/merchant_list.html'
    queryset = ZrUser.objects.filter(role__name=MERCHANT)
    context_object_name = 'merchant_list'


class DistributorCreateView(CreateView):
    template_name = 'zruser/add_distributor.html'
    form_class = DistributorForm
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    context_object_name = 'distributor'


class DistributorDetailView(DetailView):
    template_name = 'zruser/distributor_detail.html'
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    context_object_name = 'distributor'


class DistributorListView(ListView):
    template_name = 'zruser/distributor_list.html'
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    context_object_name = 'distributor_list'


class DashBoardView(ListView):
    template_name = 'zruser/user_dashboard.html'
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    context_object_name = 'distributor_list'
