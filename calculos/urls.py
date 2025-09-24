# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Rotas para Solo
    path('solo/novo/', views.criar_solo, name='criar_solo'),
    path('solo/', views.listar_solos, name='listar_solos'),
    path('solo/<int:solo_id>/deletar/', views.deletar_solo, name='deletar_solo'),

    # Rotas para Implemento
    path('implemento/novo/', views.criar_implemento, name='criar_implemento'),
    path('implemento/', views.listar_implementos, name='listar_implementos'),
    path('implemento/<int:implemento_id>/deletar/', views.deletar_implemento, name='deletar_implemento'),

    # Rotas para Cálculo
    path('calcular/', views.realizar_calculo, name='realizar_calculo'),
    path('calculos/', views.listar_calculos, name='listar_calculos'),
    path('calculo/<int:calculo_id>/relatorio-pdf/', views.gerar_relatorio_pdf, name='gerar_relatorio_pdf'),
    path('calculo/<int:calculo_id>/deletar/', views.deletar_calculo, name='deletar_calculo'),

    # Rotas gerais e de administração
    path('admin-app/', views.admin_view, name='admin_view'),
    path('', views.home_view, name='home'),
    
    # Nova rota para a calculadora simplificada
    path('calculadora-simplificada/', views.calculadora_simplificada, name='calculadora_simplificada'),
]