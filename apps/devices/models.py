from django.db import models


class MedicalDevice(models.Model):
    device_code=models.CharField(max_length=40,unique=True); product_name=models.CharField(max_length=150); model_name=models.CharField(max_length=100); manufacturer=models.CharField(max_length=150); product_category=models.CharField(max_length=100); approval_number=models.CharField(max_length=80); risk_class=models.CharField(max_length=20); manufacturing_status=models.CharField(max_length=30,default="ACTIVE"); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def __str__(self): return f"{self.product_name} ({self.model_name})"
class DeviceLot(models.Model):
    medical_device=models.ForeignKey(MedicalDevice,on_delete=models.PROTECT,related_name="lots"); lot_number=models.CharField(max_length=80); serial_number=models.CharField(max_length=80,blank=True); manufacture_date=models.DateField(); expiration_date=models.DateField(null=True,blank=True); distribution_date=models.DateField(null=True,blank=True); distribution_location=models.CharField(max_length=150,blank=True); status=models.CharField(max_length=30,default="DISTRIBUTED"); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=["medical_device","lot_number","serial_number"],name="unique_device_lot_serial")]
    def __str__(self): return f"{self.lot_number} / {self.serial_number or '-'}"
