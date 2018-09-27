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
from django.http import HttpResponse, HttpResponseRedirect

from django.conf import settings

from .models import RequestLog, HappyOffer, HappyLoan, HappyRepayment, \
    ZR_LOAN_STATUS_CHOICES
from zrpayment.models import PaymentRequest, PaymentMode, PAYMENT_REQUEST_STATUS, PAYMENT_REQUEST_TYPE
from zrwallet.models import Wallet, WalletTransactions
from zruser.models import Bank, BankDetail
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
from zruser.models import ZrUser, KYCDetail, KYCDocumentType
from zrtransaction.models import Transaction
from zrwallet.models import WalletTransactions


cohort_api_url = "cohorts"
loans_api_url = "loans"
disburse_status_url = "disbursals"
loan_status_url = "loan-status"
payment_advices_url = "payment_advices"
upload_payment_url = "payments"


def admin():
    return ZrUser.objects.filter(role__name='ADMINSTAFF').first()


def sent_at():
    return "?sent_at=" + str(int(round(time.time())))


class RepaymentView(TemplateView):
    template_name = "repayment.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(RepaymentView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RepaymentView, self).get_context_data(**kwargs)
        repayment_history = HappyRepayment.objects.all().order_by('-id')
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

        pan = KYCDetail.objects.filter(for_user=zr_user.id,
                                       type__name='PAN').order_by('-id').first()
        aadhaar_front = KYCDetail.objects.filter(for_user=zr_user.id,
                                                 type__name='Aadhaar_Front').order_by('-id').first()
        aadhaar_back = KYCDetail.objects.filter(for_user=zr_user.id,
                                                type__name='Aadhaar_Back').order_by('-id').first()
        profile = KYCDetail.objects.filter(for_user=zr_user.id,
                                           type__name='Profile').order_by('-id').first()

        kyc_status = None
        try:
            loan_response = RequestLog.objects.filter(request_type='cl', user=zr_user).order_by('-id').first()
            print('loan_response', loan_response)
            # import ast
            if loan_response is not None:
                response = loan_response.response
                print('kyc_status', response)

                if response["code"] == "OK" and "status" in response and response["status"] == "OFFERED":
                    kyc_status = response["offers"][0]["kyc_status"]
                elif response["code"] == "OK" and "status" in response and response["status"] == "REJECTED":
                    kyc_status = response["kyc_status"]
                    print('kyc_status', kyc_status)

                elif response["code"] == "E_INVALID":
                    kyc_status = response["error"]
                    print('kyc_status', kyc_status)

            else:
                print "RequestLog not found for " + zr_user
        except Exception as e:
            print(e)

        offer = HappyOffer.objects.filter(user=zr_user).order_by('-id').first()

        context["offer"] = offer
        context["zr_user"] = zr_user
        context["kyc_status"] = kyc_status

        context["pan"] = pan
        context["aadhaar_front"] = aadhaar_front
        context["aadhaar_back"] = aadhaar_back
        context["profile"] = profile

        return context


