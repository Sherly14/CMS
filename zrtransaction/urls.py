from django.conf.urls import url

from zrtransaction.views import TransactionsListView, TransactionsDetailView

urlpatterns = [
    url(r'^$', TransactionsListView.as_view(), name='transaction-list'),
    url(r'^(?P<pk>\d+)/$', TransactionsDetailView.as_view(), name='transaction-detail')
]
