import os
import sys
import django
import datetime

import time
import requests
import hmac
import hashlib
import binascii

cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))  # NOQA
sys.path.append(os.path.join(cur_dir, '..', '..'))
sys.path.append(os.path.join(cur_dir, '..', '..', 'zrcms'))
# import settings  # NOQA
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # NOQA
# from django.conf import settings
# settings.configure()
django.setup()  # NOQA

from loan.models import RequestLog, HappyOffer, HappyLoan
from zruser.models import ZrUser
from zrpayment.models import PaymentRequest
from django.db.models.expressions import RawSQL
from zrcms.env_vars import HAPPYLOAN_BASE_URL, HAPPYLOAN_API_KEY, HAPPYLOAN_API_SALT

from django.conf import settings

# api path
cohort_api_url = "cohorts"
disburse_status_url = "disbursals"


def sent_at():
    return "?sent_at=" + str(int(round(time.time())))


def get_headers(api_url):
    headers = {'content-type': 'application/json', 'x-api-key': HAPPYLOAN_API_KEY,
               'x-signature': calculate_signature(api_url)}
    return headers


def calculate_signature(api_url):
    message = HAPPYLOAN_API_SALT + "|" + HAPPYLOAN_API_KEY + "|" + api_url
    message = message.encode('utf-8')
    apiKey = HAPPYLOAN_API_KEY.encode('utf-8')
    sig = binascii.hexlify(hmac.new(apiKey,
                                    msg=message, digestmod=hashlib.sha256).digest())
    return sig


def check_cohort_status():
    print "* check_cohort_status - ", datetime.datetime.today()
    cohort_uids = list(RequestLog.objects.filter(request_type='pq').exclude(response__status__in=['successful']).
                       # values_list('url', flat=True))
                       annotate(uid=RawSQL("((response->>%s))", ('uid',))).
                       values_list('uid', flat=True))

    print cohort_uids

    for cohort_uid in cohort_uids:

        cohort_status_url = HAPPYLOAN_BASE_URL + cohort_api_url + "/" + cohort_uid + sent_at()
        headers = get_headers(cohort_status_url)

        r = requests.get(cohort_status_url, headers=headers)

        status = str(r.json()["status"]).lower() if "status" in r.json() else None

        if status == "successful":
            for pq in r.json()['pre_qualifications']:
                if pq['failure_reason'] is not None:
                    continue

                user = ZrUser.objects.filter(id=pq['customer_uid']).first()

                print "user - ", user, " | amount - ", pq['amount_offered'], " | time - ", datetime.datetime.today()
                HappyOffer(user=user, amount=pq['amount_offered'], cohort_uid=r.json()['uid'],
                           kyc_status=pq['kyc_status'], tenure=pq['tenure'], pq_response=pq,
                           calculated_on=datetime.datetime.today()
                           ).save()

                req_log = RequestLog.objects.filter(request_type='pq', response__uid=cohort_uid).\
                    exclude(response__status__in=['successful']).first()

                if not req_log:
                    continue
                req_log.response = r.json()
                req_log.save()


def check_disbursal_confirmation():
    print "* check_disbursal_confirmation - ", datetime.datetime.today()
    loan_uids = list(HappyLoan.objects.filter(status='WILL_BE_DISBURSED').
                     values_list('loan_uid', flat=True))

    print('-----------------loan_uids', loan_uids)

    for loan_uid in loan_uids:

        confirm_disbursal_url = HAPPYLOAN_BASE_URL + disburse_status_url + "/" + loan_uid + sent_at()
        headers = get_headers(confirm_disbursal_url)

        r = requests.get(confirm_disbursal_url, headers=headers)

        status = r.json()["loan_status"] if "loan_status" in r.json() else None

        print('status', r.json())

        if r.json()["code"] == "OK" and status == "DISBURSED":
            payment_request = PaymentRequest.objects.filter(payment_type=3, ref_no=loan_uid).first()
            if payment_request is None:
                message = "either payment_request was not created or loan_uid changed to rrn/utr"
                print(message)
                continue
            if r.json()["rrn"] != "":
                payment_request.ref_no = r.json()["rrn"]
            elif r.json()["utr"] != "":
                payment_request.ref_no = r.json()["utr"]
            payment_request.save()

            happy_loan = HappyLoan.objects.filter(loan_uid=loan_uid).first()
            if happy_loan is not None:
                happy_loan.response = r.json()
                happy_loan.status = r.json()["loan_status"]
                happy_loan.save()
            else:
                print "loan " + str(loan_uid) + "not found"


check_cohort_status()
check_disbursal_confirmation()