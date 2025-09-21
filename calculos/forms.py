# calculos/forms.py
from django import forms
from .models import Solo, Implemento, Trator, Calculo

# Formulário para as propriedades do solo
class SoloForm(forms.ModelForm):
    class Meta:
        model = Solo
        fields = ['nome', 'coesao', 'angulo_atrito_interno', 'peso_especifico', 'sobrecarga', 'adesao']

# Formulário para as propriedades do trator
class TratorForm(forms.ModelForm):
    class Meta:
        model = Trator
        fields = ['nome', 'massa_trator', 'potencia_motor', 'raio_roda']

# Formulário para os implementos
class ImplementoForm(forms.ModelForm):
    class Meta:
        model = Implemento
        # Inclui todos os campos de dente e disco, a validação de qual campo é obrigatório
        # será tratada na view ou em um método clean específico.
        fields = [
            'nome', 'tipo', 'largura', 'profundidade', 'angulo_ataque', 
            'angulo_plano_falha', 'angulo_atrito_implemento', 'm_val',
            'numero_ferramentas', 'espacamento', 'raio_disco', 
            'angulo_varredura', 'angulo_clareira'
        ]

# Formulário para realizar o cálculo, incluindo a seleção de trator e os dados de otimização
class CalculoForm(forms.Form):
    solo = forms.ModelChoiceField(queryset=Solo.objects.none(), label='Selecione o Solo')
    implemento = forms.ModelChoiceField(queryset=Implemento.objects.none(), label='Selecione o Implemento')
    trator = forms.ModelChoiceField(
        queryset=Trator.objects.none(), 
        required=False,
        label='Selecione o Trator',
        help_text='Opcional. Selecione um trator para realizar a otimização de tração.'
    )
    
    # Campo para a velocidade de operação
    velocidade_kmh = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        label='Velocidade de Operação (km/h)',
        help_text='Opcional. Preencha apenas se quiser considerar o efeito da velocidade no cálculo.'
    )
    
    # Checkbox para incluir a velocidade
    incluir_velocidade = forms.BooleanField(
        required=False,
        label='Incluir Velocidade no Cálculo',
        help_text='Marque para usar o valor de velocidade informado no cálculo.'
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['solo'].queryset = Solo.objects.filter(usuario=user)
        self.fields['implemento'].queryset = Implemento.objects.filter(usuario=user)
        self.fields['trator'].queryset = Trator.objects.filter(usuario=user)

    def clean(self):
        cleaned_data = super().clean()
        incluir_velocidade = cleaned_data.get('incluir_velocidade')
        velocidade_kmh = cleaned_data.get('velocidade_kmh')

        # Validação: Se a caixa de 'incluir_velocidade' for marcada, o campo 'velocidade_kmh' se torna obrigatório
        if incluir_velocidade and not velocidade_kmh:
            self.add_error('velocidade_kmh', 'Este campo é obrigatório quando a velocidade é incluída no cálculo.')
        
        return cleaned_data