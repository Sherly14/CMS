from time import sleep

import requests
from django.core.management.base import BaseCommand

from zrcms.env_vars import EKO_DEVELOPER_KEY, EKO_INITIATOR_ID, EKO_TRANSACTION_ENQUIRY_URL
from zrtransaction.models import Transaction
from zrtransaction.utils.constants import POLL_EXCLUDED_STATUS, TX_STATUS_AWAITED, TX_STATUS_FAIL, \
    TX_STATUS_REFUND_PENDING, TX_STATUS_REFUNDED, TX_STATUS_SUCCESS, TRANSACTION_STATUS_SUCCESS, \
    TRANSACTION_STATUS_FAILURE, TRANSACTION_STATUS_REFUND_PENDING, \
    TRANSACTION_STATUS_REFUNDED


class Command(BaseCommand):
    def handle(self, *args, **options):

        # Exclude all the successful and Refunded Transaction
        transactions = Transaction.objects.exclude(status__in=POLL_EXCLUDED_STATUS)

        for transaction in transactions:
            sleep(5)
            txn_id = transaction.vendor_txn_id
            headers = {'developer_key': EKO_DEVELOPER_KEY, 'cache-control': "no-cache"}
            url = EKO_TRANSACTION_ENQUIRY_URL + txn_id + '?initiator_id=' + EKO_INITIATOR_ID
            response_data = requests.post(url, headers=headers, verify=False).json()

            # refer to eko documentation for tx_status responses http://developers.eko.co.in/docs/index.html
            if response_data['status'] == "0":
                if response_data['data']['tx_status'] == TX_STATUS_SUCCESS:
                    transaction.status = TRANSACTION_STATUS_SUCCESS
                    transaction.save()
                elif response_data['data']['tx_status'] == TX_STATUS_FAIL:
                    transaction.status = TRANSACTION_STATUS_FAILURE
                    transaction.save()
                elif response_data['data']['tx_status'] == TX_STATUS_AWAITED:
                    # do nothing
                    transaction.save()
                elif response_data['data']['tx_status'] == TX_STATUS_REFUND_PENDING:
                    transaction.status = TRANSACTION_STATUS_REFUND_PENDING
                    transaction.save()
                elif response_data['data']['tx_status'] == TX_STATUS_REFUNDED:
                    amount_refunded
                    transaction.status = TRANSACTION_STATUS_REFUNDED
                    transaction.save()



