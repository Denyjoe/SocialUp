from django.urls import path

from . import views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="catalog-categories"),
    path("services/", views.ServiceListView.as_view(), name="catalog-services"),
    path(
        "services/<int:pk>/",
        views.ServiceDetailView.as_view(),
        name="catalog-service-detail",
    ),
]
