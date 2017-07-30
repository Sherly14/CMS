from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from zruser.views import DistributorDetailView, DistributorListView, MerchantListView, MerchantDetailView, \
    DistributorCreateView, MerchantCreateView, DashBoardView
from zruser.viewsets import MerchantLeadViewSet

router = DefaultRouter()

router.register(r'^leads', MerchantLeadViewSet)

urlpatterns = router.urls

urlpatterns += [
    url(r'^distributor_list/$', DistributorListView.as_view(), name='distributor-list'),
    url(r'^distributor_details/(?P<pk>\d+)/$', DistributorDetailView.as_view(), name='distributor-details'),
    url(r'^distributor_create/$', DistributorCreateView.as_view(), name='distributor-create'),


    url(r'^merchant_list/$', MerchantListView.as_view(), name='merchant-list'),
    url(r'^merchant_details/(?P<pk>\d+)/$', MerchantDetailView.as_view(), name='merchant-details'),
    url(r'^merchant_create/$', MerchantCreateView.as_view(), name='merchant-create'),

    url(r'^dashboard/$', DashBoardView.as_view(), name='dashboard'),

]
