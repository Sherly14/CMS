# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import datetime
import decimal
import json
import random
import string

from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
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
from common_utils.user_utils import is_user_superuser, file_save_s3
from zrpayment.models import PaymentRequest, Payments, PaymentMode
from zruser import mapping as user_map
from zrwallet import models as zrwallet_models
from zruser.models import Bank
from zrmapping import models as zrmappings_models
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from zrpayment import forms as zr_payment_form
from django.shortcuts import render
from django import forms
from itertools import chain
from django.urls import reverse
from django.db import transaction



SUCCESS_MESSAGE_START = '<div class="alert alert-success" role="alert"><div class="alert-content"><i class="glyphicon glyphicon-ok-circle"></i><strong>'
ERROR_MESSAGE_START = '<div class="alert alert-danger" role="alert"><div class="alert-content"><i class="glyphicon glyphicon-remove-circle"></i><strong>'
MESSAGE_END = '</strong></div>'
MERCHANT = 'MERCHANT'
DISTRIBUTOR = 'DISTRIBUTOR'
SUBDISTRIBUTOR = 'SUBDISTRIBUTOR'
BENEFICIARY = 'BENEFICIARY'
CHECKER = 'CHECKER'
ADMINSTAFF = 'ADMINSTAFF'


class PaymentRequestDetailView(DetailView):
    queryset = PaymentRequest.objects.all()
    context_object_name = 'payment_request'


class PaymentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRequest
        fields = (
            'amount', 'dmt_amount', 'non_dmt_amount',
            'to_user', 'from_user',
            'payment_mode', 'document',
            'from_account_no', 'to_account_no',
            'from_bank', 'to_bank','payment_type'
        )


