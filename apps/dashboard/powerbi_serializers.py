from rest_framework import serializers
from .powerbi_models import PowerBIReport


class PowerBIReportSerializer(serializers.ModelSerializer):
    class Meta:
        model  = PowerBIReport
        fields = ['id', 'title', 'description', 'embed_url', 'icon', 'role', 'order']
