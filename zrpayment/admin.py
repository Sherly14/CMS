# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from zrpayment.models import *

admin.site.register(PaymentMode)
admin.site.register(MerchantPaymentRequest)
admin.site.register(Payments)
