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
from zrcommission import models as zc

import pandas as pd

csv = pd.read_excel(
    os.path.join(cur_dir, 'Commission-summary.xlsx')
)

zc.DMTCommissionStructure.objects.all().update(is_enabled=False)
for index, df in csv.iterrows():
    transaction_vendor, _ = zt.Vendor.objects.get_or_create(name='INSTANT_PAY')
    min_charge = df['Min charge(INR)']
    amt_range = df['Amount']
    min_amount = amt_range.split('-')[0]
    max_amount = amt_range.split('-')[1]
    customer_fee = df['Customer Fee(% of amount)']
    commission_for_zrupee = df['Zrupee(% of customer fee/Min charge)']
    commission_for_distr = df['Distributor(% of customer fee/Min charge)']
    commission_for_sub_distr = df['Sub distributor (% of customer fee/Min charge)']
    commission_for_merchant = df['Merchant(% of customer fee/Min charge)']

    instance = zc.DMTCommissionStructure.objects.create(
        commission_type='P',
        transaction_vendor=transaction_vendor,
        min_charge=min_charge,
        minimum_amount=min_amount,
        maximum_amount=max_amount,
        customer_fee=customer_fee,
        commission_for_zrupee=commission_for_zrupee,
        commission_for_distributor=commission_for_distr,
        commission_for_sub_distributor=commission_for_sub_distr,
        commission_for_merchant=commission_for_merchant,
        tds_value=decimal.Decimal(5.000),
        gst_value=decimal.Decimal(18.0000),
        is_default=True
    )
    print(index)
