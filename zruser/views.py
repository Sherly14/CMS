# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.views.generic import CreateView, DetailView, ListView
from django.views import View
from django.http import HttpResponseRedirect
from django.contrib.auth import models as dj_auth_models

from django.db import transaction

from zruser import forms as zr_user_form
from zruser.models import ZrUser, UserRole, ZrAdminUser
from zrmapping import models as zrmappings_models

MERCHANT = 'MERCHANT'
DISTRIBUTOR = 'DISTRIBUTOR'
BENEFICIARY = 'BENEFICIARY'


def login_view(request):
    form = zr_user_form.LoginForm(request.POST or None)
    if request.POST and form.is_valid():
        user = form.login(request)
        if user:
            login(request, user)
            return redirect('user:dashboard')
    return render(request, 'login.html', {'login_form': form})


class MerchantDetailView(DetailView):
    template_name = 'zruser/merchant_detail.html'
    queryset = ZrUser.objects.filter(role__name=MERCHANT)
    context_object_name = 'merchant'


class MerchantListView(ListView):
    template_name = 'zruser/merchant_list.html'
    queryset = ZrUser.objects.filter(role__name=MERCHANT)
    context_object_name = 'merchant_list'


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


class DistributorCreateView(CreateView):
    template_name = 'zruser/add_distributor.html'

    def get(self, request):
        merchant_form = zr_user_form.MerchantDistributorForm()
        bank_detail_form = zr_user_form.BankDetailForm()

        return render(
            request, self.template_name,
            {
                'merchant_form': merchant_form,
                'bank_detail_form': bank_detail_form
            }
        )

    @transaction.atomic
    def post(self, request):
        merchant_form = zr_user_form.MerchantDistributorForm(data=request.POST)
        bank_detail_form = zr_user_form.BankDetailForm(data=request.POST)

        if not merchant_form.is_valid():
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                }
            )

        if not bank_detail_form.is_valid():
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                }
            )

        merchant_zr_user = merchant_form.save(commit=False)
        merchant_zr_user.role = UserRole.objects.filter(name=DISTRIBUTOR).last()
        merchant_zr_user.save()

        password = '%s%s' % (merchant_zr_user.pan_no, merchant_zr_user.first_name[-4:])
        dj_user = dj_auth_models.User.objects.create_user(
            merchant_zr_user.mobile_no,
            email=merchant_zr_user.email,
            password=password
        )
        bank_detail = bank_detail_form.save()
        bank_detail.for_user = merchant_zr_user
        bank_detail.save(update_fields=['for_user'])

        ZrAdminUser.objects.create(
            id=dj_user,
            mobile_no=merchant_zr_user.mobile_no,
            city=merchant_zr_user.city,
            state=merchant_zr_user.state,
            pincode=merchant_zr_user.pincode,
            address=merchant_zr_user.address_line_1,
            role=merchant_zr_user.role,
            zr_user=merchant_zr_user
        )
        #TODO: Update below url resolution to reverse.
        return HttpResponseRedirect('/user/distributor_list/')

    # template_name = 'zruser/add_distributor.html'
    # form_class = zr_user_form.DistributorForm
    # queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    # context_object_name = 'distributor'


class MerchantCreateView(View):
    template_name = 'zruser/add_merchant.html'
    def get(self, request):
        merchant_form = zr_user_form.MerchantDistributorForm()
        bank_detail_form = zr_user_form.BankDetailForm()
        return render(
            request, self.template_name,
            {
                'merchant_form': merchant_form,
                'bank_detail_form': bank_detail_form
            }
        )

    @transaction.atomic
    def post(self, request):
        merchant_form = zr_user_form.MerchantDistributorForm(data=request.POST)
        bank_detail_form = zr_user_form.BankDetailForm(data=request.POST)

        if not merchant_form.is_valid():
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                }
            )

        if not bank_detail_form.is_valid():
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                }
            )

        merchant_zr_user = merchant_form.save(commit=False)
        merchant_zr_user.role = UserRole.objects.filter(name=MERCHANT).last()
        merchant_zr_user.save()
        bank_detail = bank_detail_form.save()
        bank_detail.for_user = merchant_zr_user
        bank_detail.save(update_fields=['for_user'])

        distributor = None
        if request.user.zr_admin_user.role.name == DISTRIBUTOR:
            distributor = request.user.zr_admin_user.zr_user
        elif request.user.is_superuser:
            distributor = ZrUser.objects.filter(first_name='zuser').last()
            if not distributor:
                raise Exception("Default distributor zuser not found in database")
        else:
            raise Exception("Request user must be superuser of distributor")

        zrmappings_models.DistributorMerchant.objects.create(
            distributor=distributor,
            merchant=merchant_zr_user,
            is_active=True
        )

        #TODO: Update below url resolution to reverse.
        return HttpResponseRedirect('/user/merchant_list/')
