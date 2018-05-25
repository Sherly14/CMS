# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
from urllib import urlencode

from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic.list import ListView
from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger


from common_utils.date_utils import last_week_range, last_month
from common_utils.user_utils import is_user_superuser
from zrwallet.models import Wallet, WalletTransactions
from zruser.models import ZrUser
from zrmapping import models as zrmappings_models
from zruser.mapping import SUBDISTRIBUTOR, DISTRIBUTOR, MERCHANT
from common_utils.transaction_utils import get_merchant_id_list_from_distributor


def get_transaction_qs(request):
    queryset = None
    if is_user_superuser(request):
        queryset = WalletTransactions.objects.exclude(wallet_id=None).order_by('-id')

    elif request.user.zr_admin_user.role.name == DISTRIBUTOR:
        dist_subd = list(zrmappings_models.DistributorSubDistributor.objects.filter(
            distributor=request.user.zr_admin_user.zr_user).values_list('sub_distributor_id', flat=True))
        queryset = WalletTransactions.objects.filter(
            wallet_id__in=get_merchant_id_list_from_distributor(request.user.zr_admin_user.zr_user) +
            dist_subd + list(zrmappings_models.SubDistributorMerchant.objects.filter(
                sub_distributor__in=dist_subd).values_list('merchant_id', flat=True))
            + list(ZrUser.objects.filter(id=request.user.zr_admin_user.zr_user.id).values_list(
                'id', flat=True))).order_by('-id')

    elif request.user.zr_admin_user.role.name == SUBDISTRIBUTOR:
        queryset = WalletTransactions.objects.filter(
            wallet_id__in=list(zrmappings_models.SubDistributorMerchant.objects.filter(
                sub_distributor=request.user.zr_admin_user.zr_user).values_list(
                'merchant_id', flat=True))
            + list(ZrUser.objects.filter(id=request.user.zr_admin_user.zr_user.id).values_list(
                'id', flat=True))).order_by('-id')

    q = request.GET.get('q')
    if q:
        query_filter = Q(wallet__merchant__first_name__icontains=q) | Q(wallet__merchant__last_name__icontains=q) | \
                       Q(wallet__merchant__mobile_no__contains=q)

        queryset = queryset.filter(
            query_filter
        )

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')
    user_id = request.GET.get('user_id')
    if start_date is not None and end_date is not None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))

    if user_id is not None and int(user_id) > 0:
        queryset = queryset.filter(wallet_id=user_id)

    return queryset


class PassbookListView(ListView):
    template_name = 'zwallet/passbook_list.html'
    context_object_name = 'passbook_list'
    paginate_by = 10

    def get_context_data(self, *args, **kwargs):
        context = super(PassbookListView, self).get_context_data()
        user_list = None
        filter_by = self.request.GET.get('filter', 'all')
        q = self.request.GET.get('q')
        queryset = self.get_queryset()
        pg_no = self.request.GET.get('page_no', 1)
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        user_id = self.request.GET.get('user_id')

        if is_user_superuser(self.request):
            user_list = WalletTransactions.objects.all().distinct('wallet_id')

        elif self.request.user.zr_admin_user.role.name == DISTRIBUTOR:
            dist_subd = list(zrmappings_models.DistributorSubDistributor.objects.filter(
                distributor=self.request.user.zr_admin_user.zr_user).values_list('sub_distributor_id', flat=True))
            user_list = WalletTransactions.objects.filter(
                wallet_id__in=get_merchant_id_list_from_distributor(self.request.user.zr_admin_user.zr_user) +
                dist_subd + list(zrmappings_models.SubDistributorMerchant.objects.filter(
                    sub_distributor__in=dist_subd).values_list('merchant_id', flat=True))
                + list(ZrUser.objects.filter(id=self.request.user.zr_admin_user.zr_user.id).values_list(
                    'id', flat=True))).distinct('wallet_id')

        elif self.request.user.zr_admin_user.role.name == SUBDISTRIBUTOR:
            user_list = WalletTransactions.objects.filter(
                wallet_id__in=list(zrmappings_models.SubDistributorMerchant.objects.filter(
                    sub_distributor=self.request.user.zr_admin_user.zr_user).values_list(
                    'merchant_id', flat=True))
                + list(ZrUser.objects.filter(id=self.request.user.zr_admin_user.zr_user.id).values_list(
                    'id', flat=True))).distinct('wallet_id')
        if q:
            context['q'] = q
        if start_date:
            context['startDate'] = start_date
        if end_date:
            context['endDate'] = end_date
        if user_id:
            context['user_id'] = int(user_id)
        if user_list:
            context['user_list'] = user_list

        p = Paginator(queryset, self.paginate_by)
        try:
            page = p.page(pg_no)
        except EmptyPage:
            raise Http404

        context['queryset'] = page.object_list
        context['url_name'] = "passbook-list"

        query_string = {}
        if q:
            query_string['q'] = q
        if user_id:
            query_string['user_id'] = int(user_id)
        if start_date:
            query_string['startDate'] = start_date
        if end_date:
            query_string['endDate'] = end_date

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
        return get_transaction_qs(self.request)


