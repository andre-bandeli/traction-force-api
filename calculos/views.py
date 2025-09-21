# calculos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import SoloForm, ImplementoForm, CalculoForm, TratorForm
from .models import Solo, Implemento, Calculo, Trator
from reportlab.lib import colors
from decimal import Decimal
import math

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import SampleHorizontalLineChart

# Constantes universais
G = Decimal('9.81')  # m/s^2

# --- Funções Auxiliares de Cálculo ---

def _calculate_beta_critico(m, alpha):
    """
    Calcula β crítico conforme:
    βcrit = arctg(1/(m-cotα))
    """
    try:
        cot_alpha = Decimal(1) / Decimal(math.tan(alpha)) if math.tan(alpha) != 0 else Decimal('inf')
        if m <= cot_alpha:
            raise ValueError("m deve ser maior que cot(α) para calcular βcrit")
        beta_crit = Decimal(math.atan(1 / (m - cot_alpha)))
        return beta_crit
    except (ValueError, ZeroDivisionError) as e:
        raise Exception(f"Erro no cálculo de βcrit: {str(e)}")

def _calculate_coefficients(solo, implemento, d, w):
    """Calcula os coeficientes adimensionais seguindo exatamente a metodologia."""
    try:
        # Converter todos os valores para float para cálculos, depois para Decimal
        c = Decimal(str(solo.coesao))
        fi_deg = Decimal(str(solo.angulo_atrito_interno))
        fi_rad = Decimal(math.radians(float(fi_deg)))
        gama = Decimal(str(solo.peso_especifico))
        q_sobrecarga = Decimal(str(solo.sobrecarga))
        ca = Decimal(str(solo.adesao))
        
        alpha_deg = Decimal(str(implemento.angulo_ataque))
        alpha_rad = Decimal(math.radians(float(alpha_deg)))
        
        delta_deg = Decimal(str(implemento.angulo_atrito_implemento))
        delta_rad = Decimal(math.radians(float(delta_deg)))
        
        m = Decimal(str(implemento.m_val))
        d_dec = Decimal(str(d))
        w_dec = Decimal(str(w))

        # Calcular β crítico
        beta = _calculate_beta_critico(m, float(alpha_rad))
    
        cot_alpha = Decimal(1) / Decimal(math.tan(float(alpha_rad))) if math.tan(float(alpha_rad)) != 0 else Decimal('inf')
        cot_beta_fi = Decimal(1) / Decimal(math.tan(float(beta + fi_rad))) if math.tan(float(beta + fi_rad)) != 0 else Decimal('inf')
        
        cos_alpha_delta = Decimal(math.cos(float(alpha_rad + delta_rad)))
        sin_alpha_delta = Decimal(math.sin(float(alpha_rad + delta_rad)))
        
        denominador = (cos_alpha_delta + sin_alpha_delta * cot_beta_fi)
        if denominador == 0:
            raise ZeroDivisionError("Denominador zero no cálculo dos coeficientes.")

        # Cálculo do termo r
        r = d_dec * (cot_alpha + cot_beta_fi)
        
        # Cálculo dos adimensionais
        Ny = (r / (Decimal('2') * d_dec)) / denominador
        Nc = (Decimal('1') + (Decimal('1') / Decimal(math.tan(float(beta)))) * cot_beta_fi) / denominador if math.tan(float(beta)) != 0 else Decimal('inf')
        Nq = (r / d_dec) / denominador
        Na = (Decimal('1') - cot_alpha * cot_beta_fi) / denominador

        # Para ferramentas muito estreitas - coeficientes N' (Terzaghi modificado)
        sin_fi = Decimal(math.sin(float(fi_rad)))
        tan_fi = Decimal(math.tan(float(fi_rad))) if math.tan(float(fi_rad)) != 0 else Decimal('0.001')
        
        Kp = (Decimal('1') + sin_fi) / (Decimal('1') - sin_fi)
        exp_pi_tan_fi = Decimal(math.exp(math.pi * float(tan_fi)))
        
        Nc_prime = ((Kp * exp_pi_tan_fi) - Decimal('1')) / tan_fi
        Nq_prime = Kp
        
        # η para N'q conforme
        eta = (Decimal(math.pi) / Decimal('4')) - (fi_rad / Decimal('2'))
        Nq_prime_eta = Kp * Decimal(math.exp(math.pi * math.tan(float(eta))))

        return Ny, Nc, Nq, Na, Nc_prime, Nq_prime, Nq_prime_eta, beta
    except Exception as e:
        raise Exception(f"Erro nos cálculos de coeficientes: {str(e)}")

def _calculate_velocidade_critica(w, d):
    """
    Calcula a velocidade crítica conforme:
    Vcrit = √(5*g*(w+0.6*d))
    """
    try:
        vcrit = Decimal(math.sqrt(5 * float(G) * float(w + Decimal('0.6') * d)))
        return vcrit
    except Exception as e:
        raise Exception(f"Erro no cálculo da velocidade crítica: {str(e)}")

