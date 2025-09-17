# calculos/models.py

from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


# Modelo para as propriedades do solo
class Solo(models.Model):
    # Relacionamento: cada solo pertence a um usuário
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Propriedades do solo
    nome = models.CharField(max_length=100)
    coesao = models.DecimalField(max_digits=5, decimal_places=2, help_text="Coesão do solo (kPa)")
    angulo_atrito_interno = models.DecimalField(max_digits=5, decimal_places=2, help_text="Ângulo de atrito interno (graus)")
    peso_especifico = models.DecimalField(max_digits=5, decimal_places=2, help_text="Peso específico (kN/m³)")
    sobrecarga = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    adesao = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))

    def __str__(self):
        return f"Solo de {self.usuario.username}: {self.nome}"

# Modelo para os implementos
class Implemento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    largura = models.DecimalField(max_digits=10, decimal_places=4)
    profundidade = models.DecimalField(max_digits=10, decimal_places=4)
    angulo_ataque = models.DecimalField(max_digits=10, decimal_places=4)
    angulo_plano_falha = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('45.0000'))
    angulo_atrito_implemento = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('20.0000'))
    
    def __str__(self):
        return f"Implemento de {self.usuario.username}: {self.nome}"
    
# Modelo para armazenar os cálculos
class Calculo(models.Model):
    # Relacionamento: cada cálculo pertence a um usuário
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Relacionamento com os modelos Solo e Implemento
    solo = models.ForeignKey(Solo, on_delete=models.CASCADE)
    implemento = models.ForeignKey(Implemento, on_delete=models.CASCADE)
    
    # Campo para armazenar o resultado final do cálculo
    resultado = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Data de criação do cálculo
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Cálculo de {self.usuario.username} em {self.data_criacao.strftime('%d/%m/%Y')}"