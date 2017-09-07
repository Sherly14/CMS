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

MERCHANT = 'MERCHANT'
DISTRIBUTOR = 'DISTRIBUTOR'
SUBDISTRIBUTOR = 'SUBDISTRIBUTOR'
BENEFICIARY = 'BENEFICIARY'


# for sheet in ['Non collection', 'Collection INR 5']:
exl = pd.read_excel(
    os.path.join(cur_dir, 'bill-payment.xls'),
    sheetname='Recharge_Non Collection',
    skiprows=4
)

comm_models.DMTCommissionStructure.objects.filter(id=3).update(
    is_default=True, commission_type='P',
    tds_value=decimal.Decimal('4.237'),
    gst_value=decimal.Decimal('15.2532')
)
transaction_models.Vendor.objects.filter(name='EKO').update(name='Instant pay')
vendor, _ = transaction_models.Vendor.objects.get_or_create(name='Instant pay')
for index, df in exl.iterrows():
    service_provider = df[1].strip()
    transaction_type = get_slugify_value(df[2].strip())
    net_margin = df[3]

    transaction_type, _ = transaction_models.TransactionType.objects.get_or_create(
        name=transaction_type
    )

    sp_instance, _ = transaction_models.ServiceProvider.objects.get_or_create(
        name=service_provider,
        transaction_type=transaction_type,
        defaults={
            "vendor": vendor,
            "code": "",
            "is_enabled": True,
        }
    )

    comm_type = 'P'
    if not isinstance(net_margin, float) and not isinstance(net_margin, int) and 'Rs' in net_margin:
        comm_type = 'F'

    if comm_type == 'P':
        zrupe_comm = decimal.Decimal(df[5])
        distr_comm = decimal.Decimal(df[7])
        sub_distr_comm = decimal.Decimal(df[14])
        agent_distr_comm = decimal.Decimal(df[20])
        net_margin = round(
            decimal.Decimal(net_margin),
            3
        )
    elif comm_type == 'F':
        net_margin = decimal.Decimal(net_margin.lower().replace('rs', '').replace(',', '').strip())
        zrupe_comm = decimal.Decimal(df[5])
        distr_comm = decimal.Decimal(df[7])
        sub_distr_comm = decimal.Decimal(df[14])
        agent_distr_comm = decimal.Decimal(df[20])

    comm_struct, _ = comm_models.BillPayCommissionStructure.objects.get_or_create(
        distributor=None,
        service_provider=sp_instance,
        defaults={
            "commission_type": comm_type,
            "net_margin": net_margin,
            "commission_for_zrupee": 10,
            "commission_for_distributor": 10,
            "commission_for_sub_distributor": 10,
            "commission_for_merchant": 70,
            "gst_value": decimal.Decimal(15.2532),
            "tds_value": decimal.Decimal(4.237),
            "is_chargable": False,
            "is_default": True,
        }
    )
    print(index)


from xlrd import open_workbook
wb = open_workbook(os.path.join(cur_dir, 'bill-payment.xls'))
sheet = wb.sheet_by_name('Bill Payment_Collection INR 5')

for row in range(2, sheet.nrows):
    service_provider = sheet.cell_value(row, 0)
    transaction_type = get_slugify_value(sheet.cell_value(row, 1))

    transaction_type, _ = transaction_models.TransactionType.objects.get_or_create(
        name=transaction_type
    )

    sp_instance, _ = transaction_models.ServiceProvider.objects.get_or_create(
        name=service_provider,
        transaction_type=transaction_type,
        defaults={
            "vendor": vendor,
            "code": "",
            "is_enabled": True,
        }
    )

    zrupe_comm = 3
    distr_comm = 1
    sub_distr_comm = 1
    agent_distr_comm = 0

    comm_struct = comm_models.BillPayCommissionStructure.objects.get_or_create(
        distributor=None,
        service_provider=sp_instance,
        defaults={
            "commission_type": 'F',
            "net_margin": 5,
            "commission_for_zrupee": zrupe_comm,
            "commission_for_distributor": distr_comm,
            "commission_for_sub_distributor": sub_distr_comm,
            "commission_for_merchant": agent_distr_comm,
            "gst_value": decimal.Decimal(15.2532),
            "tds_value": decimal.Decimal(4.237),
            "is_chargable": True,
            "is_default": True
        }
    )
    print(row)
