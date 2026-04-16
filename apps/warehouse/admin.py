from django.contrib import admin
from .models import (
    DimDate, DimWell, DimWellStatus, DimPowerType, DimProdMethod,
    DimTypeWell, DimTank, FactProduction, FactTankLevel,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):               return False
    def has_change_permission(self, request, obj=None):  return False
    def has_delete_permission(self, request, obj=None):  return False


@admin.register(DimWell)
class DimWellAdmin(ReadOnlyAdmin):
    list_display  = ('well_code', 'libelle', 'layer', 'closed', 'prod_method', 'type_well')
    list_filter   = ('closed', 'type_well', 'prod_method')
    search_fields = ('well_code', 'libelle')


@admin.register(DimWellStatus)
class DimWellStatusAdmin(ReadOnlyAdmin):
    list_display  = ('well', 'date', 'prod_hours', 'bsw', 'gor', 'flow_temp')
    list_filter   = ('well',)
    search_fields = ('well__well_code',)


@admin.register(FactProduction)
class FactProductionAdmin(ReadOnlyAdmin):
    list_display  = ('well', 'date', 'daily_oil', 'daily_gas', 'daily_water')
    list_filter   = ('well',)
    search_fields = ('well__well_code',)


@admin.register(FactTankLevel)
class FactTankLevelAdmin(ReadOnlyAdmin):
    list_display  = ('tank', 'date', 'volume_bbls')
    list_filter   = ('tank',)


@admin.register(DimDate)
class DimDateAdmin(ReadOnlyAdmin):
    list_display  = ('full_date', 'day', 'month', 'year', 'quarter')
    list_filter   = ('year', 'quarter')


@admin.register(DimTank)
class DimTankAdmin(ReadOnlyAdmin):
    list_display = ('tank_key', 'tank_code', 'tank_name')


@admin.register(DimPowerType)
class DimPowerTypeAdmin(ReadOnlyAdmin):
    list_display = ('power_type_key', 'power_type_code', 'power_type_name')


@admin.register(DimProdMethod)
class DimProdMethodAdmin(ReadOnlyAdmin):
    list_display = ('prod_method_key', 'prod_method_code', 'prod_method_name')


@admin.register(DimTypeWell)
class DimTypeWellAdmin(ReadOnlyAdmin):
    list_display = ('type_well_key', 'type_well_code', 'type_well_name')
