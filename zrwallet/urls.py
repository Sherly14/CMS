from django.conf.urls import url

from . import views as zr_wallet_views

urlpatterns = [
    url(r'^passbook/$', zr_wallet_views.PaymentListView.as_view(), name='passbook-list'),
    # url(r'^passbook-csv/$', zr_wallet_views.payments_csv_download, name='passbook-csv'),
]