def get_passbook_report_csv(request):
    passbook_qs = get_transaction_qs(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="passbook.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'User name', 'Mobile No', 'Role', 'Transaction ID', 'Transaction type',
                     'Payment ID', 'Transaction Value', 'DMT Balance', 'Non DMT Balance',
                     'Bank UTR', 'Sender Mobile', 'Beneficiary Mobile', 'Beneficiary Account No', 'Payment Status'
                     ])
    for passbook in passbook_qs:
        try:
            utr = passbook.transaction.transaction_response_json.data.bank_ref_num
        except:
            utr = 'NA'
        try:
            customer = passbook.transaction.customer
        except:
            customer = 'NA'
        try:
            beneficiary = passbook.transaction.beneficiary
        except:
            beneficiary = 'NA'
        try:
            acc = passbook.transaction.beneficiary_user.account_no
        except:
            acc = 'NA'
        try:
            status = passbook.transaction.status
        except:
            status = 'NA'
        writer.writerow([
            passbook.at_created,
            passbook.wallet.merchant.full_name,
            passbook.wallet.merchant.mobile_no,
            passbook.wallet.merchant.role.name,
            passbook.transaction_id,
            passbook.transaction.type if passbook.transaction is not None else '',
            passbook.payment_request_id,
            passbook.dmt_balance if passbook.dmt_balance != 0 else passbook.non_dmt_balance,
            passbook.dmt_closing_balance,
            passbook.non_dmt_closing_balance,
            utr,
            customer,
            beneficiary,
            acc,
            status
        ])

    return response


def payments_csv_download(request):
    if not (request.user.zr_admin_user.role.name == 'ADMINSTAFF' or is_user_superuser(request)):
        return JsonResponse({"success": False})
    email_list = request.POST.get('email', '').split(",")
    report_params = {
        "email_list": email_list,
        "q": request.POST.get('q', ""),
        "filter": request.POST.get('filter', ""),
        "period": request.POST.get('period', ""),
        "user_id": request.user.id,
    }
    from zrwallet import tasks as passbook_celery_tasks
    # passbook_celery_tasks.send_passbook_report(report_params)
    passbook_celery_tasks.send_passbook_report.apply_async(args=[report_params])
    return JsonResponse({"success": True})


@transaction.atomic
def set_closing_balance(request):
    zr_wallet = Wallet.objects.all()
    for row in zr_wallet:
        mid = row.merchant_id

        dmt_closing_balance = row.dmt_balance
        non_dmt_closing_balance = row.non_dmt_balance

        dmt = 0
        non_dmt = 0

        mid_transactions = WalletTransactions.objects.all().filter(wallet=mid).order_by('-id')
        if mid_transactions:

            for r in mid_transactions:
                r.dmt_closing_balance = dmt_closing_balance + (-1 * dmt)
                r.non_dmt_closing_balance = non_dmt_closing_balance + (-1 * non_dmt)
                dmt = r.dmt_balance
                non_dmt = r.non_dmt_balance
                dmt_closing_balance = r.dmt_closing_balance
                non_dmt_closing_balance = r.non_dmt_closing_balance
                r.save()

    return JsonResponse({"success": True})
