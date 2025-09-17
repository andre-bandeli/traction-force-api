# calculos/forms.py
from django import forms
from .models import Solo, Implemento, Calculo

class SoloForm(forms.ModelForm):
    class Meta:
        model = Solo
        fields = ['nome', 'coesao', 'angulo_atrito_interno', 'peso_especifico', 'sobrecarga', 'adesao']

class ImplementoForm(forms.ModelForm):
    class Meta:
        model = Implemento
        fields = ['nome', 'largura', 'profundidade', 'angulo_ataque', 'angulo_plano_falha', 'angulo_atrito_implemento']

class CalculoForm(forms.Form):
    solo = forms.ModelChoiceField(queryset=Solo.objects.none())
    implemento = forms.ModelChoiceField(queryset=Implemento.objects.none())

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['solo'].queryset = Solo.objects.filter(usuario=user)
        self.fields['implemento'].queryset = Implemento.objects.filter(usuario=user)