from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import uuid
import logging
from django.contrib.auth.models import User
from users.serializers import UserSerializer
from .models import (
    Package, PackageStatus, Ticket, Company, Branch, Driver,
    Vehicle, Category
)
from .serializers import PackageSerializer, PackageStatusSerializer, TicketSerializer, CompanySerializer, BranchSerializer, DriverSerializer, VehicleSerializer, CategorySerializer
from users.permissions import IsAgent, IsSystemAdmin, IsCompanyAdmin, IsBranchAdmin
from decimal import Decimal,InvalidOperation

logger = logging.getLogger(__name__)

class PackageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing packages.
    
    Provides CRUD operations for packages with role-based permissions.
    """
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-created_at']
    
    def get_permissions(self):
        """
        Return custom permissions based on the requested action.
        """
        if self.action == 'create':
            return [IsAuthenticated(), IsAgent()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAgent()]
        return [IsAuthenticated()]

    def get_agent(self):
        """
        Get the agent associated with the current user.
        """
        user = self.request.user
        if user.role and user.role.name.lower() == "agent":
            return user
        return None

    def get_pending_status(self):
        """
        Get or create the 'Pending' package status.
        """
        return PackageStatus.objects.get_or_create(
            name="Pending", 
            defaults={"updated_by": self.request.user}
        )[0]

    def get_queryset(self):
        """
        Return a queryset filtered based on the user's role.
        """
        if getattr(self, 'swagger_fake_view', False):
            return Package.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return Package.objects.none()

        # If user is an agent
        if user.role and user.role.name.lower() == 'agent':
            return Package.objects.filter(
                Q(sender_agent=user) |
                Q(receiver_agent=user) |
                Q(destination_branch=user.branch)
            ).select_related(
                'status', 'category', 'sender_agent', 'receiver_agent',
                'origin_branch', 'destination_branch'
            )
                
        # If user is a branch admin
        if user.role and user.role.name.lower() == 'branch admin' and hasattr(user, 'branch'):
            return Package.objects.filter(
                Q(origin_branch=user.branch) | Q(destination_branch=user.branch)
            ).select_related(
                'status', 'category', 'sender_agent', 'receiver_agent',
                'origin_branch', 'destination_branch'
            )

        # If user is a company admin
        if user.role and user.role.name.lower() == 'company admin' and hasattr(user, 'company'):
            return Package.objects.filter(
                Q(origin_branch__company=user.company) | 
                Q(destination_branch__company=user.company)
            ).select_related(
                'status', 'category', 'sender_agent', 'receiver_agent',
                'origin_branch', 'destination_branch'
            )

        # System admin or fallback
        if user.role and user.role.name.lower() == 'system admin':
            return Package.objects.all().select_related(
                'status', 'category', 'sender_agent', 'receiver_agent',
                'origin_branch', 'destination_branch'
            )
            
        return Package.objects.none()

    def list(self, request, *args, **kwargs):
        """
        List all packages the user has access to based on their role.
        """
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=PackageSerializer,
        responses={
            status.HTTP_201_CREATED: PackageSerializer,
            status.HTTP_400_BAD_REQUEST: "Bad request",
            status.HTTP_401_UNAUTHORIZED: "Unauthorized",
            status.HTTP_403_FORBIDDEN: "Forbidden"
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new package.
        
        Only agents can create packages. A corresponding ticket will be created automatically.
        """
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """
        Handle the package creation process including validation and related ticket creation.
        """
        agent_user = self.request.user
        if not agent_user.role or agent_user.role.name.lower() != "agent":
            raise PermissionDenied("Only agents can create packages.")

        # Extract and validate data
        data = self.request.data
        destination_branch = serializer.validated_data.get('destination_branch')

        # Get driver, vehicle and departure_time from request data
        driver_id = data.get('driver')
        vehicle_id = data.get('vehicle')
        departure_time_str = data.get('departure_time')
        sender_name = serializer.validated_data.get('sender_name')
        sender_phone = serializer.validated_data.get('sender_phone')
        receiver_name = serializer.validated_data.get('receiver_name')
        receiver_phone = serializer.validated_data.get('receiver_phone')

        if not sender_name or not sender_phone:
            raise ValidationError({"sender_details": "Sender name and phone are required."})
        
        if not receiver_name or not receiver_phone:
            raise ValidationError({"receiver_details": "Receiver name and phone are required."})
        
        if not destination_branch:
            raise ValidationError({"destination_branch": "This field is required."})
            
        if destination_branch.company != agent_user.company:
            raise ValidationError({"destination_branch": "Destination branch must belong to your company."})

        # Validate driver belongs to the right branch/company
        try:
            driver = Driver.objects.get(id=driver_id)
        except (Driver.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"driver": "Driver is required."})
        
        if driver.company != agent_user.company:
            raise ValidationError({"driver": "Driver must belong to your company."})

        # Validate vehicle belongs to the specified driver
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except (Vehicle.DoesNotExist, ValueError, TypeError):
            raise ValidationError({"vehicle": "Vehicle is required."})
        
        if vehicle.company != agent_user.company:
            raise ValidationError("Vehicle must belong to your company.")

        
        try:
            departure_time = timezone.datetime.fromisoformat(departure_time_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError, TypeError):
            raise ValidationError({"departure_time": "Departure time is required in valid ISO format."})
        
        if departure_time <= timezone.now():
            raise ValidationError({"departure_time": "Departure time must be in the future."})

        # Generate tracking number and calculate shipping fee
        tracking_number = f"PKG-{uuid.uuid4().hex[:8].upper()}"
        value_str = serializer.validated_data.get('value', '0')
        try:
            value = Decimal(str(value_str))
        except InvalidOperation:
            raise ValidationError({'value': 'Invalid numeric value.'})

        shipping_fee = round(value * Decimal('0.10'), 2)
        
        try:
            # Save the package
            package = serializer.save(
                tracking_number=tracking_number,
                origin_branch=agent_user.branch,
                sender_agent=agent_user,
                status=self.get_pending_status(),
                shipping_fee=shipping_fee
            )
            
            # Create corresponding ticket
            ticket = Ticket.objects.create(
                ticket_code=f"TCK-{uuid.uuid4().hex[:6].upper()}",
                package=package,
                driver=driver,
                vehicle=vehicle,
                branch=agent_user.branch,
                company=agent_user.company,
                departure_time=departure_time,
                amount_paid=shipping_fee,
                status="sent"
            )
            
            logger.info(
                f"Package {package.tracking_number} created by agent {agent_user.username} "
                f"with ticket {ticket.ticket_code}"
            )
            
        except Exception as e:
            logger.error(f"Error creating package: {str(e)}")
            raise ValidationError({"error": f"Failed to create package: {str(e)}"})

    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: PackageSerializer,
            status.HTTP_404_NOT_FOUND: "Not found"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific package by ID.
        """
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='mark_delivered')
    def mark_delivered(self, request, pk=None):
        """
        Mark a package as delivered.
        
        Only agents at the destination branch can mark a package as delivered.
        """
        package = self.get_object()
        agent = self.get_agent()
        
        if not agent:
            raise PermissionDenied("Only agents can mark packages as delivered.")
            
        if package.destination_branch != agent.branch:
            raise PermissionDenied("Only agents at the destination branch can mark packages as delivered.")
            
        # Get or create 'Delivered' status
        delivered_status = PackageStatus.objects.get_or_create(
            name="Delivered",
            defaults={"updated_by": request.user}
        )[0]
        
        package.status = delivered_status
        package.receiver_agent = agent
        package.save()
        
        # Update corresponding ticket
        try:
            ticket = Ticket.objects.get(package=package)
            ticket.status = "delivered"
            ticket.updated_at = timezone.now()
            ticket.save()
        except Ticket.DoesNotExist:
            logger.warning(f"No ticket found for package {package.tracking_number}")
        
        return Response({"status": "Package marked as delivered"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        List all pending packages for the current user.
        """
        pending_status = PackageStatus.objects.filter(name__iexact="Pending").first()
        if not pending_status:
            return Response([], status=status.HTTP_200_OK)
            
        queryset = self.get_queryset().filter(status=pending_status)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search_by_tracking(self, request):
        """
        Search for a package by tracking number.
        """
        tracking_number = request.query_params.get('tracking_number', None)
        if not tracking_number:
            return Response(
                {"error": "Tracking number is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            package = self.get_queryset().get(tracking_number=tracking_number)
            serializer = self.get_serializer(package)
            return Response(serializer.data)
        except Package.DoesNotExist:
            return Response(
                {"error": "Package not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class PackageStatusViewSet(viewsets.ModelViewSet):
    queryset = PackageStatus.objects.all()
    serializer_class = PackageStatusSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user, updated_at=timezone.now())


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.select_related('package', 'driver', 'vehicle').all()
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        elif user.role and user.role.name.lower() == 'agent':
            return self.queryset.filter(company=user.company)
        elif user.role and user.role.name.lower() == 'branch admin':
            return self.queryset.filter(branch=user.branch)
        elif user.role and user.role.name.lower() == 'company admin':
            return self.queryset.filter(company=user.company)
        else:
            return Ticket.objects.none()

    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        ticket = self.get_object()
        new_status = request.data.get('status')
        valid_statuses = ['sent', 'received', 'delivered']

        if new_status not in valid_statuses:
            raise ValidationError({"status": f"Status must be one of {valid_statuses}"})

        ticket.status = new_status
        ticket.save()

        return Response({'message': f'Ticket status updated to {new_status}'}, status=status.HTTP_200_OK)


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated | IsSystemAdmin | IsCompanyAdmin]


class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated | IsBranchAdmin | IsCompanyAdmin]


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [IsBranchAdmin | IsCompanyAdmin | IsAgent | IsSystemAdmin]
    
    def get_queryset(self):
        """Filter drivers based on user's company"""
        user = self.request.user
        
        # System admin can see all drivers
        if user.role and user.role.name.lower() == 'system admin':
            return Driver.objects.all()
            
        # Company admins, branch admins and agents see drivers from their company
        if hasattr(user, 'company') and user.company:
            return Driver.objects.filter(company=user.company)
            
        return Driver.objects.none()
    
    def perform_create(self, serializer):
        """Auto-assign company based on the authenticated user's company"""
        user = self.request.user
        
        # If the user is a system admin and company is provided, use that
        if user.role and user.role.name.lower() == 'system admin':
            # Use the company from request data
            return serializer.save()
            
        # For company admin, branch admin, or agent - use their company
        if hasattr(user, 'company') and user.company:
            return serializer.save(company=user.company)
            
        # Fail if no company can be determined
        raise ValidationError({"company": "Unable to determine company for driver"})


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsBranchAdmin | IsCompanyAdmin | IsAgent | IsSystemAdmin]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAgent | IsAuthenticated]




