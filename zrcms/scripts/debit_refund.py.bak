import os
import sys
import django
import uuid
import decimal
import pandas as pd
import json


cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
sys.path.append(os.path.join(cur_dir, '..', '..'))
# import settings  # NOQA
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
django.setup()  # NOQA

from django.db import transaction

from zrtransaction.models import Transaction, TransactionType, Vendor
from zrwallet.models import Wallet, WalletTransactions
from zruser.models import ZrUser
from decimal import Decimal
import datetime


input_file = os.path.join(cur_dir, 'debit_refund_230719-1.xlsx')

if not os.path.exists(input_file):
    print('No Input file found')
    exit(0)

exl = pd.read_excel(
    input_file,
    sheetname='230719-1',
    skiprows=0
)


@transaction.atomic
def debit_refund():
    print "----------------------"
    print "debit_refund begins ..", datetime.datetime.now()
    for index, df in exl.iterrows():
        print '         '
        print('-->' + str(index + 1))

        dmt_transaction_id = int(df[0])
        diff_upon_refund = int(df[1])
        user_id = int(df[2])

        if 'nan' in [dmt_transaction_id, diff_upon_refund, user_id]:
            print 'Incomplete input data, nan found'
            continue

        zr_user = ZrUser.objects.filter(id=user_id, is_active=True).\
            order_by('-id').first()
        print 'zr_user -', zr_user

        if not zr_user:
            print "zr_user not found"
            continue

        zr_tran = Transaction.objects.filter(id=dmt_transaction_id).\
            order_by('-id').first()

        print 'zr_tran -', zr_tran

        if not zr_tran:
            print "zr_tran not found"
            continue

        zr_wallet = Wallet.objects.get(
            merchant=zr_user
        )

        if zr_wallet.dmt_balance >= diff_upon_refund:
            print "Enough balance in Wallet - amount =", diff_upon_refund, "balance =", zr_wallet.dmt_balance, "debiting.."
        else:
            print "Not enough balance in Wallet - amount =", diff_upon_refund, "balance =", zr_wallet.dmt_balance
            continue

        # debit wallet
        zr_wallet.dmt_balance -= diff_upon_refund
        zr_wallet.save()

        print 'zr_wallet - ', zr_wallet.pk

        wallet_transaction = WalletTransactions.objects.create(
            wallet=zr_wallet,
            transaction=zr_tran,
            payment_request=None,
            dmt_balance=-diff_upon_refund,
            non_dmt_balance=0,
            dmt_closing_balance=zr_wallet.dmt_balance,
            non_dmt_closing_balance=zr_wallet.non_dmt_balance,
            is_success=True
        )

        print 'wallet_transaction - ', wallet_transaction.pk


debit_refund()
