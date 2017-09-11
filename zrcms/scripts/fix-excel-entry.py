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
    cs = comm_models.BillPayCommissionStructure.objects.filter(
        service_provider__code=df[2],
        commission_type='P'
    ).last()
    if cs:
        if cs.pk == 884:
            import pdb; pdb.set_trace()

        cs.net_margin = df[4] * 100
        cs.save()

    print(index)
