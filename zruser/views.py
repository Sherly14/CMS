# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import datetime
import requests
import json
from urllib import urlencode

from django.conf import settings
from django.contrib.auth import login, models as dj_auth_models
from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from django.db import transaction
from django.db.models import F
from django.db.models import Q
from django.db.models import Sum
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from common_utils import date_utils
from common_utils import transaction_utils
from common_utils import zrupee_security
from common_utils.date_utils import last_month, last_week_range
from common_utils.report_util import get_excel_doc, update_excel_doc

from common_utils.user_utils import is_user_superuser, is_user_retailer

from common_utils.user_utils import is_user_superuser, is_zruser_djuser

from mapping import *
from utils import constants
from zrcommission import models as commission_models
from zrmapping import models as zrmappings_models
from zrpayment.models import PaymentMode
from zrpayment import forms as zr_payment_form
from zrtransaction import models as transaction_models
from zrtransaction.utils.constants import RECHARGES_TYPE, TRANSACTION_STATUS_SUCCESS, \
    TRANSACTION_STATUS_FAILURE, BILLS_TYPE, TRANSACTION_STATUS_PENDING
from zrtransaction.views import get_transactions_qs_with_dict
from zruser import forms as zr_user_form
from zruser.models import ZrUser, UserRole, ZrAdminUser, KYCDocumentType, KYCDetail, Bank, ZrTerminal
from zruser.utils.constants import DEFAULT_DISTRIBUTOR_MOBILE_NUMBER
from zrwallet import models as zrwallet_models
from django.contrib.auth.models import User
from itertools import chain

from zrcms.env_vars import QUICKWALLET_ZR_PARTERNERID, QUICKWALLET_SECRET, QUICKWALLET_API_CRUD_URL,\
    QUICKWALLET_API_CARD_URL, QUICKWALLET_API_LISTCARD_URL, QUICKWALLET_API_GENERATEOTP_URL, QUICKWALLET_API_ISSUE_MOBILE_URL,\
    QUICKWALLET_API_ACTIVATE_CARD_URL, QUICKWALLET_API_RECHARGE_CARD_URL, QUICKWALLET_API_PAY_URL, QUICKWALLET_API_DEACTIVATE_CARD_URL,\
    QUICKWALLET_PAYMENT_HISTORY_URL, QUICKWALLET_CREATE_OFFER_URL, QUICKWALLET_OFFER_LIST_URL, QUICKWALLET_OFFER_ASSIGN_TO_RETAILER_URL, \
    QUICKWALLET_API_LISTCARD_ACTIVATED_URL

MERCHANT = 'MERCHANT'
DISTRIBUTOR = 'DISTRIBUTOR'
SUBDISTRIBUTOR = 'SUBDISTRIBUTOR'
BENEFICIARY = 'BENEFICIARY'
CHECKER = 'CHECKER'
ADMINSTAFF = 'ADMINSTAFF'
RETAILER = 'RETAILER'
QUICKWALLET = 'QUICKWALLET'
TERMINAL = 'TERMINAL'


def redirect_user(request):
    user = request.user
    if is_user_superuser(request):
        return redirect('user:dashboard')
    elif user.zr_admin_user.role.name == CHECKER:
        return redirect('user:kyc-requests')
    else:
        return redirect('user:dashboard')


def login_view(request):
    if request.user.is_authenticated():
        return redirect_user(request)

    form = zr_user_form.LoginForm(request.POST or None)
    if request.POST and form.is_valid():
        user = form.login(request)
        if user:
            login(request, user)
            return redirect_user(request)

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
            query_filter = Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(mobile_no__icontains=q)
            queryset = queryset.filter(
                query_filter
            )

        if filter == 'Today':
            queryset = queryset.filter(at_created__gte=datetime.datetime.now().date())
        elif filter == 'Last-Week':
            queryset = queryset.filter(at_created__range=last_week_range())
        elif filter == 'Last-Month':
            queryset = queryset.filter(at_created__range=last_month())
    elif request.user.zr_admin_user.role.name == DISTRIBUTOR:
        merchant_id = request.GET.get('merchant-id')
        merchant_id_list = list(request.user.zr_admin_user.zr_user.all_merchant_mappings.filter(
            is_active=True
        ).values_list('merchant', flat=True))
        usermerchantlist = ZrUser.objects.filter(id__in=merchant_id_list).order_by('-at_created')
        merchantDistlist = usermerchantlist
        usersubdistributor = zrmappings_models.DistributorSubDistributor.objects.filter(distributor=request.user.zr_admin_user.zr_user)
        sub_distributor_list2 = []
        dist_sub_merchant_list = []
        dist_sub_all_merchant = []
        if usersubdistributor:
            for subdist2 in usersubdistributor:
                sub_distributor_list2.append(subdist2.sub_distributor_id)

        if sub_distributor_list2:
            usersubdistmerch = zrmappings_models.SubDistributorMerchant.objects.filter(sub_distributor_id__in = sub_distributor_list2 )
            for data in usersubdistmerch:
                dist_sub_merchant_list.append(data.merchant_id)
            dist_sub_all_merchant = ZrUser.objects.filter(id__in=dist_sub_merchant_list).order_by('-at_created')
            merchantDistlist = merchantDistlist | dist_sub_all_merchant

        queryset = merchantDistlist

        if merchant_id == "-1":
            DISTMERCHLIST = []
            DistMercahntData = zrmappings_models.DistributorMerchant.objects.filter(distributor_id=request.user.zr_admin_user.zr_user)

            if DistMercahntData:
                for d in DistMercahntData:
                    DISTMERCHLIST.append(d.merchant_id)

            if DISTMERCHLIST:
                queryset = ZrUser.objects.filter(id__in=DISTMERCHLIST).order_by('-at_created')

        if q:
            query_filter = Q(
                first_name__icontains=q
            ) | Q(
                last_name__icontains=q
            ) | Q(
                mobile_no__contains=q
            )
            queryset = queryset.filter(
                query_filter
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
        merchant_queryset = request.user.zr_admin_user.zr_user.merchant_sub_mappings.filter(
            is_active=True
        ).order_by('-at_created')
        queryset = ZrUser.objects.filter(id__in=merchant_queryset.values_list('merchant', flat=True)).order_by(
            '-at_created')
        if q:
            query_filter = Q(
                first_name__icontains=q
            ) | Q(
                last_name__icontains=q
            ) | Q(
                mobile_no__contains=q
            )
            queryset = queryset.filter(
                query_filter
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
            queryset = queryset.filter(at_created__range=last_month())
    sub_merchant_id = []
    subDistMerchant = zrmappings_models.SubDistributorMerchant.objects.filter(sub_distributor=request.user.zr_admin_user.zr_user)
    if subDistMerchant:
        for sub_dist in subDistMerchant:
            sub_merchant_id.append(sub_dist.merchant_id)

    if sub_merchant_id:
        queryset=ZrUser.objects.filter(id__in=sub_merchant_id)

    distributor_id = request.GET.get('distributor-id')

    merchant_id = request.GET.get('merchant-id')

    sub_distributor_id = request.GET.get('sub-distributor-id')

    if merchant_id != None and int(merchant_id) > 0:
        queryset = ZrUser.objects.filter(id=merchant_id)

    elif distributor_id != None and int(distributor_id) > 0:
        distributorMerchantList = []
        distributorSubdistributorList = []
        SubDistributorMerchantList = []
        subDsitributorMerchnat = []
        distributorMerchant = zrmappings_models.DistributorMerchant.objects.filter(distributor_id=distributor_id)

        if distributorMerchant:
            for merchantData in distributorMerchant:
                distributorMerchantList.append(merchantData.merchant_id)

        distributorSubdistributor = zrmappings_models.DistributorSubDistributor.objects.filter(distributor_id=distributor_id)

        if distributorSubdistributor:
            for subDsitributor in distributorSubdistributor:
                distributorSubdistributorList.append(subDsitributor.sub_distributor_id)

        if distributorSubdistributorList:
            subDsitributorMerchnat = zrmappings_models.SubDistributorMerchant.objects.filter(sub_distributor_id__in=distributorSubdistributorList)

        if subDsitributorMerchnat:
             for subMerchant in subDsitributorMerchnat:
                 SubDistributorMerchantList.append(subMerchant.merchant_id)

        userDsitributorMerchant = ZrUser.objects.filter(id__in=distributorMerchantList)
        userSubDistributorMerchant = ZrUser.objects.filter(id__in=SubDistributorMerchantList)

        merchantDataList = userDsitributorMerchant| userSubDistributorMerchant

        queryset = merchantDataList

    if distributor_id != None and  merchant_id == "-1":
        distmerchantlist = []
        DistM = zrmappings_models.DistributorMerchant.objects.filter(distributor_id=distributor_id)

        if DistM:
            for dist in DistM:
                distmerchantlist.append(dist.merchant_id)

        if distmerchantlist:
            queryset = ZrUser.objects.filter(id__in=distmerchantlist)

    if sub_distributor_id != None and int(sub_distributor_id) > 0:
        subMerchant = zrmappings_models.SubDistributorMerchant.objects.filter(sub_distributor_id=sub_distributor_id)
        merchantlist = []
        if subMerchant:
            for sub_merchant in subMerchant:
                merchantlist.append(sub_merchant.merchant_id)

        if merchantlist:
           queryset = ZrUser.objects.filter(id__in=merchantlist)

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')

    if start_date != None and end_date != None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))

    return queryset


def get_merchant_csv(request):
    merchant_qs = get_merchant_qs(request)
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

    for merchant in merchant_qs:
       # if not is_user_superuser(request):
        #    merchant = merchant.merchant

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


