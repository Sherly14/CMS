# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from zruser.models import *


# Register your models here.


class ZrUserAdmin(admin.ModelAdmin):
    readonly_fields = ('id', )

    class Meta:
        model = ZrUser

admin.site.register(ZrUser, ZrUserAdmin)

admin.site.register(UserRole)
admin.site.register(KYCDocumentType)
admin.site.register(ZrAdminUser)
admin.site.register(KYCDetail)
admin.site.register(BankDetail)
admin.site.register(OTPDetail)
