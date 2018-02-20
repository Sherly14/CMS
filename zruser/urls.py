from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from zruser import views as zr_user_views
from zruser.views import DistributorDetailView, DistributorListView, MerchantListView, MerchantDetailView, \
                        DistributorCreateView, MerchantCreateView, DashBoardView, SubDistributorCreateView, \
                        SubDistributorListView, UserUpdateView, RetailerCreateView, RetailerListView, \
                        TerminalCreateView, TerminalListView, UserCardCreateView, UserCardListView
from zruser.viewsets import MerchantLeadViewSet

router = DefaultRouter()

router.register(r'^leads', MerchantLeadViewSet)

urlpatterns = router.urls

urlpatterns += [
    url(r'^distributor_list/$', DistributorListView.as_view(), name='distributor-list'),
    url(r'^sub_distributor_list/$', SubDistributorListView.as_view(), name='sub-distributor-list'),
    url(r'^distributor_details/(?P<pk>\d+)/$', DistributorDetailView.as_view(), name='distributor-details'),
    url(r'^update/(?P<pk>\d+)/$', UserUpdateView.as_view(), name='user-update'),
    url(r'^distributor_create/$', DistributorCreateView.as_view(), name='distributor-create'),
    url(r'^distributor_csv/$', zr_user_views.download_distributor_list_csv, name="distributor-csv"),
    # url used in sub distributor csv create page do not remove it
    url(r'^sub_distributor_csv/$', zr_user_views.download_sub_distributor_list_csv, name="sub-distributor-csv"),

    url(r'^sub_distributor_create/$', SubDistributorCreateView.as_view(), name='sub-distributor-create'),

    url(r'^kyc_requests/$', zr_user_views.KYCRequestsView.as_view(), name='kyc-requests'),

    url(r'^merchant_list/$', MerchantListView.as_view(), name='merchant-list'),
    url(r'^merchant_details/(?P<pk>\d+)/$', MerchantDetailView.as_view(), name='merchant-details'),
    url(r'^merchant_create/$', MerchantCreateView.as_view(), name='merchant-create'),
    url(r'^merchant_csv/$', zr_user_views.get_merchant_csv, name='merchant-csv'),
    # url(r'^get_report_excel/$', zr_user_views.get_report_excel, name='get-report-excel'),

    url(r'^dashboard/$', DashBoardView.as_view(), name='dashboard'),
    url(r'^mail_report/$', zr_user_views.mail_report, name='user_mail_report'),
    url(r'^retailer_create/$', RetailerCreateView.as_view(), name='retailer-create'),
    url(r'^retailer_list/$', RetailerListView.as_view(), name='retailer-list'),
    url(r'^retailer_csv/$', zr_user_views.download_retailer_list_csv, name="retailer-csv"),
    url(r'^terminal_create/$', TerminalCreateView.as_view(), name='terminal-create'),
    url(r'^terminal_list/$', TerminalListView.as_view(), name='terminal-list'),
    url(r'^terminal_csv/$', zr_user_views.download_terminal_list_csv, name="terminal-csv"),
    url(r'^loyaltycards_create/$', UserCardCreateView.as_view(), name='card-create'),
    url(r'^loyaltycard_list/$', UserCardListView.as_view(), name='loyaltycard-list')
]
