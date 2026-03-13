from django import forms
from .models import Solo, Implemento, Trator, Calculo

class BaseTechnicalForm(forms.ModelForm):
    """Classe base para aplicar estilos industriais em todos os forms"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control form-control-sm rounded-0 border-dark',
                'placeholder': field.label
            })

class SoloForm(BaseTechnicalForm):
    class Meta:
        model = Solo
        fields = ['nome', 'coesao', 'angulo_atrito_interno', 'peso_especifico', 'sobrecarga', 'adesao', 'indice_cone']

class TratorForm(BaseTechnicalForm):
    class Meta:
        model = Trator
        fields = [
            'nome', 'massa_trator', 'potencia_motor', 'raio_roda', 
            'altura_barra_tracao', 'distancia_entre_eixos', 'peso_dianteiro', 'lastro_atual'
        ]

class ImplementoForm(BaseTechnicalForm):
    class Meta:
        model = Implemento
        fields = [
            'nome', 'tipo', 'largura', 'profundidade', 'angulo_ataque', 
            'angulo_plano_falha', 'angulo_atrito_implemento', 'm_val',
            'numero_ferramentas', 'espacamento', 'raio_disco', 
            'angulo_varredura', 'angulo_clareira'
        ]

class CalculoForm(forms.Form):
    solo = forms.ModelChoiceField(
        queryset=Solo.objects.none(), 
        label='Perfil de Solo',
        widget=forms.Select(attrs={'class': 'form-select rounded-0 border-dark'})
    )
    implemento = forms.ModelChoiceField(
        queryset=Implemento.objects.none(), 
        label='Implemento Alvo',
        widget=forms.Select(attrs={'class': 'form-select rounded-0 border-dark'})
    )
    trator = forms.ModelChoiceField(
        queryset=Trator.objects.none(), 
        required=False,
        label='Trator (Opcional)',
        widget=forms.Select(attrs={'class': 'form-select rounded-0 border-dark'})
    )
    
    velocidade_kmh = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label='Velocidade Operacional',
        widget=forms.NumberInput(attrs={'class': 'form-control rounded-0 border-dark', 'placeholder': 'km/h'})
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['solo'].queryset = Solo.objects.filter(usuario=user)
        self.fields['implemento'].queryset = Implemento.objects.filter(usuario=user)
        self.fields['trator'].queryset = Trator.objects.filter(usuario=user)