class GeneratePaymentRequestView(APIView):
    queryset = PaymentRequest.objects.all()
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        data = {}
        for detail, value in request.data.items():
            if detail == 'document' and value:
                # Upload file to S3 and set link
                #data[detail] = file_save_s3(value)
                pass
            else:
                data[detail] = value if value else ""

        data["from_user"] = request.user.zr_admin_user.zr_user.id
        main_distributor = None
        error_message = '{0} {1} {2}'.format(ERROR_MESSAGE_START,
                                             "Something went wrong, please try again",
                                             MESSAGE_END)

        if request.user.zr_admin_user.role.name == user_map.DISTRIBUTOR:
            main_distributor = get_main_admin()
        elif request.user.zr_admin_user.role.name == user_map.SUBDISTRIBUTOR:
            main_distributor = get_distributor_from_sub_distributor(request.user.zr_admin_user.zr_user)
        if not main_distributor:
            response_data = {
                "message": error_message,
                "success": False
            }
            return Response(response_data, status=status.HTTP_200_OK)
        data["to_user"] = main_distributor.id
        serializer = PaymentRequestSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            success_message = '{0} {1} {2}'.format(SUCCESS_MESSAGE_START,
                                                   "Payment request sent successfully",
                                                   MESSAGE_END)

            response_data = {
                "responser": serializer.data,
                "message": success_message,
                "success": True
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        response_data = {
            "responser": serializer.errors,
            "message": error_message,
            "success": False
        }
        return Response(response_data, status=status.HTTP_200_OK)


class RefundRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        payment_request = request.GET.get('payment_request')
        payment_request_instance = PaymentRequest.objects.filter(id=payment_request).last()
        if not payment_request_instance:
            raise Http404

        from_user_wallet = zrwallet_models.Wallet.objects.get(
            merchant=payment_request_instance.from_user
        )
        to_user_wallet = zrwallet_models.Wallet.objects.get(
            merchant=payment_request_instance.to_user
        )

        from_user_wallet.dmt_balance -= payment_request_instance.dmt_amount
        from_user_wallet.non_dmt_balance -= payment_request_instance.non_dmt_amount

        to_user_wallet.dmt_balance += payment_request_instance.dmt_amount
        to_user_wallet.non_dmt_balance += payment_request_instance.non_dmt_amount

        from_user_wallet.save(
            update_fields=['dmt_balance', 'non_dmt_balance']
        )
        to_user_wallet.save(
            update_fields=['dmt_balance', 'non_dmt_balance']
        )

        payment_request_instance.status = 3
        payment_request_instance.save(update_fields=['status'])

        zrwallet_models.WalletTransactions.objects.create(
            wallet=from_user_wallet,
            transaction=None,
            payment_request=payment_request_instance,
            dmt_balance=payment_request_instance.dmt_amount * decimal.Decimal('-1'),
            non_dmt_balance=payment_request_instance.non_dmt_amount * decimal.Decimal('-1'),
            dmt_closing_balance=from_user_wallet.dmt_balance,
            non_dmt_closing_balance=from_user_wallet.non_dmt_balance,
            is_success=True
        )

        zrwallet_models.WalletTransactions.objects.create(
            wallet=to_user_wallet,
            transaction=None,
            payment_request=payment_request_instance,
            dmt_balance=payment_request_instance.dmt_amount,
            non_dmt_balance=payment_request_instance.non_dmt_amount,
            dmt_closing_balance=to_user_wallet.dmt_balance,
            non_dmt_closing_balance=to_user_wallet.non_dmt_balance,
            is_success=True
        )

        return HttpResponseRedirect('/payment_request/')


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
                    zr_wallet = zrwallet_models.Wallet.objects.get(
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
                    zrwallet_models.WalletTransactions.objects.create(
                        wallet=zr_wallet,
                        transaction=None,
                        payment_request=payment_request,
                        dmt_balance=payment_request.dmt_amount,
                        non_dmt_balance=payment_request.non_dmt_amount,
                        dmt_closing_balance=zr_wallet.dmt_balance,
                        non_dmt_closing_balance=zr_wallet.non_dmt_balance,
                        is_success=True
                    )
                    message = "Wallet updated successfully"
                    payment_request.status = 1
                    payment_request.save(update_fields=['status'])
                elif self.request.user.zr_admin_user.role.name in ['DISTRIBUTOR', 'SUBDISTRIBUTOR']:
                    supervisor_wallet = zrwallet_models.Wallet.objects.get(
                        merchant=payment_request.to_user
                    )
                    zr_wallet = zrwallet_models.Wallet.objects.get(
                        merchant=payment_request.from_user
                    )
                    updated = False

                    balance_insufficient = []
                    if (
                                    supervisor_wallet.dmt_balance >= payment_request.dmt_amount and
                                    supervisor_wallet.non_dmt_balance >= payment_request.non_dmt_amount
                    ):
                        # For DMT
                        zr_wallet.dmt_balance += payment_request.dmt_amount
                        supervisor_wallet.dmt_balance -= payment_request.dmt_amount

                        # For non dmt
                        zr_wallet.non_dmt_balance += payment_request.non_dmt_amount
                        supervisor_wallet.non_dmt_balance -= payment_request.non_dmt_amount
                        updated = True
                    else:
                        if not (supervisor_wallet.dmt_balance >= payment_request.dmt_amount):
                            balance_insufficient.append('DMT balance')
                        elif not (supervisor_wallet.non_dmt_balance >= payment_request.non_dmt_amount):
                            balance_insufficient.append('NON DMT balance')

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
                        zrwallet_models.WalletTransactions.objects.create(
                            wallet=supervisor_wallet,
                            transaction=None,
                            payment_request=payment_request,
                            dmt_balance=payment_request.dmt_amount * decimal.Decimal('-1'),
                            non_dmt_balance=payment_request.non_dmt_amount * decimal.Decimal('-1'),
                            dmt_closing_balance=supervisor_wallet.dmt_balance,
                            non_dmt_closing_balance=supervisor_wallet.non_dmt_balance,
                            is_success=True
                        )
                        zrwallet_models.WalletTransactions.objects.create(
                            wallet=zr_wallet,
                            transaction=None,
                            payment_request=payment_request,
                            dmt_balance=payment_request.dmt_amount,
                            non_dmt_balance=payment_request.non_dmt_amount,
                            dmt_closing_balance=zr_wallet.dmt_balance,
                            non_dmt_closing_balance=zr_wallet.non_dmt_balance,
                            is_success=True
                        )
                        payment_request.status = 1
                        payment_request.save(update_fields=['status'])
                    else:
                        message = "Insufficient balance in (%s), Please recharge you wallet" % (','.join(balance_insufficient))
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
                if request.user.zr_admin_user.zr_user and payment_request.to_user.pk == request.user.zr_admin_user.zr_user.pk:
                    message = "Payment request rejected successfully"
                    payment_request.status = 2
                    payment_request.reject_comments = rejection_reason
                    payment_request.save(update_fields=['status', 'reject_comments'])
                elif is_user_superuser(request) and payment_request.to_user.role.name == 'ADMINSTAFF':
                    message = "Payment request rejected successfully"
                    payment_request.status = 2
                    payment_request.reject_comments = rejection_reason
                    payment_request.save(update_fields=['status', 'reject_comments'])
                else:
                    message = "Not allowed to accept payment request"
            else:
                message = "Payment request already {status}".format(status=payment_request.get_status_display())

        return Response({"message": message, 'success': True}, status=status.HTTP_200_OK)


def get_payment_request_qs(request, from_user=False, to_user=False, all_user=False, all_req=False):
    q = request.GET.get('q')

    queryset = []
    if is_user_superuser(request):
        if all_user and all_req:
            queryset = PaymentRequest.objects.all()
        elif all_user:
            queryset = PaymentRequest.objects.all()
        else:
            queryset = PaymentRequest.objects.filter(to_user__role__name='ADMINSTAFF',)
    elif request.user.zr_admin_user.role.name in ['DISTRIBUTOR', 'SUBDISTRIBUTOR']:
        # To get own payment request
        if from_user:
            queryset = PaymentRequest.objects.filter(
                from_user=request.user.zr_admin_user.zr_user
            )
        else:
            queryset = PaymentRequest.objects.filter(
                to_user=request.user.zr_admin_user.zr_user
            ).exclude(from_user=request.user.zr_admin_user.zr_user)
    if q:
        query = Q(
            to_user__first_name__icontains=q
        ) | Q(
            to_user__last_name__icontains=q
        ) | Q(
            to_user__mobile_no__contains=q
        ) | Q(
            to_user__first_name__icontains=q
        ) | Q(
            to_user__last_name__icontains=q
        ) | Q(
            to_user__mobile_no__contains=q
        )
        queryset = queryset.filter(query)



    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')
    to_user_id = request.GET.get('to_user_id')
    from_user_id =request.GET.get('from_user_id')

    if start_date != None and end_date != None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))

    if from_user_id!=None and int(from_user_id) > 0:
        queryset = queryset.filter(from_user_id=from_user_id)

    if to_user_id!=None and int(to_user_id) > 0:
        queryset = queryset.filter(to_user_id=to_user_id)

    return queryset.order_by('-at_created')