def get_report_excel(report_params):
    DOC_HEADERS = (
        ('Transaction Type', 'type.name'),
        ('Transaction ID', 'pk'),
        ('Distributor Name', 'distributor_name'),
        # ('Merchant Name', 'merchant_name'),

        ('Agent Email ID', 'user.email'),
        ('Agent Name', 'user.full_name'),
        ('Agent City', 'user.city'),
        ('Agent Pin code', 'user.pincode'),
        ('Agent State', 'user.state'),

        ('Beneficiary bank name', 'beneficiary_user.bank.bank_name'),
        ('Beneficiary bank code', 'beneficiary_user.bank.bank_code'),
        ('Beneficiary account number', 'beneficiary_user.bank.eko_bank_id'),

        ('Transaction Amount', 'amount'),
        ('Commission Fee', 'commission_fee'),
        ('Commission Value', 'commission_value'),
        ('Status', 'formatted_status'),
        ('Created date', 'created_date'),
        ('Created time', 'created_time'),
    )
    merchant_headers = (
        ('Merchant Mobile', 'merchant_mobile'),
        ('Merchant Gross Commission', 'merchant_gross_commission'),
        ('Merchant GST', 'merchant_gst'),
        ('Merchant TDS', 'merchant_tds'),
        ('Merchant Net Commission', 'merchant_net_commission'),
    )
    distributor_headers = (
        ('Distributor Gross Commission', 'dist_gross_commission'),
        ('Distributor GST', 'dist_gst'),
        ('Distributor TDS', 'dist_tds'),
        ('Distributor Net Commission', 'dist_net_commission'),
    )
    sub_distributor_headers = (
        ('Sub-Distributor Gross Commission', 'sub_dist_gross_commission'),
        ('Sub-Distributor GST', 'sub_dist_gst'),
        ('Sub-Distributor  TDS', 'sub_dist_tds'),
        ('Sub-Distributor  Net Commission', 'sub_dist_net_commission'),
    )
    DOC_HEADERS += merchant_headers
    is_sub_dist = False
    if report_params.get('user_type') == "SU":
        DOC_HEADERS += distributor_headers
        DOC_HEADERS += sub_distributor_headers
        DOC_HEADERS += (('Zrupee Net Commission', 'admin_net_commission'),)
    elif report_params.get('user_type') == SUBDISTRIBUTOR:
        DOC_HEADERS += sub_distributor_headers
        is_sub_dist = True
    elif report_params.get('user_type') == DISTRIBUTOR:
        DOC_HEADERS += distributor_headers
        DOC_HEADERS += sub_distributor_headers

    transactions_qs = get_transactions_qs_with_dict(report_params)
    paginator = Paginator(transactions_qs, 1)
    import string, random
    unique_name = datetime.datetime.now().strftime("%d-%m-%YT%H:%M:%S-") + ''.join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    report_file_path = settings.REPORTS_PATH + "/" + unique_name + ".xlsx"
    for x in paginator.page_range:
        page_data = paginator.page(x)
        if x == 1:
            workbook, worksheet_s, last_row = get_excel_doc(
                page_data.object_list, DOC_HEADERS, report_file_path, page_data.has_next(),
                user_type=report_params.get('user_type')
            )
        else:
            workbook, worksheet_s, last_row = update_excel_doc(
                page_data.object_list, DOC_HEADERS, workbook, worksheet_s, last_row,
                page_data.has_next())
    return report_file_path


def mail_report(request):
    email_list = request.POST.get('email', '').split(",")
    if is_user_superuser(request):
        user_type = "SU"
    elif transaction_utils.is_sub_distributor(request.user.zr_admin_user.zr_user):
        user_type = SUBDISTRIBUTOR
    else:
        user_type = request.user.zr_admin_user.role.name
    report_params = {
        "email_list": email_list,
        "user_type": user_type,
        "q": request.GET.get('q', ""),
        "filter": request.GET.get('filter', ""),
        "period": request.POST.get('period', ''),
        "start_date": request.POST.get('startDate',''),
        "end_date": request.POST.get('endDate',''),
        "user_id": request.user.id,
    }
    from zruser import tasks as zu_celery_tasks
    zu_celery_tasks.send_dashboard_report.apply_async(args=[report_params])
    return JsonResponse({"success": True})


class MerchantListView(ListView):
    template_name = 'zruser/merchant_list.html'
    context_object_name = 'merchant_list'
    paginate_by = 10

    def get_context_data(self, *args, **kwargs):
        context = super(MerchantListView, self).get_context_data(*args, **kwargs)
        queryset = self.get_queryset()
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        q = self.request.GET.get('q')
        pg_no = self.request.GET.get('page_no')
        # sub_dist_merchant_list =zrmappings_models.SubDistributorMerchant.objects.all()
        distributor_list = ZrUser.objects.filter(role__name=DISTRIBUTOR)
        merchant_id = self.request.GET.get('merchant-id')
        distributor_id = self.request.GET.get('distributor-id')
        sub_distributor = []
        sub_distributor_list = []
        sub_dist_merchant = []
        merchant = []
        subDistMerchant = {}
        sub_distributor_id = self.request.GET.get('sub-distributor-id')

        if self.request.user.zr_admin_user.role.name == DISTRIBUTOR:
            try:
                sub_distributor = zrmappings_models.DistributorSubDistributor.objects.filter(distributor=self.request.user.zr_admin_user.zr_user)
                merchant = zrmappings_models.DistributorMerchant.objects.filter(distributor=self.request.user.zr_admin_user.zr_user)
                distributor_list = []
            except:
                pass

        if self.request.user.zr_admin_user.role.name == SUBDISTRIBUTOR:
            try:
                #sub_distributor = zrmappings_models.DistributorSubDistributor.objects.filter(sub_distributor=self.request.user.zr_admin_user.zr_user)
                merchant = zrmappings_models.SubDistributorMerchant.objects.filter(sub_distributor=self.request.user.zr_admin_user.zr_user)
                distributor_list = []
            except:
                pass

        if is_user_superuser(self.request):
            merchant = zrmappings_models.DistributorMerchant.objects.filter(distributor_id=distributor_id)
            sub_distributor = zrmappings_models.DistributorSubDistributor.objects.filter(distributor_id=distributor_id)

        if sub_distributor:
            for subdist in sub_distributor:
                sub_distributor_list.append(subdist.sub_distributor_id)

        if sub_distributor_list:
            sub_dist_merchant = zrmappings_models.SubDistributorMerchant.objects.filter(sub_distributor_id__in = sub_distributor_list )

        if sub_dist_merchant:
            for sub_merchant in sub_dist_merchant:
                if sub_merchant.sub_distributor.id in subDistMerchant:
                    subDistMerchant[sub_merchant.sub_distributor.id].append(
                        [sub_merchant.sub_distributor.first_name, sub_merchant.merchant.id, sub_merchant.merchant.first_name])
                else:
                    subDistMerchant[sub_merchant.sub_distributor.id] = [
                        [sub_merchant.sub_distributor.first_name, sub_merchant.merchant.id, sub_merchant.merchant.first_name]]

        if merchant:
            for distmerchant in merchant:
                if -1 in subDistMerchant:
                    subDistMerchant[-1].append(["MERCHANTS", distmerchant.merchant.id, distmerchant.merchant.first_name])
                else:
                    subDistMerchant[-1] = [["MERCHANTS", distmerchant.merchant.id, distmerchant.merchant.first_name]]

        if not pg_no:
            pg_no = 1
        filter = self.request.GET.get('filter')
        context['is_queryset'] = False
        if q:
            context['q'] = q

        if filter:
            context['filter_by'] = filter

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if subDistMerchant:
            context['subDistMerchant'] = subDistMerchant

        if merchant_id:
            context['merchant_id'] = int(merchant_id)

        if distributor_id:
            context['distributor_id'] =int(distributor_id)

        if is_user_superuser(self.request):
            context['distributor_list'] = distributor_list

        context['subDistMerchant'] = subDistMerchant

        if sub_distributor_id:
            context['sub_distributor_id'] = int(sub_distributor_id)

        if merchant_id:
            context['sub_distributor_id'] = int(merchant_id)

        context['queryset'] = queryset
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
        elif self.request.user.zr_admin_user.role.name in [DISTRIBUTOR, SUBDISTRIBUTOR]:
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

    def get_context_data(self, **kwargs):
        filter_by = self.request.GET.get('filter', 'All')
        q = self.request.GET.get('q', "")
        user_list = ZrUser.objects.filter(is_kyc_verified=False)
        context = super(KYCRequestsView, self).get_context_data(**kwargs)
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        queryset = self.get_queryset()
        context['filter_by'] = filter_by
        context['q'] = q
        user_id = self.request.GET.get('user_id')

        approve = self.request.GET.get('approve')
        reject = self.request.GET.get('reject')
        if approve or reject:
            if not ZrUser.objects.filter(id=approve or reject).last():
                raise Http404
            else:
                status = None
                zruser = ZrUser.objects.filter(id=approve or reject).last()

                if approve:
                    status = constants.KYC_APPROVAL_CHOICES[1][0]
                    zruser.is_kyc_verified = True

                elif reject:
                    status = constants.KYC_APPROVAL_CHOICES[2][0]

                zruser.kyc_details.filter(approval_status='I').update(
                    approval_status=status
                )
                zruser.save(update_fields=['is_kyc_verified'])

                if zruser.is_kyc_verified and status == constants.KYC_APPROVAL_CHOICES[1][0]:
                    password = zrupee_security.generate_password()
                    zruser.pass_word = password
                    zruser.save(update_fields=['pass_word'])

                    if is_zruser_djuser(zruser):
                        dj_user = zruser.zr_user.id
                        dj_user.set_password(password)
                        dj_user.save()

                        zruser.send_welcome_email(password)

        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page', 1)

        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)

        context['page_obj'] = queryset

        if user_list:
            context['user_list'] = user_list

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if user_id:
            context['user_id'] = int(user_id)

        return context

    def get_queryset(self):

        filter_by = self.request.GET.get('filter', 'All')
        q = self.request.GET.get('q')
        user_id = self.request.GET.get('user_id')
        queryset = ZrUser.objects.filter(
            is_kyc_verified=False
        ).order_by('-at_created')

        if filter_by == "Last-Week":
            queryset = queryset.filter(at_created__range=last_week_range())
        elif filter_by == "Last-Month":
            queryset = queryset.filter(at_created__range=last_month())
        elif filter_by == "Today":
            queryset = queryset.filter(at_created__date__gte=datetime.date.today())

        if q:
            # added search from mobile number of user
            query = Q(
                first_name__icontains=q
            ) | Q(
                last_name__icontains=q
            ) | Q(
                mobile_no__contains=q
            )
            queryset = queryset.filter(query)
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')

        if start_date != None and end_date != None:
            queryset = queryset.filter(at_created__range=(start_date, end_date))

        if user_id != None and int(user_id) > 0:
            queryset = queryset.filter(id=user_id)

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
        query_filter = Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(mobile_no__icontains=q)
        queryset = queryset.filter(
            query_filter
        )

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')

    if start_date!=None and end_date!=None:
        queryset=queryset.filter(at_created__range=(start_date, end_date))

    distributor_id = request.GET.get('distributor-id')

    if distributor_id!=None and int(distributor_id) > 0:
        queryset = queryset.filter(id=distributor_id)


    if filter == 'Today':
        queryset = queryset.filter(at_created__gte=datetime.datetime.now().date())
    elif filter == 'Last-Week':
        queryset = queryset.filter(at_created__range=last_week_range())
    elif filter == 'Last-Month':
        queryset = queryset.filter(at_created__range=last_month())

    return queryset


