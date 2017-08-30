# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import csv

from urllib import urlencode

from django.http import HttpResponse
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
from zrwallet import models as zrwallet_models
from zrmapping import models as zrmappings_models
from common_utils.date_utils import last_month, last_week_range
from common_utils.user_utils import is_user_superuser
from utils import constants


MERCHANT = 'MERCHANT'
DISTRIBUTOR = 'DISTRIBUTOR'
SUBDISTRIBUTOR = 'SUBDISTRIBUTOR'
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


def get_merchant_qs(request):
    queryset = ZrUser.objects.filter(role__name=MERCHANT).order_by('-at_created')
    q = request.GET.get('q')
    filter = request.GET.get('filter')

    if is_user_superuser(request):
        if q:
            queryset = queryset.filter(
                first_name__contains=q,
            )

        if filter == 'Today':
            queryset = queryset.filter(at_created__gte=datetime.datetime.now().date())
        elif filter == 'Last-Week':
            queryset = queryset.filter(at_created__range=last_week_range())
        elif filter == 'Last-Month':
            queryset = queryset.filter(at_created__range=last_month())

        return queryset
    elif request.user.zr_admin_user.role.name == DISTRIBUTOR:
        queryset = request.user.zr_admin_user.zr_user.all_merchant_mappings.filter(
            is_active=True
        ).order_by('-at_created')
        if q:
            queryset = queryset.filter(
                merchant__first_name__contains=q,
            )
        else:
            queryset = queryset

        if filter == 'Today':
            queryset = queryset.filter(
                at_created__gte=datetime.datetime.now().date()
            )
        elif filter == 'Last-Week':
            queryset = queryset.filter(
                at_created__range=last_week_range()
            )
        elif filter == 'Last-Month':
            queryset = queryset.filter(
                at_created__range=last_month()
            )
    elif request.user.zr_admin_user.role.name == SUBDISTRIBUTOR:
        queryset = request.user.zr_admin_user.zr_user.merchant_sub_mappings.filter(
            is_active=True
        ).order_by('-at_created')
        if q:
            queryset = queryset.filter(
                merchant__first_name__contains=q,
            )
        else:
            queryset = queryset

        if filter == 'Today':
            queryset = queryset.filter(
                at_created__gte=datetime.datetime.now().date()
            )
        elif filter == 'Last-Week':
            queryset = queryset.filter(
                at_created__range=last_week_range()
            )
        elif filter == 'Last-Month':
            queryset = queryset.filter(
                at_created__range=last_month()
            )

    return queryset


def get_merchant_csv(request):
    merchant_qs = get_merchant_qs(request)
    pg_no = request.GET.get('page_no', 1)

    p = Paginator(merchant_qs, DistributorListView.paginate_by)
    try:
        page = p.page(pg_no)
    except EmptyPage:
        raise Http404

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="merchants.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Merchant Id',
        'Merchant Name',
        'DOJ',
        'Mobile No',
        'Email',
        'Status'
    ])

    for merchant in page.object_list:
        if not is_user_superuser(request):
            merchant = merchant.merchant

        writer.writerow(
            [
                merchant.id,
                merchant.first_name,
                merchant.at_created,
                merchant.mobile_no,
                merchant.email,
                'Active' if merchant.is_active else 'Inactive'
            ]
        )

    return response


class MerchantListView(ListView):
    template_name = 'zruser/merchant_list.html'
    context_object_name = 'merchant_list'
    paginate_by = 10

    def get_context_data(self, *args, **kwargs):
        context = super(MerchantListView, self).get_context_data(*args, **kwargs)
        queryset = self.get_queryset()

        q = self.request.GET.get('q')
        pg_no = self.request.GET.get('page_no')
        if not pg_no:
            pg_no = 1
        filter = self.request.GET.get('filter')
        context['is_queryset'] = False
        if q:
            context['q'] = q

        if filter:
            context['filter_by'] = filter

        if is_user_superuser(self.request):
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

            context['queryset'] = queryset

            p = Paginator(queryset, self.paginate_by)
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
            context['merchant_map'] = queryset
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

        return context

    def get_queryset(self):
        return get_merchant_qs(self.request)


class KYCRequestsView(ListView):
    template_name = 'zruser/kyc-requests.html'
    context_object_name = 'kyc_requests'
    paginate_by = 10

    def get_queryset(self):
        approve = self.request.GET.get('approve')
        reject = self.request.GET.get('approve')

        if approve or reject:
            if not ZrUser.objects.filter(id=approve or reject).last():
                raise Http404
            else:
                status = None
                if approve:
                    status = constants.KYC_APPROVAL_CHOICES[1][0]
                elif reject:
                    status = constants.KYC_APPROVAL_CHOICES[2][0]

                zruser = ZrUser.objects.filter(id=approve).last()
                zruser.kyc_details.all().update(
                    approval_status=status
                )
                zruser.is_kyc_verified = True
                zruser.save(update_fields=['is_kyc_verified'])

        queryset = ZrUser.objects.filter(
            is_kyc_verified=False
        ).order_by('-at_created')
        return queryset


