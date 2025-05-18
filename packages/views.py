from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, generics, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django_filters.rest_framework import DjangoFilterBackend
import uuid
import logging
from django.contrib.auth.models import User
from users.serializers import UserSerializer
from .models import (
    Package, PackageStatus, Ticket, Company, Branch, Driver,
    Vehicle, Category, Agent
)
from .serializers import PackageSerializer, PackageStatusSerializer, TicketSerializer, CompanySerializer, BranchSerializer, DriverSerializer, VehicleSerializer, CategorySerializer, AgentSerializer
from users.permissions import IsAgent, IsSystemAdmin, IsCompanyAdmin, IsBranchAdmin


logger = logging.getLogger(__name__)

class PackageViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing packages.
    
    Provides CRUD operations for packages with role-based permissions.
    """
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status__name', 'category', 'origin_branch', 'destination_branch']
    search_fields = ['tracking_number', 'name']
    ordering_fields = ['created_at', 'updated_at', 'value', 'weight']
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
        try:
            return Agent.objects.get(user=self.request.user)
        except Agent.DoesNotExist:
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
        if hasattr(user, 'agent'):
            agent = user.agent
            return Package.objects.filter(
                Q(sender_agent=agent) |
                Q(receiver_agent=agent) |
                Q(destination_branch=agent.branch)
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

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'status', openapi.IN_QUERY,
                description="Filter by status name",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            status.HTTP_200_OK: PackageSerializer(many=True),
            status.HTTP_400_BAD_REQUEST: "Bad request",
            status.HTTP_401_UNAUTHORIZED: "Unauthorized"
        }
    )
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
        agent = self.get_agent()
        if not agent:
            raise PermissionDenied("Only agents can create packages.")

        # Extract and validate data
        data = serializer.validated_data
        destination_branch = data.get('destination_branch')
        
        if not destination_branch:
            raise ValidationError({"destination_branch": "This field is required."})
            
        if destination_branch.company != agent.branch.company:
            raise ValidationError({"destination_branch": "Destination branch must belong to your company."})

        # Validate driver belongs to the right branch/company
        driver = data.get('driver')
        if not driver:
            raise ValidationError({"driver": "Driver is required."})
        if driver.branch.company != agent.branch.company:
            raise ValidationError({"driver": "Driver must belong to your company."})

        # Validate vehicle belongs to the specified driver
        vehicle = data.get('vehicle')
        if not vehicle:
            raise ValidationError({"vehicle": "Vehicle is required."})
        if vehicle.driver != driver:
            raise ValidationError({"vehicle": "Vehicle must belong to the specified driver."})

        # Validate departure time is in the future
        departure_time = data.get('departure_time')
        if not departure_time:
            raise ValidationError({"departure_time": "Departure time is required."})
        if departure_time <= timezone.now():
            raise ValidationError({"departure_time": "Departure time must be in the future."})

        # Generate tracking number and calculate shipping fee
        tracking_number = f"PKG-{uuid.uuid4().hex[:8].upper()}"
        shipping_fee = round(data.get('value', 0) * 0.10, 2)
        
        try:
            # Save the package
            package = serializer.save(
                tracking_number=tracking_number,
                origin_branch=agent.branch,
                sender_agent=agent,
                status=self.get_pending_status(),
                shipping_fee=shipping_fee
            )
            
            # Create corresponding ticket
            ticket = Ticket.objects.create(
                ticket_code=f"TCK-{uuid.uuid4().hex[:6].upper()}",
                package=package,
                driver=driver,
                vehicle=vehicle,
                branch=agent.branch,
                company=agent.branch.company,
                departure_time=departure_time,
                amount_paid=shipping_fee,
                status="sent"
            )
            
            logger.info(
                f"Package {package.tracking_number} created by agent {agent.user.username} "
                f"with ticket {ticket.ticket_code}"
            )
            
        except Exception as e:
            logger.error(f"Error creating package: {str(e)}")
            raise ValidationError({"non_field_errors": ["An error occurred while creating the package."]})

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

    @action(detail=True, methods=['post'])
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
        ticket = package.ticket
        ticket.status = "delivered"
        ticket.updated_at = timezone.now()
        ticket.save()
        
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
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'company', 'branch', 'driver', 'vehicle']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        elif hasattr(user, 'agent'):
            return self.queryset.filter(company=user.agent.branch.company)
        elif hasattr(user, 'branchadmin'):
            return self.queryset.filter(branch=user.branchadmin.branch)
        elif hasattr(user, 'companyadmin'):
            return self.queryset.filter(company=user.companyadmin.company)
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


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsBranchAdmin | IsCompanyAdmin | IsAgent | IsSystemAdmin]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAgent | IsAuthenticated]


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated | IsAgent]


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