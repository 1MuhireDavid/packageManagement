# models.py
from django.db import models
from django.utils import timezone
from users.models import User

STATUS_CHOICES = [
    ("pending", "Pending"),
    ("sent", "Sent"),
    ("received", "Received"),
    ("delivered", "Delivered"),
]

class Company(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)  # Add this
    phone = models.CharField(max_length=20)     # Add this
    email = models.EmailField()                 # Add this

class Branch(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

class Category(models.Model):
    name = models.CharField(max_length=255)

class Driver(models.Model):
    name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.license_number})"

class Vehicle(models.Model):
    plate_number = models.CharField(max_length=50)
    model = models.CharField(max_length=100)  # Add this
    company = models.ForeignKey(Company, on_delete=models.CASCADE)  # Add this
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)


class PackageStatus(models.Model):
    name = models.CharField(max_length=50)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class Package(models.Model):
    tracking_number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    weight = models.FloatField()
    value = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    sender_agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_packages')
    receiver_agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_packages', null=True)
    sending_agent = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='processed_sent_packages', null=True, blank=True)
    receiving_agent = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='processed_received_packages', null=True, blank=True)
    delivery_agent = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='processed_delivered_packages', null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    origin_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='origin_packages')
    destination_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='destination_packages')
    sender_name = models.CharField(max_length=255)
    sender_phone = models.CharField(max_length=20)
    receiver_name = models.CharField(max_length=255)
    receiver_phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Ticket(models.Model):
    ticket_code = models.CharField(max_length=20, unique=True)
    package = models.OneToOneField(Package, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    departure_time = models.DateTimeField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
