from django.conf.urls import url

from zrtransaction.views import TransactionsListView, TransactionsDetailView, download_transaction_list_csv

urlpatterns = [
    url(r'^$', TransactionsListView.as_view(), name='transaction-list'),
    url(r'^(?P<pk>\d+)/$', TransactionsDetailView.as_view(), name='transaction-detail'),
    url(r'^distributor_csv/$', download_transaction_list_csv, name="transaction-csv"),
]
