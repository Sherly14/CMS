from django.conf.urls import url

from zruser.views import SampleView

urlpatterns = [
    url(r'^sample/(?P<pk>\d+)/$', SampleView.as_view(), name='sample'),
]
