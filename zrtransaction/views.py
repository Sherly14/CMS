# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import datetime
from urllib import urlencode

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from django.http.response import Http404, HttpResponse
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from common_utils import user_utils
from common_utils.date_utils import last_month, last_week_range
from common_utils.transaction_utils import get_sub_distributor_merchant_id_list_from_distributor, \
    get_merchant_id_list_from_distributor, \
    get_sub_distributor_merchant_id_list_from_sub_distributor
from zrtransaction.models import Transaction
from zruser.mapping import DISTRIBUTOR, SUBDISTRIBUTOR


class TransactionsDetailView(DetailView):
    queryset = Transaction.objects.all()
    context_object_name = 'transaction'


def get_transactions_qs_with_dict(report_params):
    q = report_params.get('q', "")
    q_obj = Q()
    if q:
        q_obj = Q(
            user__first_name__contains=q
        ) | Q(
            user__last_name__contains=q
        ) | Q(
            user__mobile_no__contains=q
        )

    p_filter = report_params.get('filter', 'All')
    if p_filter == 'All':
        p_filter = report_params.get('period', "All")

    p_filter =report_params.get('start_date')
    p_filter = report_params.get('end_date')


    if any (date in p_filter for date in('start_date','end_date')):
        q_obj.add(Q(at_created__range=('start_date', 'end_date')),q_obj.connector)

    if p_filter in ['Today', 'today']:
        q_obj.add(Q(at_created__gte=datetime.datetime.now().date()), q_obj.connector)
    elif p_filter in ['Last-Week' or 'last-week']:
        q_obj.add(Q(at_created__range=last_week_range()), q_obj.connector)
    elif p_filter in ['Last-Month' or 'last-month']:
        q_obj.add(Q(at_created__range=last_month()), q_obj.connector)

    user = get_user_model().objects.filter(pk=report_params.get('user_id')).last()
    if report_params.get('user_type') == "SU":
        pass
        # If user is main admin then need to show all listing
    elif report_params.get('user_type') == SUBDISTRIBUTOR:
        # SUB DISTRIBUTOR
        # Get merchants for sub-distributor
        q_obj.add(
            (Q(user_id__in=
               # [request.user.zr_admin_user.zr_user_id] +
               get_sub_distributor_merchant_id_list_from_sub_distributor(user.zr_admin_user.zr_user))),
            q_obj.connector
        )
    elif report_params.get('user_type') == DISTRIBUTOR:
        # DISTRIBUTOR
        # Get merchants for distrubutor and sub-distributor
        q_obj.add(
            (Q(user_id__in=
               # [request.user.zr_admin_user.zr_user_id] +
               get_merchant_id_list_from_distributor(user.zr_admin_user.zr_user) +
               # get_sub_distributor_id_list_from_distributor(request.user.zr_admin_user.zr_user) +
               get_sub_distributor_merchant_id_list_from_distributor(user.zr_admin_user.zr_user))),
            q_obj.connector
        )


    queryset = Transaction.objects.filter(q_obj).order_by('-at_created')



    return queryset


def get_transactions_qs(request):
    q = request.GET.get('q', "")
    q_obj = Q(
        user__first_name__contains=q
    ) | Q(
        user__last_name__contains=q
    ) | Q(
        user__mobile_no__contains=q
    )
    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')
    user_transaction_id = request.GET.get('user_transaction_id')
    p_filter = request.GET.get('filter', 'All')
    if p_filter == 'All':
        p_filter = request.GET.get('period', "All")

    if p_filter in ['Today', 'today']:
        q_obj.add(Q(at_created__gte=datetime.datetime.now().date()), q_obj.connector)
    elif p_filter in ['Last-Week' or 'last-week']:
        q_obj.add(Q(at_created__range=last_week_range()), q_obj.connector)
    elif p_filter in ['Last-Month' or 'last-month']:
        q_obj.add(Q(at_created__range=last_month()), q_obj.connector)

    if user_utils.is_user_superuser(request):
        pass
        # If user is main admin then need to show all listing
    elif request.user.zr_admin_user.role.name == SUBDISTRIBUTOR:
        # SUB DISTRIBUTOR
        # Get merchants for sub-distributor
        q_obj.add(
            (Q(user_id__in=
               # [request.user.zr_admin_user.zr_user_id] +
               get_sub_distributor_merchant_id_list_from_sub_distributor(request.user.zr_admin_user.zr_user))),
            q_obj.AND,
            q_obj.connector
        )
    elif request.user.zr_admin_user.role.name == DISTRIBUTOR:
        # DISTRIBUTOR
        # Get merchants for distrubutor and sub-distributor
        q_obj.add(
            (Q(user_id__in=
               # [request.user.zr_admin_user.zr_user_id] +
               get_merchant_id_list_from_distributor(request.user.zr_admin_user.zr_user) +
               # get_sub_distributor_id_list_from_distributor(request.user.zr_admin_user.zr_user) +
               get_sub_distributor_merchant_id_list_from_distributor(request.user.zr_admin_user.zr_user))),
            q_obj.AND,
            q_obj.connector
        )

    queryset = Transaction.objects.filter(q_obj).order_by('-at_created')



    if user_transaction_id!=None and int(user_transaction_id) > 0:
        queryset = queryset.filter(user_id=user_transaction_id)


    if start_date != None and end_date != None:
        queryset = queryset.filter(at_created__range=(start_date, end_date))
    print(q_obj)
    return queryset


