# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.views.generic import TemplateView, FormView

from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from .models import DailyTransaction, UserProfile, RequestLog, UserHappyOffer, Project
from django.db.models import Count, Sum
import requests
import json
import time
import hmac
import hashlib
import binascii
import base64
from django.shortcuts import redirect
from django.urls import reverse
import random
from .forms import ProjectForm
from django.core import serializers
from .data import *
from zruser.models import ZrAdminUser, ZrUser, BankDetail, ZrTerminal, KYCDocumentType
from zrpayment.models import PaymentRequest

cohort_api_url = "cohorts"
loans_api_url = "loans"
disburse_status_url = "disbursals"
repayment_url = "payment_advices"
loan_status_url = "loan-status"
api_salt = "uat"

partner = "zrupee"
data_used = ""
api_key, base_url = "", ""

if partner == "indopay":
    base_url = "https://api-staging.arthimpact.com/v1/indopay/"
    api_key = "3bfabad5-1f02-4816-8b0c-b9fc8de4dbff"
    data_used = data_monthly_positive
elif partner == "storeking":
    base_url = "https://api-uat.arthimpact.com/v1/storeking/"
    api_key = "36bc669b-108a-42c8-854d-9413fcfa97b4"
    data_used = data_weekly_positive
elif partner == "payworld":
    base_url = "https://api-staging.arthimpact.com/v1/payworld/"
    api_key = "710d22f6-e7da-4d55-acb8-dc850188600f"
    data_used = data_positive
elif partner == "ipay":
    base_url = "https://api-staging.arthimpact.com/v1/ipay/"
    api_key = "f4893d21-1ab2-49f6-b717-a6937614ce40"
    data_used = data_monthly_positive
elif partner == "nict":
    base_url = "https://api-staging.arthimpact.com/v1/nict/"
    api_key = "710c5fa1-7f4e-426c-9657-6c5380087d12"
    data_used = data_monthly_positive_nict
elif partner == "weizmann":
    base_url = "https://api-staging.arthimpact.com/v1/weizmann-impex/"
    api_key = "49e9e1f0-884f-4970-be97-c53f2a713bec"
    data_used = data_positive
elif partner == "dipl":
    base_url = "https://api-staging.arthimpact.com/v1/dipl/"
    api_key = "00391899-f92b-441c-82e4-e9d56a99371d"
    data_used = data_monthly_positive
elif partner == "zrupee":
    base_url = "https://api-uat.arthimpact.com/v1/zrupee/"
    api_key = "cf579dea-e32c-4e1c-ae0f-832ba7749f09"
    data_used = DATA_UAT2
else:
    base_url, api_key = "", ""


class FrontPage(TemplateView):
    template_name = "index.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(FrontPage, self).dispatch(request, *args, **kwargs)


class RepaymentView(TemplateView):
    template_name = "repayment.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(RepaymentView, self).dispatch(request, *args, **kwargs)


class PreApproved(TemplateView):
    template_name = "preapproved.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(PreApproved, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PreApproved, self).get_context_data(**kwargs)
        print(self.request.user)
        up = UserProfile.objects.get(user=self.request.user)
        offer = None
        try:
            offer = UserHappyOffer.objects.get(user=self.request.user)
        except:
            pass
        context["offer"] = offer
        context["up"] = up
        return context


def TransactionsByDay(user):

    trans = PaymentRequest.objects.filter(from_user=user).values('amount')
    print 'trans', trans

    trans_list = []
    trans = DailyTransaction.objects.filter(user=user)
    trans_dict_list = trans.values('date').annotate(
        volume=Sum('amount'), count=Count('date'))
    for trans_dict in trans_dict_list:
        # expensive step
        trans_dict["date"] = trans_dict["date"].strftime('%Y-%m-%d')
        trans_dict["volume"] = float(trans_dict["volume"])
    return list(trans_dict_list)


def get_headers(api_url):
    headers = {'content-type': 'application/json', 'x-api-key': api_key,
               'x-signature': calculate_signature(api_url)}
    return headers


def calculate_signature(api_url):
    message = api_salt + "|" + api_key + "|" + api_url
    message = message.encode('utf-8')
    apiKey = api_key.encode('utf-8')
    sig = binascii.hexlify(hmac.new(apiKey,
                                    msg=message, digestmod=hashlib.sha256).digest())
    return sig


