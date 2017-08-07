# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import calendar

from datetime import timedelta
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.core.paginator import Paginator, PageNotAnInteger, PageNotAnInteger, EmptyPage

from zrpayment.models import MerchantPaymentRequest


def last_week_range():
    date = datetime.date.today()
    year, week, dow = date.isocalendar()

    # Find the first day of the week.
    if dow == 7:
        # Since we want to start with Sunday, let's test for that condition.
        start_date = date
    else:
        # Otherwise, subtract `dow` number days to get the first day
        start_date = date - timedelta(dow)

    # Now, add 6 for the last day of the week (i.e., count up to Saturday)
    end_date = start_date + timedelta(6)

    start_date = start_date - timedelta(7)
    end_date = end_date - timedelta(7)
    return (start_date, end_date)


def last_month():
    today_date = datetime.date.today()
    current_month = today_date.month
    current_year = today_date.year
    if current_month == 1:
        current_month = 12
        current_year = current_year - 1
    else:
        current_month -= 1

    start_date, end_date = calendar.monthrange(current_year, current_month)
    start_date = datetime.date(day=start_date, month=current_month, year=current_year)
    end_date = datetime.date(day=end_date, month=current_month, year=current_year)

    return start_date, end_date


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
