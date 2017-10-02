__author__ = 'hitul'
import os
import sys
import django
import uuid
import decimal

cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
sys.path.append(os.path.join(cur_dir, '..', '..'))
import settings  # NOQA
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
django.setup()  # NOQA

from zrtransaction import models as zt
from zruser import models as zu
from zrcommission import models as comm_models


for usr in zu.ZrUser.objects.filter(role__name='BENEFICIARY'):
    bank_detail = usr.bankdetail_set.all().last()
    if not bank_detail:
        print("Bank detail not found for zruser (%s)" % usr.pk)
        continue

    bank_instance = None
    ifsc = bank_detail.IFSC_code[:4]
    bank_instance = zu.Bank.objects.filter(
        ifsc_code__startswith=ifsc.upper()
    ).last()
    if not bank_instance:
        print("Bank not found for ISFC code (%s)" % (bank_detail.IFSC_code))
        continue

    bn, _ = zu.Beneficiary.objects.get_or_create(
        mobile_no=usr.mobile_no,
        defaults={
            "first_name": usr.first_name,
            "last_name": usr.last_name,
            "email": usr.email,
            "gender": usr.gender,
            "city": usr.city,
            "state": usr.state,
            "pin_code": usr.pincode,
            "address_line_1": usr.address_line_1,
            "address_line_2": usr.address_line_2,

            "account_no": bank_detail.account_no,
            "bank": bank_instance,
            "channel": bank_detail.channel,
            "IFSC_code": bank_detail.IFSC_code,
            "account_name": bank_detail.account_name,
            "is_bank_account_verified": bank_detail.is_verified,
            "is_user_active": usr.is_active,
            "is_mobile_verified": usr.is_mobile_verified
        }
    )

    print(bn)
