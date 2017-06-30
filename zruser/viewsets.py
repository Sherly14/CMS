from rest_framework import mixins
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet

from zruser.models import MerchantLead
from zruser.serializers import MerchantLeadSerializer


class MerchantLeadViewSet(GenericViewSet, mixins.CreateModelMixin):
    """ViewSet class for Role model"""

    permission_classes = [AllowAny]
    queryset = MerchantLead.objects.all()
    serializer_class = MerchantLeadSerializer
