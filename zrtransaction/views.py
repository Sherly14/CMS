# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from zrtransaction.models import Transaction


# Create your views here.

class TransactionsDetailView(DetailView):
    queryset = Transaction.objects.all()
    context_object_name = 'transaction'
    

class TransactionsListView(ListView):
    queryset = Transaction.objects.all()
    context_object_name = 'transaction_list'