def GetALoan(request):
    user = request.user
    from pprint import pprint
    print pprint(vars(user))
    print user.zr_admin_user.role.name
    print user.zr_admin_user.zr_user.id
    #user_profile = UserProfile.objects.get(user=user)
    user_profile = ZrUser.objects.get(id=user.zr_admin_user.zr_user.id)
    #trans = DailyTransaction.objects.filter(user=user)
    # data = {"cohort":
    #     [{
    #         "customer_uid": user_profile.id,
    #         "joined_on": user.date_joined.strftime('%Y-%m-%d'),
    #         "pincode": int(user_profile.pincode),
    #         "transaction_summary": TransactionsByDay(user)
    #     }]
    # }
    sent_at = "?sent_at=" + str(int(round(time.time())))
    cohort_url = base_url + cohort_api_url + sent_at
    print cohort_url
    headers = get_headers(cohort_url)
    req_obj = RequestLog(request_type='cc', url=cohort_url, user=user)
    r = requests.post(cohort_url, data=json.dumps(data_used), headers=headers)
    req_obj.response = r.json()
    req_obj.save()

    response_dict = {"data_cohort_creation": r.json()}
    print(r.json())

    if r.json()["code"] == "OK":
        time.sleep(3)
        data_cohort_status = CheckCohortStatus(r.json()["cohort_uid"], user=request.user)
        response_dict["data_cohort_status"] = data_cohort_status.json()
        print(data_cohort_status.json())
    return HttpResponse(json.dumps(response_dict))


def CheckCohortStatus(cohort_uid, user):
    sent_at = "?sent_at=" + str(int(round(time.time())))
    cohort_status_url = base_url + cohort_api_url + "/" + cohort_uid + str(sent_at)
    print len(cohort_status_url)
    headers = get_headers(cohort_status_url)
    req_obj = RequestLog(request_type='pq', url=cohort_status_url, user=user)
    r = requests.get(cohort_status_url, headers=headers)
    req_obj.response = r.json()
    req_obj.save()
    return r


def LoanApply(request):
    req_dict = {}
    print(request.POST)
    sent_at = "?sent_at=" + str(int(round(time.time())))
    req_dict["loan"] = {}
    # user_profile = UserProfile.objects.get(user=request.user)
    user_profile = ZrUser.objects.get(id=request.user.zr_admin_user.zr_user.id)
    req_dict["loan"]["amount_requested"] = request.POST["loan_amount"]
    req_dict["loan"]["customer_uid"] = random.randint(100, 1000000)
    # req_dict["loan"]["customer_uid"] = "NICT-9d45fb07-5c21-4ef6-9538-94f1c9f3784b"
    req_dict["loan"]["kyc"] = {}
    req_dict["loan"]["kyc"]["mobile"] = request.POST["mobile"]
    req_dict["loan"]["kyc"]["email"] = request.POST["email"]
    req_dict["loan"]["kyc"]["joined_on"] = user_profile.date_joined.strftime('%Y-%m-%d')
    req_dict["loan"]["kyc"]["first_name"] = request.POST["first_name"]
    req_dict["loan"]["kyc"]["last_name"] = request.POST["last_name"]
    req_dict["loan"]["kyc"]["father_name"] = "father_name"
    req_dict["loan"]["kyc"]["pan_card_no"] = request.POST["pan_no"]
    req_dict["loan"]["kyc"]["aadhar_no"] = request.POST["aadhaar_no"]
    req_dict["loan"]["kyc"]["risk_score"] = "999"
    req_dict["loan"]["kyc"]["date_of_birth"] = str(request.POST["dob"])
    req_dict["loan"]["kyc"]["street_address"] = "xyz"
    req_dict["loan"]["kyc"]["locality"] = "xyz"
    req_dict["loan"]["kyc"]["city"] = "mumbai"
    req_dict["loan"]["kyc"]["state"] = "Maha"
    req_dict["loan"]["kyc"]["pincode"] = user_profile.pincode
    req_dict["loan"]["kyc"]["gender"] = user_profile.gender
    req_dict["loan"]["kyc"]["t_consented"] = str(int(round(time.time())))
    req_dict["loan"]["kyc"]["base64_photo"] = base64.b64encode(
        user_profile.profile_photo.read()).decode('utf-8')
    req_dict["loan"]["kyc"]["base64_pan_card"] = base64.b64encode(
        user_profile.pancard_photo.read()).decode('utf-8')
    req_dict["loan"]["kyc"]["base64_aadhar_front"] = base64.b64encode(
        user_profile.aadhaar_photo_front.read()).decode('utf-8')
    req_dict["loan"]["kyc"]["base64_aadhar_back"] = base64.b64encode(
        user_profile.aadhaar_photo_back.read()).decode('utf-8')
    req_dict["loan"]["transaction_summary"] = data_used["cohort"][0]["transaction_summary"]
    req_dict["loan"]["kyc"]["bank_account_name"] = user_profile.first_name
    req_dict["loan"]["kyc"]["bank_ifsc_code"] = "123333"
    req_dict["loan"]["kyc"]["bank_account_number"] = "12344445667"
    loan_create_url = base_url + loans_api_url + sent_at
    headers = get_headers(loan_create_url)
    r = requests.post(loan_create_url, data=json.dumps(req_dict), headers=headers)
    response_from_api = r.json()
    print(response_from_api)
    if response_from_api.get("status") == "OFFERED":
        print(response_from_api["offers"])
        request.session['offer_data'] = response_from_api["offers"]
        return redirect('disburse-a-loan')
    print(r.json())
    return HttpResponse("some error")


