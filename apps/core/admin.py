from django import forms
from django.contrib import admin

from .models import SiteConfiguration


class SiteConfigurationAdminForm(forms.ModelForm):
    class Meta:
        model = SiteConfiguration
        fields = "__all__"
        widgets = {
            "maintenance_message": forms.Textarea(attrs={"rows": 4}),
            "estimated_end": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    form = SiteConfigurationAdminForm
    list_display = ("maintenance_mode", "maintenance_start", "estimated_end")

    def has_add_permission(self, request):
        return not SiteConfiguration.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
