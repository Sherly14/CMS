from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from zruser.views import DistributorDetailView, DistributorListView, MerchantListView, MerchantDetailView, \
    DistributorCreateView, MerchantCreateView, DashBoardView, SubDistributorCreateView, SubDistributorListView
from zruser.viewsets import MerchantLeadViewSet
from zruser import views as zr_user_views

router = DefaultRouter()

router.register(r'^leads', MerchantLeadViewSet)

urlpatterns = router.urls

urlpatterns += [
    url(r'^distributor_list/$', DistributorListView.as_view(), name='distributor-list'),
    url(r'^sub_distributor_list/$', SubDistributorListView.as_view(), name='sub-distributor-list'),
    url(r'^distributor_details/(?P<pk>\d+)/$', DistributorDetailView.as_view(), name='distributor-details'),
    url(r'^distributor_create/$', DistributorCreateView.as_view(), name='distributor-create'),
    url(r'^distributor_csv/$', zr_user_views.download_distributor_list_csv, name="distributor-csv"),

    url(r'^sub_distributor_create/$', SubDistributorCreateView.as_view(), name='sub-distributor-create'),

    url(r'^kyc_requests/$', zr_user_views.KYCRequestsView.as_view(), name='kyc-requests'),

    url(r'^merchant_list/$', MerchantListView.as_view(), name='merchant-list'),
    url(r'^merchant_details/(?P<pk>\d+)/$', MerchantDetailView.as_view(), name='merchant-details'),
    url(r'^merchant_create/$', MerchantCreateView.as_view(), name='merchant-create'),
    url(r'^merchant_csv/$', zr_user_views.get_merchant_csv, name='merchant-csv'),
    url(r'^get_report_excel/$', zr_user_views.get_report_excel, name='get-report-excel'),

    url(r'^dashboard/$', DashBoardView.as_view(), name='dashboard'),
    url(r'^mail_report/$', zr_user_views.mail_report, name='user_mail_report'),

]