def merchant_payment_req_csv_download(request):
    sent_request = request.GET.get('sent')
    if sent_request == 'true':
        qs = get_payment_request_qs(request, from_user=True)
    else:
        qs = get_payment_request_qs(request, to_user=True)

    if request.user.zr_admin_user.role.name == 'ADMINSTAFF':
        qs = get_payment_request_qs(request, all_user=True)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payment-requests.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Status",
        "Date",
        "Amount",
        "DMT Amount",
        "NON DMT Amount",
        "Payment Mode",
        "Challan document",
        "To User Name",
        "From User Name",
        "From Bank Account Number",
        "To Bank Account Number",
        "From bank",
        "To bank",
        "Ref Id"
    ])

    for payment_req in qs:
        writer.writerow(
            [
                payment_req.get_status(),
                payment_req.at_created,
                payment_req.amount,
                payment_req.dmt_amount,
                payment_req.non_dmt_amount,
                payment_req.payment_mode,
                payment_req.document,
                'admin' if payment_req.to_user.role.name == 'ADMINSTAFF' else payment_req.to_user.get_full_name(),
                'admin' if payment_req.from_user.role.name == 'ADMINSTAFF' else payment_req.from_user.get_full_name(),
                payment_req.from_account_no,
                payment_req.from_account_no,
                payment_req.to_account_no,
                payment_req.from_bank.bank_name.encode('utf-8', 'ignore'),
                payment_req.to_bank.bank_name.encode('utf-8', 'ignore'),
                payment_req.ref_no.encode('utf-8', 'ignore') if payment_req.ref_no else '',
            ]
        )

    return response


