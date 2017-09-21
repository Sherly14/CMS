import json
from time import sleep

import requests

from common_utils import email_utils
from zrcms.env_vars import EKO_DEVELOPER_KEY, EKO_INITIATOR_ID, EKO_TRANSACTION_ENQUIRY_URL
from zrtransaction.models import Transaction
from zrtransaction.utils.constants import POLL_EXCLUDED_STATUS, TX_STATUS_AWAITED, TX_STATUS_FAIL, \
    TX_STATUS_REFUND_PENDING, TX_STATUS_REFUNDED, TX_STATUS_SUCCESS, TRANSACTION_STATUS_SUCCESS, \
    TRANSACTION_STATUS_REFUND_PENDING, \
    TRANSACTION_STATUS_REFUNDED
from zrwallet.models import WalletTransactions


def poll_transaction_status_for_refund():
    transactions = Transaction.objects.exclude(status__in=POLL_EXCLUDED_STATUS)
    # exclude success, failure, refunded only take transactions with pending and refund pending status
    print 'polling transaction status for queryset ', transactions

    for transaction in transactions:
        sleep(1)
        txn_id = transaction.vendor_txn_id
        headers = {'developer_key': EKO_DEVELOPER_KEY, 'cache-control': "no-cache"}
        url = EKO_TRANSACTION_ENQUIRY_URL + txn_id + '?initiator_id=' + EKO_INITIATOR_ID
        print 'making eko api request ', 'URL: ', url, 'headers: ', headers
        response_data = requests.get(url, headers=headers).json()
        print response_data, response_data['status']

        # refer to eko documentation for tx_status responses http://developers.eko.co.in/docs/index.html
        if response_data['status'] == 0:
            if int(response_data['data']['tx_status']) == TX_STATUS_SUCCESS:
                print ' transaction ', transaction.vendor_txn_id
                transaction.status = TRANSACTION_STATUS_SUCCESS
                transaction.save()

                if transaction.transaction_response_json is None:
                    transaction.transaction_response_json = dict(poll_success_response=json.dumps(response_data))
                else:
                    transaction.transaction_response_json['poll_success_response'] = json.dumps(response_data)
                transaction.save()

            elif int(response_data['data']['tx_status']) == TX_STATUS_FAIL:
                # transaction.status = TRANSACTION_STATUS_FAILURE
                transaction.save()

                if transaction.transaction_response_json is None:
                    transaction.transaction_response_json = dict(poll_failure_response=json.dumps(response_data))
                else:
                    transaction.transaction_response_json['poll_failure_response'] = json.dumps(response_data)
                transaction.save()

                #     send a mail to the zrupee tech
                email_utils.send_email(
                    'Error in EKO refund polling!',
                    'tech@zrupee.com',
                    'payment_status_error',
                    {
                        'url': url,
                        'response_json': json.dumps(response_data)
                    },
                    is_html=True
                )

            elif int(response_data['data']['tx_status']) == TX_STATUS_AWAITED:
                pass

            elif int(response_data['data']['tx_status']) == TX_STATUS_REFUND_PENDING:

                if transaction.status != TRANSACTION_STATUS_REFUND_PENDING:
                    if transaction.transaction_response_json is None:
                        transaction.transaction_response_json = dict(
                            poll_refund_pending_response=json.dumps(response_data))
                    else:
                        transaction.transaction_response_json['poll_refund_pending_response'] = json.dumps(response_data)

                transaction.status = TRANSACTION_STATUS_REFUND_PENDING
                transaction.save()

            elif int(response_data['data']['tx_status']) == TX_STATUS_REFUNDED:
                merchant_wallet = transaction.user.wallet
                refund_amount = transaction.amount + transaction.additional_charges

                wallet_log = WalletTransactions()
                wallet_log.wallet = merchant_wallet
                wallet_log.transaction = transaction

                if transaction.type.name.upper() == 'DMT':
                    merchant_wallet.dmt_balance += refund_amount
                    merchant_wallet.save(
                        update_fields=[
                            'dmt_balance'
                        ]
                    )
                    wallet_log.dmt_balance = refund_amount
                else:
                    merchant_wallet.non_dmt_balance += refund_amount
                    merchant_wallet.save(
                        update_fields=[
                            'non_dmt_balance'
                        ]
                    )
                    wallet_log.non_dmt_balance = refund_amount
                wallet_log.save()
                transaction.status = TRANSACTION_STATUS_REFUNDED
                transaction.save()

                if transaction.transaction_response_json is None:
                    transaction.transaction_response_json = dict(poll_refunded_response=json.dumps(response_data))
                else:
                    transaction.transaction_response_json['poll_refunded_response'] = json.dumps(response_data)
                transaction.save()
