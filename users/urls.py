from django.urls import path,include
from .views import UserDetailView,RegisterView, CreateCompanyAdminView,CreateBranchAdminView,CreateAgentView
from users import views as user_views
from packages import views as package_views

urlpatterns = [
    path('<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('register/', RegisterView.as_view(), name='register'),
    path('admin/users/', user_views.list_all_users),
    path('company/branches/', package_views.company_branches),
    path('company/staff/', package_views.company_staff),
    path('branch/agents/', package_views.branch_agents),

    # Role-based user creation
    path('create-company-admin/', CreateCompanyAdminView.as_view(), name='create-company-admin'),
    path('create-branch-admin/', CreateBranchAdminView.as_view(), name='create-branch-admin'),
    path('create-agent/', CreateAgentView.as_view(), name='create-agent'),
]