def _calculate_profundidade_critica(solo, implemento, d, w):
    """
    Calcula a profundidade crítica (dc) usando a aproximação de Godwin conforme.
    dc = (-b ± √(b²-4*a*c')) / (2*a)
    """
    try:
        c = Decimal(str(solo.coesao))
        fi = math.radians(Decimal(str(solo.angulo_atrito_interno)))
        gama = Decimal(str(solo.peso_especifico))
        q_sobrecarga = Decimal(str(solo.sobrecarga))
        ca = Decimal(str(solo.adesao))
        alpha = math.radians(Decimal(str(implemento.angulo_ataque)))
        delta = math.radians(Decimal(str(implemento.angulo_atrito_implemento)))
        m = Decimal(str(implemento.m_val))
        
        # Obter coeficientes
        Ny, Nc, Nq, Na, Nc_prime, Nq_prime, Nq_prime_eta, beta = _calculate_coefficients(solo, implemento, d, w)
        
        # Cálculo dos termos a, b, c'
        cot_alpha = Decimal(1) / Decimal(math.tan(alpha)) if math.tan(alpha) != 0 else Decimal('inf')
        
        sin_acos_term = Decimal(math.sin(math.acos(float(cot_alpha / m)))) if m != 0 and abs(cot_alpha / m) <= 1 else Decimal(0)
        
        # a = 3*γ*Nγ*sin(α + δ)*m*sin(cos^-1(cotα/m))
        a = Decimal('3') * gama * Ny * Decimal(math.sin(alpha + delta)) * m * sin_acos_term
        
        # b = 2*(c*Nc+q*Nq)*m*sin(cos^-1(cotα/m))*sin(α + δ)+2*γ*Nγ*sin(α + δ)*w-(1-senφ)*γ*w*Nq'
        sin_fi = Decimal(math.sin(fi))
        b = (Decimal('2') * (c * Nc + q_sobrecarga * Nq) * m * sin_acos_term * Decimal(math.sin(alpha + delta)) + 
             Decimal('2') * gama * Ny * Decimal(math.sin(alpha + delta)) * w - 
             (Decimal('1') - sin_fi) * gama * w * Nq_prime)
        
        # c' = (c*Nc + Ca*Na + q*Nq)*sin(α + δ)*w+Ca*c*cosα-w*c*Nc'
        c_prime = ((c * Nc + ca * Na + q_sobrecarga * Nq) * Decimal(math.sin(alpha + delta)) * w + 
                   ca * c * Decimal(math.cos(alpha)) - w * c * Nc_prime)
        
        # Resolver equação quadrática
        discriminant = b**2 - Decimal('4') * a * c_prime
        
        if discriminant < 0:
            return d
            
        sqrt_discriminant = Decimal(math.sqrt(float(discriminant)))
        
        # Escolher a raiz com menor magnitude (positiva)
        dc1 = (-b + sqrt_discriminant) / (Decimal('2') * a)
        dc2 = (-b - sqrt_discriminant) / (Decimal('2') * a)
        
        if dc1 > 0 and dc2 > 0:
            dc = min(dc1, dc2)
        elif dc1 > 0:
            dc = dc1
        elif dc2 > 0:
            dc = dc2
        else:
            dc = d 
            
        return dc if dc <= d else d
        
    except Exception as e:
        raise Exception(f"Erro no cálculo da profundidade crítica: {str(e)}")

