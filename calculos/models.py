from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Solo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    coesao = models.DecimalField(max_digits=5, decimal_places=2, help_text="Coesão do solo (kPa)")
    angulo_atrito_interno = models.DecimalField(max_digits=5, decimal_places=2, help_text="Ângulo de atrito interno (graus)")
    peso_especifico = models.DecimalField(max_digits=5, decimal_places=2, help_text="Peso específico (kN/m³)")
    sobrecarga = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    adesao = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    indice_cone = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('800'), help_text="Índice de cone CI (kPa)")

    def __str__(self):
        return f"Solo de {self.usuario.username}: {self.nome}"

class Trator(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    massa_trator = models.DecimalField(max_digits=10, decimal_places=2, help_text="Massa total do trator (kg)")
    potencia_motor = models.DecimalField(max_digits=10, decimal_places=2, help_text="Potência nominal do motor (CV)")
    raio_roda = models.DecimalField(max_digits=5, decimal_places=2, help_text="Raio da roda motriz (m)")
    altura_barra_tracao = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('0.500'), help_text="Altura da barra de tração (m)")
    distancia_entre_eixos = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('2.500'), help_text="Distância entre eixos (m)")
    peso_dianteiro = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Peso no eixo dianteiro (kN)")
    lastro_atual = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Lastro atual do trator (kg) - opcional"
    )

    def __str__(self):
        return f"Trator de {self.usuario.username}: {self.nome}"

class Implemento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    TIPO_IMPLEMENTO_CHOICES = [
        ('dente', 'Dente (Tine)'),
        ('disco', 'Disco (Disc)'),
    ]
    tipo = models.CharField(max_length=10, choices=TIPO_IMPLEMENTO_CHOICES)
    nome = models.CharField(max_length=100)
    largura = models.DecimalField(max_digits=10, decimal_places=4)
    profundidade = models.DecimalField(max_digits=10, decimal_places=4)
    angulo_ataque = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    angulo_plano_falha = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('45.0000'), null=True, blank=True)
    angulo_atrito_implemento = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('20.0000'), null=True, blank=True)
    m_val = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Valor de m (coeficiente de distância de ruptura)")
    numero_ferramentas = models.IntegerField(null=True, blank=True, help_text="Número de ferramentas para implementos de dente múltiplos")
    espacamento = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Espaçamento entre ferramentas (m)")
    raio_disco = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    angulo_varredura = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    angulo_clareira = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    def __str__(self):
        return f"Implemento de {self.usuario.username}: {self.nome} ({self.tipo})"
    
    @property
    def d_over_w_ratio(self):
        """Calcula a razão profundidade/largura para a classificação da ferramenta."""
        if self.largura == 0:
            return None
        return self.profundidade / self.largura

class Calculo(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    
    solo = models.ForeignKey(Solo, on_delete=models.CASCADE)
    implemento = models.ForeignKey(Implemento, on_delete=models.CASCADE)
    trator = models.ForeignKey(Trator, on_delete=models.CASCADE, null=True, blank=True)
    
    resultado = models.DecimalField(max_digits=10, decimal_places=2)
    profundidade_critica = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    velocidade_kmh = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    patinagem_calculada = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    eficiencia_tracao_calculada = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    potencia_necessaria_cv = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    lastro_ideal_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Cálculo de {self.usuario.username} em {self.data_criacao.strftime('%d/%m/%Y')}"