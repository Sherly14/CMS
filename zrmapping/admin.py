# -*- coding: utf-8 -*-


from django.contrib import admin

from zrmapping.models import *

# Register your models here.
admin.site.register(DistributorMerchant)
admin.site.register(MerchantBeneficiary)
admin.site.register(SenderBeneficiary)
admin.site.register(SenderBeneficiaryMapping)
admin.site.register(MerchantSender)
admin.site.register(SubDistributorMerchant)
admin.site.register(DistributorSubDistributor)
