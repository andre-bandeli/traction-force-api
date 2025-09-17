# calculos/admin.py

from django.contrib import admin
from .models import Solo, Implemento, Calculo

admin.site.register(Solo)
admin.site.register(Implemento)
admin.site.register(Calculo)