def get_sub_distributor_qs(request):
    queryset = zrmappings_models.DistributorSubDistributor.objects.none()
    if request.user.zr_admin_user:
        try:
            queryset = request.user.zr_admin_user.zr_user.sub_dist_dist_mappings.order_by('-at_created')
        except:
            pass

    if is_user_superuser(request):
        queryset = zrmappings_models.DistributorSubDistributor.objects.order_by('-at_created')

    q = request.GET.get('q')
    filter = request.GET.get('filter')

    if q:
        query_filter = Q(
            sub_distributor__first_name__icontains=q
        ) | Q(
            sub_distributor__last_name__icontains=q
        ) | Q(
            sub_distributor__mobile_no__icontains=q
        )
        queryset = queryset.filter(
            query_filter
        )

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')

    if start_date != None and end_date != None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))

    sub_distributor_id = request.GET.get('sub-distributor-id')

    distributor_id = request.GET.get('distributor-id')

    if distributor_id != None and int(distributor_id) > 0:
        queryset = queryset.filter(distributor_id=distributor_id)

    if sub_distributor_id != None and int(sub_distributor_id) > 0:
        queryset = queryset.filter(sub_distributor_id=sub_distributor_id)

    if filter == 'Today':
        queryset = queryset.filter(at_created__gte=datetime.datetime.now().date())
    elif filter == 'Last-Week':
        queryset = queryset.filter(at_created__range=last_week_range())
    elif filter == 'Last-Month':
        queryset = queryset.filter(at_created__range=last_month())

    return queryset


def download_distributor_list_csv(request):
    distributor_qs = get_distributor_qs(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="distributors.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Distributor Id', 'Distributor Name', 'DOJ', 'Mobile', 'Email', 'Status'
    ])
    for distributor in distributor_qs:
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
        distributor_list = ZrUser.objects.filter(role__name=DISTRIBUTOR)
        q = self.request.GET.get('q')
        filter = self.request.GET.get('filter')
        pg_no = self.request.GET.get('page_no', 1)
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        distributor_id = self.request.GET.get('distributor-id')

        if activate:
            zruser = ZrUser.objects.filter(id=activate).last()
            if not zruser:
                raise Http404

            zruser.is_active = True
            zrmappings_models.DistributorMerchant.objects.filter(
                distributor=zruser
            ).update(
                is_attached_to_admin=False
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
                is_attached_to_admin=True
            )
            dj_user = zruser.zr_user
            dj_user.is_active = False
            dj_user.save(update_fields=['is_active'])
            zruser.save(update_fields=['is_active'])

        if q:
            context['q'] = q

        if filter:
            context['filter_by'] = filter

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if distributor_id:
            context['distributor_id'] =int(distributor_id)

        context['distributor_list'] = distributor_list
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

    def get_context_data(self, *args, **kwargs):
        period = self.request.GET.get('period')
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        dt_filter = {}
        if period == 'today':
          dt_filter['at_created'] = datetime.datetime.now().date()
        elif period == 'last-week':
           dt_filter['at_created__range'] = date_utils.last_week_range()
        elif period == 'last-month':
           dt_filter['at_created__range'] = date_utils.last_month()

        if start_date != None and end_date != None:
            dt_filter['at_created__range']=(start_date, end_date)

        context = super(DashBoardView, self).get_context_data(*args, **kwargs)
        if is_user_superuser(self.request):
            total_commission = commission_models.Commission.objects.filter(
                commission_user=None,
                **dt_filter
            ).aggregate(commission=Sum(
                F('net_commission') + (F('user_tds') * F('net_commission')) / 100
            ))['commission']
        else:
            req_usr = self.request.user.zr_admin_user
            total_commission = commission_models.Commission.objects.filter(
                commission_user=req_usr.zr_user,
                **dt_filter
            ).aggregate(commission=Sum(
                F('net_commission') + (F('user_tds') * F('net_commission')) / 100
            ))['commission']

        total_commission = total_commission if total_commission else 0
        context['total_commission'] = "%.4f" % total_commission

        if is_user_superuser(self.request):
            '''
            Total commission value
            '''
            context["dmt_commission_value"] = commission_models.Commission.objects.filter(
                transaction__type__name='DMT',
                commission_user=None
            ).aggregate(
                value=Sum('user_commission')
            )['value'] or 0

            context["total_bill_pay_commission_value"] = commission_models.Commission.objects.filter(
                transaction__type__name__in=BILLS_TYPE,
                commission_user=None,
                **dt_filter
            ).aggregate(
                value=Sum('user_commission')
            )['value'] or 0

            context["total_recharge_commission_value"] = commission_models.Commission.objects.filter(
                transaction__type__name__in=RECHARGES_TYPE,
                commission_user=None,
                **dt_filter
            ).aggregate(
                value=Sum('user_commission')
            )['value'] or 0

        else:
            merchants = transaction_utils.get_merchants_from_distributor(
                self.request.user.zr_admin_user.zr_user
            )
            context["dmt_commission_value"] = commission_models.Commission.objects.filter(
                transaction__type__name='DMT',
                commission_user=self.request.user.zr_admin_user.zr_user
            ).aggregate(
                value=Sum('user_commission')
            )['value'] or 0

            context["total_bill_pay_commission_value"] = commission_models.Commission.objects.filter(
                transaction__type__name__in=BILLS_TYPE,
                commission_user=self.request.user.zr_admin_user.zr_user,
                **dt_filter
            ).aggregate(
                value=Sum('user_commission')
            )['value'] or 0

            context["total_recharge_commission_value"] = commission_models.Commission.objects.filter(
                transaction__type__name__in=RECHARGES_TYPE,
                commission_user=self.request.user.zr_admin_user.zr_user,
                **dt_filter
            ).aggregate(
                value=Sum('user_commission')
            )['value'] or 0

            dt_filter['user__id__in'] = merchants

        '''
        Total transactions
        '''
        context["successful_dmt_transactions"] = transaction_models.Transaction.objects.filter(
            type__name='DMT',
            status=TRANSACTION_STATUS_SUCCESS,
            **dt_filter
        ).count()
        context["successful_bill_pay_transactions"] = transaction_models.Transaction.objects.filter(
            type__name__in=RECHARGES_TYPE,
            status=TRANSACTION_STATUS_SUCCESS,
            **dt_filter
        ).count()
        context["successful_recharge_transactions"] = transaction_models.Transaction.objects.filter(
            type__name__in=RECHARGES_TYPE,
            status=TRANSACTION_STATUS_SUCCESS,
            **dt_filter
        ).count()

        context["pending_failure_dmt_transactions"] = transaction_models.Transaction.objects.filter(
            type__name='DMT',
            status__in=[TRANSACTION_STATUS_PENDING, TRANSACTION_STATUS_FAILURE],
            **dt_filter
        ).count()
        context["pending_failure_bill_pay_transactions"] = transaction_models.Transaction.objects.filter(
            type__name__in=BILLS_TYPE,
            status__in=[TRANSACTION_STATUS_PENDING, TRANSACTION_STATUS_FAILURE],
            **dt_filter
        ).count()
        context["pending_failure_recharge_transactions"] = transaction_models.Transaction.objects.filter(
            type__name__in=RECHARGES_TYPE,
            status__in=[TRANSACTION_STATUS_PENDING, TRANSACTION_STATUS_FAILURE],
            **dt_filter
        ).count()

        '''
        Total transaction value
        '''
        context["dmt_transaction_value"] = transaction_models.Transaction.objects.filter(
            type__name='DMT',
            status=TRANSACTION_STATUS_SUCCESS,
            **dt_filter
        ).aggregate(
            value=Sum('amount')
        )['value'] or 0

        context["bill_pay_transaction_value"] = transaction_models.Transaction.objects.filter(
            type__name__in=BILLS_TYPE,
            status=TRANSACTION_STATUS_SUCCESS,
            **dt_filter
        ).aggregate(
            value=Sum('amount')
        )['value'] or 0

        context["recharge_transaction_value"] = transaction_models.Transaction.objects.filter(
            type__name__in=RECHARGES_TYPE,
            status=TRANSACTION_STATUS_SUCCESS,
            **dt_filter
        ).aggregate(
            value=Sum('amount')
        )['value'] or 0

        zr_admin_user = self.request.user.zr_admin_user
        if self.request.user.zr_admin_user.role.name == DISTRIBUTOR:
            context["total_merchants"] = zrmappings_models.DistributorMerchant.objects.filter(
                distributor=zr_admin_user.zr_user,
            ).count()
            if zr_admin_user.zr_user:
                context['total_payment_request'] = zr_admin_user.zr_user.distributor_payment_requests.all().count()
        elif self.request.user.zr_admin_user.role.name == SUBDISTRIBUTOR:
            context["total_merchants"] = zrmappings_models.DistributorMerchant.objects.filter(
                distributor=zr_admin_user.zr_user,
            ).count()
            if zr_admin_user.zr_user:
                context['total_payment_request'] = zr_admin_user.zr_user.distributor_payment_requests.all().count()
        elif self.request.user.zr_admin_user.role.name == MERCHANT:
            if zr_admin_user.zr_user:
                context['total_payment_request'] = zr_admin_user.zr_user.merchant_payment_requests.all().count()

        try:
            context['user_wallet'] = self.request.user.zr_admin_user.zr_user.wallet
        except:
            context['user_wallet'] = None

        context['payment_mods'] = PaymentMode.objects.all()
        context['is_user_superuser'] = is_user_superuser(request=self.request)
        context['bank'] = Bank.objects.all()

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        to_list=[]
        distributor_merchant = zrmappings_models.DistributorMerchant.objects.filter(
            distributor_id= self.request.user.zr_admin_user.zr_user)
        if distributor_merchant:
            for distributor_merchant_map in distributor_merchant:
                to_list.append(distributor_merchant_map.merchant)


        distributor_subdistributor = zrmappings_models.DistributorSubDistributor.objects.filter(
            distributor_id=self.request.user.zr_admin_user.zr_user)
        if distributor_subdistributor:
            for distributor_subdistributor_map in distributor_subdistributor:
                to_list.append(distributor_subdistributor_map.sub_distributor)

        subdistributor_merchant = zrmappings_models.SubDistributorMerchant.objects.filter(
            sub_distributor=self.request.user.zr_admin_user.zr_user)
        if subdistributor_merchant:
            for subdistributor_merchant_map in subdistributor_merchant:
                to_list.append(subdistributor_merchant_map.merchant)

        context['to_list']=to_list
        topup_form = zr_payment_form.TopupForm()
        # topup_form = zr_payment_form.TopupForm(initial={'to_user': request.user.zr_admin_user.zr_user.id, 'payment_type' : 2 , 'payment_mode' : 3})
        context['topup_form']=topup_form

        return context


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

        if not kyc_docs:
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                    'kyc_doc_types': self.kyc_doc_types,
                    'kyc_error': 'KYC details are mandatory'
                }
            )

        merchant_zr_user = merchant_form.save(commit=False)
        merchant_zr_user.role = UserRole.objects.filter(name=DISTRIBUTOR).last()
        password = '%s%s' % (merchant_zr_user.pan_no.lower().strip(), str(merchant_zr_user.mobile_no).lower().strip())
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

        zrwallet_models.Wallet.objects.create(merchant=merchant_zr_user)
        return HttpResponseRedirect(reverse("user:distributor-list"))


