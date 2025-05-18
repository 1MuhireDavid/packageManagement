# serializers.py
from rest_framework import serializers
from .models import *

class PackageSerializer(serializers.ModelSerializer):
    driver_id = serializers.PrimaryKeyRelatedField(queryset=Driver.objects.all(), write_only=True)
    vehicle_id = serializers.PrimaryKeyRelatedField(queryset=Vehicle.objects.all(), write_only=True)
    departure_time = serializers.DateTimeField(write_only=True)

    class Meta:
        model = Package
        fields = '__all__'
        read_only_fields = ['tracking_number', 'created_at', 'updated_at']

    def validate_departure_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Departure time must be in the future.")
        return value

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class PackageStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageStatus
        fields = '__all__'
        read_only_fields = ['updated_by', 'updated_at']

# Other serializers remain the same:
class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class AgentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=4))
    class Meta:
        model = Agent
        fields = ['id', 'user', 'branch']
    def validate(self, data):
        if data['user'].company != data['branch'].company:
            raise serializers.ValidationError("User's company must match branch's company.")
        return data
