from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import SoloForm, ImplementoForm, CalculoForm
from .models import Solo, Implemento, Calculo
from decimal import Decimal
import math

@login_required
def criar_solo(request):
    if request.method == 'POST':
        form = SoloForm(request.POST)
        if form.is_valid():
            solo = form.save(commit=False)
            solo.usuario = request.user
            solo.save()
            return redirect('listar_solos')
    else:
        form = SoloForm()
    return render(request, 'calculos/criar_solo.html', {'form': form})

@login_required
def criar_implemento(request):
    if request.method == 'POST':
        form = ImplementoForm(request.POST)
        if form.is_valid():
            implemento = form.save(commit=False)
            implemento.usuario = request.user
            implemento.save()
            return redirect('listar_implementos')
    else:
        form = ImplementoForm()
    return render(request, 'calculos/criar_implemento.html', {'form': form})

@login_required
def listar_solos(request):
    solos = Solo.objects.filter(usuario=request.user)
    return render(request, 'calculos/listar_solos.html', {'solos': solos})

@login_required
def listar_implementos(request):
    implementos = Implemento.objects.filter(usuario=request.user)
    return render(request, 'calculos/listar_implementos.html', {'implementos': implementos})

@login_required
def realizar_calculo(request):
    resultado = None
    form = CalculoForm(request.user)
    mensagem_erro = None
    
    if request.method == 'POST':
        form = CalculoForm(request.user, request.POST)
        if form.is_valid():
            solo = form.cleaned_data['solo']
            implemento = form.cleaned_data['implemento']
            
            try:
                # Coletando e convertendo os dados para float
                c = float(solo.coesao)
                fi = math.radians(float(solo.angulo_atrito_interno))
                gama = float(solo.peso_especifico)
                q = float(solo.sobrecarga) # Novo campo necessário
                ca = float(solo.adesao)     # Novo campo necessário

                b = float(implemento.largura)
                d = float(implemento.profundidade)
                alpha = math.radians(float(implemento.angulo_ataque))
                beta = math.radians(float(implemento.angulo_plano_falha)) # Novo campo necessário
                delta = math.radians(float(implemento.angulo_atrito_implemento)) # Novo campo necessário

                # --- Implementando as equações de Reece ---
                
                # Coletando a cotangente de forma segura para evitar ZeroDivisionError
                cot_alpha = 1 / math.tan(alpha) if math.tan(alpha) != 0 else float('inf')
                cot_beta = 1 / math.tan(beta) if math.tan(beta) != 0 else float('inf')
                cot_beta_fi = 1 / math.tan(beta + fi) if math.tan(beta + fi) != 0 else float('inf')

                # Denominador comum para os coeficientes N
                denominador_N = (math.cos(alpha + delta) + math.sin(alpha + delta) * cot_beta_fi)
                if denominador_N == 0:
                     raise ValueError("O denominador para os coeficientes N é zero. Verifique os valores de ângulo.")

                # Cálculo de 'r' [cite: 93]
                r = d * (cot_alpha + cot_beta)
                
                # Cálculo dos coeficientes adimensionais 
                Ny = (r / (2 * d)) / denominador_N
                Nq = (r / d) / denominador_N
                Nc = (1 + cot_beta * cot_beta_fi) / denominador_N
                Nca = (1 - cot_alpha * cot_beta_fi) / denominador_N

                # Cálculo da força total P 
                P_total = (gama * d**2 * Ny + c * d * Nc + ca * d * Nca + q * d * Nq) * b

                # Verificando se o resultado é um número válido e finito antes de salvar.
                if math.isinf(P_total) or math.isnan(P_total):
                    raise ValueError("O resultado do cálculo não é um número válido (infinito ou NaN). Por favor, verifique os valores de entrada.")
                
                resultado_arredondado = round(P_total, 10)
                resultado_db = Decimal(str(resultado_arredondado))
                
                resultado = f"Força de Tração (P): {P_total:.2f} kN"
    
                Calculo.objects.create(
                    usuario=request.user,
                    solo=solo,
                    implemento=implemento,
                    resultado=resultado_db
                )
            
            except (ValueError, TypeError, ZeroDivisionError) as e:
                mensagem_erro = f"Ocorreu um erro no cálculo. Por favor, verifique se os dados de entrada são válidos. Detalhe técnico: {e}"
                resultado = None

    return render(request, 'calculos/realizar_calculo.html', {'form': form, 'resultado': resultado, 'mensagem_erro': mensagem_erro})


@login_required
def listar_calculos(request):
    calculos = Calculo.objects.filter(usuario=request.user).order_by('-data_criacao')
    return render(request, 'calculos/listar_calculos.html', {'calculos': calculos})

@user_passes_test(lambda u: u.is_superuser)
def admin_view(request):
    solos = Solo.objects.all()
    implementos = Implemento.objects.all()
    calculos = Calculo.objects.all()

    return render(request, 'calculos/admin_view.html', {
        'solos': solos,
        'implementos': implementos,
        'calculos': calculos
    })

@login_required
def home_view(request):
    return render(request, 'calculos/home.html')