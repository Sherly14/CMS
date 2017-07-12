from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from zruser.views import DistributorDetailView, DistributorListView, MerchantListView, MerchantDetailView
from zruser.viewsets import MerchantLeadViewSet

router = DefaultRouter()

router.register(r'^leads', MerchantLeadViewSet)

urlpatterns = router.urls

urlpatterns += [
    url(r'^distributor/$', DistributorListView.as_view(), name='distributor'),
    url(r'^distributor_details/(?P<pk>\d+)/$', DistributorDetailView.as_view(), name='distributor-details'),


    url(r'^merchant/$', MerchantListView.as_view(), name='merchant'),
    url(r'^merchant_details/(?P<pk>\d+)/$', MerchantDetailView.as_view(), name='merchant-details')

]
