# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from zrcms.env_vars import HAPPYLOAN_BASE_URL, HAPPYLOAN_API_KEY, HAPPYLOAN_API_SALT
import datetime

from django.db import connection

from django.views.generic import TemplateView, FormView

from common_utils.user_utils import file_save_s3_bucket

from threading import Thread
from time import sleep

from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from .models import UserProfile, RequestLog, UserHappyOffer, UserHappyLoan, UserHappyRepayment, \
    ZR_LOAN_STATUS_CHOICES
from zrpayment.models import PaymentRequest, PaymentMode, PAYMENT_REQUEST_STATUS, PAYMENT_REQUEST_TYPE
from zrwallet.models import Wallet, WalletTransactions
from zruser.models import Bank
from django.conf import settings

from django.db.models import Count, Sum
import requests
import json
import time
import hmac
import hashlib
import binascii
import base64
from django.urls import reverse
from zruser.models import ZrUser
from zrtransaction.models import Transaction
from zrwallet.models import WalletTransactions


cohort_api_url = "cohorts"
loans_api_url = "loans"
disburse_status_url = "disbursals"
loan_status_url = "loan-status"
payment_advices_url = "payment_advices"
upload_payment_url = "payments"

# wait_seconds = 1  # dev
wait_seconds = 300  # prod


def sent_at():
    return "?sent_at=" + str(int(round(time.time())))


class RepaymentView(TemplateView):
    template_name = "repayment.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(RepaymentView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RepaymentView, self).get_context_data(**kwargs)
        repayment_history = UserHappyRepayment.objects.all().order_by('-id')
        context["repayment_history"] = repayment_history
        return context


class PreApproved(TemplateView):
    template_name = "preapproved.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(PreApproved, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PreApproved, self).get_context_data(**kwargs)
        zr_user = ZrUser.objects.filter(id=self.request.user.zr_admin_user.zr_user.id).first()

        #zr_user = ZrUser.objects.get(id=105) #dev

        kyc_status = None
        try:
            kyc_status = RequestLog.objects.filter(request_type='cl', user=zr_user).order_by('-id').first()
            import ast
            if kyc_status is not None:
                kyc_status = ast.literal_eval(kyc_status.response)

                if kyc_status["code"] == "OK" and "status" in kyc_status and kyc_status["status"] == "OFFERED":
                    kyc_status = kyc_status["offers"][0]["kyc_status"]
                elif kyc_status["code"] == "OK" and "status" in kyc_status and kyc_status["status"] == "REJECTED":
                    kyc_status = kyc_status["kyc_status"]
                elif kyc_status["code"] == "E_INVALID":
                    kyc_status = kyc_status["error"]
            else:
                print "RequestLog not found for " + zr_user
        except:
            pass

        offer = UserHappyOffer.objects.filter(user=zr_user).order_by('-id').first()

        up = UserProfile.objects.filter(user=zr_user).order_by('-id').first()

        context["offer"] = offer
        context["zr_user"] = zr_user
        context["up"] = up
        context["kyc_status"] = kyc_status
        return context