class UserUpdateView(View):
    template_name = 'zruser/user_update.html'
    kyc_doc_types = KYCDocumentType.objects.all().values_list('name', flat=True)

    def get(self, request, pk,  **kwargs):
        user = ZrUser.objects.get(id=pk)
        merchant_form = zr_user_form.UpdateMerchantDistributorForm(
            initial={'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email})
        return render(
            request, self.template_name,
            {"merchant_form": merchant_form, "zr_user": user, "kyc_doc_types": self.kyc_doc_types}
        )

    @transaction.atomic
    def post(self, request, pk):
        user = ZrUser.objects.get(id=pk)
        if "save" in request.POST:
            merchant_form = zr_user_form.UpdateMerchantDistributorForm(data=request.POST, instance=user)
            if not merchant_form.is_valid():
                return render(
                    request, self.template_name,
                    {
                        'merchant_form': merchant_form,
                        'kyc_doc_types': self.kyc_doc_types
                    }
                )

            merchant_form.save()
            if hasattr(user, "zr_user"):
                if hasattr(user.zr_user,"id"):
                    dj_user = user.zr_user.id
                    dj_user.first_name = user.first_name
                    dj_user.last_name = user.last_name
                    dj_user.email = user.email
                    dj_user.save()

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

            for doc in kyc_docs:
                KYCDetail.objects.create(
                    type=KYCDocumentType.objects.get(name=doc['doc_type']),
                    document_id=doc['doc_id'],
                    document_link=doc['doc_url'],
                    for_user=user,
                    role=user.role
                )
        if user.role.name == DISTRIBUTOR:
            return HttpResponseRedirect(reverse("user:distributor-list"))
        if user.role.name == SUBDISTRIBUTOR:
            return HttpResponseRedirect(reverse("user:sub-distributor-list"))
        if user.role.name == MERCHANT:
            return HttpResponseRedirect(reverse("user:merchant-list"))

        if user.role.name == RETAILER:
            try:
                userid = transaction_models.VendorZrRetailer.objects.get(zr_user=user.id)
                response = requests.post(QUICKWALLET_API_CRUD_URL, json={
                    "secret": QUICKWALLET_SECRET,
                    "action": "update",
                    "entity": "retailer",
                    "details": {
                        "id": userid.vendor_user,
                        "name": "{0}".format(user.first_name)
                    }
                })
            except:
                pass
            return HttpResponseRedirect(reverse("user:retailer-list"))


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
                'kyc_doc_types': self.kyc_doc_types,
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
                    'kyc_doc_types': self.kyc_doc_types,
                }
            )

        if not bank_detail_form.is_valid():
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                    'document_type_form': document_type_form,
                    'kyc_doc_types': self.kyc_doc_types,
                }
            )

        if not kyc_docs:
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                    'kyc_doc_types': self.kyc_doc_types,
                    'kyc_error': 'KYC details are mandatory',
                }
            )

        merchant_zr_user = merchant_form.save(commit=False)
        merchant_zr_user.role = UserRole.objects.filter(name=MERCHANT).last()
        merchant_zr_user.pass_word = '%s%s' % (
            merchant_zr_user.pan_no.lower().strip(), str(merchant_zr_user.mobile_no).lower().strip()
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
            distributor = ZrUser.objects.filter(mobile_no=DEFAULT_DISTRIBUTOR_MOBILE_NUMBER).last()
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
        return HttpResponseRedirect(reverse("user:merchant-list"))


def download_sub_distributor_list_csv(request):
    sub_distributor_mapping_qs = get_sub_distributor_qs(request)  # get_distributor_qs(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="subdistributors.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Sub Distributor Id', 'Sub Distributor Name', 'DOJ', 'Mobile', 'Email', 'Status'
    ])
    for sub_distributor_map_item in sub_distributor_mapping_qs:
        writer.writerow([
            sub_distributor_map_item.sub_distributor.id,
            sub_distributor_map_item.sub_distributor.first_name,
            sub_distributor_map_item.at_created,
            sub_distributor_map_item.sub_distributor.mobile_no,
            sub_distributor_map_item.sub_distributor.email,
            'Active' if sub_distributor_map_item.is_active else 'Inactive'
        ])

    return response


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

        if not kyc_docs:
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                    'kyc_doc_types': self.kyc_doc_types,
                    'kyc_error': 'KYC details are mandatory'
                }
            )

        merchant_zr_user = merchant_form.save(commit=False)
        merchant_zr_user.role = UserRole.objects.filter(name=SUBDISTRIBUTOR).last()
        password = '%s%s' % (merchant_zr_user.pan_no.lower().strip(), str(merchant_zr_user.mobile_no).lower().strip())
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
            distributor = ZrUser.objects.filter(mobile_no=DEFAULT_DISTRIBUTOR_MOBILE_NUMBER).last()
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

        zrwallet_models.Wallet.objects.create(merchant=merchant_zr_user)
        return HttpResponseRedirect(reverse("user:sub-distributor-list"))


