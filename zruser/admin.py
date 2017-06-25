# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from zruser.models import *

# Register your models here.


admin.site.register(UserRole)
admin.site.register(KYCDocumentType)
admin.site.register(ZrAdminUser)
admin.site.register(ZrUser)
admin.site.register(KYCDetail)
admin.site.register(BankDetail)
admin.site.register(OTPDetail)