def _calculate_tine_force(solo, implemento, incluir_velocidade=False, velocidade_kmh=None):
    """
    Calcula a força de tração para implementos de dente seguindo EXATAMENTE a metodologia.
    """
    w = Decimal(str(implemento.largura))
    d = Decimal(str(implemento.profundidade))
    d_over_w = d / w if w > 0 else Decimal('inf')
    
    c = Decimal(str(solo.coesao))
    fi = math.radians(Decimal(str(solo.angulo_atrito_interno)))
    gama = Decimal(str(solo.peso_especifico))
    q_sobrecarga = Decimal(str(solo.sobrecarga))
    ca = Decimal(str(solo.adesao))
    alpha = math.radians(Decimal(str(implemento.angulo_ataque)))
    delta = math.radians(Decimal(str(implemento.angulo_atrito_implemento)))
    m = Decimal(str(implemento.m_val))
    
    profundidade_critica = d
    
    # 1º DETERMINAR O TIPO DE FERRAMENTA
    if d_over_w < Decimal('0.5'):
        # --- FERRAMENTAS LARGAS ---
        # Desprezamos adesão e inércia, apenas equação de Reece
        Ny, Nc, Nq, _, _, _, _, _ = _calculate_coefficients(solo, implemento, d, w)
        P = (gama * d**2 * Ny + c * d * Nc + q_sobrecarga * d * Nq) * w
        
    elif Decimal('1') <= d_over_w <= Decimal('6'):
        # --- FERRAMENTAS ESTREITAS ---
        # Primeiro calcular velocidade crítica
        if incluir_velocidade and velocidade_kmh is not None:
            v_ms = Decimal(str(velocidade_kmh)) / Decimal('3.6')
            v_crit = _calculate_velocidade_critica(w, d)
            
            Ny, Nc, Nq, Na, _, _, _, _ = _calculate_coefficients(solo, implemento, d, w)
            
            if v_ms < v_crit:
                # v < Vcrit: sem efeito da velocidade
                # Vt e Ht
                base_force = (gama * d**2 * Ny + c * d * Nc)
                largura_efetiva = w + d * (m - (Decimal('1')/Decimal('3')) * (m - Decimal('1')))
                
                Vt = base_force * largura_efetiva * Decimal(math.cos(alpha + delta))
                Ht = base_force * largura_efetiva * Decimal(math.sin(alpha + delta))
                P = Ht 
                
            else:
                # v > Vcrit: levar em conta efeito da adesão
                base_force = (gama * d**2 * Ny + c * d * Nc + ca * d * Na + q_sobrecarga * d * Nq)
                largura_efetiva = w + d * (m - (Decimal('1')/Decimal('3')) * (m - Decimal('1')))
                P = base_force * largura_efetiva * Decimal(math.sin(alpha + delta))
        else:
            # Sem consideração de velocidade
            Ny, Nc, Nq, Na, _, _, _, _ = _calculate_coefficients(solo, implemento, d, w)
            base_force = (gama * d**2 * Ny + c * d * Nc + ca * d * Na + q_sobrecarga * d * Nq)
            largura_efetiva = w + d * (m - (Decimal('1')/Decimal('3')) * (m - Decimal('1')))
            P = base_force * largura_efetiva * Decimal(math.sin(alpha + delta))
            
    else:  # d_over_w > 6
        # --- FERRAMENTAS MUITO ESTREITAS ---
        dc = _calculate_profundidade_critica(solo, implemento, d, w)
        profundidade_critica = dc
        
        Ny, Nc, Nq, Na, Nc_prime, Nq_prime, _, _ = _calculate_coefficients(solo, implemento, dc, w)
        
        # Verificar se dc >= d (sem efeito da zona de fratura inferior)
        if dc >= d:
            # Usar metodologia de ferramenta estreita
            if incluir_velocidade and velocidade_kmh is not None:
                v_ms = Decimal(str(velocidade_kmh)) / Decimal('3.6')
                v_crit = _calculate_velocidade_critica(w, d)
                
                if v_ms >= v_crit:
                    base_force = (gama * d**2 * Ny + c * d * Nc + ca * d * Na + q_sobrecarga * d * Nq)
                else:
                    base_force = (gama * d**2 * Ny + c * d * Nc)
            else:
                base_force = (gama * d**2 * Ny + c * d * Nc + ca * d * Na + q_sobrecarga * d * Nq)
            
            largura_efetiva = w + d * (m - (Decimal('1')/Decimal('3')) * (m - Decimal('1')))
            P = base_force * largura_efetiva * Decimal(math.sin(alpha + delta))
        else:
            # dc < d: considerar zona de fratura inferior
            # Calcular H até profundidade crítica
            base_force = (gama * dc**2 * Ny + c * dc * Nc + ca * dc * Na + q_sobrecarga * dc * Nq)
            largura_efetiva = w + dc * (m - (Decimal('1')/Decimal('3')) * (m - Decimal('1')))
            H = base_force * largura_efetiva * Decimal(math.sin(alpha + delta))
            
            # Calcular Q (efeito da zona de fratura inferior)
            sin_fi = Decimal(math.sin(fi))
            Q = (w * c * Nc_prime * (d - dc) + 
                 Decimal('0.5') * (Decimal('1') - sin_fi) * gama * w * Nq_prime * (d**2 - dc**2))
            
            # Ht = H + Q
            P = H + Q
            
            # Consideração de velocidade para ferramentas muito estreitas
            if incluir_velocidade and velocidade_kmh is not None:
                v_ms = Decimal(str(velocidade_kmh)) / Decimal('3.6')
                v_crit = _calculate_velocidade_critica(w, d)
                
                if v_ms >= v_crit:
                    # Adicionar termo de velocidade (aproximação)
                    termo_velocidade = (gama * v_ms**2 / G) * Na * d * (w + Decimal('0.6') * d)
                    P += termo_velocidade
    
    return P, profundidade_critica

def _calculate_multiple_tines(solo, implemento, P_single, profundidade_utilizada):
    """
    Calcula força para múltiplas ferramentas seguindo metodologia.
    """
    n = implemento.numero_ferramentas
    s = Decimal(str(implemento.espacamento))
    d = profundidade_utilizada  # Usar dc para muito estreitas, d para outras
    
    # Verificar sobreposição
    if d < s / Decimal('2'):
        # Não há sobreposição
        D = P_single * n
        return D
    else:
        # Há sobreposição - calcular ferramenta virtual
        d_i = d - s / Decimal('2')  # Profundidade da ferramenta virtual
        
        # Calcular força da ferramenta virtual
        w = Decimal(str(implemento.largura))
        
        # Criar implemento virtual temporário para cálculo
        class ImplementoVirtual:
            def __init__(self, implemento_orig, nova_prof):
                self.largura = implemento_orig.largura
                self.profundidade = float(nova_prof)
                self.angulo_ataque = implemento_orig.angulo_ataque
                self.angulo_atrito_implemento = implemento_orig.angulo_atrito_implemento
                self.m_val = implemento_orig.m_val
                self.tipo = implemento_orig.tipo
        
        implemento_virtual = ImplementoVirtual(implemento, d_i)
        
        P_virtual, _ = _calculate_tine_force(solo, implemento_virtual, False, None)
        
        # Corrigir resultado com profundidade virtual
        D = (P_single * n) - ((n - 1) * P_virtual)
        
        return D

