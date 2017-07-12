from django.conf.urls import url

from zrpayment.views import MerchantPaymentRequestListView, MerchantPaymentRequestDetailView

urlpatterns = [
    url(r'^$', MerchantPaymentRequestListView.as_view(), name='payment-request-list'),
    url(r'^(?P<pk>\d+)/$', MerchantPaymentRequestDetailView.as_view(), name='payment-request-detail')
]
