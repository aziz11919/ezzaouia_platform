from django.db import models


class Anomalie(models.Model):
    well_code = models.CharField(max_length=32, blank=True, default="")
    anomaly_type = models.CharField(max_length=120, blank=True, default="")
    severity = models.CharField(max_length=40, blank=True, default="")
    description = models.TextField(blank=True, default="")
    detected_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=40, blank=True, default="")

    class Meta:
        ordering = ["-detected_at"]
        verbose_name = "Anomalie"
        verbose_name_plural = "Anomalies"

    def __str__(self):
        dt = self.detected_at.strftime("%Y-%m-%d %H:%M") if self.detected_at else "-"
        return f"{self.well_code} - {self.severity} - {dt}"

