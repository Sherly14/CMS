from django.conf.urls import url

from loan.views import FrontPage, GetALoan, PreApproved, LoanApply, DisburseLoan, \
    AcceptLoan, GetLoanStatus, ProjectView, RepaymentView, GetRepayments, \
    LoanStatusView, GetLoanStatus, GetLoanStatusAPI

urlpatterns = [
    url(r'^$', FrontPage.as_view(), name="home"),
    url(r'^preapproved$', PreApproved.as_view(), name="preapproved"),
    url(r'^loan-apply$', LoanApply, name="loanapply"),
    url(r'^get-a-loan$', GetALoan, name="get-a-loan"),
    url(r'^loan-disburse$', DisburseLoan.as_view(), name="disburse-a-loan"),
    url(r'^loan-accept$', AcceptLoan, name="accept-a-loan"),
    url(r'^get-loan-status$', GetLoanStatus, name="get-loan-status"),
    url(r'^p/(?P<slug>.*)$', ProjectView.as_view(), name="project-view"),
    url(r'^repayments$', RepaymentView.as_view(), name="repayment-view"),
    url(r'^get-repayments/(?P<date>.*)$', GetRepayments, name="get-repayment"),
    url(r'^loan-status$', LoanStatusView.as_view(), name="status-view"),
    url(r'^get-loan-api-status/(?P<loan_id>.*)$', GetLoanStatusAPI, name="get-loan-status-api"),
]
