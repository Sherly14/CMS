from django.conf.urls import url

from zrcommission.views import CommissionDisplay

urlpatterns = [
    url(r'^$', CommissionDisplay.as_view(), name='display-commission'),
]
