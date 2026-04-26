"""
Modèles Django mappés sur le Data Warehouse SQL Server EZZAOUIA.
Tous managed=False : Django ne touche jamais au schéma SQL Server.
"""
from django.db import models


class DimDate(models.Model):
    date_key   = models.IntegerField(primary_key=True, db_column='DateKey')
    full_date  = models.DateField(db_column='FullDate')
    day        = models.SmallIntegerField(db_column='Day')
    month      = models.SmallIntegerField(db_column='Month')
    year       = models.SmallIntegerField(db_column='Year')
    quarter    = models.SmallIntegerField(db_column='Quarter')
    month_name = models.CharField(max_length=20, db_column='MonthName')

    class Meta:
        managed = False
        db_table = 'DimDate'

    def __str__(self):
        return str(self.full_date)


class DimPowerType(models.Model):
    power_type_key  = models.IntegerField(primary_key=True, db_column='PowerTypeKey')
    power_type_code = models.IntegerField(db_column='PowerTypeCode')
    power_type_name = models.CharField(max_length=50, db_column='PowerTypeName')

    class Meta:
        managed = False
        db_table = 'DimPowerType'

    def __str__(self):
        return self.power_type_name


class DimProdMethod(models.Model):
    prod_method_key  = models.IntegerField(primary_key=True, db_column='ProdMethodKey')
    prod_method_code = models.IntegerField(db_column='ProdMethodCode')
    prod_method_name = models.CharField(max_length=50, db_column='ProdMethodName')

    class Meta:
        managed = False
        db_table = 'DimProdMethod'

    def __str__(self):
        return self.prod_method_name


class DimTypeWell(models.Model):
    type_well_key  = models.IntegerField(primary_key=True, db_column='TypeWellKey')
    type_well_code = models.IntegerField(db_column='TypeWellCode')
    type_well_name = models.CharField(max_length=50, db_column='TypeWellName')

    class Meta:
        managed = False
        db_table = 'DimTypeWell'

    def __str__(self):
        return self.type_well_name


class DimTank(models.Model):
    tank_key  = models.IntegerField(primary_key=True, db_column='TankKey')
    tank_code = models.CharField(max_length=20, db_column='TankCode')
    tank_name = models.CharField(max_length=50, db_column='TankName')

    class Meta:
        managed = False
        db_table = 'DimTank'

    def __str__(self):
        return f'{self.tank_code} — {self.tank_name}'


class DimWell(models.Model):
    well_key    = models.IntegerField(primary_key=True, db_column='WellKey')
    well_code   = models.CharField(max_length=5, db_column='WellCode')
    libelle     = models.CharField(max_length=100, db_column='Libelle')
    layer       = models.CharField(max_length=50, db_column='Layer')
    closed      = models.CharField(max_length=1, null=True, blank=True, db_column='Closed')
    max_prod    = models.IntegerField(null=True, blank=True, db_column='MaxProd')
    affichable  = models.CharField(max_length=1, null=True, blank=True, db_column='Affichable')
    ordre       = models.IntegerField(null=True, blank=True, db_column='Ordre')
    power_type  = models.ForeignKey(
        'DimPowerType', null=True, blank=True,
        on_delete=models.DO_NOTHING, db_column='PowerTypeKey',
        related_name='wells',
    )
    prod_method = models.ForeignKey(
        'DimProdMethod', null=True, blank=True,
        on_delete=models.DO_NOTHING, db_column='ProdMethodKey',
        related_name='wells',
    )
    type_well   = models.ForeignKey(
        'DimTypeWell', null=True, blank=True,
        on_delete=models.DO_NOTHING, db_column='TypeWellKey',
        related_name='wells',
    )

    class Meta:
        managed = False
        db_table = 'DimWell'
        ordering = ['ordre', 'well_code']

    def __str__(self):
        return f'{self.well_code} — {self.libelle}'

    @property
    def is_active(self):
        return self.closed != 'Y'


class DimWellStatus(models.Model):
    """
    Données opérationnelles journalières par puits.
    Reliée à FactProduction via well_status FK.
    """
    well_status_key  = models.IntegerField(primary_key=True, db_column='WellStatusKey')
    well             = models.ForeignKey(
        'DimWell', on_delete=models.DO_NOTHING,
        db_column='WellKey', related_name='well_statuses',
    )
    date             = models.ForeignKey(
        'DimDate', on_delete=models.DO_NOTHING,
        db_column='DateKey', related_name='well_statuses',
    )
    prod_hours       = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='ProdHours')
    bsw              = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='BSW')
    gor              = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='GOR')
    flow_temp        = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='FlowTempDegF')
    choke            = models.CharField(max_length=100, null=True, blank=True, db_column='Choke16In')
    tubing_psig      = models.CharField(max_length=100, null=True, blank=True, db_column='TubingPsig')
    casing_psig      = models.CharField(max_length=100, null=True, blank=True, db_column='CasingPsig')
    vess_pres        = models.CharField(max_length=100, null=True, blank=True, db_column='VessPresPsig')
    power_fluid      = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='PowerFluidBFPD')
    inj_pre          = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='InjPre')
    manifold         = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='ManifoldDegF')
    water_allocation = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='WaterAllocation')
    remarque         = models.CharField(max_length=255, null=True, blank=True, db_column='Remarque')

    class Meta:
        managed = False
        db_table = 'DimWellStatus'

    def __str__(self):
        return f'{self.well} | {self.date} — BSW:{self.bsw}% GOR:{self.gor}'


class FactProduction(models.Model):
    """
    Faits : production journalière par puits.
    Huile (STB/j) · Gaz (MSCF) · Eau (BWPD).
    BSW / GOR / ProdHours via well_status → DimWellStatus.
    """
    fact_prod_key = models.IntegerField(primary_key=True, db_column='FactProdKey')
    date          = models.ForeignKey(
        'DimDate', on_delete=models.DO_NOTHING,
        db_column='DateKey', related_name='productions',
    )
    well          = models.ForeignKey(
        'DimWell', on_delete=models.DO_NOTHING,
        db_column='WellKey', related_name='productions',
    )
    well_status   = models.ForeignKey(
        'DimWellStatus', on_delete=models.DO_NOTHING,
        db_column='WellStatusKey', null=True, blank=True,
        related_name='productions',
    )
    daily_oil     = models.IntegerField(db_column='DailyOilPerWellSTBD')
    daily_gas     = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='DailyGasPerWellMSCF')
    daily_water   = models.DecimalField(max_digits=18, decimal_places=3, null=True, blank=True, db_column='WellStatusWaterBWPD')

    class Meta:
        managed = False
        db_table = 'FactProduction'
        ordering = ['-date']

    def __str__(self):
        return f'{self.well} | {self.date} | {self.daily_oil} STB/j'


class FactTankLevel(models.Model):
    fact_tank_key = models.IntegerField(primary_key=True, db_column='FactTankKey')
    tank          = models.ForeignKey(
        'DimTank', on_delete=models.DO_NOTHING,
        db_column='TankKey', related_name='tank_levels',
    )
    date          = models.ForeignKey(
        'DimDate', on_delete=models.DO_NOTHING,
        db_column='DateKey', related_name='tank_levels',
    )
    volume_bbls   = models.IntegerField(null=True, blank=True, db_column='VolumeBBLS')

    class Meta:
        managed = False
        db_table = 'FactTankLevel'
        unique_together = (('tank', 'date'),)

    def __str__(self):
        return f'{self.tank} | {self.date} | {self.volume_bbls} BBLS'