def transactions_by_month(user, cohort=True):
    from dateutil.relativedelta import relativedelta

    date_to = None

    date_from = ((datetime.date.today() - relativedelta(months=6)).replace(day=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    if cohort:
        date_to = (datetime.date.today().replace(day=1) - relativedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    else:
        date_to = datetime.date.today().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

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
        else 
        (to_date(d.ym, 'YYYY-MM') + interval '1 month' - interval '1 day')::date - 
        (select at_created::date from zruser_zruser where id=''' + str(user.id) + ''')
        end as total_days  
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
        users = list(ZrUser.objects.filter(role__name="DISTRIBUTOR", id=187))
        print('users', users)
        initiator = admin()

    data = {
        "cohort": [{
            "customer_uid": str(user.id),
            "joined_on": user.at_created.strftime('%Y-%m-%d'),
            "pincode": int(user.pincode) if user.pincode else '',
            "transaction_summary": transactions_by_month(user)
        } for user in users]
    }

    cohort_url = HAPPYLOAN_BASE_URL + cohort_api_url + sent_at()
    headers = get_headers(cohort_url)

    # print 'data', data
    print 'cohort_url', cohort_url

    req_obj = RequestLog(request_type='cc', url=cohort_url, user=initiator)
    r = None
    try:
        r = requests.post(cohort_url, data=json.dumps(data), headers=headers)
    except requests.exceptions.RequestException as err:
        print ("OOps: Something Else", err)

    from pprint import pprint
    print '%%%%%%%%%%%%%'
    print pprint(vars(r))

    req_obj.response = r.json()
    req_obj.save()

    response_dict = {"data_cohort_creation": r.json()}

    if r.json()["code"] == "OK":
        check_cohort_status(r.json()["cohort_uid"], initiator)
    return HttpResponse(json.dumps(response_dict))


def check_cohort_status(cohort_uid, initiator):
    # time.sleep(3) prod

    cohort_status_url = HAPPYLOAN_BASE_URL + cohort_api_url + "/" + cohort_uid + sent_at()
    headers = get_headers(cohort_status_url)
    req_obj = RequestLog(request_type='pq', url=cohort_status_url, user=initiator)

    r = requests.get(cohort_status_url, headers=headers)

    status = str(r.json()["status"]).lower() if "status" in r.json() else None

    if status == "successful":
        for pq in r.json()['pre_qualifications']:
            if pq['failure_reason'] is not None:
                continue

            user = ZrUser.objects.filter(id=pq['customer_uid']).first()

            HappyOffer(user=user, amount=pq['amount_offered'], cohort_uid=r.json()['uid'],
                       kyc_status=pq['kyc_status'], tenure=pq['tenure'], pq_response=pq,
                       calculated_on=datetime.datetime.today()
                       ).save()

    req_obj.response = r.json()
    req_obj.save()
    return


def loan_apply(request):
    req_dict = {}

    user = ZrUser.objects.filter(id=request.user.zr_admin_user.zr_user.id).first()

    req_dict["loan"] = {}

    req_dict["loan"]["amount_requested"] = request.POST["loan_amount"]
    req_dict["loan"]["customer_uid"] = str(user.id)
    req_dict["loan"]["transaction_summary"] = transactions_by_month(user, cohort=False)

    req_dict["loan"]["kyc"] = {}

    update_fields = {}
    if request.POST or request.FILES:
        if request.POST:
            for key, value in request.POST.iteritems():
                if key in ["first_name", "last_name", "father_name", "gender", "email", "aadhaar_no",
                           "date_of_birth", "pan_no", "state", "city", "address_line_1", "address_line_2", "pincode"]:
                    if (user is not None and user[key] != value) or user is None:
                        update_fields[key] = value
            if update_fields:
                ZrUser.objects.filter(id=user.id).update(**update_fields)
        if request.FILES:
            for filename, file in request.FILES.iteritems():
                # update_fields[filename] = "https://s3.ap-south-1.amazonaws.com/zrupee-kyc-documents/c4b5e92b-26ae-4208-9559-f94b961d63c0.jpg" # dev
                doc_id, doc_url = file_save_s3_bucket(file, "zrupee-kyc-documents")  # prod
                KYCDetail.objects.create(
                    type=KYCDocumentType.objects.get(name=filename),
                    document_id=doc_id,
                    document_link=doc_url,
                    for_user=user,
                    role=user.role
                )

    user = ZrUser.objects.filter(id=user.id).first()

    req_dict["loan"]["kyc"]["mobile"] = user.mobile_no
    req_dict["loan"]["kyc"]["email"] = user.email
    req_dict["loan"]["kyc"]["joined_on"] = user.at_created.strftime('%Y-%m-%d')  # "2018-01-01"
    req_dict["loan"]["kyc"]["first_name"] = user.first_name  # "First"
    req_dict["loan"]["kyc"]["last_name"] = user.last_name  # "Second"
    req_dict["loan"]["kyc"]["father_name"] = user.father_name  # "father name"
    req_dict["loan"]["kyc"]["pan_card_no"] = user.pan_no  # "ADCPY5932E"
    req_dict["loan"]["kyc"]["aadhar_no"] = user.aadhaar_no  # "830122323612"
    req_dict["loan"]["kyc"]["risk_score"] = "none"
    req_dict["loan"]["kyc"]["date_of_birth"] = user.date_of_birth.strftime('%Y-%m-%d')  # '1975-03-04'
    req_dict["loan"]["kyc"]["street_address"] = user.address_line_1  # "221/B, Park Avenue"
    req_dict["loan"]["kyc"]["locality"] = user.address_line_2  # "Dadar East"
    req_dict["loan"]["kyc"]["city"] = user.city  # "mumbai"
    req_dict["loan"]["kyc"]["state"] = user.state  # "Maharashtra"
    req_dict["loan"]["kyc"]["pincode"] = user.pincode  # "421301"
    req_dict["loan"]["kyc"]["gender"] = user.gender  # "male"
    req_dict["loan"]["kyc"]["t_consented"] = int(round(time.time()))

    req_dict["loan"]["kyc"]["base64_photo"] = base64.b64encode(requests.get(
        KYCDetail.objects.filter(for_user=user.id,
                                 type__name='Profile').order_by('-id').first().document_link
    ).content).decode('utf-8')
    req_dict["loan"]["kyc"]["base64_pan_card"] = base64.b64encode(requests.get(
        KYCDetail.objects.filter(for_user=user.id,
                                 type__name='PAN').order_by('-id').first().document_link
    ).content).decode('utf-8')
    req_dict["loan"]["kyc"]["base64_aadhar_front"] = base64.b64encode(requests.get(
        KYCDetail.objects.filter(for_user=user.id,
                                 type__name='Aadhaar_Front').order_by('-id').first().document_link
    ).content).decode('utf-8')
    req_dict["loan"]["kyc"]["base64_aadhar_back"] = base64.b64encode(requests.get(
        KYCDetail.objects.filter(for_user=user.id,
                                 type__name='Aadhaar_Back').order_by('-id').first().document_link
    ).content).decode('utf-8')

    req_dict["loan"]["kyc"]["bank_account_name"] = settings.HAPPYLOAN_DISBURSE_ACC['ACCOUNT_NAME']  # "Lalwani Innovations Private Limited"
    req_dict["loan"]["kyc"]["bank_ifsc_code"] = settings.HAPPYLOAN_DISBURSE_ACC['IFSC']  # "UTIB0000373"
    req_dict["loan"]["kyc"]["bank_account_number"] = settings.HAPPYLOAN_DISBURSE_ACC['ACCOUNT_NO']  # "918020030276406"

    loan_create_url = HAPPYLOAN_BASE_URL + loans_api_url + sent_at()
    headers = get_headers(loan_create_url)

    req_obj = RequestLog(request_type='cl', url=loan_create_url, user=user)

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

    req_obj = RequestLog(request_type='ld', url=disburse_url, user=user)

    r = requests.put(disburse_url, data=json.dumps(request_data), headers=headers)
    req_obj.response = r.json()
    req_obj.save()

    if "loan_status" in r.json() and r.json()['loan_status'] == 'WILL_BE_DISBURSED':
        payment_mode = PaymentMode.objects.filter(name='IMPS').first()
        to_bank = Bank.objects.filter(bank_code=settings.HAPPYLOAN_DISBURSE_ACC['CODE']).first()
        to_account_no = settings.HAPPYLOAN_DISBURSE_ACC['ACCOUNT_NO']
        from_bank = Bank.objects.all().filter(bank_code='UTIB').first()

        payment_request = PaymentRequest(from_user=user, to_user=admin(), amount=r.json()['amount_disbursed'],
                                         dmt_amount=r.json()['amount_disbursed'], non_dmt_amount=0,
                                         to_bank=to_bank, to_account_no=to_account_no,
                                         from_bank=from_bank, from_account_no='',
                                         payment_mode=payment_mode, ref_no=loan_uid,
                                         status=0, payment_type=3)
        payment_request.save()

        happy_loan = HappyLoan(user=user, amount=r.json()['amount_disbursed'],
                               loan_uid=r.json()['loan_uid'],
                               status=r.json()['loan_status'],
                               response=r.json(),
                               payment_request=payment_request,
                               disbursed_on=datetime.datetime.today())
        happy_loan.save()

        get_loan_status_disbursal(request, "true")

    response_dict = {"response": r.json()}
    return HttpResponse(json.dumps(response_dict))


def get_loan_status_disbursal(request, auto="false"):
    loan_uid = request.session['offer_data'][0]['loan_uid']
    get_disbursal_url = HAPPYLOAN_BASE_URL + disburse_status_url + "/" + loan_uid + sent_at()
    headers = get_headers(get_disbursal_url)

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

        happy_loan = HappyLoan.objects.filter(loan_uid=loan_uid).first()
        if happy_loan is not None:
            happy_loan.response = r.json()
            happy_loan.status = r.json()["loan_status"]
            happy_loan.save()
        else:
            print "loan " + str(loan_uid) + "not found"
    else:
        print "not disbursed"

    if auto == "false":
        response_dict = {"response": r.json()}
        return HttpResponse(json.dumps(response_dict))

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

        user_loans = []
        loan_uids = None
        if self.request.user.zr_admin_user.role.name == "ADMINSTAFF" or self.request.user.zr_admin_user.role.name == "OPERATIONS":
            loan_uids = list(HappyLoan.objects.all().values('loan_uid', 'user__id'))
        else:
            user = ZrUser.objects.filter(id=self.request.user.zr_admin_user.zr_user.id).first()
            loan_uids = list(HappyLoan.objects.filter(user=user).values('loan_uid', 'user__id'))

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
        repayment_today = HappyRepayment.objects.filter(user=repayment_requested['customer_uid'],
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

            payment_mode = PaymentMode.objects.filter(name='NEFT')
            to_bank = Bank.objects.filter(bank_code=settings.HAPPYLOAN_REPAYMENT_ACC['CODE']).first()

            payment_req_data = {
                'to_bank': to_bank.id, 'dmt_amount': -repayment_amount,
                'to_account_no': settings.HAPPYLOAN_REPAYMENT_ACC['ACCOUNT_NO'], 'from_bank': '100',
                'ref_no': '', 'to_user': admin().id, 'amount': -repayment_amount, 'non_dmt_amount': '0',
                'from_user': user.id,
                'payment_mode': payment_mode, 'document': 'NA', 'from_account_no': 'XXXXXDistributor', 'status': 1,
                'comments': '', 'payment_type': 4
            }

            from zrcommission.views import PaymentRequestSerializer

            serializer = PaymentRequestSerializer(data=payment_req_data)
            payment_req_obj = None
            if serializer.is_valid():
                payment_req_obj = serializer.save()

                zr_wallet = Wallet.objects.get(
                    merchant=user
                )

                zr_wallet.dmt_balance += payment_req_obj.dmt_amount
                zr_wallet.non_dmt_balance += payment_req_obj.non_dmt_amount

                zr_wallet.save()

                wallet_transaction = WalletTransactions.objects.create(
                    wallet=zr_wallet,
                    transaction=None,
                    payment_request=payment_req_obj,
                    dmt_balance=payment_req_obj.dmt_amount,
                    non_dmt_balance=payment_req_obj.non_dmt_amount,
                    dmt_closing_balance=zr_wallet.dmt_balance,
                    non_dmt_closing_balance=zr_wallet.non_dmt_balance,
                    is_success=True
                )

                import pytz
                import delorean

                data = {
                    "payment": {
                        "loan_uid": repayment_requested['loan_uid'],
                        "time_wallet_transaction": int(delorean.Delorean(wallet_transaction.at_created, timezone=pytz.timezone('Asia/Kolkata')).epoch),  # 1536599204,
                        "amount_repaid": int(repayment_amount),
                        "wallet_transaction_id": wallet_transaction.pk,
                        "utr_no": ""
                    }
                }
                r = requests.post(upload_payment_url_full, data=json.dumps(data), headers=headers)
                response.append(r.json())
                user_happy_repayment = HappyRepayment(user=user,
                                                      repayments_request_ref=repayments_request_ref,
                                                      loan_uid=repayment_requested['loan_uid'],
                                                      amount_repaid=int(repayment_amount),
                                                      payment_request=payment_req_obj,
                                                      status=r.json()["payment_status"])
                user_happy_repayment.save()
            else:
                print('invalid serializer', serializer.errors)
        else:
            print "wallet balance below the repayment_amount - " + str(user)

    response_dict = {"response": response}
    return HttpResponse(json.dumps(response_dict))
