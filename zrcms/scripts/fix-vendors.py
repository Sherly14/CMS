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
from zrcommission import models as zc


zt.ServiceProvider.objects.all().update(
    vendor=zt.Vendor.objects.get(name='INSTANT_PAY')
)
zc.DMTCommissionStructure.objects.all().update(
    transaction_vendor=zt.Vendor.objects.get(name='EKO')
)
