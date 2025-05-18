from rest_framework.permissions import BasePermission

class IsAgent(BasePermission):
    def has_permission(self, request, view):
        return request.user.role and request.user.role.name.lower() == 'agent'

class IsSystemAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role and request.user.role.name.lower() == 'system admin'

class IsCompanyAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role and request.user.role.name.lower() == 'company admin'

class IsBranchAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.role and request.user.role.name.lower() == 'branch admin'

    