from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("plan-trip/", views.plan_trip, name="plan-trip"),
]
