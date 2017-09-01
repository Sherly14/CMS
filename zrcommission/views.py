# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import unicode_literals

from django.views.generic import ListView

from zrcommission.models import Commission
from django.db.models import Sum
from django.db.models import F


class CommissionDisplay(ListView):
    context_object_name = 'commissions'
    template_name = 'zrcommission/dashboard.html'

    def get_context_data(self, *args, **kwargs):
        context = super(CommissionDisplay, self).get_context_data(*args, **kwargs)
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

        context['commissions'] = self.get_queryset()
        return context

    def get_queryset(self):
        req_usr = self.request.user.zr_admin_user
        return Commission.objects.filter(
            commission_user=req_usr.zr_user
        )
