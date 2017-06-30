from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from zruser.views import SampleView
from zruser.viewsets import MerchantLeadViewSet

router = DefaultRouter()

router.register(r'^leads', MerchantLeadViewSet)

urlpatterns = router.urls

urlpatterns += [
    url(r'^sample/(?P<pk>\d+)/$', SampleView.as_view(), name='sample')
]