def _calculate_disc_force(solo, implemento):
    """
    Calcula as forças de tração para implementos de disco seguindo.
    """
    try:
        # Parâmetros do disco - converter tudo para float para cálculos
        R = float(implemento.raio_disco)
        theta_deg = float(implemento.angulo_varredura)
        theta_rad = math.radians(theta_deg)
        lambd_deg = float(implemento.angulo_clareira)
        lambd_rad = math.radians(lambd_deg)
        d = float(implemento.profundidade)
        
        # Usar largura do implemento ou raio como fallback
        if hasattr(implemento, 'largura') and implemento.largura:
            x = float(implemento.largura)
        else:
            x = R  # Fallback para raio do disco

        # Parâmetros do solo - converter para float
        c = float(solo.coesao)
        fi_deg = float(solo.angulo_atrito_interno)
        fi_rad = math.radians(fi_deg)
        gama = float(solo.peso_especifico)
        q_sobrecarga = float(solo.sobrecarga)
        ca = float(solo.adesao)
        
        # Ângulos para disco
        sigma_rad = math.radians(45)  # Ângulo no meio da corda
        alpha_disc_deg = float(implemento.angulo_ataque)
        alpha_disc_rad = math.radians(alpha_disc_deg)
        delta_disc_deg = float(implemento.angulo_atrito_implemento)
        delta_disc_rad = math.radians(delta_disc_deg)

        # 1. Força na cara interna do disco
        W = 2 * math.sqrt(2 * R * d - d**2)
        l = W * math.sin(theta_rad)
        
        # Coeficientes simplificados para disco
        sin_fi = math.sin(fi_rad)
        cos_fi = math.cos(fi_rad)
        tan_fi = sin_fi / cos_fi if cos_fi != 0 else 0.001
        
        # Coeficientes de capacidade de carga para disco
        Nc_disc = (math.exp(math.pi * tan_fi) * (math.tan(math.pi/4 + fi_rad/2)**2) - 1) / tan_fi
        Nq_disc = math.exp(math.pi * tan_fi) * (math.tan(math.pi/4 + fi_rad/2)**2)
        
        # Força P na cara interna
        P_interno = (gama * d * Nq_disc + c * Nc_disc) * l * math.sin(theta_rad)

        # Componentes da força P
        Dp_interno = P_interno * math.sin(sigma_rad) * math.sin(theta_rad)
        Vp_interno = -P_interno * math.cos(sigma_rad)
        Sp_interno = P_interno * math.sin(sigma_rad) * math.cos(theta_rad)
        
        # 2. Força na cara externa do disco (Teoria de Terzaghi)
        A = math.pi * R * x

        # Coeficientes de Terzaghi
        Kp = (1 + sin_fi) / (1 - sin_fi)
        exp_term = math.exp(math.pi * tan_fi)
        Nc_prime = ((Kp * exp_term) - 1) / tan_fi if tan_fi != 0 else 0

        q_prime = Nc_prime * c

        # Força na cara externa
        if theta_deg <= lambd_deg:
            sin_relation = math.sin(math.pi * (lambd_deg - theta_deg) / (2 * lambd_deg))
            Vs_externo = q_prime * A * sin_relation
        else:
            Vs_externo = 0
        
        # Componentes da força externa
        tan_diff = math.tan(alpha_disc_rad - delta_disc_rad)
        sin_lambd_theta = math.sin(lambd_rad - theta_rad)
        cos_lambd_theta = math.cos(lambd_rad - theta_rad)
        
        Ds_externo = Vs_externo * tan_diff * sin_lambd_theta
        Ss_externo = Vs_externo * tan_diff * cos_lambd_theta
        
        # 3. Forças totais (converter de volta para Decimal para consistência)
        D_total = Decimal(str(Dp_interno + Ds_externo))
        V_total = Decimal(str(Vp_interno + Vs_externo))
        S_total = Decimal(str(Sp_interno - Ss_externo))
        
        return D_total, V_total, S_total
        
    except Exception as e:
        raise Exception(f"Erro nos cálculos para implementos de disco: {str(e)}")
    
