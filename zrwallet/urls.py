from django.conf.urls import url

from . import views as zr_wallet_views

urlpatterns = [
    url(r'^passbook/$', zr_wallet_views.PassbookListView.as_view(), name='passbook-list'),
    url(r'^passbook-csv/$', zr_wallet_views.get_passbook_report_csv, name='passbook-csv'),
    url(r'^update_transaction/$', zr_wallet_views.set_closing_balance, name='closing-balance'),
]
