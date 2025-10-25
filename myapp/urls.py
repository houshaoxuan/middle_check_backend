from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/echo/', views.api_echo, name='api_echo'),
    path('api/runTest/', views.readResult_via_sse, name='run_Test'),
    path('api/run/', views.runTest, name='run'),
]
