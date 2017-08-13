# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import calendar

from datetime import timedelta
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.core.paginator import Paginator, PageNotAnInteger, PageNotAnInteger, EmptyPage

from zrpayment.models import MerchantPaymentRequest
from common_utils.date_utils import last_month, last_week_range


class MerchantPaymentRequestDetailView(DetailView):
    queryset = MerchantPaymentRequest.objects.all()
    context_object_name = 'payment_request'


class MerchantPaymentRequestListView(ListView):
    context_object_name = 'payment_request_list'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        payment_approved = self.request.GET.get('payment-approve')
        if payment_approved:
            if self.request.user.is_superuser:
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
            return context

        filter_by = self.request.GET.get('filter')

        paginator = Paginator(queryset, self.paginate_by)
        page = self.request.GET.get('page', 1)

        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            queryset = paginator.page(1)

        context['page_obj'] = queryset
        context['filter_by'] = filter_by
        return context

    def get_queryset(self):
        filter_by = self.request.GET.get('filter')
        queryset = []
        if self.request.user.is_superuser:
            queryset = MerchantPaymentRequest.objects.all()
        elif self.request.user.zr_admin_user.role == 'DISTRIBUTOR':
            queryset = MerchantPaymentRequest.objects.filter(
                distributor=self.request.user.zr_admin_user
            )

        if filter_by == 'last_week':
            queryset = queryset.filter(at_created__range=last_week_range())
        elif filter_by == 'last_month':
                queryset = queryset.filter(at_created__range=last_month())
        elif filter_by == 'today':
            queryset = queryset.filter(at_created__date__gte=datetime.date.today())

        return queryset