def get_report_csv(params):
    qs = get_payment_qs_dict(params)
    response = HttpResponse(content_type='text/csv')
    unique_name = datetime.datetime.now().strftime("%d-%m-%YT%H:%M:%S-") + ''.join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    report_file_path = settings.REPORTS_PATH + "/" + unique_name + ".csv"
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(report_file_path)

    with open(report_file_path, 'w') as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow([
            "Vendor Id",
            "Mode",
            "Amount",
            "Transaction Id",
            "Vendor Transaction Id",
            "Customer",
            "User",
            "Additional Charges",
            "Settled",
        ])
        paginator = Paginator(qs, 1)
        for x in paginator.page_range:
            page_data = paginator.page(x)
            for payment_req in page_data:
                writer.writerow(
                    [
                        payment_req.vendor.id if payment_req.vendor else 'N/A',
                        payment_req.mode,
                        payment_req.amount,
                        payment_req.txn_id,
                        payment_req.vendor_txn_id,
                        payment_req.customer,
                        payment_req.user.get_full_name(),
                        payment_req.additional_charges,
                        payment_req.settled,
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
        "start_date": request.POST.get('startDate', ''),
        "end_date": request.POST.get('endDate', ''),
        "user_id": request.user.id,
    }
    from zrpayment import tasks as payment_celery_tasks
    payment_celery_tasks.send_payment_report.apply_async(args=[report_params])
    return JsonResponse({"success": True})


class PaymentRequestListView(ListView):
    context_object_name = 'payment_request_list'
    template_name = 'payment_request_list.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        filter_by = self.request.GET.get('filter')
        q = self.request.GET.get('q')
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        from_user_id = self.request.GET.get('from_user_id')
        context = super(PaymentRequestListView, self).get_context_data(**kwargs)
        fromuser_list = PaymentRequest.objects.all().filter(to_user__role__name='ADMINSTAFF', ).distinct('from_user_id')
        distributor_id = self.request.GET.get('distributor-id')
        sub_distributor_list = []
        queryset = self.get_queryset()
       # if not queryset:
       #     context['filter_by'] = filter_by
        #    context['q'] = q
         #   return context
        if is_user_superuser(self.request):
            fromuser_list = PaymentRequest.objects.all().filter(to_user__role__name='ADMINSTAFF', ).distinct(
                'from_user_id')

        elif self.request.user.zr_admin_user.role.name in ['DISTRIBUTOR']:
            fromuser_list = PaymentRequest.objects.all().filter(from_user=self.request.user.zr_admin_user.zr_user ).distinct(
                'from_user_id')

        elif self.request.user.zr_admin_user.role.name in ['SUBDISTRIBUTOR']:
            fromuser_list = PaymentRequest.objects.all().filter(to_user__role__name='SUBDISTRIBUTOR', ).distinct('from_user_id')

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
            try:
                wallet = zrwallet_models.Wallet.objects.get(
                    merchant=self.request.user.zr_admin_user.zr_user
                )
            except:
                pass
        context['wallet'] = wallet
        context['url_name'] = "payment-request-list"
        context['is_superuser'] = is_user_superuser(self.request)
        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if distributor_id:
            context['distributor_id'] = int(distributor_id)

        if from_user_id:
            context['from_user_id'] = int(from_user_id)

        if fromuser_list:
            context['fromuser_list'] = fromuser_list

        return context

    def get_queryset(self):
        return get_payment_request_qs(self.request, from_user=False, to_user=True)


def get_payment_qs(request):
    q = request.GET.get('q')
    queryset = Payments.objects.all()

    if q:
        query = Q(
            txn_id__contains=q
        ) | Q(
            vendor_txn_id__contains=q
        ) | Q(
            vendor__id__contains=q
        ) | Q(
            customer__contains=q
        ) | Q(
            vendor__name__icontains=q
        ) | Q(
            user__mobile_no__contains=q
        ) | Q(
            user__first_name__icontains=q
        ) | Q(
            user__last_name__icontains=q
        )
        queryset = queryset.filter(query)

    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')
    user_payment_id = request.GET.get('user_payment_id')

    if start_date != None and end_date != None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))

    if user_payment_id!=None and int(user_payment_id) > 0:
        queryset = queryset.filter(user_id=user_payment_id)

    return queryset.order_by('-at_created')


def get_payment_qs_dict(report_params):
    filter_by = report_params.get('filter', "")
    q = report_params.get('q', "")

    queryset = Payments.objects.all()
    if q:
        query = Q(
            customer__icontains=q
        ) | Q(
            txn_id__icontains=q
        ) | Q(
            merchant__id=q
        ) | Q(
            merchant__first_name__icontains=q
        ) | Q(
            merchant__last_name__icontains=q
        )
        queryset = queryset.filter(query)

    if filter_by == 'last_week':
        queryset = queryset.filter(at_created__range=last_week_range())
    elif filter_by == 'last_month':
        queryset = queryset.filter(at_created__range=last_month())
    elif filter_by == 'today':
        queryset = queryset.filter(at_created__date__gte=datetime.date.today())

    start_date = report_params.get('start_date')
    end_date = report_params.get('end_date')

    if start_date != None and end_date != None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))

    return queryset.order_by('-at_created')


