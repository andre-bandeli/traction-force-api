# calculos/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('solo/novo/', views.criar_solo, name='criar_solo'),
    path('solo/', views.listar_solos, name='listar_solos'),
    path('implemento/novo/', views.criar_implemento, name='criar_implemento'),
    path('implemento/', views.listar_implementos, name='listar_implementos'),
    path('calcular/', views.realizar_calculo, name='realizar_calculo'), # Adicione esta linha
    path('calculos/', views.listar_calculos, name='listar_calculos'), # Adicione esta linha
    path('admin-app/', views.admin_view, name='admin_view'), # Adicione esta linha
    path('', views.home_view, name='home'), # Adicione esta linha


]