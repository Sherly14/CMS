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
from zrwallet.models import Passbook, Wallet, WalletTransactions
from zruser.models import ZrUser
from zrmapping import models as zrmappings_models


def get_passbook_qs(request, is_request_dict=False):
    if is_request_dict:
        filter_by = request.get('filter')
        q = request.get('q')
    else:
        filter_by = request.GET.get('filter')
        q = request.GET.get('q')

    queryset = Passbook.objects.all()
    if q:
        query = Q(
            user__mobile_no__contains=q
        ) | Q(
            user__first_name__icontains=q
        ) | Q(
            user__last_name__icontains=q
        )
        queryset = queryset.filter(query)

    if filter_by == 'last_week':
        queryset = queryset.filter(at_created__range=last_week_range())
    elif filter_by == 'last_month':
        queryset = queryset.filter(at_created__range=last_month())
    elif filter_by == 'today':
        queryset = queryset.filter(at_created__date__gte=datetime.date.today())

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')
    distributor_id = request.GET.get('distributor-id')
    merchant_id = request.GET.get('merchant-id')
    sub_distributor_id = request.GET.get('sub-distributor-id')

    if merchant_id != None and int(merchant_id) > 0:
        queryset = Passbook.objects.filter(user_id=merchant_id)

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

        userDsitributorMerchant =Passbook.objects.filter(user_id__in=distributorMerchantList)
        userSubDistributorMerchant =Passbook.objects.filter(user_id__in=SubDistributorMerchantList)

        merchantDataList = userDsitributorMerchant| userSubDistributorMerchant

        queryset = merchantDataList

    if distributor_id != None and  merchant_id == "-1":
        distmerchantlist = []
        DistM = zrmappings_models.DistributorMerchant.objects.filter(distributor_id=distributor_id)

        if DistM:
            for dist in DistM:
                distmerchantlist.append(dist.merchant_id)

        if distmerchantlist:
            queryset = Passbook.objects.filter(user_id__in=distmerchantlist)

    if start_date != None and end_date != None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))

    return queryset.order_by('-at_created')


def get_transaction_qs(request):
    queryset = WalletTransactions.objects.all().order_by('id')
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
        filter_by = self.request.GET.get('filter', 'all')
        q = self.request.GET.get('q')
        context['passbook_list'] = passbook_list
        queryset = WalletTransactions.objects.all()
        page = self.request.GET.get('page', 1)
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')

        context = super(PassbookListView, self).get_context_data(**kwargs)

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

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


class PaymentListView(ListView):
    context_object_name = 'passbook_list'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        filter_by = self.request.GET.get('filter', 'all')
        q = self.request.GET.get('q')
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        distributor_list = ZrUser.objects.filter(role_id=2)
        merchant_id = self.request.GET.get('merchant-id')
        distributor_id = self.request.GET.get('distributor-id')
        sub_distributor = []
        sub_distributor_list = []
        sub_dist_merchant = []
        merchant = []
        subDistMerchant = {}
        sub_distributor_id = self.request.GET.get('sub-distributor-id')

        context = super(PaymentListView, self).get_context_data(**kwargs)

        queryset = self.get_queryset()
       # if not queryset:
        #    context['filter_by'] = filter_by
         #   context['q'] = q
          #  return context

        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page', 1)

        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)
        from django.core.urlresolvers import reverse

        sub_distributor = zrmappings_models.DistributorSubDistributor.objects.filter(distributor=distributor_id)
        merchant = zrmappings_models.DistributorMerchant.objects.filter(distributor=distributor_id)

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date


        if sub_distributor:
            for subdist in sub_distributor:
                sub_distributor_list.append(subdist.sub_distributor_id)

        if sub_distributor_list:
            sub_dist_merchant = zrmappings_models.SubDistributorMerchant.objects.filter(sub_distributor_id__in=sub_distributor_list)

        if sub_dist_merchant:
            for sub_merchant in sub_dist_merchant:
                if sub_merchant.sub_distributor.id in subDistMerchant:
                    subDistMerchant[sub_merchant.sub_distributor.id].append([sub_merchant.sub_distributor.first_name, sub_merchant.merchant.id,sub_merchant.merchant.first_name])
                else:
                    subDistMerchant[sub_merchant.sub_distributor.id] = [[sub_merchant.sub_distributor.first_name, sub_merchant.merchant.id,sub_merchant.merchant.first_name]]

        if merchant:
            for distmerchant in merchant:
                if -1 in subDistMerchant:
                    subDistMerchant[-1].append(["MERCHANTS", distmerchant.merchant.id, distmerchant.merchant.first_name])
                else:
                    subDistMerchant[-1] = [["MERCHANTS", distmerchant.merchant.id, distmerchant.merchant.first_name]]

        if distributor_list:
            context['distributor_list'] = distributor_list

        context['main_url'] = reverse('wallet:passbook-list')
        context['page_obj'] = queryset
        context['filter_by'] = filter_by
        context['q'] = q

        if subDistMerchant:
            context['subDistMerchant'] = subDistMerchant

        if merchant_id:
            context['merchant_id'] = int(merchant_id)

        if distributor_id:
            context['distributor_id'] = int(distributor_id)

        if sub_distributor_id:
            context['sub_distributor_id'] = int(sub_distributor_id)

        if merchant_id:
            context['sub_distributor_id'] = int(merchant_id)

        context['is_superuser'] = is_user_superuser(self.request)
        return context

    def get_queryset(self):
        return get_passbook_qs(self.request)


def get_passbook_report_csv(params):
    qs = get_passbook_qs(params, is_request_dict=True)
    response = HttpResponse(content_type='text/csv')
    unique_name = 'passbook-' + datetime.datetime.now().strftime("%d-%m-%YT%H:%M:%S-") + ''.join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    report_file_path = settings.REPORTS_PATH + "/" + unique_name + ".csv"
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(report_file_path)

    with open(report_file_path, 'w') as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow([
            "User name",
            "Mobile No",
            "DMT opening_balance",
            "DMT opening_wallet_balance",
            "DMT wallet_credit",
            "DMT wallet_debit",
            "DMT closing balance",
            "DMT closing wallet balance",
            "Non DMT opening balance",
            "Non DMT opening wallet balance",
            "Non DMT wallet credit",
            "Non DMT wallet debit",
            "Non DMT closing balance",
            "Non DMT closing wallet balance",
        ])
        paginator = Paginator(qs, 1)
        for x in paginator.page_range:
            page_data = paginator.page(x)
            for passbook in page_data:
                writer.writerow(
                    [
                        passbook.user.full_name,
                        passbook.user.mobile_no,
                        passbook.dmt_opening_balance,
                        passbook.dmt_opening_wallet_balance,
                        passbook.dmt_wallet_credit,
                        passbook.dmt_wallet_debit,
                        passbook.dmt_closing_balance,
                        passbook.dmt_closing_wallet_balance,
                        passbook.non_dmt_opening_balance,
                        passbook.non_dmt_opening_wallet_balance,
                        passbook.non_dmt_wallet_credit,
                        passbook.non_dmt_wallet_debit,
                        passbook.non_dmt_closing_balance,
                        passbook.non_dmt_closing_wallet_balance,
                    ]
                )
    return report_file_path


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
