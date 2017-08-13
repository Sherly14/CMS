# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from urllib import urlencode

from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.views.generic import CreateView, DetailView, ListView
from django.views import View
from django.http import HttpResponseRedirect
from django.contrib.auth import models as dj_auth_models
from django.core.paginator import EmptyPage
from django.http import Http404
from django.db import transaction
from django.core.paginator import Paginator
from django.urls import reverse
from django.shortcuts import redirect

from zruser import forms as zr_user_form
from zruser.models import ZrUser, UserRole, ZrAdminUser, KYCDocumentType, KYCDetail
from zrmapping import models as zrmappings_models
from common_utils.date_utils import last_month, last_week_range


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
    context_object_name = 'merchant_list'
    paginate_by = 1

    def get_context_data(self, *args, **kwargs):
        context = super(MerchantListView, self).get_context_data(*args, **kwargs)
        queryset = self.get_queryset()

        q = self.request.GET.get('q')
        pg_no = self.request.GET.get('page_no')
        if not pg_no:
            pg_no = 1
        filter = self.request.GET.get('filter')
        context['is_queryset'] = False

        if self.request.user.is_superuser:
            activate = self.request.GET.get('activate')
            disable = self.request.GET.get('disable')

            if activate:
                zruser = ZrUser.objects.filter(id=activate).last()
                if not zruser:
                    raise Http404

                zruser.is_active = True
                zruser.save(update_fields=['is_active'])

            if disable:
                zruser = ZrUser.objects.filter(id=disable).last()
                if not zruser:
                    raise Http404

                zruser.is_active = False
                zruser.save(update_fields=['is_active'])

            if q:
                context['queryset'] = queryset.filter(
                    first_name__contains=q,
                )
                context['q'] = q
            else:
                context['queryset'] = queryset

            if filter == 'Today':
                context['queryset'] = queryset.filter(at_created__gte=datetime.datetime.now().date())
                context['filter_by'] = filter
            elif filter == 'Last-Week':
                context['queryset'] = queryset.filter(at_created__range=last_week_range())
                context['filter_by'] = filter
            elif filter == 'Last-Month':
                context['queryset'] = queryset.filter(at_created__range=last_month())
                context['filter_by'] = filter

            p = Paginator(context['queryset'], self.paginate_by)
            try:
                page = p.page(pg_no)
            except EmptyPage:
                raise Http404

            context['queryset'] = page.object_list
            query_string = {}
            if q:
                query_string['q'] = q

            if filter:
                query_string['filter'] = filter

            if page.has_next():
                query_string['page_no'] = page.next_page_number()
                context['next_page_qs'] = urlencode(query_string)
                context['has_next_page'] = page.has_next()
            if page.has_previous():
                query_string['page_no'] = page.previous_page_number()
                context['prev_page_qs'] = urlencode(query_string)
                context['has_prev_page'] = page.has_previous()

            context['is_queryset'] = True
        elif self.request.user.zr_admin_user.role.name == DISTRIBUTOR:
            queryset = self.request.user.zr_admin_user.zr_user.all_merchant_mappings.filter(
                is_active=True
            ).order_by('-at_created')
            if q:
                context['merchant_map'] = queryset.filter(
                    merchant__first_name__contains=q,
                )
            else:
                context['merchant_map'] = queryset

            if filter == 'Today':
                context['merchant_map'] = queryset.filter(
                    at_created__gte=datetime.datetime.now().date()
                )
            elif filter == 'Last-Week':
                context['merchant_map'] = queryset.filter(
                    at_created__range=last_week_range()
                )
            elif filter == 'Last-Month':
                context['merchant_map'] = self.request.user.zr_admin_user.zr_user.all_merchant_mappings.filter(
                    at_created__range=last_month()
                )

            p = Paginator(context['merchant_map'], self.paginate_by)
            try:
                page = p.page(pg_no)
            except EmptyPage:
                raise Http404

            context['merchant_map'] = page.object_list

            query_string = {}
            if q:
                query_string['q'] = q

            if filter:
                query_string['filter'] = filter

            if page.has_next():
                query_string['page_no'] = page.next_page_number()
                context['next_page_qs'] = urlencode(query_string)
                context['has_next_page'] = page.has_next()
            if page.has_previous():
                query_string['page_no'] = page.previous_page_number()
                context['prev_page_qs'] = urlencode(query_string)
                context['has_prev_page'] = page.has_previous()

            context['is_queryset'] = False
            context['filter_by'] = filter

        return context

    def get_queryset(self):
        return ZrUser.objects.filter(role__name=MERCHANT).order_by('-at_created')


