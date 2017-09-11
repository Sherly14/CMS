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

# for sheet in ['Non collection', 'Collection INR 5']:
exl = pd.read_excel(
    os.path.join(cur_dir, 'bill-payment.xls'),
    sheetname='Recharge_Non Collection',
    skiprows=4
)

for index, df in exl.iterrows():
    code = df[2].strip()
    net_margin = df[4]

    comm_type = 'P'
    if not isinstance(net_margin, float) and not isinstance(net_margin, int) and 'Rs' in net_margin:
        comm_type = 'F'

    if comm_type == 'P':
        net_margin = net_margin * 100
    elif comm_type == 'F':
        net_margin = decimal.Decimal(net_margin.lower().replace('rs', '').replace(',', '').strip())

    sp_instance = zt.ServiceProvider.objects.filter(
        code=code,
        is_enabled=True
    ).last()
    print(comm_models.BillPayCommissionStructure.objects.filter(
        distributor=None,
        service_provider=sp_instance,
        is_enabled=True,
        is_default=True
    ))
    print(net_margin)
    comm_struct = comm_models.BillPayCommissionStructure.objects.filter(
        distributor=None,
        service_provider=sp_instance,
        is_enabled=True,
        is_default=True
    ).last()
    import ipdb; ipdb.set_trace()
    comm_struct.net_margin = net_margin
    comm_struct.save()
    print(index)
