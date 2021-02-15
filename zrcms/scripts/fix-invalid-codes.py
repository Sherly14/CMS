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

import pandas as pd
from zrcommission import models as comm_models
from zrtransaction import models as transaction_models
from zruser import models as user_models
from zrutils.common.modelutils import get_slugify_value


from xlrd import open_workbook
wb = open_workbook(os.path.join(cur_dir, 'bill-payment.xls'))
sheet = wb.sheet_by_name('Bill Payment_Collection INR 5')
vendor, _ = transaction_models.Vendor.objects.get_or_create(name='EKO')
for row in range(2, sheet.nrows):
    service_provider = sheet.cell_value(row, 0)
    transaction_type = get_slugify_value(sheet.cell_value(row, 2))
    code = sheet.cell_value(row, 1)

    transaction_type_code = transaction_models.TransactionType.objects.filter(name=code).last()
    if not transaction_type_code:
        continue

    transaction_type = transaction_models.TransactionType.objects.get(name=transaction_type)
    transaction_models.Transaction.objects.filter(
        type=transaction_type_code
    ).update(
        type=transaction_type
    )

    transaction_models.ServiceProvider.objects.filter(
        transaction_type=transaction_type_code
    ).update(
        transaction_type=transaction_type
    )

    transaction_type_code.delete()
