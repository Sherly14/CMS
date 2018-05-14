from django.conf.urls import url

from zrcommission.views import CommissionDisplay, get_comission_csv, SettleCommission

urlpatterns = [
    url(r'^$', CommissionDisplay.as_view(), name='display-commission'),
    url(r'^commission-csv/$', get_comission_csv, name='commission-request-csv'),
    url(r'^settle_commission/$', SettleCommission.as_view(), name='settle_commission')
]
