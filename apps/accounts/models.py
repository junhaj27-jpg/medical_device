from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "관리자"; RA_QA = "RA_QA", "RA·QA"; STAFF = "STAFF", "직원"
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from django.contrib.auth.models import Group
        group, _ = Group.objects.get_or_create(name=self.role)
        self.groups.set([group])