class SubDistributorListView(ListView):
    template_name = 'zruser/sub_distributor_list.html'
    queryset = ZrUser.objects.filter(role__name=SUBDISTRIBUTOR)
    context_object_name = 'sub_distributor_list'
    paginate_by = 10

    def get_context_data(self, *args, **kwargs):
        context = super(SubDistributorListView, self).get_context_data()
        activate = self.request.GET.get('activate')
        disable = self.request.GET.get('disable')
        queryset = self.get_queryset()
        q = self.request.GET.get('q')
        filter = self.request.GET.get('filter')
        pg_no = self.request.GET.get('page_no', 1)
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        sub_distributor_id = self.request.GET.get('sub-distributor-id')
        distributor_id = self.request.GET.get('distributor-id')
        subDistributor = {}
        sub_distributor_list =[]

        if self.request.user.zr_admin_user:
            try:
                sub_distributor_list = zrmappings_models.DistributorSubDistributor.objects.filter(distributor=self.request.user.zr_admin_user.zr_user)
            except:
                pass

        if is_user_superuser(self.request):
            sub_distributor_list = zrmappings_models.DistributorSubDistributor.objects.all()

        if activate:
            zruser = ZrUser.objects.filter(id=activate).last()
            if not zruser:
                raise Http404

            zruser.is_active = True
            zrmappings_models.SubDistributorMerchant.objects.filter(
                sub_distributor=zruser
            ).update(
                is_attached_to_admin=False
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
            zrmappings_models.SubDistributorMerchant.objects.filter(
                sub_distributor=zruser
            ).update(
                is_attached_to_admin=True
            )
            dj_user = zruser.zr_user
            dj_user.is_active = False
            dj_user.save(update_fields=['is_active'])
            zruser.save(update_fields=['is_active'])

        if q:
            context['q'] = q

        if filter:
            context['filter_by'] = filter


        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if sub_distributor_id:
            context['sub_distributor_id'] = int(sub_distributor_id)

        if distributor_id:
            context['distributor_id'] = int(distributor_id)

        if sub_distributor_list:
            for subdist in sub_distributor_list:
                if subdist.distributor.id in subDistributor:
                    subDistributor[subdist.distributor.id].append([subdist.distributor.first_name, subdist.sub_distributor.id,subdist.sub_distributor.first_name])
                else:
                    subDistributor[subdist.distributor.id] = [[subdist.distributor.first_name, subdist.sub_distributor.id,subdist.sub_distributor.first_name]]
                    # subDistributor[subdist.distributor.id] = [subdist.distributor.first_name, subdist.sub_distributor.id,subdist.sub_distributor.first_name]

        context['queryset'] = queryset

        context['subDistributor'] = subDistributor

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
        return get_sub_distributor_qs(self.request)


class RetailerCreateView(CreateView):
    template_name = 'zruser/add_retailer.html'
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
            error = False
            api_error = ""

            if not merchant_form.is_valid():
                error = True

            if not bank_detail_form.is_valid():
                error = True
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
                    # error = False
                    kyc_docs.append(
                        {
                            'doc_url': request.POST.get(doc_type_name),
                            'doc_id': request.POST.get(doc_type_id),
                            'doc_type': doc_type_name.replace('-', ' ')
                        }
                    )

            if not kyc_docs:
                return render(
                    request, self.template_name,
                    {
                        'merchant_form': merchant_form,
                        'bank_detail_form': bank_detail_form,
                        'kyc_doc_types': self.kyc_doc_types,
                        'kyc_error': 'KYC details are mandatory'
                    }
                )
            if error==False:
                response = requests.post(QUICKWALLET_API_CRUD_URL, json={
                    "secret": QUICKWALLET_SECRET,
                    "action": "create",
                    "entity": "retailer",
                    "details": {
                        "name": merchant_form.data['first_name']
                    }
                })

                if 300 > response.status_code >= 200:
                    try:
                        json_data = json.loads(response.text)
                    except:
                        pass

                if json_data:
                    if json_data['status']:
                        status = json_data['status']
                        if status == "failed":
                            return render(
                                request, self.template_name,
                                {
                                    "api_error":"something went wrong, please try again!"
                                }
                            )
                        else:
                            vendor_user_id = json_data['data']['id']
                            company_id = json_data['data']['companyid']
                            merchant_zr_user = merchant_form.save(commit=False)
                            merchant_zr_user.role = UserRole.objects.filter(name=RETAILER).last()
                            password = '%s%s' % (
                                merchant_zr_user.pan_no.lower().strip(),
                                str(merchant_zr_user.mobile_no).lower().strip())
                            merchant_zr_user.pass_word = password

                            merchant_zr_user.save()

                            quick_wallet = transaction_models.Vendor.objects.get(name="QUICKWALLET")
                            transaction_models.VendorZrRetailer.objects.create(
                                vendor=quick_wallet,
                                zr_user=merchant_zr_user,
                                vendor_user=str(vendor_user_id),
                                company_id=str(company_id)
                            )

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

                            zrwallet_models.Wallet.objects.create(merchant=merchant_zr_user)
                            return HttpResponseRedirect(reverse("user:retailer-list"))
            if error is True:
                api_error = "Something went wrong, please try again!"

            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form,
                    'bank_detail_form': bank_detail_form,
                    'kyc_doc_types': self.kyc_doc_types,
                    'api_error' : api_error
                }
            )


class RetailerListView(ListView):
    template_name = 'zruser/retailer_list.html'
    queryset = ZrUser.objects.filter(role__name=RETAILER)
    context_object_name = 'retailer_list'
    paginate_by = 10

    def get_context_data(self, *args, **kwargs):
        context = super(RetailerListView, self).get_context_data()
        activate = self.request.GET.get('activate')
        disable = self.request.GET.get('disable')
        queryset = self.get_queryset()
        retailer_list = ZrUser.objects.filter(role__name=RETAILER)
        q = self.request.GET.get('q')
        filter = self.request.GET.get('filter')
        pg_no = self.request.GET.get('page_no', 1)
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        retailer_id = self.request.GET.get('retailer-id')

        if activate:
            zruser = ZrUser.objects.filter(id=activate).last()
            if not zruser:
                raise Http404

            zruser.is_active = True
            dj_user = zruser.zr_user
            dj_user.is_active = True
            dj_user.save(update_fields=['is_active'])
            zruser.save(update_fields=['is_active'])
            try:
                vendor = transaction_models.VendorZrRetailer.objects.get(zr_user=int(zruser.id))
                response = requests.post(QUICKWALLET_API_CRUD_URL, json={
                    "secret": QUICKWALLET_SECRET,
                    "action": "update",
                    "entity": "retailer",
                    "details": {
                        "id": vendor.vendor_user,
                        "isactive": "Y"
                    }
                })
            except:
                pass

        if disable:
            zruser = ZrUser.objects.filter(id=disable).last()
            if not zruser:
                raise Http404

            zruser.is_active = False
            dj_user = zruser.zr_user
            dj_user.is_active = False
            dj_user.save(update_fields=['is_active'])
            zruser.save(update_fields=['is_active'])

            try:
                vendor = transaction_models.VendorZrRetailer.objects.get(zr_user=int(zruser.id))
                response = requests.post(QUICKWALLET_API_CRUD_URL, json={
                    "secret": QUICKWALLET_SECRET,
                    "action": "update",
                    "entity": "retailer",
                    "details": {
                        "id": vendor.vendor_user,
                        "isactive": "N"
                    }
                })
            except:
                pass

        if q:
            context['q'] = q

        if filter:
            context['filter_by'] = filter

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if retailer_id:
            context['retailer_id'] =int(retailer_id)

        context['retailer_list'] = retailer_list
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
        return get_retailer_qs(self.request)


def get_retailer_qs(request):
    queryset = ZrUser.objects.filter(role__name=RETAILER).order_by('-at_created')
    q = request.GET.get('q')
    filter = request.GET.get('filter')

    if q:
        query_filter = Q(first_name__contains=q) | Q(last_name__contains=q) | Q(mobile_no__contains=q)
        queryset = queryset.filter(
            query_filter
        )

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')

    if start_date!=None and end_date!=None:
        queryset=queryset.filter(at_created__range=(start_date, end_date))

    retailer_id = request.GET.get('retailer-id')

    if retailer_id!=None and int(retailer_id) > 0:
        queryset = queryset.filter(id=retailer_id)

    if filter == 'Today':
        queryset = queryset.filter(at_created__gte=datetime.datetime.now().date())
    elif filter == 'Last-Week':
        queryset = queryset.filter(at_created__range=last_week_range())
    elif filter == 'Last-Month':
        queryset = queryset.filter(at_created__range=last_month())

    return queryset


def download_retailer_list_csv(request):
    retailer_qs = get_retailer_qs(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="retailers.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Retailer Id', 'Retailer Name', 'DOJ', 'Mobile', 'Email', 'Status'
    ])
    for retailer in retailer_qs:
        writer.writerow([
            retailer.id,
            retailer.first_name,
            retailer.at_created,
            retailer.mobile_no,
            retailer.email,
            'Active' if retailer.is_active else 'Inactive'
        ])

    return response


class TerminalCreateView(CreateView):
    template_name = 'zruser/add_terminal.html'

    def get(self, request):
        merchant_form = zr_user_form.TerminalRetailerForm()

        return render(
            request, self.template_name,
            {
                'merchant_form': merchant_form
            }
        )

    @transaction.atomic
    def post(self, request):
        merchant_form = zr_user_form.TerminalRetailerForm(data=request.POST)
        error = False

        if not merchant_form.is_valid():
            error = True
            return render(
                request, self.template_name,
                {
                    'merchant_form': merchant_form
                }
            )

        if error == False:
            retailer_id = request.user.zr_admin_user.zr_user_id
            retailer_api_id = transaction_models.VendorZrRetailer.objects.get(zr_user=retailer_id)
            id = request.POST.get('mobile_no', '')
            response = requests.post(QUICKWALLET_API_CRUD_URL, json={
                "secret": QUICKWALLET_SECRET,
                "action": "create",
                "entity": "outlet",
                "details": {
                    "name": merchant_form.data['first_name'],
                    "retailerid": int(retailer_api_id.vendor_user),
                    "udoutletid": int(id)
                }
            })
            if 300 > response.status_code >= 200:
                try:
                    json_data = json.loads(response.text)
                except:
                    pass
            if json_data:
                if json_data['status']:
                    status = json_data['status']
                    if status == "failed":
                        return render(
                            request, self.template_name,
                            {
                                "api_error": "something went wrong, please try again!"
                            }
                        )
                    else:
                        terminal_id = json_data['data']['id']
                        password = zrupee_security.generate_password()
                        merchant_zr_user = merchant_form.save(commit=False)
                        r_email = request.user.zr_admin_user.zr_user.email
                        merchant_zr_user.pass_word = password
                        merchant_zr_user.role = UserRole.objects.filter(name=TERMINAL).last()
                        merchant_zr_user.send_welcome_email_RT(password, r_email)

                        merchant_zr_user.save()
                        quick_wallet = transaction_models.Vendor.objects.get(name=QUICKWALLET)

                        if is_user_retailer(request):
                            retailer = request.user.zr_admin_user.zr_user
                            zrmappings_models.RetailerTerminal.objects.create(
                                retailer=retailer,
                                terminal=merchant_zr_user,
                                is_active=True
                            )

                        transaction_models.VendorZrTerminal.objects.create(
                            vendor=quick_wallet,
                            zr_terminal=merchant_zr_user,
                            vendor_user=terminal_id,
                            is_active=True
                        )
                        return HttpResponseRedirect(reverse("user:terminal-list"))

        if error == False:
            api_error = "Something went wrong, please try again!"

        return render(
            request, self.template_name,
            {
                'merchant_form': merchant_form,
                'api_error' : api_error
            }
        )


