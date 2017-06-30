from rest_framework import serializers

from zruser.models import MerchantLead


class MerchantLeadSerializer(serializers.ModelSerializer):
    """Serializer class for Role model"""

    class Meta:
        model = MerchantLead
        fields = ('name', 'email', 'mobile_no')