class DistributorDetailView(DetailView):
    template_name = 'zruser/distributor_detail.html'
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    context_object_name = 'distributor'


class DistributorListView(ListView):
    template_name = 'zruser/distributor_list.html'
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    context_object_name = 'distributor_list'
    paginate_by = 1

    def get_context_data(self, *args, **kwargs):
        context = super(DistributorListView, self).get_context_data()
        activate = self.request.GET.get('activate')
        disable = self.request.GET.get('disable')
        queryset = self.get_queryset()
        q = self.request.GET.get('q')
        filter = self.request.GET.get('filter')
        pg_no = self.request.GET.get('page_no', 1)

        if activate:
            zruser = ZrUser.objects.filter(id=activate).last()
            if not zruser:
                raise Http404

            zruser.is_active = True
            zrmappings_models.DistributorMerchant.objects.filter(
                distributor=zruser
            ).update(
                is_attaches_to_admin=False
            )
            dj_user = zruser.zr_user
            dj_user.is_active = True
            dj_user.save(update_fields=['is_active'])
            zruser.save(update_fields=['is_active'])

        if disable:
            zruser = ZrUser.objects.filter(id=disable).last()
            if not zruser:
                raise Http404

            zruser.is_active = False
            zrmappings_models.DistributorMerchant.objects.filter(
                distributor=zruser
            ).update(
                is_attaches_to_admin=True
            )
            dj_user = zruser.zr_user
            dj_user.is_active = False
            dj_user.save(update_fields=['is_active'])
            zruser.save(update_fields=['is_active'])

        if q:
            context['queryset'] = queryset.filter(
                first_name__contains=q,
            )
            context['q'] = q
        else:
            context['queryset'] = queryset

        if filter == 'Today':
            context['queryset'] = queryset.filter(at_created__gte=datetime.datetime.now().date())
            context['filter_by'] = filter
        elif filter == 'Last-Week':
            context['queryset'] = queryset.filter(at_created__range=last_week_range())
            context['filter_by'] = filter
        elif filter == 'Last-Month':
            context['queryset'] = queryset.filter(at_created__range=last_month())
            context['filter_by'] = filter

        p = Paginator(context['queryset'], self.paginate_by)
        try:
            page = p.page(pg_no)
        except EmptyPage:
            raise Http404

        context['queryset'] = page.object_list
        query_string = {}
        if q:
            query_string['q'] = q

        if filter:
            query_string['filter'] = filter

        if page.has_next():
            query_string['page_no'] = page.next_page_number()
            context['next_page_qs'] = urlencode(query_string)
            context['has_next_page'] = page.has_next()
        if page.has_previous():
            query_string['page_no'] = page.previous_page_number()
            context['prev_page_qs'] = urlencode(query_string)
            context['has_prev_page'] = page.has_previous()

        return context

    def get_queryset(self):
        return ZrUser.objects.filter(role__name=DISTRIBUTOR).order_by('-at_created')


class DashBoardView(ListView):
    template_name = 'zruser/user_dashboard.html'
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    context_object_name = 'distributor_list'


