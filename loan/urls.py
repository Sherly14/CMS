from django.conf.urls import url

from loan.views import FrontPage, GetALoan, PreApproved, LoanApply, DisburseLoan, \
    AcceptLoan, GetLoanStatus, ProjectView, RepaymentView, GetRepayments, \
    LoanStatusView, GetLoanStatus, GetLoanStatusAPI

urlpatterns = [
    url(r'^$', FrontPage.as_view(), name="home"),
    url(r'^get_loan/$', GetALoan, name='get-loan'),
]
