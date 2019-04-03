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
from zrmapping.models import SenderBeneficiaryMapping
from zrcommission.models import DMTCommissionStructure

from common_utils.transaction_utils import get_main_distributor_from_merchant, get_main_admin

from decimal import Decimal
import datetime

from random import randint

input_file = os.path.join(cur_dir, 'aeps_activation.xls')


if not os.path.exists(input_file):
    print('No Input file found')
    exit(0)

exl = pd.read_excel(
    input_file,
    sheetname='Sheet1',
    skiprows=0
)


@transaction.atomic
def debit_wallet():
    print "----------------------"
    print "debit_wallet begins ..", datetime.datetime.now()
    for index, df in exl.iterrows():
        print '         '
        print('-->' + str(index + 1))
        print 'df - ', df

        merchant_id = str(df[0])

        if 'nan' in [merchant_id]:
            print 'Incomplete input data, nan found'
            continue

        print 'merchant_id -', int(float(merchant_id))

        amount = 500

        zr_user = ZrUser.objects.filter(id=int(float(merchant_id)), role__name='MERCHANT', is_active=True).\
            order_by('-id').first()
        print 'zr_user -', zr_user

        if not zr_user:
            print "zr_user not found"
            continue

        vendor = Vendor.objects.filter(name='EKO').first()

        total_amount = 500

        zr_wallet = Wallet.objects.get(
            merchant=zr_user
        )

        if zr_wallet.dmt_balance >= total_amount:
            print "Enough balance in Wallet - amount =", total_amount, "balance =", zr_wallet.dmt_balance, "debiting.."
        else:
            print "Not enough balance in Wallet - amount =", total_amount, "balance =", zr_wallet.dmt_balance
            continue

        transaction_type = TransactionType.objects.filter(name='SERVICE_ACTIVATION_AEPS').first()

        transaction_request_json = {"data": "AePS Activation: Manual Debit"}

        zr_transaction = Transaction.objects.create(
            status='I',
            type=transaction_type,
            vendor=vendor,
            service_provider=None,
            amount=amount,
            vendor_txn_id='NA',
            txn_id=str(randint(1000000000000, 9999999999999)) + 'AEPS',
            customer=zr_user.mobile_no,
            beneficiary=get_main_admin().mobile_no,
            user=zr_user,
            transaction_request_json=transaction_request_json,
            transaction_response_json=transaction_request_json,
            additional_charges=0,
            is_commission_created=False,
            beneficiary_user=None
        )

        print 'zr_transaction - ', zr_transaction.pk

        if not zr_transaction:
            print "No transaction created"
            continue

        # debit wallet
        zr_wallet.dmt_balance -= total_amount
        zr_wallet.save()

        print 'zr_wallet - ', zr_wallet.pk

        wallet_transaction = WalletTransactions.objects.create(
            wallet=zr_wallet,
            transaction=zr_transaction,
            payment_request=None,
            dmt_balance=-total_amount,
            non_dmt_balance=0,
            dmt_closing_balance=zr_wallet.dmt_balance,
            non_dmt_closing_balance=zr_wallet.non_dmt_balance,
            is_success=True
        )

        print 'wallet_transaction - ', wallet_transaction.pk


debit_wallet()
