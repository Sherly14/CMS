from django.conf.urls import url

from zrpayment import views as zr_payment_views

urlpatterns = [
    url(r'^$', zr_payment_views.PaymentRequestListView.as_view(), name='payment-request-list'),
    url(r'^payments/$', zr_payment_views.PaymentListView.as_view(), name='payment-list'),
    url(r'^payments-csv/$', zr_payment_views.payments_csv_download, name='payments-csv'),
    url(r'^merchant-payment-req-csv/$', zr_payment_views.merchant_payment_req_csv_download, name='payment-request-csv'),
    url(r'^payment-request-sent/$', zr_payment_views.PaymentRequestSentListView.as_view(), name='payment-request-sent-view'),
    url(r'^refund-request/$', zr_payment_views.RefundRequestView.as_view(), name='refund-request-view'),
    url(r'^(?P<pk>\d+)/$', zr_payment_views.PaymentRequestDetailView.as_view(), name='payment-request-detail'),
    url(r'^generate_payment_request/$', zr_payment_views.GeneratePaymentRequestView.as_view(), name='generate_payment_request'),
    url(r'^generate_topup_request/$', zr_payment_views.GenerateTopUpRequestView.as_view(), name='generate_topup_request'),
    url(r'^accept_payment_request/$', zr_payment_views.AcceptPaymentRequestView.as_view(), name='accept_payment_request'),
    url(r'^reject_payment_request/$', zr_payment_views.RejectPaymentRequestView.as_view(), name='reject_payment_request'),
    url(r'^topup/add/$', zr_payment_views.TopupCreateView.as_view(), name='topup-add'),
]
