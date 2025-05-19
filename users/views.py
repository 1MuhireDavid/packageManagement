from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from .models import User, Role
from .serializers import UserSerializer,RegisterSerializer
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsSystemAdmin, IsCompanyAdmin, IsBranchAdmin
from rest_framework.decorators import api_view, permission_classes
from packages.models import Company, Branch

class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [IsSystemAdmin]

@api_view(['GET'])
@permission_classes([IsSystemAdmin])
def list_all_users(request):
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)

class CreateCompanyAdminView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    
    def perform_create(self, serializer):
        # Get company admin role
        company_admin_role = get_object_or_404(Role, name="company admin")
        
        # Get company
        company_id = self.request.data.get('company')
        company = get_object_or_404(Company, id=company_id)
        
        # Create user with company admin role
        user = serializer.save(
            role=company_admin_role,
            company=company,
            is_staff=False
        )
        return user

# Company Admin creates Branch Admin
class CreateBranchAdminView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [IsAuthenticated, IsCompanyAdmin]
    
    def perform_create(self, serializer):
        user = self.request.user
        
        # Get branch admin role
        branch_admin_role = get_object_or_404(Role, name="branch admin")
        
        # Get branch
        branch_id = self.request.data.get('branch')
        branch = get_object_or_404(Branch, id=branch_id, company=user.company)
        
        # Create user with branch admin role
        user = serializer.save(
            role=branch_admin_role,
            company=user.company,
            branch=branch,
            is_staff=False
        )
        return user

# Branch Admin creates Agent
class CreateAgentView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [IsAuthenticated, IsBranchAdmin]
    
    def perform_create(self, serializer):
        user = self.request.user
        
        agent_role = get_object_or_404(Role, id=4)
        
        new_user = serializer.save(
            role=agent_role,
            company=user.company,
            branch=user.branch,
            is_staff=False
        )
                
        return new_user