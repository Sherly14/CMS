# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from zrpayment.models import MerchantPaymentRequest


# Create your views here.

class MerchantPaymentRequestDetailView(DetailView):
    queryset = MerchantPaymentRequest.objects.all()
    context_object_name = 'payment_request'


class MerchantPaymentRequestListView(ListView):
    queryset = MerchantPaymentRequest.objects.all()
    context_object_name = 'payment_request_list'
