from django.conf.urls import url

from zrpayment import views as zr_payment_views

urlpatterns = [
    url(r'^$', zr_payment_views.MerchantPaymentRequestListView.as_view(), name='payment-request-list'),
    url(r'^merchant-payment-req-csv/$', zr_payment_views.merchant_payment_req_csv_download, name='payment-request-csv'),
    url(r'^(?P<pk>\d+)/$', zr_payment_views.MerchantPaymentRequestDetailView.as_view(), name='payment-request-detail')
]