def _optimize_tractor(trator, forca_tracao, velocidade_kmh):
    """
    Realiza os cálculos de otimização de tração.
    """
    try:
        massa_trator_kg = Decimal(str(trator.massa_trator))
        potencia_motor_cv = Decimal(str(trator.potencia_motor))
        lastro_atual = Decimal(str(trator.lastro_atual)) if trator.lastro_atual is not None else Decimal(0)

        # Conversões
        forca_tracao_N = forca_tracao * Decimal('1000')
        velocidade_ms = velocidade_kmh / Decimal('3.6')
        
        # Patinagem
        peso_total = (massa_trator_kg + lastro_atual) * G
        forca_disponivel = peso_total * Decimal('0.8')  # Coeficiente de tração
        patinagem_porcentagem = (forca_tracao_N / forca_disponivel) * Decimal('100')
        patinagem_porcentagem = max(patinagem_porcentagem, Decimal('0'))
        
        # Eficiência de Tração
        eficiencia_tracao = Decimal('0.85') - patinagem_porcentagem / Decimal('200')
        eficiencia_tracao_porcentagem = max(min(eficiencia_tracao * Decimal('100'), Decimal('100')), Decimal('0'))
        
        # Potência Necessária
        potencia_necessaria_kW = (forca_tracao_N * velocidade_ms) / Decimal('1000')
        potencia_necessaria_cv = potencia_necessaria_kW / Decimal('0.7457')
        
        # Lastro Ideal
        lastro_ideal_kg = max((forca_tracao_N / (G * Decimal('0.8'))) - massa_trator_kg, Decimal('0'))
        
        return {
            'patinagem_calculada': patinagem_porcentagem.quantize(Decimal('0.01')),
            'eficiencia_tracao_calculada': eficiencia_tracao_porcentagem.quantize(Decimal('0.01')),
            'potencia_necessaria_cv': potencia_necessaria_cv.quantize(Decimal('0.01')),
            'lastro_ideal_kg': lastro_ideal_kg.quantize(Decimal('0.01')),
        }
    except Exception as e:
        raise Exception(f'Erro na otimização do trator: {e}')

# --- Views (mantidas iguais, apenas mudando as chamadas das funções) ---

@login_required
def criar_solo(request):
    if request.method == 'POST':
        form = SoloForm(request.POST)
        if form.is_valid():
            solo = form.save(commit=False)
            solo.usuario = request.user
            solo.save()
            messages.success(request, 'Solo cadastrado com sucesso!')
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
            messages.success(request, 'Implemento cadastrado com sucesso!')
            return redirect('listar_implementos')
    else:
        form = ImplementoForm()
    return render(request, 'calculos/criar_implemento.html', {'form': form})

@login_required
def criar_trator(request):
    if request.method == 'POST':
        form = TratorForm(request.POST)
        if form.is_valid():
            trator = form.save(commit=False)
            trator.usuario = request.user
            trator.save()
            messages.success(request, 'Trator cadastrado com sucesso!')
            return redirect('realizar_calculo')
    else:
        form = TratorForm()
    return render(request, 'calculos/criar_trator.html', {'form': form})

@login_required
def listar_solos(request):
    solos_list = Solo.objects.filter(usuario=request.user).order_by('nome')
    paginator = Paginator(solos_list, 10)
    page = request.GET.get('page')
    try:
        solos = paginator.page(page)
    except PageNotAnInteger:
        solos = paginator.page(1)
    except EmptyPage:
        solos = paginator.page(paginator.num_pages)
    return render(request, 'calculos/listar_solos.html', {'solos': solos})

@login_required
def listar_implementos(request):
    implementos_list = Implemento.objects.filter(usuario=request.user).order_by('nome')
    paginator = Paginator(implementos_list, 10)
    page = request.GET.get('page')
    try:
        implementos = paginator.page(page)
    except PageNotAnInteger:
        implementos = paginator.page(1)
    except EmptyPage:
        implementos = paginator.page(paginator.num_pages)
    return render(request, 'calculos/listar_implementos.html', {'implementos': implementos})

@login_required
def deletar_calculo(request, calculo_id):
    calculo = get_object_or_404(Calculo, id=calculo_id, usuario=request.user)
    if request.method == 'POST':
        calculo.delete()
        messages.success(request, 'Cálculo excluído com sucesso.')
        return redirect('listar_calculos')
    return render(request, 'calculos/confirmar_exclusao.html', {'item': calculo, 'tipo': 'Cálculo'})

@login_required
def deletar_solo(request, solo_id):
    solo = get_object_or_404(Solo, id=solo_id, usuario=request.user)
    if request.method == 'POST':
        solo.delete()
        messages.success(request, 'Solo excluído com sucesso.')
        return redirect('listar_solos')
    return render(request, 'calculos/confirmar_exclusao.html', {'item': solo, 'tipo': 'Solo'})

@login_required
def deletar_implemento(request, implemento_id):
    implemento = get_object_or_404(Implemento, id=implemento_id, usuario=request.user)
    if request.method == 'POST':
        implemento.delete()
        messages.success(request, 'Implemento excluído com sucesso.')
        return redirect('listar_implementos')
    return render(request, 'calculos/confirmar_exclusao.html', {'item': implemento, 'tipo': 'Implemento'})

