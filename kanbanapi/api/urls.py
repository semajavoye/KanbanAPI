"""URL configuration for API endpoints.

This module defines all API routes and their mappings to viewsets.
"""

# Django Modules
from django.urls import include, path

# 3rd Party
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import routers

from api import views

router = routers.DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Resource-stable endpoints
    path("articles/", views.ArticlesView.as_view(), name="articles"),
    path("tags/", views.TagsView.as_view(), name="tags"),
    path("orders/", views.OrderView.as_view(), name="orders"),
]
