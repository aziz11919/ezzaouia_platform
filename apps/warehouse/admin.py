from django.contrib import admin
from .models import (
    DimDate, DimWell, DimPowerType, DimProdMethod,
    DimTypeWell, DimTank, FactDailyProduction, FactWellTest, FactTankLevel
)

class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(DimWell)
class DimWellAdmin(ReadOnlyAdmin):
    list_display  = ('wellcode', 'libelle', 'layer', 'closed', 'prodmethodkey', 'typewellkey')
    list_filter   = ('closed', 'typewellkey', 'prodmethodkey')
    search_fields = ('wellcode', 'libelle')

@admin.register(FactDailyProduction)
class FactDailyProductionAdmin(ReadOnlyAdmin):
    list_display  = ('wellkey', 'datekey', 'dailyoilprodstbd', 'bsw', 'gorscfstb', 'prodhours')
    list_filter   = ('wellkey',)
    search_fields = ('wellkey__wellcode',)

@admin.register(FactWellTest)
class FactWellTestAdmin(ReadOnlyAdmin):
    list_display  = ('wellkey', 'datekey', 'oilbopd', 'testhours', 'gasmscfd', 'waterbwpd', 'gor')
    list_filter   = ('wellkey',)
    search_fields = ('wellkey__wellcode',)

@admin.register(FactTankLevel)
class FactTankLevelAdmin(ReadOnlyAdmin):
    list_display  = ('tankkey', 'datekey', 'volumebbls')
    list_filter   = ('tankkey',)

@admin.register(DimDate)
class DimDateAdmin(ReadOnlyAdmin):
    list_display  = ('fulldate', 'day', 'month', 'year', 'quarter')
    list_filter   = ('year', 'quarter')

@admin.register(DimTank)
class DimTankAdmin(ReadOnlyAdmin):
    list_display = ('tankkey', 'tankcode', 'tankname')

@admin.register(DimPowerType)
class DimPowerTypeAdmin(ReadOnlyAdmin):
    list_display = ('powertypekey', 'powertypecode', 'powertypename')

@admin.register(DimProdMethod)
class DimProdMethodAdmin(ReadOnlyAdmin):
    list_display = ('prodmethodkey', 'prodmethodcode', 'prodmethodname')

@admin.register(DimTypeWell)
class DimTypeWellAdmin(ReadOnlyAdmin):
    list_display = ('typewellkey', 'typewellcode', 'typewellname')