class TerminalListView(ListView):
    template_name = 'zruser/terminal_list.html'
    queryset = ZrTerminal.objects.filter(role__name=TERMINAL)
    context_object_name = 'terminal_list'
    paginate_by = 10

    def get_context_data(self, *args, **kwargs):
        context = super(TerminalListView, self).get_context_data()
        activate = self.request.GET.get('activate')
        disable = self.request.GET.get('disable')
        queryset = self.get_queryset()
        terminal_list = ZrTerminal.objects.filter(role__name=TERMINAL)
        q = self.request.GET.get('q')
        filter = self.request.GET.get('filter')
        pg_no = self.request.GET.get('page_no', 1)
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        terminal_id = self.request.GET.get('terminal-id')
        retailer_id = self.request.GET.get('retailer-id')
        terminaldict = {}

        if self.request.user.zr_admin_user:
            try:
                terminal_list = zrmappings_models.RetailerTerminal.objects.filter(retailer=self.request.user.zr_admin_user.zr_user)
            except:
                pass

        if is_user_superuser(self.request):
            terminal_list = zrmappings_models.RetailerTerminal.objects.all()

        if activate:
            zruser = ZrTerminal.objects.filter(id=activate).last()
            if not zruser:
                raise Http404
            zruser.is_active = True
            zruser.save(update_fields=['is_active'])
            zrmappings_models.RetailerTerminal.objects.filter(
                terminal=zruser
            ).update(
                # is_active=True,
                is_attached_to_admin=False
            )

            try:
                response = requests.post(QUICKWALLET_API_CRUD_URL, json={
                    "secret": QUICKWALLET_SECRET,
                    "action": "update",
                    "entity": "outlet",
                    "details": {
                        "udoutletid": int(activate),
                        "isactive": "Y"
                    }
                })
                json_data = json.loads(response.text)
            except:
                pass

        if disable:
            zruser = ZrTerminal.objects.filter(id=disable).last()
            if not zruser:
                raise Http404
            zruser.is_active = False
            zruser.save(update_fields=['is_active'])
            zrmappings_models.RetailerTerminal.objects.filter(
                terminal=zruser
            ).update(
                # is_active=False,
                is_attached_to_admin=True
            )

            try:
                response = requests.post(QUICKWALLET_API_CRUD_URL, json={
                    "secret": QUICKWALLET_SECRET,
                    "action": "update",
                    "entity": "outlet",
                    "details": {
                        "udoutletid": int(disable),
                        "isactive": "N"
                    }
                })
                json_data = json.loads(response.text)
            except:
                pass

        if terminal_list:
            for terminal in terminal_list:
                if terminal.retailer.id in terminaldict:
                    terminaldict[terminal.retailer.id].append(
                        [terminal.retailer.first_name, terminal.terminal.id,
                         terminal.terminal.first_name])
                else:
                    terminaldict[terminal.retailer.id] = [
                        [terminal.retailer.first_name, terminal.terminal.id,
                         terminal.terminal.first_name]]

        if q:
            context['q'] = q

        if filter:
            context['filter_by'] = filter

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if terminaldict:
            context['terminaldict']=terminaldict

        if terminal_id:
            context['terminal_id'] = int(terminal_id)

        if retailer_id:
            context['retailer_id'] = int(retailer_id)
        context['terminal_list'] = terminal_list
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
        return get_terminal_qs(self.request)


def get_terminal_qs(request):
    queryset = zrmappings_models.RetailerTerminal.objects.none()
    if request.user.zr_admin_user:
        try:
            queryset = request.user.zr_admin_user.zr_user.terminal_retailer_mappings.order_by('at_created')
        except:
            pass

    if is_user_superuser(request):
        queryset = zrmappings_models.RetailerTerminal.objects.order_by('at_created')

    q = request.GET.get('q')
    filter = request.GET.get('filter')

    if q:
        query_filter = Q(terminal__first_name__contains=q) | Q(terminal__last_name__contains=q) | Q(terminal__mobile_no__contains=q)
        queryset = queryset.filter(
            query_filter
        )

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')

    if start_date != None and end_date != None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))

    terminal_id = request.GET.get('terminal-id')

    retailer_id = request.GET.get('retailer-id')

    if retailer_id != None and int(retailer_id) > 0:
        queryset = queryset.filter(retailer_id=retailer_id)

    if terminal_id != None and int(terminal_id) > 0:
        queryset = queryset.filter(terminal_id=terminal_id)

    if filter == 'Today':
        queryset = queryset.filter(at_created__gte=datetime.datetime.now().date())
    elif filter == 'Last-Week':
        queryset = queryset.filter(at_created__range=last_week_range())
    elif filter == 'Last-Month':
        queryset = queryset.filter(at_created__range=last_month())

    return queryset


def download_terminal_list_csv(request):
    terminal_qs = get_terminal_qs(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="terminals.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Terminal Id', 'Terminal Name', 'DOJ', 'Mobile', 'Email', 'Status'
    ])
    for terminal in terminal_qs:
        writer.writerow([
            terminal.terminal.id,
            terminal.terminal.first_name,
            terminal.terminal.at_created,
            terminal.terminal.mobile_no,
            terminal.terminal.email,
            'Active' if terminal.terminal.is_active else 'Inactive'
        ])

    return response


class TerminalUpdateView(View):
    template_name = 'zruser/terminal_update.html'

    def get(self, request, pk,  **kwargs):
            user = ZrTerminal.objects.get(id=pk)
            merchant_form = zr_user_form.UpdateMerchantTerminalForm(
                initial={'first_name': user.first_name, 'last_name': user.last_name, 'email': user.email})
            return render(
                request, self.template_name, {"merchant_form": merchant_form, "terminal_user": user}
            )

    @transaction.atomic
    def post(self, request, pk):
        user = ZrTerminal.objects.get(id=pk)
        if "save" in request.POST:
            merchant_form = zr_user_form.UpdateMerchantTerminalForm(data=request.POST, instance=user)
            if not merchant_form.is_valid():
                return render(
                    request, self.template_name,
                    {
                        'merchant_form': merchant_form
                    }
                )

            merchant_form.save()
            try:
                response = requests.post(QUICKWALLET_API_CRUD_URL, json={
                    "secret": QUICKWALLET_SECRET,
                    "action": "update",
                    "entity": "outlet",
                    "details": {
                        "udoutletid": user.mobile_no,
                        "name": "{0}".format(user.first_name)
                    }
                })
            except:
                pass
        return HttpResponseRedirect(reverse("user:terminal-list"))


class TerminalView(View):
    template_name = 'zruser/terminal_view.html'

    def get(self, request, pk,  **kwargs):
            user = ZrTerminal.objects.get(id=pk)
            return render(
                request, self.template_name, {"zr_user": user}
            )

    # @transaction.atomic
    # def post(self, request, pk):
    #     user = ZrTerminal.objects.get(id=pk)
    #     if "save" in request.POST:
    #         merchant_form = zr_user_form.UpdateMerchantTerminalForm(data=request.POST, instance=user)
    #         if not merchant_form.is_valid():
    #             return render(
    #                 request, self.template_name,
    #                 {
    #                     'merchant_form': merchant_form
    #                 }
    #             )
    #
    #         merchant_form.save()
    #         # print(user.id)
    #         # try:
    #         #     userid = transaction_models.VendorZrTerminal.objects.get(zr_terminal=user.id)
    #         #     print(userid.vendor_user)
    #         #     response = requests.post(QUICKWALLET_API_CRUD_URL, json={
    #         #         "secret": QUICKWALLET_SECRET,
    #         #         "action": "update",
    #         #         "entity": "outlet",
    #         #         "details": {
    #         #             "id": userid.vendor_user,
    #         #             "name": "{0}".format(user.first_name)
    #         #         }
    #         #     })
    #         #     print(response)
    #         # except:
    #         #     pass
    #     return HttpResponseRedirect(reverse("user:terminal-list"))


class UserCardCreateView(CreateView):
    template_name = 'zruser/card_create.html'

    def get(self, request):

        return render(
            request, self.template_name
        )

    @transaction.atomic
    def post(self, request):
        quantity = request.POST.get('quantity', '')
        zr_retailer_id = request.user.zr_admin_user.zr_user.id
        vendor = transaction_models.VendorZrRetailer.objects.get(zr_user=zr_retailer_id)
        response = requests.post(QUICKWALLET_API_CARD_URL, json={"secret": QUICKWALLET_SECRET,
                                                                 "retailerid": vendor.vendor_user,
                                                                 "qty": int(quantity)})
        if 300 > response.status_code >= 200:
            try:
                json_data = json.loads(response.text)
                if json_data:
                    if json_data['status']:
                        status = json_data['status']
                        if status == "failed":
                            return render(
                                request, self.template_name,
                                {
                                    "api_error": "something went wrong, please try again!"
                                }
                            )
                        else:
                            return HttpResponseRedirect(reverse("user:dashboard"))
            except:
                pass
            return render(
                request, self.template_name,
                {
                    "api_error": "something went wrong, please try again!"
                }
            )


class UserCardListView(View):
    template_name = 'zruser/loyaltycard_list.html'
    paginate_by = 10

    def get(self, request, **kwargs):

        zr_retailer_id = request.user.zr_admin_user.zr_user.id
        vendor = transaction_models.VendorZrRetailer.objects.get(zr_user=zr_retailer_id)
        response = requests.post(QUICKWALLET_API_LISTCARD_URL, json={
            "secret": QUICKWALLET_SECRET,
            "retailerid": vendor.vendor_user
        })
        if 300 > response.status_code >= 200:
            try:
                json_data = json.loads(response.text)
                loyalty_cards = json_data['data']['loyaltycards']

                return render(
                    request, self.template_name, {"loyalty_cards": loyalty_cards}
                )
            except:
                pass

            return render(
                request, self.template_name, {"api_error": "something went wrong, please try again!"}
            )


