# models.py
from django.db import models
from django.utils import timezone
from users.models import User

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
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)  # Add this
    phone = models.CharField(max_length=20)  # Add this
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

class Vehicle(models.Model):
    plate_number = models.CharField(max_length=50)
    model = models.CharField(max_length=100)  # Add this
    company = models.ForeignKey(Company, on_delete=models.CASCADE)  # Add this
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)

class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)

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
    status = models.ForeignKey(PackageStatus, on_delete=models.SET_NULL, null=True)
    sender_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='sent_packages')
    receiver_agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='received_packages')
    origin_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='origin_packages')
    destination_branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='destination_packages')
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
    status = models.CharField(max_length=20, choices=[("sent", "Sent"), ("received", "Received"), ("delivered", "Delivered")])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
