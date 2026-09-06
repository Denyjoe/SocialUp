from rest_framework import generics, permissions

from .models import Category, Service
from .serializers import CategorySerializer, ServiceSerializer


class CategoryListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = CategorySerializer
    pagination_class = None
    queryset = Category.objects.filter(is_active=True)


class ServiceListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = ServiceSerializer

    def get_queryset(self):
        qs = Service.objects.filter(is_active=True).select_related("category", "health_stat")
        category = self.request.query_params.get("category")
        platform = self.request.query_params.get("platform")
        search = self.request.query_params.get("search")
        if category:
            qs = qs.filter(category_id=category)
        if platform:
            from django.db.models import Q
            qs = qs.filter(Q(category__platform=platform) | Q(category__name__icontains=platform))
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class ServiceDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = ServiceSerializer
    queryset = Service.objects.filter(is_active=True).select_related("category", "health_stat")
