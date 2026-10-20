from django.urls import path
from . import views
urlpatterns = [
    path("health/", views.health),
    path("samples/", views.samples),
    path("evaluate/", views.evaluate),
    path("runs/", views.runs),
]
