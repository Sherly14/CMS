# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import unicode_literals

import urllib
import datetime

from django.views.generic import ListView

from zrcommission.models import Commission
from common_utils import transaction_utils
from django.db.models import Sum
from django.core.paginator import Paginator
from django.db.models import F

from common_utils import user_utils
from common_utils import date_utils


def get_commission_qs(comm_display):
    pg_no = comm_display.request.GET.get('pg-no')
    period = comm_display.request.GET.get('period')
    search = comm_display.request.GET.get('q')

    req_usr = comm_display.request.user.zr_admin_user
    return Commission.objects.filter(
        commission_user=req_usr.zr_user
    )


class CommissionDisplay(ListView):
    context_object_name = 'commissions'
    template_name = 'zrcommission/dashboard.html'
    paginated_by = 10

    def get_context_data(self, *args, **kwargs):
        pg_no = self.request.GET.get('pg-no')
        period = self.request.GET.get('period')
        search = self.request.GET.get('q')

        context = super(CommissionDisplay, self).get_context_data(*args, **kwargs)
        if user_utils.is_user_superuser(self.request):
            context['commissions'] = self.get_queryset()
            context['total_commission'] = transaction_utils.calculate_zrupee_user_commission()
        else:
            req_usr = self.request.user.zr_admin_user
            context['total_commission'] = Commission.objects.filter(
                commission_user=req_usr.zr_user
            ).aggregate(commission=Sum(
                F('net_commission') + (F('user_tds') * F('net_commission')) / 100
            ))['commission']
            if context['total_commission']:
                context['total_commission'] = '%.2f' % context['total_commission']
            else:
                context['total_commission'] = 0

        context['period'] = period
        context['search'] = search

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
        pg_no = self.request.GET.get('pg-no')
        period = self.request.GET.get('period')
        search = self.request.GET.get('q')

        req_usr = self.request.user.zr_admin_user
        queryset = Commission.objects.all().order_by('-at_created')
        if user_utils.is_user_superuser(self.request):
            if search:
                queryset = queryset.filter(
                    commission_user__mobile_no__contains=search
                ).order_by('-at_created')
        else:
            if search:
                queryset =Commission.objects.filter(
                    commission_user=req_usr.zr_user,
                    commission_user__mobile_no__contains=search
                )
            else:
                queryset = Commission.objects.filter(
                    commission_user=req_usr.zr_user
                )

        if period == 'today':
            queryset = queryset.filter(at_created=datetime.datetime.now().date())
        elif period == 'last-week':
            queryset = queryset.filter(at_created__range=date_utils.last_week_range())
        elif period == 'last-month':
            queryset = queryset.filter(at_created__range=date_utils.last_month())

        return queryset
