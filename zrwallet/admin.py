# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from zrwallet.models import *

# Register your models here.

admin.site.register(Wallet)
admin.site.register(WalletTransactions)
