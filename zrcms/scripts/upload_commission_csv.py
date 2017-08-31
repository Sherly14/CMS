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


MERCHANT = 'MERCHANT'
DISTRIBUTOR = 'DISTRIBUTOR'
SUBDISTRIBUTOR = 'SUBDISTRIBUTOR'
BENEFICIARY = 'BENEFICIARY'


# for sheet in ['Non collection', 'Collection INR 5']:
exl = pd.read_excel(
    '/home/hitul/Downloads/zrupee.xls',
    sheetname='Sheet4',
    header=1
)
vendor = transaction_models.Vendor.objects.get(name='EKO')
for index, df in exl.iterrows():
    sp_instance = transaction_models.ServiceProvider.objects.create(
        name=df['Service Provider'],
        vendor=vendor,
        code=str(uuid.uuid4()),
        is_enabled=True
    )

    distributors = user_models.ZrUser.objects.filter(
        role__name=DISTRIBUTOR
    )
    comm_type = 'P'
    if not isinstance(df['Margin (NET of TDS)'], float) and 'Rs' in df['Margin (NET of TDS)']:
        comm_type = 'F'

    if comm_type == 'P':
        df['Margin (NET of TDS)'] = df['Margin (NET of TDS)'] * 100

    if comm_type == 'P':
        zrupe_comm = 10.00
        distr_comm = 10.00
        sub_distr_comm = 10.00
        agent_distr_comm = 70.00
    elif comm_type == 'F':
        zrupe_comm = float(df['Zrupee (10%) upto 2 decimals '].replace('Rs', '').replace(' ', ''))
        distr_comm = float(df['Distributor Gross Distributor Margin upto 2 decimals'].replace('Rs', '').replace(' ', ''))
        sub_distr_comm = float(df['Sub Distributor Gross Distributor Margin'].replace('Rs', '').replace(' ', ''))
        agent_distr_comm = float(df['Agent  Margin'].replace('Rs', '').replace(' ', ''))

    if not isinstance(df['Margin (NET of TDS)'], float):
        net_margin = int(df['Margin (NET of TDS)'].replace('Rs', '').replace('%', '').replace(' ', ''))
    else:
        net_margin = df['Margin (NET of TDS)']

    net_margin = '%.2f' % net_margin
    net_margin = decimal.Decimal(net_margin)
    for dist in distributors:
        comm_struct = comm_models.BillPayCommissionStructure.objects.get_or_create(
            distributor=dist,
            service_provider=sp_instance,
            commission_type=comm_type,
            net_margin=4.0,
            commission_for_zrupee=10,
            commission_for_distributor=10,
            commission_for_sub_distributor=10,
            commission_for_merchant=70,
            gst_value=0,
            tds_value=5,
            is_chargable=False,
        )
    print(index)

exl = pd.read_excel(
    '/home/hitul/Downloads/zrupee.xls',
    sheetname='Sheet5',
    header=1
)
for index, df in exl.iterrows():
    sp_instance = transaction_models.ServiceProvider.objects.create(
        name=df['Service'],
        vendor=vendor,
        code=str(uuid.uuid4()),
        is_enabled=True
    )

    distributors = user_models.ZrUser.objects.filter(
        role__name=DISTRIBUTOR
    )

    zrupe_comm = 3
    distr_comm = 1
    sub_distr_comm = 1
    agent_distr_comm = 0

    for dist in distributors:
        comm_struct = comm_models.BillPayCommissionStructure.objects.get_or_create(
            distributor=dist,
            service_provider=sp_instance,
            commission_type='F',
            net_margin=5,
            commission_for_zrupee=zrupe_comm,
            commission_for_distributor=distr_comm,
            commission_for_sub_distributor=sub_distr_comm,
            commission_for_merchant=agent_distr_comm,
            gst_value=0,
            tds_value=5,
            is_chargable=False,
        )
    print(index)