# Successful offer
# {'code': 'OK', 'request_ref': '46eb3cda-efbf-4ed6-b88b-c14f2bf9f40c',
# 'customer_uid': '9465561042', 'status': 'OFFERED',
# 'offers': [{'loan_uid': 'PAYWORLD-a64dc0c3-f08a-4fbd-83ce-3611a7c548ea',
# 'amount_offered': 10000.0, 'tenure': '3 days', 'offer_pf': '2%',
# 'offer_interest': '0.2%', 'kyc_status': 'ACCEPT',
# 'tnc': {'link': 'http://ai-analytics-api-staging.herokuapp.com/l/payworld/PAYWORLD-a64dc0c3-f08a-4fbd-83ce-3611a7c548ea',
# 'accepted_via_partner': False}}]}


class DisburseLoan(TemplateView):
    template_name = "disburse.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(DisburseLoan, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DisburseLoan, self).get_context_data(**kwargs)
        context["offer"] = self.request.session['offer_data']
        return context


def AcceptLoan(request):
    bo = request.body.decode("utf-8")
    loan_id = json.loads(bo)["loan_id"]
    time_accept = str(int(round(time.time())))
    sent_at = "?sent_at=" + str(int(round(time.time())))
    disburse_url = base_url + loans_api_url + "/" + loan_id + sent_at
    headers = get_headers(disburse_url)
    request_data = {"loan":
                        {"time_tnc_accepted_via_partner": time_accept}
                    }
    r = requests.put(disburse_url, data=json.dumps(request_data), headers=headers)
    print(r.json())
    response_dict = {"response": r.json()}
    return HttpResponse(json.dumps(response_dict))


def GetLoanStatus(request):
    loan_uid = request.session['offer_data'][0]['loan_uid']
    sent_at = "?sent_at=" + str(int(round(time.time())))
    get_disbursal_url = base_url + disburse_status_url + "/" + loan_uid + sent_at
    headers = get_headers(get_disbursal_url)
    r = requests.get(get_disbursal_url, headers=headers)
    print(r.json())
    response_dict = {"response": r.json()}
    return HttpResponse(json.dumps(response_dict))


class ProjectView(TemplateView):
    template_name = 'project.html'

    def get_context_data(self, **kwargs):
        context = super(ProjectView, self).get_context_data(**kwargs)
        try:
            project = Project.objects.filter(slug=self.kwargs["slug"])
            id_p = project[0].id
            for obj in project:
                obj.fields = dict((field.name, field.value_to_string(obj))
                                  for field in obj._meta.fields)

        except Exception as e:
            print("Fff")
            Project.DoesNotExist
        context["project"] = project
        context["id_p"] = id_p
        return context


def GetRepayments(request, date):
    bo = request.body.decode("utf-8")
    sent_at = "?sent_at=" + str(int(round(time.time())))
    repayment_url_full = base_url + repayment_url + "/" + date + sent_at
    headers = get_headers(repayment_url_full)
    print(repayment_url_full)
    r = requests.get(repayment_url_full, headers=headers)
    print(r.json())
    response_dict = {"response": r.json()}
    return HttpResponse(json.dumps(response_dict))


class LoanStatusView(TemplateView):
    template_name = "loan_status.html"

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        return super(LoanStatusView, self).dispatch(request, *args, **kwargs)


def GetLoanStatusAPI(request, loan_id):
    bo = request.body.decode("utf-8")
    sent_at = "?sent_at=" + str(int(round(time.time())))
    loan_status_url_full = base_url + loan_status_url + "/" + loan_id + sent_at
    headers = get_headers(loan_status_url_full)
    print(loan_status_url_full)
    r = requests.get(loan_status_url_full, headers=headers)
    print(r.json())
    response_dict = {"response": r.json()}
    return HttpResponse(json.dumps(response_dict))
