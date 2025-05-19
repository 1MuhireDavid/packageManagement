from rest_framework import serializers
from .models import *
from django.utils import timezone

class PackageSerializer(serializers.ModelSerializer):
    # Add these fields for handling in the API but don't save to model
    driver = serializers.PrimaryKeyRelatedField(
        queryset=Driver.objects.all(), 
        write_only=True,
        required=False
    )
    vehicle = serializers.PrimaryKeyRelatedField(
        queryset=Vehicle.objects.all(), 
        write_only=True,
        required=False
    )
    departure_time = serializers.DateTimeField(
        write_only=True,
        required=False
    )
    receiver_name = serializers.CharField(
        write_only=True,
        required=False
    )
    receiver_phone = serializers.CharField(
        write_only=True,
        required=False
    )
    sender_name = serializers.CharField(
        write_only=True,
        required=False
    )
    sender_phone = serializers.CharField(
        write_only=True,
        required=False
    )
    status = serializers.ChoiceField(choices=STATUS_CHOICES, read_only=True)

    sending_agent_name = serializers.SerializerMethodField()
    receiving_agent_name = serializers.SerializerMethodField()
    delivery_agent_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Package
        fields = [
            'id', 'tracking_number', 'name', 'weight', 'value', 'shipping_fee',
            'category', 'status', 'sender_agent', 'receiver_agent',
            'origin_branch', 'destination_branch', 'created_at', 'updated_at',
            'driver', 'vehicle', 'departure_time',
            'receiver_name', 'receiver_phone', 'sender_name', 'sender_phone',
            'sending_agent', 'sending_agent_name', 'sent_at',
            'receiving_agent', 'receiving_agent_name', 'received_at',
            'delivery_agent', 'delivery_agent_name', 'delivered_at'
        ]
        read_only_fields = ['tracking_number', 'sender_agent', 'origin_branch', 
                           'shipping_fee', 'status', 'created_at', 'updated_at',
                           'sending_agent', 'sent_at', 'receiving_agent', 'received_at',
                            'delivery_agent', 'delivered_at'
                            
                    ]
                    
    def get_receiver_agent_name(self, obj):
            return obj.receiver_agent.username if obj.receiver_agent else None
    
    def get_sending_agent_name(self, obj):
        return obj.sending_agent.username if obj.sending_agent else None
    
    def get_receiving_agent_name(self, obj):
        return obj.receiving_agent.username if obj.receiving_agent else None
    
    def get_delivery_agent_name(self, obj):
        return obj.delivery_agent.username if obj.delivery_agent else None


    def create(self, validated_data):
        driver = validated_data.pop('driver', None)
        vehicle = validated_data.pop('vehicle', None)
        departure_time = validated_data.pop('departure_time', None)
        
        # Create the package with only the fields that belong to the Package model
        package = Package.objects.create(**validated_data)
        
        # Store the extra fields in the serializer context for use in the view
        self.context['driver'] = driver
        self.context['vehicle'] = vehicle
        self.context['departure_time'] = departure_time
        
        return package

    
class TicketSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=STATUS_CHOICES, read_only=True)
    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_departure_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Departure time must be in the future.")
        return value

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
        fields = ['id', 'name', 'license_number', 'phone', 'company']
        read_only_fields = ['id']

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'