class DistributorCreateView(CreateView):
    template_name = 'zruser/add_distributor.html'
    kyc_doc_types = KYCDocumentType.objects.all().values_list('name', flat=True)

    def get(self, request):
        merchant_form = zr_user_form.MerchantDistributorForm()
        bank_detail_form = zr_user_form.BankDetailForm()

        return render(
            request, self.template_name,
            {
                'merchant_form': merchant_form,
                'bank_detail_form': bank_detail_form,
                'kyc_doc_types': self.kyc_doc_types
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
                    'kyc_doc_types': self.kyc_doc_types
                }
            )

        if not bank_detail_form.is_valid():
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                    'kyc_doc_types': self.kyc_doc_types
                }
            )

        kyc_docs = []
        for doc_type in KYCDocumentType.objects.all().values_list('name', flat=True):
            doc_type_name = doc_type.replace(' ', '-')
            doc_type_id = '-'.join(['doc_id', doc_type_name])

            if doc_type_name in request.POST:
                kyc_docs.append(
                    {
                        'doc_url': request.POST.get(doc_type_name),
                        'doc_id': request.POST.get(doc_type_id),
                        'doc_type': doc_type_name.replace('-', ' ')
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

        for doc in kyc_docs:
            KYCDetail.objects.create(
                type=KYCDocumentType.objects.get(name=doc['doc_type']),
                document_id=doc['doc_id'],
                document_link=doc['doc_url'],
                for_user=merchant_zr_user,
                role=merchant_zr_user.role
            )

        #TODO: Update below url resolution to reverse.
        return HttpResponseRedirect('/user/distributor_list/')

    # template_name = 'zruser/add_distributor.html'
    # form_class = zr_user_form.DistributorForm
    # queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    # context_object_name = 'distributor'


class MerchantCreateView(View):
    template_name = 'zruser/add_merchant.html'
    kyc_doc_types = KYCDocumentType.objects.all().values_list('name', flat=True)

    def get(self, request):
        merchant_form = zr_user_form.MerchantDistributorForm()
        bank_detail_form = zr_user_form.BankDetailForm()
        return render(
            request, self.template_name,
            {
                'merchant_form': merchant_form,
                'bank_detail_form': bank_detail_form,
                'kyc_doc_types': self.kyc_doc_types
            }
        )

    @transaction.atomic
    def post(self, request):
        merchant_form = zr_user_form.MerchantDistributorForm(data=request.POST)
        bank_detail_form = zr_user_form.BankDetailForm(data=request.POST)
        document_type_form = zr_user_form.KYCDocumentType()

        kyc_docs = []
        for doc_type in KYCDocumentType.objects.all().values_list('name', flat=True):
            doc_type_name = doc_type.replace(' ', '-')
            doc_type_id = '-'.join(['doc_id', doc_type_name])

            if doc_type_name in request.POST:
                kyc_docs.append(
                    {
                        'doc_url': request.POST.get(doc_type_name),
                        'doc_id': request.POST.get(doc_type_id),
                        'doc_type': doc_type_name.replace('-', ' ')
                    }
                )

        if not merchant_form.is_valid():
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                    'kyc_doc_type': None,
                    'kyc_doc_types': self.kyc_doc_types
                }
            )

        if not bank_detail_form.is_valid():
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                    'document_type_form': document_type_form,
                    'kyc_doc_types': self.kyc_doc_types
                }
            )

        merchant_zr_user = merchant_form.save(commit=False)
        merchant_zr_user.role = UserRole.objects.filter(name=MERCHANT).last()
        merchant_zr_user.pass_word = '%s%s' % (
            merchant_zr_user.pan_no, merchant_zr_user.first_name[-4:]
        )
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

        for doc in kyc_docs:
            KYCDetail.objects.create(
                type=KYCDocumentType.objects.get(name=doc['doc_type']),
                document_id=doc['doc_id'],
                document_link=doc['doc_url'],
                for_user=merchant_zr_user,
                role=merchant_zr_user.role
            )

        #TODO: Update below url resolution to reverse.
        return HttpResponseRedirect('/user/merchant_list/')
