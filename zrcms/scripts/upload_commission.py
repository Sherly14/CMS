import os
import sys
import django
import decimal
import math
import pandas as pd


cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
sys.path.append(os.path.join(cur_dir, '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
django.setup()  # NOQA

from zrcommission import models as comm_models
from zrtransaction import models as transaction_models

exl = pd.read_excel(
    os.path.join(cur_dir, 'NON_DMT_COMMISSION_STRUCTURE.xls'),
    sheetname='Sheet1',
    skiprows=0
)

for index, df in exl.iterrows():
    distributor = df[0]
    vendor = df[1]
    pid = df[2]
    service_provider = df[3]
    transaction_type = df[4]
    is_chargeable = df[5]
    commission_type = df[6]
    margin = df[7]
    z_comm = df[8]
    d_comm = df[9]
    sd_comm = df[10]
    m_comm = df[11]

    transaction_type_object = transaction_models.TransactionType.objects.get(
        name=transaction_type
    )

    vendor_object = transaction_models.Vendor.objects.get(
        name=vendor
    )

    print index + 1, transaction_type_object, vendor_object

    if transaction_type_object and vendor_object:

        if transaction_models.ServiceProvider.objects.filter(
            name=service_provider,
            transaction_type=transaction_type_object,
            vendor=vendor_object
        ).count() == 0:
            print '...Service Provider Id not found'
        else:
            service_provider_object = transaction_models.ServiceProvider.objects.get(
                name=service_provider,
                transaction_type=transaction_type_object,
                vendor=vendor_object
            )
            if distributor is '' or math.isnan(distributor):
                comm_models.BillPayCommissionStructure.objects.filter(
                    service_provider=service_provider_object,
                    is_default=True,
                    distributor=None
                ).update(
                    is_enabled=False
                )

                comm_models.BillPayCommissionStructure.objects.create(
                    distributor=None,
                    service_provider=service_provider_object,
                    commission_type=commission_type,
                    net_margin=margin,
                    commission_for_zrupee=z_comm,
                    commission_for_distributor=d_comm,
                    commission_for_sub_distributor=sd_comm,
                    commission_for_merchant=m_comm,
                    gst_value=decimal.Decimal(18.0000),
                    tds_value=decimal.Decimal(5.000),
                    is_chargable=False,
                    is_default=True,
                    is_enabled=True
                )
            else:
                comm_models.BillPayCommissionStructure.objects.filter(
                    service_provider=service_provider_object['id'],
                    is_default=False,
                    distributor=distributor
                ).update(
                    is_enabled=False
                )

                comm_models.BillPayCommissionStructure.objects.create(
                    distributor=distributor,
                    service_provider=service_provider,
                    commission_type=commission_type,
                    net_margin=margin,
                    commission_for_zrupee=z_comm,
                    commission_for_distributor=d_comm,
                    commission_for_sub_distributor=sd_comm,
                    commission_for_merchant=m_comm,
                    gst_value=decimal.Decimal(18.0000),
                    tds_value=decimal.Decimal(5.000),
                    is_chargable=False,
                    is_default=False,
                    is_enabled=True
                )
    else:
        if transaction_type_object is None:
            print 'Transaction type', transaction_type, ' not found'
        if vendor_object is None:
            print 'Vendor', vendor_object, ' not found'
        continue



