# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import datetime
import random
import string

from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views.generic.list import ListView

from common_utils.date_utils import last_week_range, last_month
from common_utils.user_utils import is_user_superuser
from zrwallet.models import Wallet, WalletTransactions
from zruser.models import ZrUser
from zrmapping import models as zrmappings_models


def get_transaction_qs(request):
    queryset = WalletTransactions.objects.all().order_by('id')
    q = request.GET.get('q')
    filter = request.GET.get('filter')
    if q:
        query_filter = Q(wallet__merchant__first_name__icontains=q) | Q(wallet__merchant__last_name__icontains=q) | \
                       Q(wallet__merchant__mobile_no__contains=q)

        queryset = queryset.filter(
            query_filter
        )

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')
    distributor_id = request.GET.get('distributor-id')
    if start_date!=None and end_date!=None:
        queryset=queryset.filter(at_created__range=(start_date, end_date))

    if distributor_id!=None and int(distributor_id) > 0:
        queryset=queryset.filter(wallet_id=distributor_id)

    # distributor_id = request.GET.get('distributor-id')
    #
    # if distributor_id!=None and int(distributor_id) > 0:
    #     queryset = queryset.filter(id=distributor_id)
    #
    #
    # if filter == 'Today':
    #     queryset = queryset.filter(at_created__gte=datetime.datetime.now().date())
    # elif filter == 'Last-Week':
    #     queryset = queryset.filter(at_created__range=last_week_range())
    # elif filter == 'Last-Month':
    #     queryset = queryset.filter(at_created__range=last_month())

    return queryset


class PassbookListView(ListView):
    template_name = 'zwallet/passbook_list.html'
    context_object_name = 'passbook_list'
    paginate_by = 10

    def get_context_data(self, *args, **kwargs):
        context = super(PassbookListView, self).get_context_data()
        passbook_list = WalletTransactions.objects.all()
        user_list = WalletTransactions.objects.all().distinct('wallet')
        filter_by = self.request.GET.get('filter', 'all')
        q = self.request.GET.get('q')
        context['passbook_list'] = passbook_list
        queryset = WalletTransactions.objects.all()
        page = self.request.GET.get('page', 1)
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        distributor_id = self.request.GET.get('distributor-id')
        context = super(PassbookListView, self).get_context_data(**kwargs)

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if distributor_id:
            context['distributor_id'] = int(distributor_id)
        if user_list:
            context['user_list'] = user_list

        #queryset = self.get_queryset()
        paginator = Paginator(queryset, self.paginate_by)

        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)

        from django.core.urlresolvers import reverse

        context['main_url'] = reverse('wallet:passbook-list')
        context['page_obj'] = queryset
        context['filter_by'] = filter_by
        context['q'] = q

        return context

# ------------******------------
#     context = super(DistributorListView, self).get_context_data()
#     queryset = self.get_queryset()
#     distributor_list = ZrUser.objects.filter(role__name=DISTRIBUTOR)
#     q = self.request.GET.get('q')
#     filter = self.request.GET.get('filter')
#     pg_no = self.request.GET.get('page_no', 1)
#     start_date = self.request.GET.get('startDate')
#     end_date = self.request.GET.get('endDate')
#     distributor_id = self.request.GET.get('distributor-id')
#
#     if activate:
#         zruser = ZrUser.objects.filter(id=activate).last()
#         if not zruser:
#             raise Http404
#
#         zruser.is_active = True
#         zrmappings_models.DistributorMerchant.objects.filter(
#             distributor=zruser
#         ).update(
#             is_attached_to_admin=False
#         )
#         dj_user = zruser.zr_user
#         dj_user.is_active = True
#         dj_user.save(update_fields=['is_active'])
#         zruser.save(update_fields=['is_active'])
#
#     if disable:
#         zruser = ZrUser.objects.filter(id=disable).last()
#         if not zruser:
#             raise Http404
#
#         zruser.is_active = False
#         zrmappings_models.DistributorMerchant.objects.filter(
#             distributor=zruser
#         ).update(
#             is_attached_to_admin=True
#         )
#         dj_user = zruser.zr_user
#         dj_user.is_active = False
#         dj_user.save(update_fields=['is_active'])
#         zruser.save(update_fields=['is_active'])
#
#     if q:
#         context['q'] = q
#
#     if filter:
#         context['filter_by'] = filter
#
#     if start_date:
#         context['startDate'] = start_date
#
#     if end_date:
#         context['endDate'] = end_date
#
#     if distributor_id:
#         context['distributor_id'] = int(distributor_id)
#
#     context['distributor_list'] = distributor_list
#     context['queryset'] = queryset
#     p = Paginator(context['queryset'], self.paginate_by)
#     try:
#         page = p.page(pg_no)
#     except EmptyPage:
#         raise Http404
#
#     context['queryset'] = page.object_list
#     query_string = {}
#     if q:
#         query_string['q'] = q
#
#     if filter:
#         query_string['filter'] = filter
#
#     if page.has_next():
#         query_string['page_no'] = page.next_page_number()
#         context['next_page_qs'] = urlencode(query_string)
#         context['has_next_page'] = page.has_next()
#     if page.has_previous():
#         query_string['page_no'] = page.previous_page_number()
#         context['prev_page_qs'] = urlencode(query_string)
#         context['has_prev_page'] = page.has_previous()
#
#     return context
#
# --------****-----------

    def get_queryset(self):
        return get_transaction_qs(self.request)


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
