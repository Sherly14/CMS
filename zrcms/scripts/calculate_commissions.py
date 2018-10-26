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

from common_utils import transaction_utils
transaction_utils.calculate_commission()

# from zrcms.scripts import poll_transaction_status
# poll_transaction_status.poll_transaction_status_for_refund()

