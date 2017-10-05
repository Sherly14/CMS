# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import datetime
import json

from django.core.paginator import Paginator, PageNotAnInteger
from django.db.models import Q
from django.http import HttpResponse
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common_utils.date_utils import last_month, last_week_range
from common_utils.transaction_utils import get_distributor_from_sub_distributor, \
    get_main_admin
from common_utils.user_utils import is_user_superuser
from zrpayment.models import PaymentRequest
from zruser import mapping as user_map
from zrwallet import models as zrwallet_models


class PaymentRequestDetailView(DetailView):
    queryset = PaymentRequest.objects.all()
    context_object_name = 'payment_request'


class PaymentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRequest
        fields = (
            'amount', 'dmt_amount',
            'non_dmt_amount', 'to_user',
            'from_user', 'payment_mode',
            'from_account_no',
            'to_account_no',
            'from_bank',
            'to_bank'
        )


class GeneratePaymentRequestView(APIView):
    queryset = PaymentRequest.objects.all()
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        data = dict(request.POST)
        if data['request_type'] == 'DMT':
            data['dmt_amount'] = data['amount']
        else:
            data['non_dmt_amount'] = data['amount']

        data["from_user"] = request.user.zr_admin_user.zr_user.id
        if request.user.zr_admin_user.role.name == user_map.DISTRIBUTOR:
            main_distributor = get_main_admin()
            data["to_user"] = main_distributor.id
        elif request.user.zr_admin_user.role.name == user_map.SUBDISTRIBUTOR:
            main_distributor = get_distributor_from_sub_distributor(request.user.zr_admin_user.zr_user)
            data["to_user"] = main_distributor.id
        serializer = PaymentRequestSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            response_data = {
                "responser": serializer.data,
                "message": "Payment request sent successfully",
                "success": True
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        response_data = {
            "responser": serializer.errors,
            "message": "Something went wrong, please try again",
            "success": False
        }
        return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


class AcceptPaymentRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        data = dict(json.loads(request.data.keys()[0]))
        request_id = data.get("request_id")
        payment_request = PaymentRequest.objects.filter(id=request_id).last()
        message = "Something went wrong, Please try again!"
        if payment_request:
            if payment_request.status == 0:
                if is_user_superuser(self.request) and payment_request.to_user.role.name == 'ADMINSTAFF':
                    message = "Wallet updated successfully"
                    payment_request.status = 1
                    payment_request.save(update_fields=['status'])

                    zr_wallet, _ = zrwallet_models.Wallet.objects.get(
                        merchant=payment_request.from_user
                    )
                    zr_wallet.dmt_balance += payment_request.dmt_amount
                    zr_wallet.non_dmt_balance += payment_request.non_dmt_amount
                    zr_wallet.save(
                        update_fields=[
                            'dmt_balance',
                            'non_dmt_balance'
                        ]
                    )
                elif self.request.user.zr_admin_user.role.name in ['DISTRIBUTOR', 'SUBDISTRIBUTOR']:
                    supervisor_wallet, _ = zrwallet_models.Wallet.objects.get(
                        merchant=payment_request.to_user
                    )
                    zr_wallet, _ = zrwallet_models.Wallet.objects.get_or_create(
                        merchant=payment_request.from_user
                    )
                    updated = False
                    if supervisor_wallet.dmt_balance > payment_request.dmt_amount:
                        # For DMT
                        zr_wallet.dmt_balance += payment_request.dmt_amount
                        supervisor_wallet.dmt_balance -= payment_request.dmt_amount
                        updated = True
                    elif supervisor_wallet.non_dmt_balance > payment_request.non_dmt_amount:
                        # For non dmt
                        zr_wallet.non_dmt_balance += payment_request.non_dmt_amount
                        supervisor_wallet.non_dmt_balance -= payment_request.non_dmt_amount
                        updated = True

                    if updated:
                        message = "Wallet updated successfully"
                        zr_wallet.save(
                            update_fields=[
                                'dmt_balance',
                                'non_dmt_balance'
                            ]
                        )
                        supervisor_wallet.save(
                            update_fields=[
                                'dmt_balance',
                                'non_dmt_balance'
                            ]
                        )
                        payment_request.status = 1
                        payment_request.save(update_fields=['status'])
                    else:
                        message = "Insufficient balance, Please recharge you wallet"
            else:
                message = "Payment request already {status}".format(status=payment_request.get_status_display())

        return Response({"message": message, 'success': True}, status=status.HTTP_200_OK)


class RejectPaymentRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        data = dict(json.loads(request.data.keys()[0]))
        request_id = data.get("request_id")
        rejection_reason = data.get("rejection_reason")
        payment_request = PaymentRequest.objects.filter(id=request_id).last()
        message = "Something went wrong, Please try again!!"
        if payment_request:
            if payment_request.status == 0:
                if payment_request.to_user.pk == request.user.zr_admin_user.zr_user.pk:
                    message = "Payment request rejected successfully"
                    payment_request.status = 2
                    payment_request.reject_comments = rejection_reason
                    payment_request.save(update_fields=['status', 'comments'])
                elif is_user_superuser(request) and payment_request.to_user.role == 'ADMINSTAFF':
                    message = "Payment request rejected successfully"
                    payment_request.status = 2
                    payment_request.reject_comments = rejection_reason
                    payment_request.save(update_fields=['status', 'comments'])
                else:
                    message = "Not allowed to accept payment request"
            else:
                message = "Payment request already {status}".format(status=payment_request.get_status_display())

        return Response({"message": message, 'success': True}, status=status.HTTP_200_OK)


def get_payment_request_qs(request):
    filter_by = request.GET.get('filter')
    q = request.GET.get('q')

    queryset = []
    if is_user_superuser(request):
        queryset = PaymentRequest.objects.all()
    elif request.user.zr_admin_user.role.name in ['DISTRIBUTOR', 'SUBDISTRIBUTOR']:
        # To get own payment request
        queryset = PaymentRequest.objects.filter(
            to_user=request.user.zr_admin_user.zr_user
        ).exclude(from_user=request.user.zr_admin_user.zr_user)

    if q:
        query = Q(
            merchant_payment_mode__name__contains=q
        ) | Q(
            supervisor__first_name__contains=q
        ) | Q(
            merchant__first_name__contains=q
        )
        queryset = queryset.filter(query)

    if filter_by == 'last_week':
        queryset = queryset.filter(at_created__range=last_week_range())
    elif filter_by == 'last_month':
        queryset = queryset.filter(at_created__range=last_month())
    elif filter_by == 'today':
        queryset = queryset.filter(at_created__date__gte=datetime.date.today())

    return queryset.order_by('-at_created')


def merchant_payment_req_csv_download(request):
    qs = get_payment_request_qs(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payment-requests.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Date',
        'Type',
        'Amount',
        'Payment Mode',
        'From User Name',
        'From User Id',
        'Ref Id',
    ])

    for payment_req in qs:
        writer.writerow(
            [
                payment_req.at_created,
                'DMT' if payment_req.dmt_amount else 'NON_DMD',
                payment_req.amount,
                payment_req.payment_mode,
                payment_req.from_user.first_name,
                payment_req.from_user.id,
                payment_req.ref_no,
            ]
        )

    return response


class PaymentRequestListView(ListView):
    context_object_name = 'payment_request_list'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        filter_by = self.request.GET.get('filter')
        q = self.request.GET.get('q')

        context = super(PaymentRequestListView, self).get_context_data(**kwargs)

        queryset = self.get_queryset()
        if not queryset:
            context['filter_by'] = filter_by
            context['q'] = q
            return context

        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page', 1)

        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)

        context['page_obj'] = queryset
        context['filter_by'] = filter_by
        context['q'] = q

        wallet = None
        if not is_user_superuser(self.request):
            wallet = zrwallet_models.Wallet.objects.get(
                merchant=None
            )
        context['wallet'] = wallet
        context['is_superuser'] = is_user_superuser(self.request)
        return context

    def get_queryset(self):
        return get_payment_request_qs(self.request)