class TerminalActivatedCardListView(View):
    template_name = 'zruser/activatedcard_list.html'
    paginate_by = 10

    def get(self, request, pk, **kwargs):
        user = ZrTerminal.objects.get(id=pk)
        response = requests.post(QUICKWALLET_API_LISTCARD_ACTIVATED_URL, json={
            "secret": QUICKWALLET_SECRET,
            "udoutletid": int(user.mobile_no)
        })

        if 300 > response.status_code >= 200:
            try:
                json_data = json.loads(response.text)
                activated_cards = json_data['data']['activations']

                return render(
                    request, self.template_name, {"zr_user": user, "activated_cards": activated_cards}
                )
            except:
                pass

            return render(
                request, self.template_name, {"zr_user": user, "api_error": "something went wrong, please try again!"}
            )


class GenerateOTPView(View):
    template_name = 'zruser/generate_otp.html'

    def get(self, request, pk,  **kwargs):
        user = ZrTerminal.objects.get(id=pk)
        zr_retailer_id = request.user.zr_admin_user.zr_user.id
        vendor = transaction_models.VendorZrRetailer.objects.get(zr_user=zr_retailer_id)
        response = requests.post(QUICKWALLET_API_LISTCARD_URL, json={
            "secret": QUICKWALLET_SECRET,
            "retailerid": vendor.vendor_user
        })

        # response = requests.post(QUICKWALLET_API_LISTCARD_ACTIVATED_URL, json={
        #     "secret": QUICKWALLET_SECRET,
        #     "udoutletid": int(user.mobile_no)
        # })
        if 300 > response.status_code >= 200:
            try:
                json_data = json.loads(response.text)
                loyalty_cards = json_data['data']['loyaltycards']
                loyalty_cardslist = []
                for card in loyalty_cards:
                    loyalty_cardslist.append(card['cardnumber'])
                # activated_cards = json_data['data']['activations']
                # activated_cardslist = []
                # for card in activated_cards:
                #     activated_cardslist.append(card.cardnumber)

                return render(
                    request, self.template_name, {"zr_user": user, "loyalty_cardslist": loyalty_cardslist}
                )
            except:
                pass

            return render(
                request, self.template_name, {"zr_user": user, "api_error": "something went wrong, please try again!"}
            )

    @transaction.atomic
    def post(self, request, pk):
        user = ZrTerminal.objects.get(id=pk)
        if "save" in request.POST:
            cardnumber = request.POST.get('card_number', '')
            udoutletid = request.POST.get('udoutletid', '')
            mobile = request.POST.get('mobile', '')
            # validation
            error = False
            if not cardnumber:
                error = True
            if mobile:
                if not mobile.isdigit() and (len(mobile)<10):
                    error = True

            if int(udoutletid) != int(user.mobile_no):
                error = True

            if error == False:
                try:
                    response = requests.post(QUICKWALLET_API_GENERATEOTP_URL, json={
                        "secret": QUICKWALLET_SECRET,
                        "cardnumber": int(cardnumber),
                        "udoutletid": int(udoutletid),
                        "mobile": int(mobile)
                    })
                    if 300 > response.status_code >= 200:
                        try:
                            json_data = json.loads(response.text)
                        except:
                            pass

                    if json_data:
                        if json_data['status']:
                            status = json_data['status']
                            if status == "failed":
                                error = True
                            else:
                                success = "OTP Send to {0}".format(mobile)
                                return render(
                                    request, self.template_name, {"zr_user": user, "success": success}
                                )
                except:
                    pass
            if error == True:
                return render(
                    request, self.template_name, {"zr_user": user, "api_error": "something went wrong, please try again!"}
                )

        return render(
            request, self.template_name, {"zr_user": user}
        )


class IssueMobileView(View):
    template_name = 'zruser/issue_to_mobile.html'

    def get(self, request, pk,  **kwargs):
            user = ZrTerminal.objects.get(id=pk)
            return render(
                request, self.template_name, {"zr_user": user}
            )

    @transaction.atomic
    def post(self, request, pk):
        user = ZrTerminal.objects.get(id=pk)
        if "save" in request.POST:
            cardnumber = request.POST.get('cardnumber', '')
            udoutletid = request.POST.get('udoutletid', '')
            mobile = request.POST.get('mobile', '')
            otp = request.POST.get('otp', '')
            # validation
            error = False
            if not cardnumber:
                error = True
            if mobile:
                if not mobile.isdigit() and (len(mobile)<10):
                    error = True

            if int(udoutletid) != int(user.mobile_no):
                error = True

            if error == False:
                try:
                    response = requests.post(QUICKWALLET_API_ISSUE_MOBILE_URL, json={
                        "secret": QUICKWALLET_SECRET,
                        "cardnumber": int(cardnumber),
                        "udoutletid": int(udoutletid),
                        "mobile": int(mobile),
                        "otp": otp
                    })
                    if 300 > response.status_code >= 200:
                        try:
                            json_data = json.loads(response.text)
                        except:
                            pass

                    if json_data:
                        if json_data['status']:
                            status = json_data['status']
                            if status == "failed":
                                error = True
                            else:
                                success = "{0} issued to {1}".format(cardnumber, mobile)
                                return render(
                                    request, self.template_name, {"zr_user": user, "success": success}
                                )
                except:
                    pass
            if error == True:
                return render(
                    request, self.template_name, {"zr_user": user, "api_error": "something went wrong, please try again!"}
                )

        return render(
            request, self.template_name, {"zr_user": user}
        )


class ActivateCardView(View):
    template_name = 'zruser/activate_card.html'

    def get(self, request, pk,  **kwargs):
            user = ZrTerminal.objects.get(id=pk)
            return render(
                request, self.template_name, {"zr_user": user}
            )

    @transaction.atomic
    def post(self, request, pk):
        user = ZrTerminal.objects.get(id=pk)
        if "save" in request.POST:
            cardnumber = request.POST.get('cardnumber', '')
            udoutletid = request.POST.get('udoutletid', '')
            mobile = request.POST.get('mobile', '')
            otp = request.POST.get('otp', '')
            # validation
            error = False
            if not cardnumber:
                error = True
            if mobile:
                if not mobile.isdigit() and (len(mobile)<10):
                    error = True

            if int(udoutletid) != int(user.mobile_no):
                error = True

            if error == False:
                try:
                    response = requests.post(QUICKWALLET_API_ACTIVATE_CARD_URL, json={
                        "secret": QUICKWALLET_SECRET,
                        "cardnumber": int(cardnumber),
                        "udoutletid": int(udoutletid),
                        "mobile": int(mobile),
                        "otp": otp
                    })
                    if 300 > response.status_code >= 200:
                        try:
                            json_data = json.loads(response.text)
                        except:
                            pass

                    if json_data:
                        if json_data['status']:
                            status = json_data['status']
                            if status == "failed":
                                error = True
                            else:
                                success = "{0} Activated".format(cardnumber)
                                return render(
                                    request, self.template_name, {"zr_user": user, "success": success}
                                )
                except:
                    pass
            if error == True:
                return render(
                    request, self.template_name, {"zr_user": user, "api_error": "something went wrong, please try again!"}
                )

        return render(
            request, self.template_name, {"zr_user": user}
        )


class RechargeCardView(View):
    template_name = 'zruser/recharge_card.html'

    def get(self, request, pk,  **kwargs):
            user = ZrTerminal.objects.get(id=pk)
            return render(
                request, self.template_name, {"zr_user": user}
            )

    @transaction.atomic
    def post(self, request, pk):
        user = ZrTerminal.objects.get(id=pk)
        if "save" in request.POST:
            cardnumber = request.POST.get('cardnumber', '')
            udoutletid = request.POST.get('udoutletid', '')
            amount = request.POST.get('amount', '')
            # validation
            error = False
            if not cardnumber:
                error = True
            if amount:
                if not amount.isdigit() and amount <= 0:
                    error = True

            if int(udoutletid) != int(user.mobile_no):
                error = True

            if error == False:
                try:
                    response = requests.post(QUICKWALLET_API_RECHARGE_CARD_URL, json={
                        "secret": QUICKWALLET_SECRET,
                        "cardnumber": int(cardnumber),
                        "udoutletid": int(udoutletid),
                        "amount": int(amount)
                    })
                    if 300 > response.status_code >= 200:
                        try:
                            json_data = json.loads(response.text)
                        except:
                            pass

                    if json_data:
                        if json_data['status']:
                            status = json_data['status']
                            if status == "failed":
                                error = True
                            else:
                                success = "Rs. {0} added to {1}".format(amount, cardnumber)
                                return render(
                                    request, self.template_name, {"zr_user": user, "success": success}
                                )
                except:
                    pass
            if error == True:
                return render(
                    request, self.template_name, {"zr_user": user, "api_error": "something went wrong, please try again!"}
                )

        return render(
            request, self.template_name, {"zr_user": user}
        )


