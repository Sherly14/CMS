# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime
from django.core.paginator import Paginator, PageNotAnInteger
from django.db.models import Q
from django.views.generic.list import ListView

from common_utils.date_utils import last_week_range, last_month
from common_utils.user_utils import is_user_superuser
from zrwallet.models import Passbook


def get_passbook_qs(request):
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

    return queryset.order_by('-at_created')


class PaymentListView(ListView):
    context_object_name = 'passbook_list'
    paginate_by = 1

    def get_context_data(self, **kwargs):
        filter_by = self.request.GET.get('filter', 'all')
        q = self.request.GET.get('q')

        context = super(PaymentListView, self).get_context_data(**kwargs)

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
        from django.core.urlresolvers import reverse

        context['main_url'] = reverse('wallet:passbook-list')
        context['page_obj'] = queryset
        context['filter_by'] = filter_by
        context['q'] = q

        context['is_superuser'] = is_user_superuser(self.request)
        return context

    def get_queryset(self):
        return get_passbook_qs(self.request)
