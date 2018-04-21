# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import unicode_literals

import csv
import datetime
import urllib

from django.core.paginator import Paginator
from django.db.models import F
from django.db.models import Sum
from django.http import Http404
from django.http import HttpResponse
from django.views.generic import ListView
from django.db.models import Q

from common_utils import date_utils
from common_utils import user_utils
from zrcommission.models import Commission


def get_commission_qs(comm_display):
    pg_no = comm_display.request.GET.get('pg-no')
    period = comm_display.request.GET.get('period')
    search = comm_display.request.GET.get('q')

    req_usr = comm_display.request.user.zr_admin_user
    return Commission.objects.filter(
        commission_user=req_usr.zr_user
    )


def get_commission_display_qs(request):
    period = request.GET.get('period')
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
            )
        else:
            queryset = Commission.objects.filter(
                commission_user=req_usr.zr_user,
                is_settled=False
            )

    if period == 'today':
        queryset = queryset.filter(at_created=datetime.datetime.now().date())
    elif period == 'last-week':
        queryset = queryset.filter(at_created__range=date_utils.last_week_range())
    elif period == 'last-month':
        queryset = queryset.filter(at_created__range=date_utils.last_month())

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
        pg_no = self.request.GET.get('pg-no')
        period = self.request.GET.get('period')
        search = self.request.GET.get('q')
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')

        context = super(CommissionDisplay, self).get_context_data(*args, **kwargs)
        if user_utils.is_user_superuser(self.request):
            context['commissions'] = self.get_queryset()
            total_commission = Commission.objects.filter(
                commission_user=None,
                is_settled=False
            ).aggregate(commission=Sum(
                F('net_commission') + (F('user_tds') * F('net_commission')) / 100
            ))['commission']
            if total_commission:
                context['total_commission'] = '%.2f' % total_commission
            else:
                context['total_commission'] = '%.2f' % 0
        else:
            req_usr = self.request.user.zr_admin_user
            total_commission = Commission.objects.filter(
                commission_user=req_usr.zr_user,
                is_settled=False
            ).aggregate(commission=Sum(
                F('net_commission') + (F('user_tds') * F('net_commission')) / 100
            ))['commission']
            if total_commission:
                context['total_commission'] = '%.2f' % total_commission
            else:
                context['total_commission'] = '%.2f' % 0

        context['period'] = period
        context['search'] = search

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        query_result = self.get_queryset()
        p = Paginator(query_result, self.paginated_by)
        pg = None
        try:
            if pg_no:
                pg = p.page(pg_no)
            else:
                pg = p.page(1)
        except:
            pg = p.page(1)

        qs_data = {}

        if period:
            qs_data['period'] = period

        if search:
            qs_data['search'] = search

        qs = urllib.urlencode(qs_data)
        context['commissions'] = pg
        context['qs'] = qs
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