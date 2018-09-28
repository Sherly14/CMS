from django.conf.urls import url

from loan.views import cohort_pq, PreApproved, loan_apply, DisburseLoan, \
    accept_loan, RepaymentView, get_repayments, \
    LoanStatusView, get_loan_status_disbursal, get_loan_status_request, GetUserLoans, upload_repayments

urlpatterns = [
    url(r'^$', PreApproved.as_view(), name="preapproved"),
    # url(r'^preapproved$', PreApproved.as_view(), name="preapproved"),
    url(r'^loan-apply$', loan_apply, name="loanapply"),
    url(r'^cohort-pq$', cohort_pq, name="cohort-pq"),
    url(r'^loan-disburse$', DisburseLoan.as_view(), name="disburse-a-loan"),
    url(r'^loan-accept$', accept_loan, name="accept-a-loan"),
    url(r'^get-loan-status-disbursal/(?P<auto>.*)$', get_loan_status_disbursal, name="get-loan-status-disbursal"),
    url(r'^repayments$', RepaymentView.as_view(), name="repayment-view"),
    url(r'^get-repayments/(?P<upload>\w+)/(?P<date>.*)/$', get_repayments, name="get-repayments"),
    url(r'^upload-repayments$', upload_repayments, name="upload-repayments"),
    url(r'^loan-status$', LoanStatusView.as_view(), name="status-view"),
    url(r'^get-loan-status-api/(?P<loan_id>.*)$', get_loan_status_request, name="get-loan-status-api"),
    url(r'^user-loans$', GetUserLoans.as_view(), name="user-loans"),
]