class PaymentListView(ListView):
    context_object_name = 'payment_list'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        filter_by = self.request.GET.get('filter', 'all')
        q = self.request.GET.get('q')
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        user_payment_id = self.request.GET.get('user_payment_id')
        context = super(PaymentListView, self).get_context_data(**kwargs)
        user_list = Payments.objects.all().distinct('user_id')
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

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if user_list:
            context['user_list'] = user_list

        if user_payment_id:
            context['user_payment_id'] = int(user_payment_id)

        context['main_url'] = reverse('payment-requests:payment-list')
        context['page_obj'] = queryset
        context['filter_by'] = filter_by
        context['q'] = q
        context['url_name'] = "payment-list"

        context['is_superuser'] = is_user_superuser(self.request)
        return context

    def get_queryset(self):
        return get_payment_qs(self.request)


class PaymentRequestSentListView(ListView):
    context_object_name = 'paymentrequestsent_list'
    template_name = 'zrpayment/paymentrequestsent_list.html'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        filter_by = self.request.GET.get('filter')
        q = self.request.GET.get('q')
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')
        to_user_id = self.request.GET.get('to_user_id')
        touser_list = []
        context = super(PaymentRequestSentListView, self).get_context_data(**kwargs)

        queryset = self.get_queryset()
        #if not queryset:
         #   context['filter_by'] = filter_by
          #  context['q'] = q
           # return context

        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page', 1)

        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)

        context['page_obj'] = queryset
        context['filter_by'] = filter_by
        context['q'] = q

        if is_user_superuser(self.request):
            touser_list = PaymentRequest.objects.all().distinct('to_user_id')
        elif self.request.user.zr_admin_user.role.name in ['DISTRIBUTOR', 'SUBDISTRIBUTOR']:
            touser_list = PaymentRequest.objects.filter(to_user=self.request.user.zr_admin_user.zr_user)

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if touser_list:
            context['touser_list'] = touser_list

        if to_user_id:
            context['to_user_id'] = int(to_user_id)

        wallet = None
        if not is_user_superuser(self.request):
           try:
            wallet = zrwallet_models.Wallet.objects.get(
                merchant=self.request.user.zr_admin_user.zr_user
            )
           except:
               pass

        context['wallet'] = wallet
        context['url_name'] = "payment-request-sent-view"
        context['is_superuser'] = is_user_superuser(self.request)
        return context

    def get_queryset(self):
        if is_user_superuser(self.request):
            return get_payment_request_qs(self.request, all_user=True, all_req=True)
        else:
            return get_payment_request_qs(self.request, from_user=True)


