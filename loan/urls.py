from django.conf.urls import url

from loan.views import create_cohort_get_pq_user, PreApproved, loan_apply, DisburseLoan, \
    accept_loan, RepaymentView, get_repayments, \
    LoanStatusView, get_loan_status, get_loan_status_request, GetUserLoans, upload_repayments, \
    create_cohort_get_pq_all

urlpatterns = [
    url(r'^$', PreApproved.as_view(), name="preapproved"),
    # url(r'^preapproved$', PreApproved.as_view(), name="preapproved"),
    url(r'^loan-apply$', loan_apply, name="loanapply"),
    url(r'^create-cohort-get-pq-user$', create_cohort_get_pq_user, name="create-cohort-get-pq-user"),
    url(r'^create-cohort-get-pq-all$', create_cohort_get_pq_all, name="create-cohort-get-pq-all"),
    url(r'^loan-disburse$', DisburseLoan.as_view(), name="disburse-a-loan"),
    url(r'^loan-accept$', accept_loan, name="accept-a-loan"),
    url(r'^get-loan-status$', get_loan_status, name="get-loan-status"),
    # url(r'^p/(?P<slug>.*)$', ProjectView.as_view(), name="project-view"),
    url(r'^repayments$', RepaymentView.as_view(), name="repayment-view"),
    url(r'^get-repayments/(?P<date>.*)$', get_repayments, name="get-repayment"),
    url(r'^upload-repayments$', upload_repayments, name="upload-repayments"),
    url(r'^loan-status$', LoanStatusView.as_view(), name="status-view"),
    url(r'^get-loan-status-api/(?P<loan_id>.*)$', get_loan_status_request, name="get-loan-status-api"),
    url(r'^user-loans$', GetUserLoans.as_view(), name="user-loans"),
]
