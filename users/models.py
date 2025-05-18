from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True) 
    
    def __str__(self):
        return self.name

class Permission(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('role', 'permission')
    
    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"

class User(AbstractUser):
    full_name = models.CharField(
        max_length=255,
        verbose_name="Full Name",
        help_text="The full name of the user."
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        db_index=True,
        verbose_name="Role",
        help_text="The role assigned to the user."
    )
    company = models.ForeignKey(
        'packages.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Company",
        help_text="The company the user belongs to."
    )
    branch = models.ForeignKey(
        'packages.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Branch",
        help_text="The branch the user belongs to."
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Email Address",
        help_text="The email address of the user."
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Username",
        help_text="The username of the user."
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['id']  # Default ordering by ID

    def __str__(self):
        return self.username or self.email or "Unnamed User"