class TicketReportView(generics.ListAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated | IsAgent | IsSystemAdmin | IsCompanyAdmin | IsBranchAdmin]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Ticket.objects.none()
        
        queryset = Ticket.objects.all()
        user = self.request.user
        if not user.is_authenticated:
            return Ticket.objects.none()
        
        if user.role and user.role.name.lower() == 'agent':
            queryset = queryset.filter(sender_agent__user=user)
        elif user.role and user.role.name.lower() == 'branch admin':
            queryset = queryset.filter(branch=user.branch)
        elif user.role and user.role.name.lower() == 'company admin':
            queryset = queryset.filter(company=user.company)

        status = self.request.query_params.get('status')
        company_id = self.request.query_params.get('company')
        if status:
            queryset = queryset.filter(status=status)
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset
    

@api_view(['GET'])
@permission_classes([IsCompanyAdmin])
def company_branches(request):
    company = request.user.company
    branches = Branch.objects.filter(company=company)
    return Response({
        "company": company.name,
        "branches": [{"id": b.id, "name": b.name, "location": b.location} for b in branches]
    })

@api_view(['GET'])
@permission_classes([IsCompanyAdmin])
def company_staff(request):
    users = User.objects.filter(company=request.user.company)
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsBranchAdmin | IsCompanyAdmin])
def branch_agents(request):
    branch = request.user.branch
    agents = User.objects.filter(role__name="agent", branch=branch)
    serializer = UserSerializer(agents, many=True)
    return Response(serializer.data)