@login_required
def realizar_calculo(request):
    resultado_implemento = None
    resultado_trator = {}
    
    # Verifica se o usuário tem solos, implementos e tratores cadastrados
    solo_count = Solo.objects.filter(usuario=request.user).count()
    implemento_count = Implemento.objects.filter(usuario=request.user).count()
    trator_count = Trator.objects.filter(usuario=request.user).count()

    form = CalculoForm(request.user, request.POST or None)
    context = {'form': form, 'solo_count': solo_count, 'implemento_count': implemento_count, 'trator_count': trator_count}
    
    if request.method == 'POST' and form.is_valid():
        try:
            solo = form.cleaned_data['solo']
            implemento = form.cleaned_data['implemento']
            trator = form.cleaned_data.get('trator')
            
            incluir_velocidade = form.cleaned_data.get('incluir_velocidade', False)
            velocidade_kmh = form.cleaned_data.get('velocidade_kmh')
            
            profundidade_critica = None

            # --- FLUXO DE CÁLCULO DO IMPLEMENTO SEGUINDO ---
            if implemento.tipo == 'dente':
                # Calcular força para uma ferramenta
                D_single, profundidade_critica = _calculate_tine_force(
                    solo, implemento, incluir_velocidade, velocidade_kmh
                )
                
                # Verificar se há múltiplas ferramentas
                if implemento.numero_ferramentas and implemento.numero_ferramentas > 1:
                    # Usar profundidade crítica para ferramentas muito estreitas, profundidade normal para outras
                    w = Decimal(str(implemento.largura))
                    d = Decimal(str(implemento.profundidade))
                    d_over_w = d / w if w > 0 else Decimal('inf')
                    
                    profundidade_para_multiplas = profundidade_critica if d_over_w > Decimal('6') else d
                    D_implemento = _calculate_multiple_tines(solo, implemento, D_single, profundidade_para_multiplas)
                else:
                    D_implemento = D_single
                    
            elif implemento.tipo == 'disco':
                D_implemento, V_total, S_total = _calculate_disc_force(solo, implemento)
            else:
                raise ValueError("Tipo de implemento inválido.")

            # --- FLUXO DE OTIMIZAÇÃO TRATOR-IMPLEMENTO ---
            if trator and velocidade_kmh:
                resultado_trator = _optimize_tractor(trator, D_implemento, velocidade_kmh)
            
            # Formatar resultado
            resultado_implemento = f"Força de Tração Total: {D_implemento:.2f} kN"
            resultado_db = D_implemento

            # Salvar cálculo
            calculo_salvo = Calculo.objects.create(
                usuario=request.user,
                solo=solo,
                implemento=implemento,
                trator=trator,
                resultado=resultado_db,
                profundidade_critica=profundidade_critica,
                velocidade_kmh=velocidade_kmh,
                **resultado_trator
            )
            
            messages.success(request, 'Cálculo realizado e salvo com sucesso!')
            form = CalculoForm(request.user)
            
            # Adicionar informações de diagnóstico
            w = Decimal(str(implemento.largura))
            d = Decimal(str(implemento.profundidade))
            d_over_w = d / w if w > 0 else Decimal('inf')
            
            tipo_ferramenta = ""
            if implemento.tipo == 'dente':
                if d_over_w < Decimal('0.5'):
                    tipo_ferramenta = "Ferramenta Larga (d/w < 0.5)"
                elif Decimal('1') <= d_over_w <= Decimal('6'):
                    tipo_ferramenta = "Ferramenta Estreita (1 ≤ d/w ≤ 6)"
                elif d_over_w > Decimal('6'):
                    tipo_ferramenta = "Ferramenta Muito Estreita (d/w > 6)"
                else:
                    tipo_ferramenta = f"Intermediária (d/w = {d_over_w:.2f})"
            
            # Verificar velocidade crítica se aplicável
            info_velocidade = ""
            if incluir_velocidade and velocidade_kmh and implemento.tipo == 'dente' and d_over_w >= Decimal('1'):
                v_crit = _calculate_velocidade_critica(w, d)
                v_ms = Decimal(str(velocidade_kmh)) / Decimal('3.6')
                if v_ms < v_crit:
                    info_velocidade = f"Velocidade ({v_ms:.2f} m/s) < Vcrit ({v_crit:.2f} m/s) - Sem efeito da adesão por velocidade"
                else:
                    info_velocidade = f"Velocidade ({v_ms:.2f} m/s) ≥ Vcrit ({v_crit:.2f} m/s) - Com efeito da adesão por velocidade"
            
            context.update({
                'form': form,
                'resultado': resultado_implemento, 
                'profundidade_critica': profundidade_critica,
                'velocidade_kmh': velocidade_kmh,
                'resultado_trator': resultado_trator,
                'tipo_ferramenta': tipo_ferramenta,
                'info_velocidade': info_velocidade,
                'd_over_w': f"{d_over_w:.2f}" if d_over_w != Decimal('inf') else "∞"
            })
            return render(request, 'calculos/realizar_calculo.html', context)
            
        except (ValueError, TypeError, ZeroDivisionError) as e:
            mensagem_erro = f"Erro no cálculo. Verifique os dados de entrada. Detalhe: {e}"
            messages.error(request, mensagem_erro)
        except Exception as e:
            mensagem_erro = f"Erro inesperado: {str(e)}"
            messages.error(request, mensagem_erro)

    return render(request, 'calculos/realizar_calculo.html', context)

@login_required
def listar_calculos(request):
    calculos_list = Calculo.objects.filter(usuario=request.user).order_by('-data_criacao')
    paginator = Paginator(calculos_list, 10)
    page = request.GET.get('page')
    try:
        calculos = paginator.page(page)
    except PageNotAnInteger:
        calculos = paginator.page(1)
    except EmptyPage:
        calculos = paginator.page(paginator.num_pages)
    return render(request, 'calculos/listar_calculos.html', {'calculos': calculos})

@user_passes_test(lambda u: u.is_superuser)
def admin_view(request):
    solos = Solo.objects.all()
    implementos = Implemento.objects.all()
    calculos = Calculo.objects.all()
    return render(request, 'calculos/admin_view.html', {'solos': solos, 'implementos': implementos, 'calculos': calculos})

