import os
import sys
import django
import decimal
import math
import numbers
import pandas as pd


cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
sys.path.append(os.path.join(cur_dir, '..', '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
django.setup()  # NOQA

from zrcommission import models as comm_models
from zrtransaction import models as transaction_models

from zruser import models as user_models
# input_file = os.path.join(cur_dir, 'NON-DMT DEFAULT COMMISSION STRUCTURE new.xls')
input_file = os.path.join(cur_dir, 'Final System sheet_Sangeeta Mobile - Arpana.xls')


if not os.path.exists(input_file):
    print('No Input file found')
    exit(0)

exl = pd.read_excel(
    input_file,
    sheetname='Actual System Used Sheet',
    #sheetname='NON DMT COMMISSION STRUCTURE',
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

    if distributor and not isinstance(distributor, numbers.Number):
        print('Distributor should be an Integer')
        continue

    if vendor == '':
        print('No Vendor Found')
        continue

    if pid and not isinstance(pid, numbers.Number):
        print('pid should be an Integer')
        continue

    if service_provider == '':
        print('No Service Provider Found')
        continue

    if is_chargeable or (isinstance(is_chargeable, basestring) and is_chargeable.lower() in ['t', 'true', 'y', 'yes']):
        is_chargeable = True
    elif is_chargeable or (isinstance(is_chargeable, basestring) and is_chargeable.lower() in ['f', 'false', 'n', 'no']):
        is_chargeable = False
    else:
        print('Unknown Is-Chargeable value')
        continue

    if commission_type and (isinstance(commission_type, basestring) and commission_type.lower() in ['p']):
        commission_type = 'P'
    elif commission_type and (isinstance(commission_type, basestring) and commission_type.lower() in ['f']):
        commission_type = 'F'
    else:
        print('Unknown Commission Type value')
        continue

    if margin == '':
        print('No Margin Found')
        continue

    if transaction_models.TransactionType.objects.filter(
        name=transaction_type
    ).count() > 0:
        transaction_type_object = transaction_models.TransactionType.objects.get(
            name=transaction_type
        )
    else:
        print 'Transaction Type not found'
        continue

    if transaction_models.Vendor.objects.filter(
        name=vendor
    ).count():
        vendor_object = transaction_models.Vendor.objects.get(
            name=vendor
        )
    else:
        print 'Vendor not found'
        continue

    print index + 1, transaction_type_object, vendor_object

    if transaction_type_object and vendor_object:

        if transaction_models.ServiceProvider.objects.filter(
            name=service_provider,
            transaction_type=transaction_type_object,
            vendor=vendor_object
        ).count() == 0:
            print 'Service Provider Id not found'
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
                    is_chargable=is_chargeable,
                    is_default=True,
                    is_enabled=True
                )
            else:
                distributor_object = None

                if user_models.ZrUser.objects.filter(
                        id=distributor
                ).count() == 0:
                    print('Distributor not found in records - ', distributor)
                    continue
                else:
                    distributor_object = user_models.ZrUser.objects.get(id=distributor)

                    comm_models.BillPayCommissionStructure.objects.filter(
                        service_provider=service_provider_object,
                        is_default=False,
                        distributor=distributor_object
                    ).update(
                        is_enabled=False
                    )

                    comm_models.BillPayCommissionStructure.objects.create(
                        distributor=distributor_object,
                        service_provider=service_provider_object,
                        commission_type=commission_type,
                        net_margin=margin,
                        commission_for_zrupee=z_comm,
                        commission_for_distributor=d_comm,
                        commission_for_sub_distributor=sd_comm,
                        commission_for_merchant=m_comm,
                        gst_value=decimal.Decimal(18.0000),
                        tds_value=decimal.Decimal(5.000),
                        is_chargable=is_chargeable,
                        is_default=False,
                        is_enabled=True
                    )
    else:
        if transaction_type_object is None:
            print 'Transaction type', transaction_type, ' not found'
        if vendor_object is None:
            print 'Vendor', vendor_object, ' not found'
        continue



