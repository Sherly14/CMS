# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import datetime
import random
import string

from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.generic.list import ListView

from common_utils.date_utils import last_week_range, last_month
from common_utils.user_utils import is_user_superuser
from zrwallet.models import Passbook


def get_passbook_qs(request, is_request_dict=False):
    if is_request_dict:
        filter_by = request.get('filter')
        q = request.get('q')
    else:
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
    paginate_by = 10

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


def get_passbook_report_csv(params):
    qs = get_passbook_qs(params, is_request_dict=True)
    response = HttpResponse(content_type='text/csv')
    unique_name = 'passbook-' + datetime.datetime.now().strftime("%d-%m-%YT%H:%M:%S-") + ''.join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    report_file_path = settings.REPORTS_PATH + "/" + unique_name + ".csv"
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(report_file_path)

    with open(report_file_path, 'w') as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow([
            "User name",
            "Mobile No",
            "DMT opening_balance",
            "DMT opening_wallet_balance",
            "DMT wallet_credit",
            "DMT wallet_debit",
            "DMT closing_balance",
            "DMT closing_wallet_balance",
            "Non DMT opening_balance",
            "Non DMT opening_wallet_balance",
            "Non DMT wallet_credit",
            "Non DMT wallet_debit",
            "Non DMT closing_balance",
            "Non DMT closing_wallet_balance",
        ])
        paginator = Paginator(qs, 1)
        for x in paginator.page_range:
            page_data = paginator.page(x)
            for passbook in page_data:
                writer.writerow(
                    [
                        passbook.user.full_name,
                        passbook.user.mobile_no,
                        passbook.dmt_opening_balance,
                        passbook.dmt_opening_wallet_balance,
                        passbook.dmt_wallet_credit,
                        passbook.dmt_wallet_debit,
                        passbook.dmt_closing_balance,
                        passbook.dmt_closing_wallet_balance,
                        passbook.non_dmt_opening_balance,
                        passbook.non_dmt_opening_wallet_balance,
                        passbook.non_dmt_wallet_credit,
                        passbook.non_dmt_wallet_debit,
                        passbook.non_dmt_closing_balance,
                        passbook.non_dmt_closing_wallet_balance,
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
        "user_id": request.user.id,
    }
    from zrwallet import tasks as passbook_celery_tasks
    # passbook_celery_tasks.send_passbook_report(report_params)
    passbook_celery_tasks.send_passbook_report.apply_async(args=[report_params])
    return JsonResponse({"success": True})
