# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import csv

from django.db.models import Q
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.core.paginator import Paginator, PageNotAnInteger
from django.http import HttpResponse

from zrpayment.models import MerchantPaymentRequest
from common_utils.date_utils import last_month, last_week_range


class MerchantPaymentRequestDetailView(DetailView):
    queryset = MerchantPaymentRequest.objects.all()
    context_object_name = 'payment_request'


def get_merchant_payment_qs(request):
    filter_by = request.GET.get('filter')
    q = request.GET.get('q')

    queryset = []
    if request.user.is_superuser or request.user.zr_admin_user.role.name == "ADMINSTAFF":
        queryset = MerchantPaymentRequest.objects.all()
    elif request.user.zr_admin_user.role.name == 'DISTRIBUTOR':
        queryset = MerchantPaymentRequest.objects.filter(
            distributor=request.user.zr_admin_user
        )

    if q:
        query = Q(
            merchant_payment_mode__name__contains=q
        ) | Q(
            distributor__first_name__contains=q
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
    qs = get_merchant_payment_qs(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payment-requests.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Date',
        'Type',
        'Amount',
        'Payment Mode',
        'Merchant Name',
        'Merchant Id',
        'Ref Id',
    ])

    paginator = Paginator(qs, MerchantPaymentRequestListView.paginate_by)
    page = request.GET.get('page', 1)

    try:
        queryset = paginator.page(page)
    except PageNotAnInteger:
        queryset = paginator.page(1)

    qs = queryset.object_list
    for payment_req in qs:
        writer.writerow(
            [
                payment_req.at_created,
                'TYPE',
                payment_req.amount,
                payment_req.merchant_payment_mode,
                payment_req.merchant.first_name,
                payment_req.merchant.id,
                payment_req.merchant_ref_no,
            ]
        )

    return response


class MerchantPaymentRequestListView(ListView):
    context_object_name = 'payment_request_list'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        payment_approved = self.request.GET.get('payment-approve')
        filter_by = self.request.GET.get('filter')
        q = self.request.GET.get('q')

        if payment_approved:
            if self.request.user.is_superuser or self.request.user.zr_admin_user.role.name == 'ADMINSTAFF':
                MerchantPaymentRequest.objects.filter(
                    id=payment_approved
                ).update(
                    is_admin_approved=True
                )
            elif self.request.user.zr_admin_user.role.name == 'DISTRIBUTOR':
                MerchantPaymentRequest.objects.filter(
                    id=payment_approved
                ).update(
                    is_distributor_approved=True
                )

        context = super(MerchantPaymentRequestListView, self).get_context_data(**kwargs)

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
        return context

    def get_queryset(self):
        return get_merchant_payment_qs(self.request)