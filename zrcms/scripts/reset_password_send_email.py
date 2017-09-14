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

from django.db.models.fields.related_descriptors import RelatedObjectDoesNotExist:

from common_utils import zrupee_security
from zruser.utils import constants
from zruser import models as zu


for zruser in zu.ZrUser.objects.filter(
    is_kyc_verified=True
):
    if not zruser.kyc_details.filter(approval_status=constants.KYC_APPROVAL_CHOICES[1][0]):
        continue

    password = zrupee_security.generate_password()
    zruser.pass_word = password
    zruser.save(update_fields=['pass_word'])

    try:
        dj_user = zruser.zr_user.id
    except:
        zruser.send_welcome_email(password)
        continue

    dj_user.set_password(password)
    dj_user.save()

    zruser.send_welcome_email(password)
    print(zruser)
