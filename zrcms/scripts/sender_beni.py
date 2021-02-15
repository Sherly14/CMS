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
from zrmapping import models as zm


for sbm in zm.SenderBeneficiary.objects.all():
    if not (zm.Sender.objects.filter(mobile_no=sbm.sender.mobile_no).count() and
                zm.Beneficiary.objects.filter(mobile_no=sbm.beneficiary.mobile_no).count()):
        print(("Sender or beneficiary not found for"), sbm, sbm.pk)
        continue
    else:
        mapping, created = zm.SenderBeneficiaryMapping.objects.get_or_create(
            sender=zm.Sender.objects.get(mobile_no=sbm.sender.mobile_no),
            beneficiary=zm.Beneficiary.objects.get(mobile_no=sbm.beneficiary.mobile_no),
            is_active=True,
            eko_sender_id=sbm.eko_sender_id,
            eko_beneficiary_id=sbm.eko_beneficiary_id
        )
        if created:
            print(("SenderBeneficiaryMapping created"), mapping)
        else:
            print(("SenderBeneficiaryMapping already exists"), mapping)