class GenerateTopUpRequestView(APIView):
    queryset = PaymentRequest.objects.all()
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        err_msg = "Something went wrong, please try again"
        data = {}

        bank = Bank.objects.all().first()

        wallet = PaymentMode.objects.all().filter(name='WALLET')
        for detail, value in request.data.items():
            data[detail] = value

        # return Response(data, status=status.HTTP_200_OK)
        data['to_user'] = request.user.zr_admin_user.zr_user.id

        data['payment_type'] = 2
        data['payment_mode'] = wallet
        data['dmt_amount'] = 0
        data['non_dmt_amount'] = 0
        if data['type'] == "DMT":
            data['dmt_amount'] = data['amount']
        else:
            data['non_dmt_amount'] = data['amount']

        data['from_account_no'] = "xxx_Topup_{0}".format(str(data['to_user']))
        data['to_account_no'] = "xxx_Topup_{0}".format(str(data['from_user']))

        data['from_bank'] = bank.id
        data['to_bank'] = bank.id
        data['comments'] = "TOPUP"
        data['status'] = 0

        topup_form = zr_payment_form.TopupForm(data=data)
        if not topup_form.is_valid():
            to_list = []
            distributor_merchant = []
            distributor_subdistributor = []

            distributor_merchant = zrmappings_models.DistributorMerchant.objects.filter(
                distributor_id=request.user.zr_admin_user.zr_user)
            if distributor_merchant:
                for distributor_merchant_map in distributor_merchant:
                    to_list.append(distributor_merchant_map.merchant)

            distributor_subdistributor = zrmappings_models.DistributorSubDistributor.objects.filter(
                distributor_id=request.user.zr_admin_user.zr_user)
            if distributor_subdistributor:
                for distributor_subdistributor_map in distributor_subdistributor:
                    to_list.append(distributor_subdistributor_map.sub_distributor)

            error_message = '{0} {1} {2} {3}'.format(ERROR_MESSAGE_START,
                                                 err_msg , topup_form.errors,
                                                 MESSAGE_END)

            response_data = {
                "responser": topup_form.errors,
                "message": error_message,
                "success": False
            }
            return Response(response_data, status=status.HTTP_200_OK)

        # updating the topup data in zrwallet table
        payment_request = topup_form.save()
        if payment_request:
            if payment_request.status == 0:
                if is_user_superuser(self.request) and payment_request.to_user.role.name == 'ADMINSTAFF':
                    zr_wallet = zrwallet_models.Wallet.objects.get(
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
                    zrwallet_models.WalletTransactions.objects.create(
                        wallet=zr_wallet,
                        transaction=None,
                        payment_request=payment_request,
                        dmt_balance=payment_request.dmt_amount,
                        non_dmt_balance=payment_request.non_dmt_amount,
                        dmt_closing_balance=zr_wallet.dmt_balance,
                        non_dmt_closing_balance=zr_wallet.non_dmt_balance,
                        is_success=True
                    )
                    # "Wallet updated successfully"
                    payment_request.status = 1
                    payment_request.save(update_fields=['status'])
                elif self.request.user.zr_admin_user.role.name in ['DISTRIBUTOR', 'SUBDISTRIBUTOR']:
                    # Amount from supervisor_wallet transferred to zr_wallet
                    # supervisor_wallet is self(from) wallet for TOPUP
                    supervisor_wallet = zrwallet_models.Wallet.objects.get(
                        merchant=payment_request.to_user
                    )
                    # zr_wallet is other(to) wallet for TOPUP
                    zr_wallet = zrwallet_models.Wallet.objects.get(
                        merchant=payment_request.from_user
                    )
                    updated = False

                    balance_insufficient = []
                    if (
                            supervisor_wallet.dmt_balance >= payment_request.dmt_amount and
                            supervisor_wallet.non_dmt_balance >= payment_request.non_dmt_amount
                    ):
                        # For DMT
                        zr_wallet.dmt_balance += payment_request.dmt_amount
                        supervisor_wallet.dmt_balance -= payment_request.dmt_amount

                        # For non dmt
                        zr_wallet.non_dmt_balance += payment_request.non_dmt_amount
                        supervisor_wallet.non_dmt_balance -= payment_request.non_dmt_amount
                        updated = True
                    else:
                        if not (supervisor_wallet.dmt_balance >= payment_request.dmt_amount):
                            balance_insufficient.append('DMT balance')
                        elif not (supervisor_wallet.non_dmt_balance >= payment_request.non_dmt_amount):
                            balance_insufficient.append('NON DMT balance')

                    if updated:
                        # "Wallet updated successfully"
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
                        zrwallet_models.WalletTransactions.objects.create(
                            wallet=supervisor_wallet,
                            transaction=None,
                            payment_request=payment_request,
                            dmt_balance=payment_request.dmt_amount * decimal.Decimal('-1'),
                            non_dmt_balance=payment_request.non_dmt_amount * decimal.Decimal('-1'),
                            dmt_closing_balance=supervisor_wallet.dmt_balance,
                            non_dmt_closing_balance=supervisor_wallet.non_dmt_balance,
                            is_success=True
                        )
                        zrwallet_models.WalletTransactions.objects.create(
                            wallet=zr_wallet,
                            transaction=None,
                            payment_request=payment_request,
                            dmt_balance=payment_request.dmt_amount,
                            non_dmt_balance=payment_request.non_dmt_amount,
                            dmt_closing_balance=zr_wallet.dmt_balance,
                            non_dmt_closing_balance=zr_wallet.non_dmt_balance,
                            is_success=True
                        )
                        payment_request.status = 1
                        payment_request.save(update_fields=['status'])
                        message = '{0} {1} {2}'.format(SUCCESS_MESSAGE_START,
                                                               "TopUp sent successfully",
                                                               MESSAGE_END)

                    else:
                        message = "Insufficient balance in (%s), Please recharge you wallet" % (
                        ','.join(balance_insufficient))

                    response_data = {
                        "responser": "payment_request",
                        "message": message,
                        "success": True
                    }
                return Response(response_data, status=status.HTTP_201_CREATED)