class TransactionsListView(ListView):
    queryset = Transaction.objects.filter()
    context_object_name = 'transaction_list'
    paginate_by = 10

    def get_queryset(self):
        return get_transactions_qs(self.request)

    def get_context_data(self, *args, **kwargs):
        context = super(TransactionsListView, self).get_context_data()
        query_string = {}
        start_date = self.request.GET.get('startDate')
        end_date = self.request.GET.get('endDate')

        if user_utils.is_user_superuser(self.request):
            user_transaction_data = Transaction.objects.all().distinct('user_id').exclude(txn_id ='')

        elif self.request.user.zr_admin_user.role.name == SUBDISTRIBUTOR:
            user_transaction_data = Transaction.objects.filter(user_id__in=get_sub_distributor_merchant_id_list_from_sub_distributor(self.request.user.zr_admin_user.zr_user)).distinct('user_id').exclude(txn_id='')

        elif self.request.user.zr_admin_user.role.name == DISTRIBUTOR:
            user_transaction_data = Transaction.objects.filter(user_id__in=get_merchant_id_list_from_distributor(self.request.user.zr_admin_user.zr_user) +
               get_sub_distributor_merchant_id_list_from_distributor(self.request.user.zr_admin_user.zr_user)).distinct('user_id').exclude(txn_id='')

        user_transaction_id =self.request.GET.get('user_transaction_id')
        # Search context
        q = self.request.GET.get('q')
        if q:
            context['q'] = q
            query_string['q'] = q

        # Period filter
        p_filter = self.request.GET.get('filter')

        if p_filter:
            context['filter_by'] = p_filter
            query_string['filter'] = p_filter

        # Pagination
        pg_no = self.request.GET.get('page_no', 1)
        queryset = self.get_queryset()
        context['queryset'] = queryset
        p = Paginator(context['queryset'], self.paginate_by)
        try:
            page = p.page(pg_no)
        except EmptyPage:
            raise Http404

        if start_date:
            context['startDate'] = start_date

        if end_date:
            context['endDate'] = end_date

        if user_transaction_data:
            context['user_transaction_data'] = user_transaction_data


        if user_transaction_id :
            context['user_transaction_id'] =int(user_transaction_id)



        context['queryset'] = page.object_list
        if page.has_next():
            query_string['page_no'] = page.next_page_number()
            context['next_page_qs'] = urlencode(query_string)
            context['has_next_page'] = page.has_next()
        if page.has_previous():
            query_string['page_no'] = page.previous_page_number()
            context['prev_page_qs'] = urlencode(query_string)
            context['has_prev_page'] = page.has_previous()

        return context


def download_transaction_list_csv(request):
    transactions_qs = get_transactions_qs(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Merchant Id", "Vendor Txn Id", "status", "Amount", "Type", "Mobile number", "Customer", "Amount",
        "Additional charges", "Transaction type", "Service provider"
    ])
    for transaction in transactions_qs:
        writer.writerow([
            transaction.user.id,
            transaction.vendor_txn_id,
            transaction.get_status_display(),
            transaction.amount,
            transaction.type,
            transaction.user.mobile_no,
            transaction.customer,
            transaction.amount,
            transaction.additional_charges,
            transaction.type,
            transaction.service_provider.name if transaction.service_provider else "",
            # 'Active' if distributor.is_active else 'Inactive'
        ])

    return response
