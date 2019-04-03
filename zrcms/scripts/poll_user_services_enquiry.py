# coding: utf-8
import os
import django

import sys

cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
sys.path.append(os.path.join(cur_dir, '..', '..'))
import settings  # NOQA
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
django.setup()  # NOQA

import json
from time import sleep

import requests

from common_utils import email_utils
from zrcms.env_vars import EKO_DEVELOPER_KEY, EKO_INITIATOR_ID, EKO_USER_SERVICES_ENQUIRY_URL, EKO_AEPS_INITIATOR_ID, \
    EKO_AEPS_USER_CODE
from zrtransaction.models import Transaction
from zrtransaction.utils.constants import INITIATED, ACTIVATED, PENDING, APPROVED, RESUBMISSION, AEPS_ONBOARDING_STATUS
from zrwallet.models import WalletTransactions

from django.db import transaction as dj_transaction


def poll_user_services_enquiry():
    transactions = Transaction.objects.filter(type__name='SERVICE_ACTIVATION_AEPS')\
        .exclude(status=AEPS_ONBOARDING_STATUS['ACTIVATED'], amount=0)
    # exclude success
    print 'polling user services status for queryset ', transactions, transactions

    for transaction in transactions:
        try:
            with dj_transaction.atomic():
                sleep(1)
                user_code = transaction.user.user_code
                # STAGING TEST
                # user_code = '20810200'
                headers = {
                    'developer_key': EKO_DEVELOPER_KEY,
                    'cache-control': "no-cache"
                }
                url = EKO_USER_SERVICES_ENQUIRY_URL + 'user_code:' + user_code + '?initiator_id=' + EKO_AEPS_INITIATOR_ID
                print 'making eko api request ', 'URL: ', url, 'headers: ', headers
                response_data = requests.get(url, headers=headers).json()
                print response_data, response_data['status']

                aeps_service = None

                if 'data' in response_data and 'service_status_list' in response_data['data']:
                    service_status_list = response_data['data']['service_status_list']
                    # print service_status_list
                    for service in service_status_list:
                        if service['service_code'] == '1':
                            # print 'service - ', service
                            aeps_service = service
                            # print service['status'], service['status_desc'], service['comments']

                # refer to eko documentation for tx_status responses http://developers.eko.co.in/docs/index.html

                if aeps_service['status'] == ACTIVATED:
                    transaction.status = AEPS_ONBOARDING_STATUS['ACTIVATED']
                    transaction.save()

                    if transaction.transaction_response_json is None:
                        transaction.transaction_response_json = dict(poll_activated_response=aeps_service)
                    else:
                        transaction.transaction_response_json['poll_activated_response'] = aeps_service
                    transaction.save()

                elif aeps_service['status'] == PENDING and transaction.status == AEPS_ONBOARDING_STATUS['PENDING'] or \
                        aeps_service['status'] == APPROVED and transaction.status == AEPS_ONBOARDING_STATUS['APPROVED']:
                    pass

                elif transaction.transaction_response_json is not None and 'poll_resubmission_response' in \
                        transaction.transaction_response_json and aeps_service['comments'] != \
                        transaction.transaction_response_json['poll_resubmission_response']['comments']:

                    transaction.status = AEPS_ONBOARDING_STATUS['RESUBMISSION']
                    transaction.save()

                    if transaction.transaction_response_json is None:
                        transaction.transaction_response_json = dict(poll_resubmission_response=aeps_service)
                    else:
                        transaction.transaction_response_json['poll_resubmission_response'] = aeps_service
                    transaction.save()

                elif aeps_service['status'] == PENDING:

                    transaction.status = AEPS_ONBOARDING_STATUS['PENDING']
                    transaction.save()

                    if transaction.transaction_response_json is None:
                        transaction.transaction_response_json = dict(poll_pending_response=aeps_service)
                    else:
                        transaction.transaction_response_json['poll_pending_response'] = aeps_service
                    transaction.save()

                elif aeps_service['status'] == APPROVED:

                    transaction.status = AEPS_ONBOARDING_STATUS['APPROVED']
                    transaction.save()

                    if transaction.transaction_response_json is None:
                        transaction.transaction_response_json = dict(poll_approved_response=aeps_service)
                    else:
                        transaction.transaction_response_json['poll_approved_response'] = aeps_service
                    transaction.save()

                elif aeps_service['status'] == RESUBMISSION:

                    transaction.status = AEPS_ONBOARDING_STATUS['RESUBMISSION']
                    transaction.save()

                    if transaction.transaction_response_json is None:
                        transaction.transaction_response_json = dict(poll_resubmission_response=aeps_service)
                    elif 'poll_resubmission_response' in transaction.transaction_response_json and \
                            aeps_service['comments'] == \
                            transaction.transaction_response_json['poll_resubmission_response']['comments']:
                        pass
                    else:
                        transaction.transaction_response_json['poll_resubmission_response'] = aeps_service
                    transaction.save()

                else:
                    print 'Something went wrong'

        except Exception as e:
            print('Err - ', transaction, e)


poll_user_services_enquiry()