class DistributorDetailView(DetailView):
    template_name = 'zruser/distributor_detail.html'
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    context_object_name = 'distributor'


def get_distributor_qs(request):
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR).order_by('-at_created')
    q = request.GET.get('q')
    filter = request.GET.get('filter')

    if q:
        queryset = queryset.filter(
            first_name__contains=q,
        )

    if filter == 'Today':
        queryset = queryset.filter(at_created__gte=datetime.datetime.now().date())
    elif filter == 'Last-Week':
        queryset = queryset.filter(at_created__range=last_week_range())
    elif filter == 'Last-Month':
        queryset = queryset.filter(at_created__range=last_month())

    return queryset


def download_distributor_list_csv(request):
    distributor_qs = get_distributor_qs(request)
    pg_no = request.GET.get('page_no', 1)

    p = Paginator(distributor_qs, DistributorListView.paginate_by)
    try:
        page = p.page(pg_no)
    except EmptyPage:
        raise Http404

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="distributors.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Distributor Id', 'Distributor Name', 'DOJ', 'Mobile', 'Email', 'Status'
    ])
    for distributor in page.object_list:
        writer.writerow([
            distributor.id,
            distributor.first_name,
            distributor.at_created,
            distributor.mobile_no,
            distributor.email,
            'Active' if distributor.is_active else 'Inactive'
        ])

    return response


class DistributorListView(ListView):
    template_name = 'zruser/distributor_list.html'
    queryset = ZrUser.objects.filter(role__name=DISTRIBUTOR)
    context_object_name = 'distributor_list'
    paginate_by = 10

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
            context['q'] = q

        if filter:
            context['filter_by'] = filter

        context['queryset'] = queryset
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
        return get_distributor_qs(self.request)


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
        password = '%s%s' % (merchant_zr_user.pan_no.lower().strip(), merchant_zr_user.first_name[:4].lower().strip())
        merchant_zr_user.pass_word = password
        merchant_zr_user.save()

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

        #  TODO: Update below url resolution to reverse.
        return HttpResponseRedirect('/user/distributor_list/')


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

        if request.user.zr_admin_user.role.name == DISTRIBUTOR:
            distributor = request.user.zr_admin_user.zr_user
            zrmappings_models.DistributorMerchant.objects.create(
                distributor=distributor,
                merchant=merchant_zr_user,
                is_active=True
            )
        elif request.user.zr_admin_user.role.name == SUBDISTRIBUTOR:
            distributor = request.user.zr_admin_user.zr_user
            zrmappings_models.SubDistributorMerchant.objects.create(
                sub_distributor=distributor,
                merchant=merchant_zr_user,
                is_active=True
            )
        elif is_user_superuser(request):
            distributor = ZrUser.objects.filter(first_name='zuser').last()
            if not distributor:
                raise Exception("Default distributor zuser not found in database")
            zrmappings_models.DistributorMerchant.objects.create(
                distributor=distributor,
                merchant=merchant_zr_user,
                is_active=True
            )
        else:
            raise Exception("Request user must be superuser of distributor")

        for doc in kyc_docs:
            KYCDetail.objects.create(
                type=KYCDocumentType.objects.get(name=doc['doc_type']),
                document_id=doc['doc_id'],
                document_link=doc['doc_url'],
                for_user=merchant_zr_user,
                role=merchant_zr_user.role
            )

        zrwallet_models.Wallet.objects.create(merchant=merchant_zr_user)
        # TODO: Update below url resolution to reverse.
        return HttpResponseRedirect('/user/merchant_list/')


class SubDistributorCreateView(CreateView):
    template_name = 'zruser/add_sub_distributor.html'
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
        merchant_zr_user.role = UserRole.objects.filter(name=SUBDISTRIBUTOR).last()
        password = '%s%s' % (merchant_zr_user.pan_no.lower().strip(), merchant_zr_user.first_name[:3].lower().strip())
        merchant_zr_user.pass_word = password
        merchant_zr_user.save()

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

        if request.user.zr_admin_user.role.name == DISTRIBUTOR:
            distributor = request.user.zr_admin_user.zr_user
            zrmappings_models.DistributorSubDistributor.objects.create(
                distributor=distributor,
                sub_distributor=merchant_zr_user,
                is_active=True
            )
        elif is_user_superuser(request):
            distributor = ZrUser.objects.filter(first_name='zuser').last()
            if not distributor:
                raise Exception("Default distributor zuser not found in database")
            zrmappings_models.DistributorMerchant.objects.create(
                distributor=distributor,
                sub_distributor=merchant_zr_user,
                is_active=True
            )
        else:
            raise Exception("Request user must be superuser of distributor")

        for doc in kyc_docs:
            KYCDetail.objects.create(
                type=KYCDocumentType.objects.get(name=doc['doc_type']),
                document_id=doc['doc_id'],
                document_link=doc['doc_url'],
                for_user=merchant_zr_user,
                role=merchant_zr_user.role
            )

        # TODO: Update below url resolution to reverse.
        return HttpResponseRedirect('/user/distributor_list/')