def transactions_by_month(user, cohort=True):
    from dateutil.relativedelta import relativedelta

    date_to = None

    date_from = ((datetime.date.today() - relativedelta(months=6)).replace(day=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    if cohort:
        date_to = (datetime.date.today().replace(day=1) - relativedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    else:
        date_to = datetime.date.today().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    data_all = None

    def dictfetchall(cursor):
        "Return all rows from a cursor as a dict"
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    prod = ''' 
        COALESCE(volume, 0)::int volume,                             
        COALESCE(dmt_volume, 0)::int dmt_volume,                     
        COALESCE(non_dmt_volume, 0)::int non_dmt_volume,             
        COALESCE(dmt_count, 0) dmt_count,                            
        COALESCE(non_dmt_count, 0) non_dmt_count,                    
        COALESCE(q.cnt, 0)::int active_days,  
        COALESCE(w.min_wallet_balance, 0)::int min_wallet_balance,         
        COALESCE(w.max_wallet_balance, 0)::int max_wallet_balance,             
    '''

    dev = '''
        3000000 volume, 
        1500000 dmt_volume, 
        1500000 non_dmt_volume, 
        25 dmt_count, 
        25 non_dmt_count, 
        25 active_days,
        1000000 min_wallet_balance,
        4000000 max_wallet_balance,
    '''

    all = '''  
        select 
        to_char(to_date(d.ym, 'YYYY-MM'), 'YYYY')::int as year, 
        to_char(to_date(d.ym, 'YYYY-MM'), 'fmMM')::int as month, 
      ''' + prod + '''
        case when (to_date(d.ym, 'YYYY-MM') + interval '1 month' - interval '1 day')::date - 
        (select at_created::date from zruser_zruser where id=''' + str(user.id) + ''') >
        (SELECT  
             DATE_PART('days', 
                 DATE_TRUNC('month', to_date(d.ym, 'YYYY-MM')) 
                 + '1 MONTH'::INTERVAL 
                 - '1 DAY'::INTERVAL
             ))
        then (SELECT  
             DATE_PART('days', 
                 DATE_TRUNC('month', to_date(d.ym, 'YYYY-MM')) 
                 + '1 MONTH'::INTERVAL 
                 - '1 DAY'::INTERVAL
             ))::int
        else 0 end as total_days  
        from 
        (
            SELECT to_char(ym_q, 'YYYY-MM') ym
            FROM generate_series(timestamp \'''' + date_from + '''\'
                                 , timestamp \'''' + date_to + '''\'
                                 , interval  '1 month') ym_q
        ) d
        left join
        (
        SELECT to_char(at_created, 'YYYY-MM') ym, 
        sum(amount) volume,
        sum(dmt_amount) dmt_volume,
        sum(non_dmt_amount) non_dmt_volume,
        count(case when dmt_amount > 0 then 1 end) dmt_count,
        count(case when non_dmt_amount > 0 then 1 end) non_dmt_count
         
        FROM public.zrpayment_paymentrequest
        where from_user_id=''' + str(user.id) + ''' and status=1 and payment_type=0
        and at_created::timestamp with time zone AT TIME ZONE 'Asia/Kolkata'  
        between \'''' + date_from + '''\' and \'''' + date_to + '''\'
        group by to_char(at_created, 'YYYY-MM')
        order by to_char(at_created, 'YYYY-MM')
        ) vc
        
        on d.ym=vc.ym
        
        left join
        
        (select ym, count(cnt) cnt
        from
        (SELECT to_char(at_created, 'YYYY-MM') ym,  to_char(at_created, 'DD') d,  count(*) cnt
        FROM public.zrpayment_paymentrequest
        where from_user_id=''' + str(user.id) + ''' and status=1 and payment_type=0
        and at_created::timestamp with time zone AT TIME ZONE 'Asia/Kolkata'  
        between \'''' + date_from + '''\' and \'''' + date_to + '''\'
        group by to_char(at_created, 'YYYY-MM'), to_char(at_created, 'DD')
        having sum(amount)>0
        order by to_char(at_created, 'YYYY-MM'), to_char(at_created, 'DD')) sq
        group by ym) q
        on vc.ym=q.ym
        
        left join
        (
        SELECT 
        to_char(at_created, 'YYYY-MM') ym, 
        min( dmt_closing_balance + non_dmt_closing_balance) min_wallet_balance,
        max( dmt_closing_balance + non_dmt_closing_balance) max_wallet_balance
        FROM public.zrwallet_wallettransactions
        where wallet_id=''' + str(user.id) + '''
        and at_created::timestamp with time zone AT TIME ZONE 'Asia/Kolkata'  
        between \'''' + date_from + '''\' and \'''' + date_to + '''\'
        group by to_char(at_created, 'YYYY-MM')
        order by to_char(at_created, 'YYYY-MM')
        ) w
        on q.ym=w.ym                                                                                                
    '''

    cursor = connection.cursor()
    cursor.execute(all)
    data_all = dictfetchall(cursor)
      
    for trans_dict in data_all:
        # expensive step
    
        trans_dict["count"] = int(trans_dict["dmt_count"] + trans_dict["non_dmt_count"])

        trans_dict["verticals"] = [{
            "vertical_name": "money_transfers",
            "volume": int(trans_dict["dmt_volume"]),
            "count": int(trans_dict["dmt_count"])
        }, {
            "vertical_name": "others",
            "volume": int(trans_dict["non_dmt_volume"]),
            "count": int(trans_dict["non_dmt_count"])
        }]

        del trans_dict["dmt_volume"]
        del trans_dict["non_dmt_volume"]
        del trans_dict["dmt_count"]
        del trans_dict["non_dmt_count"]

    return list(data_all)


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


def cohort_pq(request=None):
    users = []
    initiator = None

    if request is not None and request.user.zr_admin_user.role.name != 'ADMINSTAFF':
        user = initiator = ZrUser.objects.filter(id=request.user.zr_admin_user.zr_user.id).first()
        users = [user]
    else:
        users = list(ZrUser.objects.filter(role__name="DISTRIBUTOR"))
        admin = ZrUser.objects.filter(role__name='ADMINSTAFF').first()
        initiator = admin

    data = {
        "cohort": [{
            "customer_uid": str(user.id),
            "joined_on": user.at_created.strftime('%Y-%m-%d'),
            "pincode": int(user.pincode),
            "transaction_summary": transactions_by_month(user)
        } for user in users]
    }

    cohort_url = HAPPYLOAN_BASE_URL + cohort_api_url + sent_at()
    headers = get_headers(cohort_url)

    req_obj = RequestLog(request_type='cc', url=cohort_url, user=initiator)
    r = requests.post(cohort_url, data=json.dumps(data), headers=headers)
    req_obj.response = r.json()
    req_obj.save()

    response_dict = {"data_cohort_creation": r.json()}

    if r.json()["code"] == "OK":
        cohort_status_timer = Thread(target=check_cohort_status, args=[r.json()["cohort_uid"], initiator])
        cohort_status_timer.start()

    return HttpResponse(json.dumps(response_dict))


def check_cohort_status(cohort_uid, initiator):
    time.sleep(3)

    cohort_status_url = HAPPYLOAN_BASE_URL + cohort_api_url + "/" + cohort_uid + sent_at()
    headers = get_headers(cohort_status_url)
    req_obj = RequestLog(request_type='pq', url=cohort_status_url, user=initiator)

    status = None
    counter = 0
    counter_limit = 12
    r = None
    while status != "successful" and counter < counter_limit:
        r = requests.get(cohort_status_url, headers=headers)

        status = str(r.json()["status"]).lower() if "status" in r.json() else None

        if status == "successful":
            for pq in r.json()['pre_qualifications']:
                if pq['failure_reason'] is not None:
                    continue

                user = ZrUser.objects.filter(id=pq['customer_uid']).first()

                UserHappyOffer(user=user, amount=pq['amount_offered'], cohort_uid=r.json()['uid'],
                               kyc_status=pq['kyc_status'], tenure=pq['tenure'], pq_response=pq,
                               calculated_on=datetime.datetime.today()
                               ).save()
        else:
            print "no successful response from get cohort"
            counter = counter + 1
            sleep(wait_seconds)

    req_obj.response = r.json()
    if status != "successful":
        req_obj.comment = "no successful response from get cohort after " + str(counter + 1) + " tries"
    req_obj.save()
    return


def loan_apply(request):
    req_dict = {}

    zr_user = ZrUser.objects.filter(id=request.user.zr_admin_user.zr_user.id).first()

    # zr_user = ZrUser.objects.get(id=105) #dev

    req_dict["loan"] = {}

    req_dict["loan"]["amount_requested"] = request.POST["loan_amount"]
    req_dict["loan"]["customer_uid"] = str(zr_user.id)
    req_dict["loan"]["transaction_summary"] = transactions_by_month(zr_user, cohort=False)

    #if request.POST.get("kyc_status", "") == 'INCOMPLETE':

    req_dict["loan"]["kyc"] = {}

    user_profile = UserProfile.objects.filter(user=zr_user.pk).first()
    update_fields = {}
    if request.POST or request.FILES:
        if request.POST:
            for key, value in request.POST.iteritems():
                if key == "date_of_birth":
                    if (user_profile is not None and unicode(user_profile[key]) != value) or user_profile is None:
                        update_fields[key] = datetime.datetime.strptime(value, '%Y-%m-%d').date()
                if key in ["first_name", "last_name", "father_name", "gender", "email", "aadhaar_number",
                           "pan_number", "state", "city", "locality", "street_address", "pincode"]:
                    if (user_profile is not None and user_profile[key] != value) or user_profile is None:
                        update_fields[key] = value
        if request.FILES:
            for filename, file in request.FILES.iteritems():
                # update_fields[filename] = "https://s3.ap-south-1.amazonaws.com/zrupee-kyc-documents/c4b5e92b-26ae-4208-9559-f94b961d63c0.jpg" # dev
                update_fields[filename] = file_save_s3_bucket(file, "zrupee-kyc-documents") # prod

        if user_profile is None:
            update_fields["phone_number"] = zr_user.mobile_no
            update_fields["date_joined"] = datetime.datetime.strptime(zr_user.at_created.strftime('%Y-%m-%d'), '%Y-%m-%d').date()

        if update_fields:
            user_profile, created = UserProfile.objects.update_or_create(
                user=zr_user,
                defaults=update_fields)

    req_dict["loan"]["kyc"]["mobile"] = user_profile.phone_number
    req_dict["loan"]["kyc"]["email"] = user_profile.email
    req_dict["loan"]["kyc"]["joined_on"] = user_profile.date_joined.strftime('%Y-%m-%d')  # "2018-01-01"
    req_dict["loan"]["kyc"]["first_name"] = user_profile.first_name  # "First"
    req_dict["loan"]["kyc"]["last_name"] = user_profile.last_name  # "Second"
    req_dict["loan"]["kyc"]["father_name"] = user_profile.father_name  # "father name"
    req_dict["loan"]["kyc"]["pan_card_no"] = user_profile.pan_number  # "ADCPY5932E"
    req_dict["loan"]["kyc"]["aadhar_no"] = user_profile.aadhaar_number  # "830122323612"
    req_dict["loan"]["kyc"]["risk_score"] = "none"
    req_dict["loan"]["kyc"]["date_of_birth"] = user_profile.date_of_birth.strftime('%Y-%m-%d')  # '1975-03-04'
    req_dict["loan"]["kyc"]["street_address"] = user_profile.street_address  # "221/B, Park Avenue"
    req_dict["loan"]["kyc"]["locality"] = user_profile.locality  # "Dadar East"
    req_dict["loan"]["kyc"]["city"] = user_profile.city  # "mumbai"
    req_dict["loan"]["kyc"]["state"] = user_profile.state  # "Maharashtra"
    req_dict["loan"]["kyc"]["pincode"] = user_profile.pincode  # "421301"
    req_dict["loan"]["kyc"]["gender"] = user_profile.gender  # "male"
    req_dict["loan"]["kyc"]["t_consented"] = int(round(time.time()))

    req_dict["loan"]["kyc"]["base64_photo"] = base64.b64encode(requests.get(
        user_profile.profile_photo
    ).content).decode('utf-8')
    req_dict["loan"]["kyc"]["base64_pan_card"] = base64.b64encode(requests.get(
        user_profile.pan_card_photo
    ).content).decode('utf-8')
    req_dict["loan"]["kyc"]["base64_aadhar_front"] = base64.b64encode(requests.get(
        user_profile.aadhaar_photo_front
    ).content).decode('utf-8')
    req_dict["loan"]["kyc"]["base64_aadhar_back"] = base64.b64encode(requests.get(
        user_profile.aadhaar_photo_back
    ).content).decode('utf-8')

    req_dict["loan"]["kyc"]["bank_account_name"] = "Lalwani Innovations Private Limited"
    req_dict["loan"]["kyc"]["bank_ifsc_code"] = "UTIB0000373"
    req_dict["loan"]["kyc"]["bank_account_number"] = "918020030276406"

    from django.http import HttpResponseRedirect

    loan_create_url = HAPPYLOAN_BASE_URL + loans_api_url + sent_at()
    headers = get_headers(loan_create_url)

    req_obj = RequestLog(request_type='cl', url=loan_create_url, user=zr_user)

    r = requests.post(loan_create_url, data=json.dumps(req_dict), headers=headers)
    req_obj.response = r.json()
    req_obj.save()

    create_loan_response = r.json()
    if create_loan_response.get("status") == "OFFERED":
        request.session['offer_data'] = create_loan_response["offers"]
        return HttpResponseRedirect(reverse('loan:disburse-a-loan', args=()))
    preapproved_path = request.POST.get('preapproved_path', '/')

    request.session['offer_data'] = create_loan_response

    return HttpResponseRedirect(preapproved_path)


class DisburseLoan(TemplateView):
    template_name = "disburse.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(DisburseLoan, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DisburseLoan, self).get_context_data(**kwargs)
        # context["offer"] = self.request.session['offer_data']
        return context


def accept_loan(request):
    bo = request.body.decode("utf-8")
    loan_uid = json.loads(bo)["loan_uid"]
    time_accept = str(int(round(time.time())))
    
    disburse_url = HAPPYLOAN_BASE_URL + loans_api_url + "/" + loan_uid + sent_at()
    headers = get_headers(disburse_url)
    request_data = {
        "loan": {
            "time_tnc_accepted_via_partner": time_accept
            }
        }

    user = ZrUser.objects.filter(id=request.user.zr_admin_user.zr_user.id).first()

    # user = ZrUser.objects.get(id=105) #dev
    req_obj = RequestLog(request_type='ld', url=disburse_url, user=user)

    r = requests.put(disburse_url, data=json.dumps(request_data), headers=headers)
    req_obj.response = r.json()
    req_obj.save()

    if "loan_status" in r.json() and r.json()['loan_status'] == 'WILL_BE_DISBURSED':
        payment_mode = PaymentMode.objects.all().filter(name='IMPS').first()
        bank = Bank.objects.all().filter(bank_code='UTIB').first()
        to_user = ZrUser.objects.filter(role__name='ADMINSTAFF').first()
        payment_request = PaymentRequest(from_user=user, to_user=to_user, amount=r.json()['amount_disbursed'],
                                         dmt_amount=r.json()['amount_disbursed'], non_dmt_amount=0,
                                         to_bank=bank, to_account_no='918020030276406',
                                         from_bank=bank, from_account_no='',
                                         payment_mode=payment_mode, ref_no=loan_uid,
                                         status=0, payment_type=3)
        payment_request.save()

        happy_loan = UserHappyLoan(user=user, amount=r.json()['amount_disbursed'],
                                   loan_uid=r.json()['loan_uid'],
                                   status=r.json()['loan_status'],
                                   response=r.json(),
                                   payment_request=payment_request,
                                   disbursed_on=datetime.datetime.today())
        happy_loan.save()

        cohort_status_timer = Thread(target=get_loan_status_disbursal, args=[request, "true"])
        cohort_status_timer.start()

    response_dict = {"response": r.json()}
    return HttpResponse(json.dumps(response_dict))


def get_loan_status_disbursal(request, auto="false"):
    loan_uid = request.session['offer_data'][0]['loan_uid']
    get_disbursal_url = HAPPYLOAN_BASE_URL + disburse_status_url + "/" + loan_uid + sent_at()
    headers = get_headers(get_disbursal_url)
    req_obj = None

    if auto == "true":
        sleep(wait_seconds)
        admin = ZrUser.objects.filter(role__name='ADMINSTAFF').first()
        req_obj = RequestLog(request_type='ldc', url=get_disbursal_url, user=admin)

    status = None
    counter = 0
    counter_limit = 12
    r = None
    while status != "DISBURSED" and counter < counter_limit:
        r = requests.get(get_disbursal_url, headers=headers)
        status = r.json()["loan_status"] if "loan_status" in r.json() else None

        if r.json()["code"] == "OK" and status == "DISBURSED":
            payment_request = PaymentRequest.objects.filter(payment_type=3, ref_no=loan_uid).first()
            if payment_request is None:
                message = "either payment_request was not created or loan_uid changed to rrn/utr"
                print(message)
                if auto == "false":
                    response_dict = {"response": r.json()}
                    return HttpResponse(json.dumps(response_dict))
            if r.json()["rrn"] != "":
                payment_request.ref_no = r.json()["rrn"]
            elif r.json()["utr"] != "":
                payment_request.ref_no = r.json()["utr"]
            payment_request.save()

            happy_loan = UserHappyLoan.objects.filter(loan_uid=loan_uid).first()
            if happy_loan is not None:
                happy_loan.response = r.json()
                happy_loan.status = r.json()["loan_status"]
                happy_loan.save()
            else:
                print "loan " + str(loan_uid) + "not found"
            if auto == "false":
                response_dict = {"response": r.json()}
                return HttpResponse(json.dumps(response_dict))
        else:
            print "not disbursed"
            counter = counter + 1

            if auto == "true":
                sleep(wait_seconds)
            else:
                response_dict = {"response": r.json()}
                return HttpResponse(json.dumps(response_dict))

    req_obj.response = r.json()
    if status != "DISBURSED":
        req_obj.comment = "no successful response from get loan status after " + str(counter + 1) + " tries"
        print "no successful response from get loan status after " + str(counter + 1) + " tries"
    req_obj.save()
    return


class LoanStatusView(TemplateView):
    template_name = "loan_status.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(LoanStatusView, self).dispatch(request, *args, **kwargs)


def get_loan_status_request(request, loan_id):
    loan_status_url_full = HAPPYLOAN_BASE_URL + loan_status_url + "/" + loan_id + sent_at()
    headers = get_headers(loan_status_url_full)
    r = requests.get(loan_status_url_full, headers=headers)
    response_dict = {"response": r.json()}
    return HttpResponse(json.dumps(response_dict))


class GetUserLoans(TemplateView):
    template_name = "user_loans.html"

    def get_context_data(self, **kwargs):
        context = super(GetUserLoans, self).get_context_data(**kwargs)
        # user = ZrUser.objects.get(id=105) #dev

        user_loans = []
        loan_uids = None
        if self.request.user.zr_admin_user.role.name == "ADMINSTAFF" or self.request.user.zr_admin_user.role.name == "OPERATIONS":
            loan_uids = list(UserHappyLoan.objects.all().values('loan_uid', 'user__id'))
        else:
            user = ZrUser.objects.filter(id=self.request.user.zr_admin_user.zr_user.id).first()
            loan_uids = list(UserHappyLoan.objects.filter(user=user).values('loan_uid', 'user__id'))

        for loan_uid in loan_uids:
            loan_status = json.loads(get_loan_status_request(self.request, loan_uid["loan_uid"]).content)["response"]
            loan_status["zr_id"] = loan_uid["user__id"]
            user_loans.append(loan_status)

        context["user_loans"] = user_loans
        return context


def get_repayments(request=None, upload="false", date=datetime.datetime.today().strftime("%Y-%m-%d")):
    repayment_url_full = HAPPYLOAN_BASE_URL + payment_advices_url + "/" + date + sent_at()
    headers = get_headers(repayment_url_full)
    r = requests.get(repayment_url_full, headers=headers)

    if request is not None and str(upload) == "false":
        request.session['get_repayments'] = r.json()
        response_dict = {"response": r.json()}
        return HttpResponse(json.dumps(response_dict))
    else:
        if str(upload) == "true":
            upload_repayments(repayments=json.dumps(r.json()))
        return


def upload_repayments(request=None, repayments=None):
    repayments_request_ref = None
    response_dict = None

    if request is not None:
        if "repayments_requested" not in request.session["get_repayments"]:
            response_dict = {"response": "No get_repayments"}
            return HttpResponse(json.dumps(response_dict))
        repayments_requested = request.session["get_repayments"]["repayments_requested"]
        repayments_request_ref = request.session["get_repayments"]["request_ref"]
    else:
        repayments = json.loads(repayments)
        if repayments["code"] != "OK":
            print repayments["error"] if "error" in repayments else "Something went wrong"
            return
        repayments_requested = repayments["repayments_requested"]
        if not repayments_requested:
            print "repayments_requested is empty"
            return
        repayments_request_ref = repayments["request_ref"]
    
    upload_payment_url_full = HAPPYLOAN_BASE_URL + upload_payment_url + "/" + sent_at()
    headers = get_headers(upload_payment_url_full)

    import decimal
    response = []

    for i, repayment_requested in enumerate(repayments_requested):
        print "-----" + str(i + 1) + " - customer_uid - ", repayment_requested["customer_uid"]
        loan_status = json.loads(get_loan_status_request(request, repayment_requested['loan_uid']).content)["response"]["status"]
        repayment_today = UserHappyRepayment.objects.filter(user=repayment_requested['customer_uid'],
                                                            loan_uid=repayment_requested['loan_uid'],
                                                            at_created__date=datetime.datetime.today().
                                                            strftime("%Y-%m-%d"))

        if loan_status == "fully_repaid" or repayment_today:
            print "fully_repaid or repayment_today"
            continue

        user = ZrUser.objects.filter(id=repayment_requested['customer_uid']).first()
        wallet = Wallet.objects.filter(merchant=user).first()

        if user is None or wallet is None:
            print "user or wallet not found"
            continue

        repayment_amount = decimal.Decimal(float(repayment_requested['repayment_amount']))
        if wallet.dmt_balance >= repayment_amount:
            print "user wallet balance is greater than or equal to repayment_amount"

            wallet.dmt_balance -= repayment_amount
            wallet.save()

            wallet_transactions = WalletTransactions(
                wallet=wallet,
                transaction=None,
                payment_request=None,
                dmt_balance=-repayment_amount,
                non_dmt_balance=0,
                dmt_closing_balance=wallet.dmt_balance,
                non_dmt_closing_balance=wallet.non_dmt_balance,
                is_success=True
            )
            wallet_transactions.save()

            import pytz
            import delorean

            # epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=IST)
            data = {
                "payment": {
                    "loan_uid": repayment_requested['loan_uid'],
                    "time_wallet_transaction": int(delorean.Delorean(wallet_transactions.at_created, timezone=pytz.timezone('Asia/Kolkata')).epoch),  # 1536599204,
                    "amount_repaid": int(repayment_amount),
                    "wallet_transaction_id": wallet_transactions.pk,
                    "utr_no": ""
                }
            }
            r = requests.post(upload_payment_url_full, data=json.dumps(data), headers=headers)
            response.append(r.json())
            user_happy_repayment = UserHappyRepayment(user=user,
                                                      repayments_request_ref=repayments_request_ref,
                                                      loan_uid=repayment_requested['loan_uid'],
                                                      amount_repaid=int(repayment_amount),
                                                      status=r.json()["payment_status"])
            user_happy_repayment.save()
        else:
            print "wallet balance below the repayment_amount - " + str(user)

    response_dict = {"response": response}
    return HttpResponse(json.dumps(response_dict))
