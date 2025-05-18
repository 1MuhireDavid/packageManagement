from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import PackageViewSet, PackageStatusViewSet, TicketViewSet, CompanyViewSet,BranchViewSet, DriverViewSet, VehicleViewSet, CategoryViewSet, TicketReportView

router = DefaultRouter()
router.register(r'packages', PackageViewSet)
router.register(r'status', PackageStatusViewSet)
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'companies', CompanyViewSet)
router.register(r'branches', BranchViewSet)
router.register(r'drivers', DriverViewSet)
router.register(r'vehicles', VehicleViewSet)
router.register(r'categories', CategoryViewSet)

urlpatterns = router.urls + [
    path('tickets/report/', TicketReportView.as_view(), name='ticket-report'),
]

urlpatterns = router.urls