@login_required
def home_view(request):
    return render(request, 'calculos/home.html')

@login_required
def gerar_relatorio_pdf(request, calculo_id):
    calculo = get_object_or_404(Calculo, id=calculo_id, usuario=request.user)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_calculo_{calculo.id}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter)
    story = []
    
    # Definição de Estilos
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='HeaderStyle', fontSize=24, alignment=1, spaceAfter=24, textColor=colors.darkblue, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=18, alignment=1, spaceAfter=12))
    styles.add(ParagraphStyle(name='SubtitleStyle', fontSize=12, alignment=0, spaceAfter=6, textColor=colors.darkblue, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='BodyStyle', fontSize=10, alignment=0, spaceAfter=4))

    # Cabeçalho do Documento
    story.append(Paragraph("DynaTech", styles['HeaderStyle']))
    story.append(Paragraph("Otimização Trator-Implemento", styles['HeaderStyle']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Relatório de Cálculo", styles['TitleStyle']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Usuário:</b> {request.user.get_full_name()}", styles['BodyStyle']))
    story.append(Paragraph(f"<b>Data do Cálculo:</b> {calculo.data_criacao.strftime('%d/%m/%Y %H:%M')}", styles['BodyStyle']))
    story.append(Spacer(1, 12))

    # Classificação da Ferramenta
    if calculo.implemento.tipo == 'dente':
        w = Decimal(str(calculo.implemento.largura))
        d = Decimal(str(calculo.implemento.profundidade))
        d_over_w = d / w if w > 0 else Decimal('inf')
        
        story.append(Paragraph("<b>Classificação da Ferramenta</b>", styles['SubtitleStyle']))
        story.append(Paragraph(f"<b>Razão d/w:</b> {d_over_w:.2f}", styles['BodyStyle']))
        
        if d_over_w < Decimal('0.5'):
            tipo_class = "Ferramenta Larga (d/w < 0.5)"
            metodo = "Equação de Reece simplificada (despreza adesão e inércia)"
        elif Decimal('1') <= d_over_w <= Decimal('6'):
            tipo_class = "Ferramenta Estreita (1 ≤ d/w ≤ 6)"
            metodo = "Equação de Reece com efeito dos flancos laterais"
        else:
            tipo_class = "Ferramenta Muito Estreita (d/w > 6)"
            metodo = "Equação de Reece com zona de fratura inferior (Godwin)"
            
        story.append(Paragraph(f"<b>Classificação:</b> {tipo_class}", styles['BodyStyle']))
        story.append(Paragraph(f"<b>Metodologia Aplicada:</b> {metodo}", styles['BodyStyle']))
        story.append(Spacer(1, 12))

    # Informações do Solo
    story.append(Paragraph("<b>Parâmetros do Solo</b>", styles['SubtitleStyle']))
    solo_data = [
        ["Nome:", calculo.solo.nome],
        ["Coesão (c) [kPa]:", f"{calculo.solo.coesao}"],
        ["Ângulo de Atrito Interno (φ) [°]:", f"{calculo.solo.angulo_atrito_interno}"],
        ["Peso Específico (γ) [kN/m³]:", f"{calculo.solo.peso_especifico}"],
        ["Sobrecarga (q) [kPa]:", f"{calculo.solo.sobrecarga}"],
        ["Adesão (Ca) [kPa]:", f"{calculo.solo.adesao}"]
    ]
    solo_table = Table(solo_data, colWidths=[3*72, 2*72])
    solo_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)
    ]))
    story.append(solo_table)
    story.append(Spacer(1, 12))

    # Informações do Implemento
    story.append(Paragraph("<b>Parâmetros do Implemento</b>", styles['SubtitleStyle']))
    implemento_data = [
        ["Nome:", calculo.implemento.nome],
        ["Largura (w) [m]:", f"{calculo.implemento.largura}"],
        ["Profundidade (d) [m]:", f"{calculo.implemento.profundidade}"],
        ["Tipo:", calculo.implemento.tipo.title()],
        ["Ângulo de Ataque (α) [°]:", f"{calculo.implemento.angulo_ataque}"],
        ["Ângulo de Atrito (δ) [°]:", f"{calculo.implemento.angulo_atrito_implemento}"],
        ["Parâmetro m:", f"{calculo.implemento.m_val}"]
    ]
    
    if calculo.implemento.numero_ferramentas:
        implemento_data.append(["Número de Ferramentas:", f"{calculo.implemento.numero_ferramentas}"])
    if calculo.implemento.espacamento:
        implemento_data.append(["Espaçamento [m]:", f"{calculo.implemento.espacamento}"])
    
    implemento_table = Table(implemento_data, colWidths=[3*72, 2*72])
    implemento_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey)
    ]))
    story.append(implemento_table)
    story.append(Spacer(1, 12))

    # Resultados do Cálculo
    story.append(Paragraph("<b>Resultados do Cálculo</b>", styles['SubtitleStyle']))
    story.append(Paragraph(f"<b>Força de Tração Total:</b> {calculo.resultado:.2f} kN", styles['BodyStyle']))
    
    if calculo.profundidade_critica and calculo.profundidade_critica != calculo.implemento.profundidade:
        story.append(Paragraph(f"<b>Profundidade Crítica (dc):</b> {calculo.profundidade_critica:.3f} m", styles['BodyStyle']))
        story.append(Paragraph(f"<b>Profundidade de Operação (d):</b> {calculo.implemento.profundidade} m", styles['BodyStyle']))
        if calculo.profundidade_critica < Decimal(str(calculo.implemento.profundidade)):
            story.append(Paragraph("⚠️ <b>Zona de fratura inferior ativa</b> (dc < d)", styles['BodyStyle']))
        else:
            story.append(Paragraph("✓ Sem zona de fratura inferior (dc ≥ d)", styles['BodyStyle']))
    
    if calculo.velocidade_kmh:
        if calculo.velocidade_kmh is not None:
            velocidade_kmh = float(calculo.velocidade_kmh)
            velocidade_ms = velocidade_kmh / 3.6
            story.append(Paragraph(f"<b>Velocidade de Operação:</b> {velocidade_kmh:.2f} km/h ({velocidade_ms:.2f} m/s)", styles['BodyStyle']))
        else:
            story.append(Paragraph("<b>Velocidade de Operação:</b> Não informada", styles['BodyStyle']))
        
        # Calcular e mostrar velocidade crítica se aplicável
        if calculo.implemento.tipo == 'dente' and d_over_w >= Decimal('1'):
            try:
                v_crit = _calculate_velocidade_critica(w, d)
                v_ms = Decimal(str(calculo.velocidade_kmh)) / Decimal('3.6')
                story.append(Paragraph(f"<b>Velocidade Crítica (Vcrit):</b> {v_crit:.2f} m/s", styles['BodyStyle']))
                if v_ms >= v_crit:
                    story.append(Paragraph("Efeito da adesão por velocidade considerado (v ≥ Vcrit)", styles['BodyStyle']))
                else:
                    story.append(Paragraph("Efeito da adesão por velocidade não aplicado (v < Vcrit)", styles['BodyStyle']))
            except:
                pass
    
    # Múltiplas ferramentas
    if calculo.implemento.numero_ferramentas and calculo.implemento.numero_ferramentas > 1:
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"<b>Análise de Múltiplas Ferramentas:</b>", styles['SubtitleStyle']))
        story.append(Paragraph(f"<b>Número de ferramentas:</b> {calculo.implemento.numero_ferramentas}", styles['BodyStyle']))
        story.append(Paragraph(f"<b>Espaçamento:</b> {calculo.implemento.espacamento} m", styles['BodyStyle']))
        
        # Verificar sobreposição
        prof_analise = calculo.profundidade_critica if calculo.profundidade_critica else Decimal(str(calculo.implemento.profundidade))
        s = Decimal(str(calculo.implemento.espacamento))
        
        if prof_analise < s / Decimal('2'):
            story.append(Paragraph("Sem sobreposição entre flancos (d < s/2)", styles['BodyStyle']))
            story.append(Paragraph("Força total = Força unitária × Número de ferramentas", styles['BodyStyle']))
        else:
            story.append(Paragraph("⚠️ Com sobreposição entre flancos (d > s/2)", styles['BodyStyle']))
            story.append(Paragraph("Correção aplicada usando ferramenta virtual", styles['BodyStyle']))
    
    story.append(Spacer(1, 12))
    
    # Resultados do Trator
    if calculo.trator:
        story.append(Paragraph("<b>Otimização do Trator</b>", styles['SubtitleStyle']))
        trator_data = [
            ["Trator:", calculo.trator.nome],
            ["Massa [kg]:", f"{calculo.trator.massa_trator}"],
            ["Potência [CV]:", f"{calculo.trator.potencia_motor}"],
            ["", ""],
            ["Patinagem Calculada [%]:", f"{calculo.patinagem_calculada:.2f}" if calculo.patinagem_calculada is not None else "N/A"],
            ["Eficiência de Tração [%]:", f"{calculo.eficiencia_tracao_calculada:.2f}" if calculo.eficiencia_tracao_calculada is not None else "N/A"],
            ["Potência Necessária [CV]:", f"{calculo.potencia_necessaria_cv:.2f}" if calculo.potencia_necessaria_cv is not None else "N/A"],
            ["Lastro Ideal [kg]:", f"{calculo.lastro_ideal_kg:.2f}" if calculo.lastro_ideal_kg is not None else "N/A"]
        ]
        trator_table = Table(trator_data, colWidths=[3*72, 2*72])
        trator_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('SPAN', (0, 3), (1, 3)),
            ('GRID', (0, 3), (1, 3), 0, colors.white)
        ]))
        story.append(trator_table)

    # Rodapé
    story.append(Spacer(1, 20))
    story.append(Paragraph("Relatório gerado automaticamente pelo Sistema", styles['BodyStyle']))
    story.append(Paragraph("Metodologia baseada no curso Trator-Implemento do Departamento de Máquinas da Faculdade de Engenharia Agrícola da Unicamp", styles['BodyStyle']))
    story.append(Paragraph("Responsável: André Luiz Bandeli Júnior. ", styles['BodyStyle']))

    doc.build(story)
    return response