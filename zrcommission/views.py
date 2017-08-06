# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import unicode_literals

from django.views.generic import ListView

from zrcommission.models import Commission


class CommissionDisplay(ListView):
    queryset = Commission.objects.all()
    context_object_name = 'commissions'
    template_name = 'zrcommission/dashboard.html'

