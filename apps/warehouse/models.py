from django.db import models

class DimDate(models.Model):
    datekey   = models.IntegerField(db_column='DateKey', primary_key=True)
    fulldate  = models.DateField(db_column='FullDate')
    day       = models.SmallIntegerField(db_column='Day')
    month     = models.SmallIntegerField(db_column='Month')
    year      = models.SmallIntegerField(db_column='Year')
    quarter   = models.SmallIntegerField(db_column='Quarter')
    monthname = models.CharField(db_column='MonthName', max_length=20)
    class Meta:
        managed = False
        db_table = 'DimDate'
    def __str__(self):
        return str(self.fulldate)

class DimPowerType(models.Model):
    powertypekey  = models.AutoField(db_column='PowerTypeKey', primary_key=True)
    powertypecode = models.IntegerField(db_column='PowerTypeCode')
    powertypename = models.CharField(db_column='PowerTypeName', max_length=50)
    class Meta:
        managed = False
        db_table = 'DimPowerType'
    def __str__(self):
        return self.powertypename

class DimProdMethod(models.Model):
    prodmethodkey  = models.AutoField(db_column='ProdMethodKey', primary_key=True)
    prodmethodcode = models.IntegerField(db_column='ProdMethodCode')
    prodmethodname = models.CharField(db_column='ProdMethodName', max_length=50)
    class Meta:
        managed = False
        db_table = 'DimProdMethod'
    def __str__(self):
        return self.prodmethodname

class DimTypeWell(models.Model):
    typewellkey  = models.AutoField(db_column='TypeWellKey', primary_key=True)
    typewellcode = models.IntegerField(db_column='TypeWellCode')
    typewellname = models.CharField(db_column='TypeWellName', max_length=50)
    class Meta:
        managed = False
        db_table = 'DimTypeWell'
    def __str__(self):
        return self.typewellname

class DimTank(models.Model):
    tankkey  = models.AutoField(db_column='TankKey', primary_key=True)
    tankcode = models.CharField(db_column='TankCode', max_length=20)
    tankname = models.CharField(db_column='TankName', max_length=50)
    class Meta:
        managed = False
        db_table = 'DimTank'
    def __str__(self):
        return self.tankname

class DimWell(models.Model):
    wellkey      = models.AutoField(db_column='WellKey', primary_key=True)
    wellcode     = models.CharField(db_column='WellCode', max_length=5)
    libelle      = models.CharField(db_column='Libelle', max_length=100)
    layer        = models.CharField(db_column='Layer', max_length=50)
    closed       = models.CharField(db_column='Closed', max_length=1, blank=True, null=True)
    maxprod      = models.IntegerField(db_column='MaxProd', blank=True, null=True)
    affichable   = models.CharField(db_column='Affichable', max_length=1, blank=True, null=True)
    ordre        = models.IntegerField(db_column='Ordre', blank=True, null=True)
    powertypekey  = models.ForeignKey(DimPowerType,  on_delete=models.DO_NOTHING, db_column='PowerTypeKey',  blank=True, null=True, related_name='wells')
    prodmethodkey = models.ForeignKey(DimProdMethod, on_delete=models.DO_NOTHING, db_column='ProdMethodKey', blank=True, null=True, related_name='wells')
    typewellkey   = models.ForeignKey(DimTypeWell,   on_delete=models.DO_NOTHING, db_column='TypeWellKey',   blank=True, null=True, related_name='wells')
    class Meta:
        managed = False
        db_table = 'DimWell'
        ordering = ['ordre', 'wellcode']
    def __str__(self):
        return f'{self.wellcode} — {self.libelle}'
    @property
    def is_active(self):
        return self.closed != 'Y'

class FactDailyProduction(models.Model):
    factprodkey         = models.AutoField(db_column='FactProdKey', primary_key=True)
    wellkey             = models.ForeignKey(DimWell, on_delete=models.DO_NOTHING, db_column='WellKey', related_name='daily_productions')
    datekey             = models.ForeignKey(DimDate, on_delete=models.DO_NOTHING, db_column='DateKey', related_name='daily_productions')
    dailyoilprodstbd    = models.IntegerField(db_column='DailyOilProdSTBD')
    dailywaterprodblsd  = models.IntegerField(db_column='DailyWaterProdBLSD', blank=True, null=True)
    dailygasprodmscf    = models.IntegerField(db_column='DailyGasProdMSCF', blank=True, null=True)
    prodhours           = models.DecimalField(db_column='ProdHours', max_digits=18, decimal_places=3, blank=True, null=True)
    flowtempdegf        = models.IntegerField(db_column='FlowTempDegF', blank=True, null=True)
    bsw                 = models.DecimalField(db_column='BSW', max_digits=18, decimal_places=3, blank=True, null=True)
    wellstatuswaterbwpd = models.DecimalField(db_column='WellStatusWaterBWPD', max_digits=18, decimal_places=3, blank=True, null=True)
    gorscfstb           = models.IntegerField(db_column='GORSCFSTB', blank=True, null=True)
    cumoilstbcorrected  = models.IntegerField(db_column='CumOilStbCorrected', blank=True, null=True)
    cumwaterbbls        = models.IntegerField(db_column='CumWaterBBLS', blank=True, null=True)
    cumgasmscf          = models.IntegerField(db_column='CumGasMSCF', blank=True, null=True)
    sales               = models.DecimalField(db_column='Sales', max_digits=18, decimal_places=3, blank=True, null=True)
    fuel                = models.DecimalField(db_column='Fuel', max_digits=18, decimal_places=3, blank=True, null=True)
    lifting             = models.IntegerField(db_column='Lifting', blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'FactDailyProduction'
        unique_together = (('wellkey', 'datekey'),)
        ordering = ['-datekey']
    def __str__(self):
        return f'{self.wellkey} | {self.datekey} | {self.dailyoilprodstbd} STB/j'

class FactTankLevel(models.Model):
    facttankkey = models.AutoField(db_column='FactTankKey', primary_key=True)
    tankkey     = models.ForeignKey(DimTank, on_delete=models.DO_NOTHING, db_column='TankKey', related_name='tank_levels')
    datekey     = models.ForeignKey(DimDate, on_delete=models.DO_NOTHING, db_column='DateKey', related_name='tank_levels')
    volumebbls  = models.IntegerField(db_column='VolumeBBLS', blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'FactTankLevel'
        unique_together = (('tankkey', 'datekey'),)
    def __str__(self):
        return f'{self.tankkey} | {self.datekey} | {self.volumebbls} BBLS'

class FactWellTest(models.Model):
    facttestkey = models.AutoField(db_column='FactTestKey', primary_key=True)
    wellkey     = models.ForeignKey(DimWell, on_delete=models.DO_NOTHING, db_column='WellKey', related_name='well_tests')
    datekey     = models.ForeignKey(DimDate, on_delete=models.DO_NOTHING, db_column='DateKey', related_name='well_tests')
    testhours   = models.IntegerField(db_column='TestHours')
    oilbopd     = models.IntegerField(db_column='OilBOPD', blank=True, null=True)
    waterbwpd   = models.DecimalField(db_column='WaterBWPD', max_digits=18, decimal_places=3)
    gasmscfd    = models.IntegerField(db_column='GasMSCFD')
    gor         = models.IntegerField(db_column='GOR', blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'FactWellTest'
        unique_together = (('wellkey', 'datekey'),)
        ordering = ['-datekey']
    def __str__(self):
        return f'Test {self.wellkey} | {self.datekey}'