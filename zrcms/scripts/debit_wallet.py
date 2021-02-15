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

from common_utils.transaction_utils import get_main_distributor_from_merchant

from decimal import Decimal
import datetime

input_file = os.path.join(cur_dir, 'TID_DATA_final.xls')


if not os.path.exists(input_file):
    print('No Input file found')
    exit(0)

exl = pd.read_excel(
    input_file,
    sheetname='Sheet3',
    skiprows=0
)


@transaction.atomic
def debit_wallet():
    print("----------------------")
    print("debit_wallet begins ..", datetime.datetime.now())
    for index, df in exl.iterrows():
        print('         ')
        print(('-->' + str(index + 1)))

        tid = str(df[0])
        date = str(df[1])
        status = str(df[2]).encode('utf-8').strip()
        request_log_raw = str(df[3])
        response_log = str(df[4])
        merchant_id = str(df[5])

        if 'nan' in [tid, date, status, request_log_raw, response_log, merchant_id]:
            print('Incomplete input data, nan found')
            continue

        print('merchant_id -', int(float(merchant_id)), ', tid -', tid)

        request_log_list = request_log_raw.strip()[1: -1].split(',')

        request_log = {r.strip().split('=')[0]: r.strip().split('=')[1] for r in request_log_list}

        for k, v in request_log.items():
            if k in ["state", "amount", "channel", "merchant_document_id_type"]:
                request_log[k] = int(v)

        print("amount -", request_log["amount"], ', pan -', request_log["user_pan"])

        response_log = json.loads(response_log)

        print("status -", response_log["status"])

        if str(tid) != str(response_log["data"]["tid"]) or str(request_log["client_ref_id"]) != str(response_log["data"]["client_ref_id"]):
            print("tid or client_ref_id mis-match")
            continue

        if response_log["data"]["tx_status"] != '0':
            print("Unsuccessful transaction in response_log for tid =", response_log["data"]["tid"])
            continue

        if Decimal(request_log["amount"]) == Decimal(response_log["data"]["amount"]):
            amount = Decimal(request_log["amount"])
        else:
            print("Request and Response amount mismatch")
            continue

        zr_user = ZrUser.objects.filter(id=int(float(merchant_id)), pan_no=request_log["user_pan"], role__name='MERCHANT', is_active=True).\
            order_by('-id').first()
        print('zr_user -', zr_user)

        if not zr_user:
            print("zr_user not found")
            continue

        vendor = Vendor.objects.filter(name='EKO').first()

        commission_amount = get_dmt_commission(zr_user, vendor, amount)

        if not commission_amount:
            print("No commission calculated")
            continue

        total_amount = amount + commission_amount

        zr_wallet = Wallet.objects.get(
            merchant=zr_user
        )

        if zr_wallet.dmt_balance >= total_amount:
            print("Enough balance in Wallet - amount =", total_amount, "balance =", zr_wallet.dmt_balance, "debiting..")
        else:
            print("Not enough balance in Wallet - amount =", total_amount, "balance =", zr_wallet.dmt_balance)
            continue

        print('eko_sender_id - ', response_log["data"]["customer_id"])
        print('eko_beneficiary_id - ', response_log["data"]["recipient_id"])
        sender_beneficiary_map = SenderBeneficiaryMapping.objects.filter(
            eko_sender_id=str(response_log["data"]["customer_id"]),
            eko_beneficiary_id=str(response_log["data"]["recipient_id"])
        ).first()

        if sender_beneficiary_map is None:
            print('sender_beneficiary_map not found')
            continue

        print('sender_beneficiary_map ', sender_beneficiary_map.pk)

        transaction_type = TransactionType.objects.filter(name='DMT').first()

        # transaction_request_json = json.dumps(request_log)
        transaction_request_json = json.dumps({"data": request_log,
                                               "route": "/transactions"
                                               })

        zr_transaction = Transaction.objects.create(
            status='S',
            type=transaction_type,
            vendor=vendor,
            service_provider=None,
            amount=amount,
            vendor_txn_id=response_log["data"]["tid"],
            txn_id=response_log["data"]["client_ref_id"],
            customer=response_log["data"]["customer_id"],
            beneficiary=sender_beneficiary_map.beneficiary.mobile_no,
            user=zr_user,
            transaction_request_json=transaction_request_json,
            transaction_response_json=response_log,
            additional_charges=commission_amount,
            is_commission_created=False,
            beneficiary_user=sender_beneficiary_map.beneficiary
        )

        print('zr_transaction - ', zr_transaction.pk)

        if not zr_transaction:
            print("No transaction created")
            continue

        # debit wallet
        zr_wallet.dmt_balance -= total_amount
        zr_wallet.save()

        print('zr_wallet - ', zr_wallet.pk)

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

        print('wallet_transaction - ', wallet_transaction.pk)


@transaction.atomic
def get_dmt_commission(zr_user, vendor, amount):
    distributor = get_main_distributor_from_merchant(zr_user)

    if not distributor:
        print("No distributor found")
        return None

    dmt_comm_str = DMTCommissionStructure.objects.filter(distributor=distributor,
                                                         transaction_vendor=vendor,
                                                         is_enabled=True,
                                                         is_default=False,
                                                         minimum_amount__lte=amount,
                                                         maximum_amount__gte=amount).first()

    # default comm str
    if not dmt_comm_str:
        dmt_comm_str = DMTCommissionStructure.objects.filter(distributor=None,
                                                             transaction_vendor=vendor,
                                                             is_enabled=True,
                                                             is_default=True,
                                                             minimum_amount__lte=amount,
                                                             maximum_amount__gte=amount).first()

    if not dmt_comm_str:
        print("No Commission Structure found for distributor - ", distributor.id)
        return None

    min_charge = dmt_comm_str.min_charge
    commission_amount = 0

    if dmt_comm_str.commission_type == 'F':
        commission_amount += dmt_comm_str.customer_fee
    elif dmt_comm_str.commission_type == 'P':
        commission_amount += amount * (dmt_comm_str.customer_fee / 100)

    commission_amount = min_charge if min_charge > commission_amount else commission_amount
    return commission_amount


debit_wallet()
