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

import pandas as pd

for usr in zu.ZrUser.objects.filter(role__name='SENDER'):
    sender, _ = zu.Sender.objects.get_or_create(
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
            "is_user_active": True,
            "is_mobile_verified": usr.is_mobile_verified,
            "is_kyc_verified": usr.is_kyc_verified
        }
    )

    for k in usr.kyc_details.all():
        kyc = zu.SenderKYCDetail.objects.get_or_create(
            document_id=k.document_id,
            defaults={
                "type": k.type,
                "document_id": k.document_id,
                "document_link": k.document_link,
                "for_sender": sender,
                "approval_status": k.approval_status,
                "by_approved": k.by_approved
            }
        )
        print(kyc)

    print(sender)


# for sheet in ['Non collection', 'Collection INR 5']:
exl = pd.read_excel(
    os.path.join(cur_dir, 'Master-Bank-List_v2.xlsx'),
    sheetname='Sheet1',
)

import math
for index, row in exl.iterrows():
    is_master_ifsc = True if row['IsMasterIFSC'] else False
    ifsc_formula = 0
    acc_len = 0
    if row['Ifsc formula'] and math.isnan(row['Ifsc formula']):
        ifsc_formula = 0
    else:
        ifsc_formula = row['Ifsc formula']

    if row['AccountLength'] and math.isnan(row['AccountLength']):
        acc_len = 0
    else:
        acc_len = row['AccountLength']

    ifsc_code = None
    if isinstance(row['IFSC'], float) and row['IFSC'] and math.isnan(row['IFSC']):
        ifsc_code = None
    else:
        ifsc_code = row['IFSC']

    b, _ = zu.Bank.objects.get_or_create(
        bank_name=row['Bank Name'],
        defaults={
            'bank_code': row['Bank Code'],
            'eko_bank_id': row['EkoBankID'],
            'account_length': acc_len,
            'ifsc_code': ifsc_code,
            'is_master_ifsc': is_master_ifsc,
            'ifsc_formula': ifsc_formula,
            'is_enabled': True
        }
    )

    print(b)
