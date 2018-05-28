# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import datetime
import urllib
import json
from urllib import urlencode


from django.core.paginator import Paginator
from django.db.models import F
from django.db.models import Sum

from common_utils import date_utils
from common_utils import user_utils
from zrcommission.models import Commission


from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger
from django.db.models import Q
from zruser.models import ZrUser

from django.http import Http404, JsonResponse
from django.http import HttpResponse
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common_utils.date_utils import last_month, last_week_range
from common_utils.transaction_utils import get_distributor_from_sub_distributor, is_sub_distributor
from common_utils.user_utils import is_user_superuser, file_save_s3
from zrpayment.models import PaymentRequest, Payments, PaymentMode
from zrwallet.models import Wallet, WalletTransactions

from django.views.generic import CreateView, DetailView, ListView, UpdateView
from common_utils.user_utils import is_user_superuser
import ast


def get_commission_qs(comm_display):
    pg_no = comm_display.request.GET.get('pg-no')
    period = comm_display.request.GET.get('period')
    search = comm_display.request.GET.get('q')

    req_usr = comm_display.request.user.zr_admin_user
    return Commission.objects.filter(
        commission_user=req_usr.zr_user
    )


def get_commission_display_qs(request):
    search = request.GET.get('q')

    req_usr = request.user.zr_admin_user
    queryset = Commission.objects.filter(commission_user=None, is_settled=False).order_by('-at_created')
    query_filter = Q(
        commission_user__mobile_no__contains=search
    ) | Q(
        commission_user__first_name__icontains=search
    ) | Q(
        commission_user__last_name__icontains=search
    )
    if user_utils.is_user_superuser(request):
        if search:
            queryset = queryset.filter(
                query_filter
            ).order_by('-at_created')
    else:
        if search:
            queryset = Commission.objects.filter(
                query_filter,
                commission_user=req_usr.zr_user,
                is_settled=False
            ).order_by('-at_created')
        else:
            queryset = Commission.objects.filter(
                commission_user=req_usr.zr_user,
                is_settled=False
            ).order_by('-at_created')

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')
    if start_date != None and end_date != None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))

    return queryset


class CommissionDisplay(ListView):
    context_object_name = 'commissions'
    template_name = 'zrcommission/dashboard.html'
    paginated_by = 10

    def get_context_data(self, *args, **kwargs):
        pg_no = self.request.GET.get('page_no')
        search = self.request.GET.get('q')
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')

        context = super(CommissionDisplay, self).get_context_data(*args, **kwargs)

        user = None if user_utils.is_user_superuser(self.request) else self.request.user.zr_admin_user.zr_user

        ids_qs = Commission.objects.filter(
            commission_user=user,
            is_settled=False
        ).values_list('id', flat=True).order_by('id')
        ids = [comm_id for comm_id in ids_qs]
        context['ids'] = ids
        total_commission = Commission.objects.filter(
            id__in=ids
        ).aggregate(commission=Sum(
            F('user_commission') - F('user_tds')
        ))['commission']

        if total_commission:
            context['total_commission'] = '%.2f' % total_commission
        else:
            context['total_commission'] = '%.2f' % 0

        context['search'] = search

        if not is_user_superuser(self.request):
            context['user_id'] = user.id

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        query_result = self.get_queryset()
        p = Paginator(query_result, self.paginated_by)
        page = None
        try:
            if pg_no:
                page = p.page(pg_no)
            else:
                page = p.page(1)
        except:
            page = p.page(1)

        context['commissions'] = page
        context['url_name'] = "display-commission"

        query_string = {}
        if search:
            query_string['search'] = search

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
        queryset = get_commission_display_qs(self.request)
        return queryset


def get_comission_csv(request):
    commission_qs = get_commission_display_qs(request)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="commissions.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'My Commission After TDS',
        'Merchant commission',
        'Merchant ID',
        'Name'
    ])

    for commission in commission_qs:
        name = [commission.transaction.user.first_name]
        if commission.transaction.user.last_name:
            name.append(commission.transaction.user.last_name)

        writer.writerow(
            [
                commission.get_commission_without_comm(),
                commission.get_merchant_commission(),
                commission.transaction.user.pk,
                ' '.join(name)
            ]
        )

    return response


class PaymentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRequest
        fields = (
            'amount', 'dmt_amount', 'non_dmt_amount',
            'to_user', 'from_user',
            'payment_mode', 'document',
            'from_account_no', 'to_account_no',
            'from_bank', 'to_bank', 'payment_type',
            'status', 'comments'
        )


class SettleCommission(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        data = dict(json.loads(request.data.keys()[0]))
        user_id = data.get("user_id")
        ids = ast.literal_eval(data.get("ids"))
        total_commission = data.get("total_commission")

        user = ZrUser.objects.filter(id=int(user_id))

        supervisor = None
        if is_sub_distributor(user):
            supervisor = get_distributor_from_sub_distributor(user).id
        else:
            supervisor = ZrUser.objects.filter(role__name='ADMINSTAFF').last().id

        if not supervisor:
            response_data = {
                "message": "Something went wrong, please try again",
                "success": False
            }
            return Response(response_data, status=status.HTTP_200_OK)

        payment_mode = PaymentMode.objects.all().filter(name='WALLET')
        payment_req_data = {
            'to_bank': '100', 'dmt_amount': total_commission, 'to_account_no': 'XXXXXZrupee', 'from_bank': '100',
            'ref_id': '', 'to_user': supervisor, 'amount': total_commission, 'non_dmt_amount': '0', 'from_user': user,
            'payment_mode': payment_mode, 'document': 'NA', 'from_account_no': 'XXXXXMerchant', 'status': 1,
            'comments': data.get("ids"), 'payment_type': 1
        }
        serializer = PaymentRequestSerializer(data=payment_req_data)
        payment_req_obj = None
        if serializer.is_valid():
            payment_req_obj = serializer.save()

            zr_wallet = Wallet.objects.get(
                merchant=user
            )

            zr_wallet.dmt_balance += payment_req_obj.dmt_amount
            zr_wallet.non_dmt_balance += payment_req_obj.non_dmt_amount

            zr_wallet.save(
                update_fields=[
                    'dmt_balance', 'non_dmt_balance'
                ]
            )

            WalletTransactions.objects.create(
                wallet=zr_wallet,
                transaction=None,
                payment_request=payment_req_obj,
                dmt_balance=payment_req_obj.dmt_amount,
                non_dmt_balance=payment_req_obj.non_dmt_amount,
                dmt_closing_balance=zr_wallet.dmt_balance,
                non_dmt_closing_balance=zr_wallet.non_dmt_balance,
                is_success=True
            )

            Commission.objects.filter(
                id__in=ids
            ).update(
                is_settled=True
            )

            response_data = {
                "responser": serializer.data,
                "message": "Commission Settled Successfully",
                "success": True
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        response_data = {
            "responser": serializer.errors,
            "message": "data and model mismatch",
            "success": False
        }
        return Response(response_data, status=status.HTTP_200_OK)
