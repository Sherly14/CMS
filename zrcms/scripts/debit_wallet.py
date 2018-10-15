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
import settings  # NOQA
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
django.setup()  # NOQA


from zrtransaction.models import Transaction
from zrwallet.models import Wallet, WalletTransactions
from zruser.models import ZrUser
from zrmapping.models import SenderBeneficiaryMapping

input_file = os.path.join(cur_dir, 'TID_DATA.xlsx')


if not os.path.exists(input_file):
    print('No Input file found')
    exit(0)

exl = pd.read_excel(
    input_file,
    sheetname='Sheet3',
    skiprows=0
)


for index, df in exl.iterrows():
    print('-->' + str(index + 1))
    tid = df[0]
    date = df[1]
    status = str(df[2]).encode('utf-8').strip()
    request_log = str(df[3])
    response_log = str(df[4])

    # request_log = json.loads(request_log)
    # request_log_dumps = json.dumps(request_log)

    if 'nan' in [tid, date, status, request_log, response_log]:
        print 'nan found'
        continue

    # print 'request_log ', request_log, type(request_log)

    request_log = request_log.strip()[1: -1].split(',')

    # print 'request_log ', request_log

    # request_log = dict(r.strip().split('=') for r in request_log)
    request_log = {r.strip().split('=')[0]: r.strip().split('=')[1] for r in request_log}
    # request_log = request_log[1: -1]
    # print "request_log_dumps - ", request_log
    # print type(request_log)

    for k, v in request_log.iteritems():
        if k in ["state", "amount", "channel", "merchant_document_id_type"]:
            request_log[k] = int(v)

    # request_log = json.dumps(request_log)

    # print 'request_log', request_log, type(request_log)
    print "amount - ", request_log["amount"], request_log["user_pan"]


    # print 'response_log', response_log, type(response_log)

    # print response_log["status"]

    response_log = json.loads(response_log)
    # response_log = json.dumps(response_log)

    # print 'response_log', response_log

    print "status - ", response_log["status"]

    sender_beneficiary_map = SenderBeneficiaryMapping.objects.filter(
        eko_sender_id=response_log["data"]["customer_id"],
        eko_beneficiary_id=response_log["data"]["recipient_id"]
    )

    if sender_beneficiary_map is None:
        print 'sender_beneficiary_map not found'
        continue

    zr_user = ZrUser.objects.filter(pan_no=request_log["user_pan"])
    print zr_user

    transaction = Transaction.objects.create(
        status='S',
        type=62,
        vendor=2,
        service_provider=None,
        amount=response_log["data"]["amount"],
        vendor_txn_id=response_log["data"]["tid"],
        txn_id=response_log["data"]["client_ref_id"],
        customer=response_log["data"]["customer_id"],
        beneficiary=sender_beneficiary_map.beneficiary.mobile_no,
        user=zr_user,
        transaction_request_json=json.dumps(request_log),
        transaction_response_json=response_log,
        additional_charges=0,  # dev
        is_commission_created=False,
        beneficiary_user=sender_beneficiary_map.beneficiary
    )

    # request_log_json = json.loads(request_log_json)
    # print 'request_log_json', request_log_json
    # print tid, date, status, request_log, response_log