class PayView(View):
    template_name = 'zruser/pay.html'

    def get(self, request, pk, **kwargs):
        user = ZrTerminal.objects.get(id=pk)
        return render(
            request, self.template_name, {"zr_user": user}
        )

    @transaction.atomic
    def post(self, request, pk):
        user = ZrTerminal.objects.get(id=pk)
        if "save" in request.POST:
            cardnumber = request.POST.get('cardnumber', '')
            udoutletid = request.POST.get('udoutletid', '')
            mobile = request.POST.get('mobile', '')
            otp = request.POST.get('otp', '')
            amount = request.POST.get('amount', '')
            # validation
            error = False
            if not cardnumber:
                error = True
            if mobile:
                if not mobile.isdigit() and (len(mobile)) < 10:
                    error = True

            if int(udoutletid) != int(user.mobile_no):
                error = True

            if error == False:
                try:
                    response = requests.post(QUICKWALLET_API_PAY_URL, json={
                        "secret": QUICKWALLET_SECRET,
                        "cardnumber": int(cardnumber),
                        "udoutletid": int(udoutletid),
                        "mobile": int(mobile),
                        "otp": otp,
                        "amount": int(amount)
                    })
                    if 300 > response.status_code >= 200:
                        try:
                            json_data = json.loads(response.text)
                        except:
                            pass

                    if json_data:
                        if json_data['status']:
                            status = json_data['status']
                            if status == "failed":
                                error = True
                            else:
                                success = "Rs. {0} paid".format(amount)
                                return render(
                                    request, self.template_name, {"zr_user": user, "success": success}
                                )
                except:
                    pass
            if error == True:
                return render(
                    request, self.template_name,
                    {"zr_user": user, "api_error": "something went wrong, please try again!"}
                )

        return render(
            request, self.template_name, {"zr_user": user}
        )


class DeactivateCardView(View):
    template_name = 'zruser/deactivate_card.html'

    def get(self, request, pk,  **kwargs):
            user = ZrTerminal.objects.get(id=pk)
            return render(
                request, self.template_name, {"zr_user": user}
            )

    @transaction.atomic
    def post(self, request, pk):
        user = ZrTerminal.objects.get(id=pk)
        if "save" in request.POST:
            cardnumber = request.POST.get('cardnumber', '')
            udoutletid = request.POST.get('udoutletid', '')
            mobile = request.POST.get('mobile', '')
            otp = request.POST.get('otp', '')
            # validation
            error = False
            if not cardnumber:
                error = True
            if mobile:
                if not mobile.isdigit() and (len(mobile)<10):
                    error=True

            if int(udoutletid) != int(user.mobile_no):
                error = True

            if error == False:
                try:
                    response = requests.post(QUICKWALLET_API_DEACTIVATE_CARD_URL, json={
                        "secret": QUICKWALLET_SECRET,
                        "cardnumber": int(cardnumber),
                        "udoutletid": int(udoutletid),
                        "mobile": int(mobile),
                        "otp": otp
                    })
                    if 300 > response.status_code >= 200:
                        try:
                            json_data = json.loads(response.text)
                        except:
                            pass

                    if json_data:
                        if json_data['status']:
                            status = json_data['status']
                            if status == "failed":
                                error = True
                            else:
                                success = "{0} Deactivated".format(cardnumber)
                                return render(
                                    request, self.template_name, {"zr_user": user, "success": success}
                                )
                except:
                    pass
            if error == True:
                return render(
                    request, self.template_name, {"zr_user": user, "api_error": "something went wrong, please try again!"}
                )

        return render(
            request, self.template_name, {"zr_user": user}
        )


class PaymentHistoryView(View):
    template_name = 'zruser/payment_history.html'

    @transaction.atomic
    def get(self, request, pk, **kwargs):
        if pk != '0':
            user = ZrTerminal.objects.get(id=pk)
            response = requests.post(QUICKWALLET_PAYMENT_HISTORY_URL, json={"secret": QUICKWALLET_SECRET,
                                                                            "udoutletid": int(user.mobile_no)})
        elif is_user_retailer(request):
            user = None
            zr_retailer_id = request.user.zr_admin_user.zr_user.id
            vendor = transaction_models.VendorZrRetailer.objects.get(zr_user=zr_retailer_id)
            response = requests.post(QUICKWALLET_PAYMENT_HISTORY_URL, json={"secret": QUICKWALLET_SECRET,
                                                                     "retailerid": vendor.vendor_user})
        elif is_user_superuser(request):
            user = None
            response = requests.post(QUICKWALLET_PAYMENT_HISTORY_URL, json={"secret": QUICKWALLET_SECRET})

        if 300 > response.status_code >= 200:
            try:
                json_data = json.loads(response.text)
                payments = json_data['data']['payments']
                return render(
                    request, self.template_name, {"payments": payments, "zr_user": user}
                )
            except:
                pass

            return render(
                request, self.template_name, {"api_error": "something went wrong, please try again!"}
            )


class OfferCreateView(CreateView):
    template_name = 'zruser/offer_create.html'

    def get(self, request):

        return render(
            request, self.template_name
        )

    @transaction.atomic
    def post(self, request):
        if "save" in request.POST:
            id = request.POST.get('id', '')
            type = request.POST.get('type', '')
            availability = request.POST.get('availability', '')
            redemptions = request.POST.get('redemptions', '')
            short_desc = request.POST.get('short_desc', '')
            long_desc = request.POST.get('long_desc', '')
            cashback = request.POST.get('cashback', '')
            isactive = request.POST.get('isactive', '')
            min = request.POST.get('min', '')
            dis = request.POST.get('dis', '')

            # validation
            error = False
            # if not cardnumber:
            #     error = True
            # if mobile:
            #     if not mobile.isdigit() and (len(mobile)) < 10:
            #         error = True
            #
            # if int(udoutletid) != int(user.mobile_no):
            #     error = True

            if error == False:
                try:
                    response = requests.post(QUICKWALLET_CREATE_OFFER_URL, json={"secret": QUICKWALLET_SECRET,
                                                        "details":{
                                                        "id": int(id),
                                                        "sdesc": short_desc,
                                                        "ldesc": long_desc,
                                                        "min": min,
                                                        "type": type,
                                                        "availability": availability,
                                                        "redemptions": redemptions,
                                                        "cashback": cashback,
                                                        "isactive": isactive,
                                                        "dis": dis
                                                         }
                                                    })
                    if 300 > response.status_code >= 200:
                        try:
                            json_data = json.loads(response.text)
                        except:
                            pass

                    if json_data:
                        if json_data['status']:
                            status = json_data['status']
                            if status == "failed":
                                error = True
                            else:
                                success = "Offer {0} Created".format(id)
                                return render(
                                    request, self.template_name, {"success": success}
                                )
                except:
                    pass
        return render(
            request, self.template_name)


class OfferListView(View):
    template_name = 'zruser/offer_list.html'
    paginate_by = 10

    def get(self, request, api_error=None, success=None, **kwargs):

        response = requests.post(QUICKWALLET_OFFER_LIST_URL, json={
            "secret": QUICKWALLET_SECRET
        })
        if 300 > response.status_code >= 200:
            try:
                json_data = json.loads(response.text)
                offers = json_data['data']['offers']
                retailer_list = ZrUser.objects.filter(role__name=RETAILER)
                # terminal_list = ZrTerminal.objects.filter(role__name=TERMINAL)
                # print(request.user.zr_admin_user.zr_user.id)

                # for terminal in terminal_list:
                #     print(terminal.terminal.mobile_no)
                if request.user.zr_admin_user.role.name == "RETAILER":
                    terminal_list = zrmappings_models.RetailerTerminal.objects.filter(retailer=request.user.zr_admin_user.zr_user.id)
                    zr_user_id = request.user.zr_admin_user.zr_user.id
                    vendor = transaction_models.VendorZrRetailer.objects.get(zr_user=zr_user_id)
                else:
                    vendor = None
                    terminal_list = None
                return render(
                    request, self.template_name,
                    {"offers": offers, "vendor": vendor, "retailer_list": retailer_list, "terminal_list": terminal_list, "api_error": api_error, "success": success}
                )
            except:
                pass

            return render(
                request, self.template_name, {"api_error": "something went wrong, please try again!"}
            )

    def post(self, request, **kwargs):

        if request.user.zr_admin_user.role.name != "RETAILER":
            retailer_id = request.POST.get('retailer','')
            offer_id = request.POST.get('offer_id','')
            order_id_list = []
            order_id_list.append(str(offer_id))

            vendor = transaction_models.VendorZrRetailer.objects.get(zr_user = retailer_id)

            # validations
            error = False
            # if not retailer_id:
            #         error = True
            #
            # if not offer_id:
            #     error = True
            #
            # if error == False:
            try:
                response = requests.post(QUICKWALLET_OFFER_ASSIGN_TO_RETAILER_URL, json={
                    "secret": QUICKWALLET_SECRET,
                    "offerids": order_id_list,
                    "retailerid": vendor.vendor_user
                })
                if 300 > response.status_code >= 200:
                    try:
                        json_data = json.loads(response.text)
                    except:
                        pass

                if json_data:
                    if json_data['status']:
                        status = json_data['status']
                        if status == "failed":
                            error = True
                        else:
                            success = "Offer {0} assigned".format(offer_id)
                            return self.get(request, success)
            except:
                pass
            if error == True:
                api_error = "something went wrong, please try again!"
                return self.get(request, api_error)
            return self.get(request)


        elif request.user.zr_admin_user.role.name == "RETAILER":
            terminal_id = request.POST.get('terminal', '')
            offer_id = request.POST.get('offer_id_terminal', '')
            order_id_list = []
            order_id_list.append(str(offer_id))
            terminal_id_list = []
            terminal_id_list.append(str(terminal_id))

            # validations
            error = False
            # if not retailer_id:
            #         error = True
            #
            # if not offer_id:
            #     error = True
            #
            # if error == False:
            try:
                # the url is same for assign retailer & terminal
                response = requests.post(QUICKWALLET_OFFER_ASSIGN_TO_RETAILER_URL, json={
                    "secret": QUICKWALLET_SECRET,
                    "offerids": order_id_list,
                    "udoutletids": terminal_id_list
                })
                if 300 > response.status_code >= 200:
                    try:
                        json_data = json.loads(response.text)
                    except:
                        pass

                if json_data:
                    if json_data['status']:
                        status = json_data['status']
                        if status == "failed":
                            error = True
                        else:
                            success = "Offer {0} assigned".format(offer_id)
                            return self.get(request, success)
            except:
                pass
            if error == True:
                api_error = "something went wrong, please try again!"
                return self.get(request, api_error)
            return self.get(request)
