# import os
# import sys
# import django
# import uuid
# import decimal
#
#
# cur_dir = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
# sys.path.append(os.path.join(cur_dir, '..', '..'))
# import settings  # NOQA
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
# django.setup()  # NOQA

from zrwallet.models import Wallet, WalletTransactions
from django.db import transaction


@transaction.atomic
def run():
    zr_wallet = Wallet.objects.all()
    for row in zr_wallet:
        mid = row.merchant_id

        dmt_closing_balance = row.dmt_balance
        non_dmt_closing_balance = row.non_dmt_balance

        dmt = 0
        non_dmt = 0

        mid_transactions = WalletTransactions.objects.all().filter(wallet=mid).order_by('-id')
        if mid_transactions:

            for r in mid_transactions:
                r.dmt_closing_balance = dmt_closing_balance + (-1 * dmt)
                r.non_dmt_closing_balance = non_dmt_closing_balance + (-1 * non_dmt)
                dmt = r.dmt_balance
                non_dmt = r.non_dmt_balance
                dmt_closing_balance = r.dmt_closing_balance
                non_dmt_closing_balance = r.non_dmt_closing_balance
                r.save()
