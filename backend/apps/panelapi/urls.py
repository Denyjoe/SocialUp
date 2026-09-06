from django.urls import path

from .views import PanelAPIView

urlpatterns = [
    path("", PanelAPIView.as_view(), name="panel-api"),
]
