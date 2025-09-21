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
def _calculate_coefficients(solo, implemento, d, w):
    """Calcula os coeficientes adimensionais para ferramentas de dente."""
    try:
        c = Decimal(str(solo.coesao))
        fi = math.radians(Decimal(str(solo.angulo_atrito_interno)))
        gama = Decimal(str(solo.peso_especifico))
        q_sobrecarga = Decimal(str(solo.sobrecarga))
        ca = Decimal(str(solo.adesao))
        alpha = math.radians(Decimal(str(implemento.angulo_ataque)))
        beta = math.radians(Decimal(str(implemento.angulo_plano_falha)))
        delta = math.radians(Decimal(str(implemento.angulo_atrito_implemento)))
        m = Decimal(str(implemento.m_val))
    except (ValueError, TypeError):
        raise ValueError("Dados de entrada para cálculo de coeficientes são inválidos. Verifique os valores numéricos.")

    try:
        cot_alpha = Decimal(1) / Decimal(math.tan(alpha)) if math.tan(alpha) != 0 else Decimal('inf')
        cot_beta_fi = Decimal(1) / Decimal(math.tan(beta + fi)) if math.tan(beta + fi) != 0 else Decimal('inf')
        
        denominador = (Decimal(math.cos(alpha + delta)) + Decimal(math.sin(alpha + delta)) * cot_beta_fi)
        if denominador == 0:
            raise ZeroDivisionError("Denominador zero no cálculo dos coeficientes.")

        r = d * (cot_alpha + cot_beta_fi)
        Ny = (r / (Decimal(2) * d)) / denominador
        Nc = (Decimal(1) + (Decimal(1) / Decimal(math.tan(beta))) * cot_beta_fi) / denominador if math.tan(beta) != 0 else Decimal('inf')
        Nq = (r / d) / denominador
        
        Nca = (Decimal(1) - cot_alpha * cot_beta_fi) / denominador

        Kp = (Decimal(1) + Decimal(math.sin(fi))) / (Decimal(1) - Decimal(math.sin(fi)))
        Nc_prime = ((Kp * Decimal(math.exp(math.pi * math.tan(fi)))) - Decimal(1)) / Decimal(math.tan(fi)) if math.tan(fi) != 0 else Decimal(0)
        Nq_prime = Kp
        
        # Coeficiente Na para o termo de velocidade
        denominador_Na = (Decimal(math.cos(alpha + delta)) + Decimal(math.sin(alpha + delta)) * cot_beta_fi) * (Decimal(1) + (Decimal(1) / Decimal(math.tan(beta))) * cot_alpha)
        Na = (Decimal(math.tan(beta)) + cot_beta_fi) / denominador_Na if denominador_Na != 0 else Decimal(0)

        return Ny, Nc, Nq, Nca, Nc_prime, Nq_prime, Na
    except (ValueError, ZeroDivisionError) as e:
        raise Exception(f"Erro nos cálculos de coeficientes: {str(e)}")


def _calculate_tine_force(solo, implemento, incluir_velocidade, velocidade_kmh):
    """Calcula a força de tração para implementos de dente (simples ou múltiplas)."""
    w = Decimal(str(implemento.largura))
    d = Decimal(str(implemento.profundidade))
    d_over_w = d / w if w > 0 else Decimal('inf')
    
    P_total = Decimal('0.00')
    profundidade_critica_valida = d
    
    # Parâmetros necessários para todas as categorias
    c = Decimal(str(solo.coesao))
    fi = math.radians(Decimal(str(solo.angulo_atrito_interno)))
    gama = Decimal(str(solo.peso_especifico))
    q_sobrecarga = Decimal(str(solo.sobrecarga))
    
    # --- CÁLCULO PARA FERRAMENTAS LARGAS (d/w < 0.5) ---
    if d_over_w < Decimal('0.5'):
        Ny, Nc, Nq, _, _, _, _ = _calculate_coefficients(solo, implemento, d, w)
        # Adesão e inércia são desprezados para ferramentas largas
        H_t = (gama * d**2 * Ny + c * d * Nc + q_sobrecarga * d * Nq) * w
        P_total = H_t

    # --- CÁLCULO PARA FERRAMENTAS ESTREITAS (1 <= d/w <= 6) ---
    elif Decimal('1') <= d_over_w <= Decimal('6'):
        Ny, Nc, Nq, Nca, _, _, Na = _calculate_coefficients(solo, implemento, d, w)
        H_t = (gama * d**2 * Ny + c * d * Nc + Decimal(str(solo.adesao)) * d * Nca + q_sobrecarga * d * Nq) * w

        if incluir_velocidade and velocidade_kmh is not None:
            v_ms = Decimal(str(velocidade_kmh)) / Decimal('3.6')
            termo_velocidade = (gama * v_ms**2 / G) * Na * d * (w + Decimal('0.6') * d)
            H_t += termo_velocidade
            
        P_total = H_t
        
    # --- CÁLCULO PARA FERRAMENTAS MUITO ESTREITAS (d/w > 6) ---
    elif d_over_w > Decimal('6'):
        Ny, Nc, Nq, Nca, Nc_prime, Nq_prime, Na = _calculate_coefficients(solo, implemento, d, w)
        alpha = math.radians(Decimal(str(implemento.angulo_ataque)))
        delta = math.radians(Decimal(str(implemento.angulo_atrito_implemento)))
        m = Decimal(str(implemento.m_val))
        ca = Decimal(str(solo.adesao))

        try:
            # Cálculo da profundidade crítica (dc)
            acos_arg = Decimal(math.tan(alpha) / m) if m != 0 else Decimal('inf')
            
            # Coeficientes a, b e c'
            a = Decimal('3') * gama * Ny * m * Decimal(math.sin(math.acos(acos_arg))) * Decimal(math.sin(alpha + delta))
            b = (Decimal('2') * (c * Nc + q_sobrecarga * Nq) * m * Decimal(math.sin(math.acos(acos_arg))) * Decimal(math.sin(alpha + delta)) + 
                 Decimal('2') * gama * Ny * w * Decimal(math.sin(alpha + delta)) - (Decimal('1') - Decimal(math.sin(fi))) * gama * w * Nq_prime)
            c_prime = (c * Nc + ca * Nca + q_sobrecarga * Nq) * w * Decimal(math.sin(alpha + delta)) + ca * c * Decimal(math.cos(alpha)) - w * c * Nc_prime
            
            discriminant = b**2 - Decimal('4') * a * c_prime
            if discriminant < 0:
                dc = d
            else:
                dc_val = (-b + Decimal(math.sqrt(discriminant))) / (Decimal('2') * a)
                dc = Decimal(dc_val) if dc_val > 0 else d # Garante que a profundidade crítica é positiva

        except (ValueError, ZeroDivisionError) as e:
            dc = d
        
        profundidade_critica_valida = dc if dc < d else d
        
        # Força Horizontal (Ht = H + Q)
        H_t_base = (gama * profundidade_critica_valida**2 * Ny + c * profundidade_critica_valida * Nc + q_sobrecarga * profundidade_critica_valida * Nq) * (w + d * (m - Decimal('1') / Decimal('3') * (m - Decimal('1')))) * Decimal(math.sin(alpha + delta))
        Q = w * c * Nc_prime * (d - profundidade_critica_valida) + Decimal('0.5') * (Decimal('1') - Decimal(math.sin(fi))) * gama * w * Nq_prime * (d**2 - profundidade_critica_valida**2)
        
        H_t = H_t_base + Q
        
        if incluir_velocidade and velocidade_kmh is not None:
            v_ms = Decimal(str(velocidade_kmh)) / Decimal('3.6')
            termo_velocidade = (gama * v_ms**2 / G) * Na * d * (w + Decimal('0.6') * d)
            H_t += termo_velocidade
            
        P_total = H_t

    # --- CÁLCULO PARA MÚLTIPLAS FERRAMENTAS ---
    n = implemento.numero_ferramentas
    s = implemento.espacamento
    if n > 1 and s is not None:
        d_i = d - Decimal(str(s)) / Decimal('2')
        Ny_i, Nc_i, Nq_i, Nca_i, _, _, _ = _calculate_coefficients(solo, implemento, d_i, w)
        
        Hi = (gama * d_i**2 * Ny_i + c * d_i * Nc_i + Decimal(str(solo.adesao)) * d_i * Nca_i + q_sobrecarga * d_i * Nq_i) * w
        
        P_total = n * P_total - (n - 1) * Hi
        
    return P_total, profundidade_critica_valida

def _calculate_disc_force(solo, implemento):
    """Calcula as forças de tração para implementos de disco."""
    try:
        R = Decimal(str(implemento.raio_disco))
        theta = Decimal(str(math.radians(float(implemento.angulo_varredura))))  # Converter para Decimal
        lambd = Decimal(str(math.radians(float(implemento.angulo_clareira))))   # Converter para Decimal
        x = Decimal(str(implemento.raio_disco))
        
        c = Decimal(str(solo.coesao))
        fi = Decimal(str(math.radians(float(solo.angulo_atrito_interno))))      # Converter para Decimal
        gama = Decimal(str(solo.peso_especifico))
        q_sobrecarga = Decimal(str(solo.sobrecarga))
        ca = Decimal(str(solo.adesao))
        
        alpha_disc = Decimal(str(math.radians(20)))                             # Converter para Decimal
        delta_disc = Decimal(str(math.radians(20)))                             # Converter para Decimal

        # Cálculo da Força Passiva - converter funções math para Decimal
        tan_fi = Decimal(str(math.tan(float(fi))))
        sin_alpha_delta = Decimal(str(math.sin(float(alpha_disc + delta_disc))))
        cos_alpha_delta = Decimal(str(math.cos(float(alpha_disc + delta_disc))))
        sin_theta = Decimal(str(math.sin(float(theta))))
        cos_theta = Decimal(str(math.cos(float(theta))))
        
        # P = (gama * (Decimal('2') * R - Decimal('1'))**2 * Decimal('1') + 
        #      c * (Decimal('2') * R - Decimal('1')) * Decimal('1') + 
        #      q_sobrecarga * (Decimal('2') * R - Decimal('1')) * Decimal('1')) * tan_fi

        # Obter os coeficientes adimensionais para a profundidade d
        Ny, Nc, Nq, Nca, _, _, _ = _calculate_coefficients(solo, implemento, d=Decimal(str(implemento.profundidade)), w=Decimal('1.0'))
        
        # Calcular o comprimento de corte efetivo (l)
        d = Decimal(str(implemento.profundidade))
        W = Decimal('2') * Decimal(math.sqrt(Decimal('2') * R * d - d**2))
        l = W * Decimal(math.sin(float(theta)))

        # Força Passiva P, usando a equação de Reece do material da Aula 7
        P = (gama * d**2 * Ny + c * d * Nc + ca * d * Nca + q_sobrecarga * d * Nq) * l
             
        Dp = P * sin_alpha_delta * sin_theta
        Vp = -P * cos_alpha_delta
        Sp = P * sin_alpha_delta * cos_theta

        # Cálculo da Força de Esfrega (Scrubbing)
        sin_fi = Decimal(str(math.sin(float(fi))))
        tan_fi_val = Decimal(str(math.tan(float(fi))))
        exp_val = Decimal(str(math.exp(math.pi * float(tan_fi_val))))
        
        Kp = (Decimal('1') + sin_fi) / (Decimal('1') - sin_fi)
        Nc_prime = ((Kp * exp_val) - Decimal('1')) / tan_fi_val if tan_fi_val != 0 else Decimal('0')
        q_prime = Nc_prime * c
        
        A = Decimal(str(math.pi)) * R * x
        
        sin_val = Decimal(str(math.sin(math.pi * float(lambd - theta) / (2 * float(lambd)))))
        Vs = q_prime * A * sin_val
        
        tan_alpha_delta_diff = Decimal(str(math.tan(float(alpha_disc - delta_disc))))
        sin_lambd_theta = Decimal(str(math.sin(float(lambd - theta))))
        cos_lambd_theta = Decimal(str(math.cos(float(lambd - theta))))
        
        Ds = Vs * tan_alpha_delta_diff * sin_lambd_theta
        Ss = Vs * tan_alpha_delta_diff * cos_lambd_theta

        # Forças totais
        D_total = Dp + Ds
        V_total = Vp + Vs
        S_total = Sp - Ss

    except (ValueError, TypeError, ZeroDivisionError) as e:
        raise Exception(f"Erro nos cálculos para implementos de disco: {str(e)}")

    return D_total, V_total, S_total

def _optimize_tractor(trator, forca_tracao, velocidade_kmh):
    """
    Realiza os cálculos de otimização de tração com base em um modelo simplificado.
    NOTA: As fórmulas a seguir são simplificadas. Substitua-as pelas suas equações completas.
    """
    try:
        massa_trator_kg = Decimal(str(trator.massa_trator))
        potencia_motor_cv = Decimal(str(trator.potencia_motor))
        lastro_atual = Decimal(str(trator.lastro_atual)) if trator.lastro_atual is not None else Decimal(0)

        # Conversões
        forca_tracao_N = forca_tracao * Decimal('1000') # kN para N
        velocidade_ms = velocidade_kmh / Decimal('3.6') # km/h para m/s
        
        # Patinagem
        patinagem_porcentagem = (forca_tracao_N / (massa_trator_kg * G * Decimal('0.8') + lastro_atual * G * Decimal('0.8'))) * Decimal('100')
        patinagem_porcentagem = patinagem_porcentagem if patinagem_porcentagem >= 0 else Decimal(0)
        
        # Eficiência de Tração
        eficiencia_tracao = Decimal('0.85') - patinagem_porcentagem / Decimal('200')
        eficiencia_tracao_porcentagem = eficiencia_tracao * Decimal('100')
        eficiencia_tracao_porcentagem = eficiencia_tracao_porcentagem if eficiencia_tracao_porcentagem <= 100 else Decimal(100)
        
        # Potência Necessária
        potencia_necessaria_kW = (forca_tracao_N * velocidade_ms) / Decimal('1000')
        potencia_necessaria_cv = potencia_necessaria_kW / Decimal('0.7457')
        
        # Lastro Ideal
        lastro_ideal_kg = (forca_tracao_N / (G * Decimal('0.8'))) - massa_trator_kg
        
        return {
            'patinagem_calculada': patinagem_porcentagem.quantize(Decimal('0.01')),
            'eficiencia_tracao_calculada': eficiencia_tracao_porcentagem.quantize(Decimal('0.01')),
            'potencia_necessaria_cv': potencia_necessaria_cv.quantize(Decimal('0.01')),
            'lastro_ideal_kg': lastro_ideal_kg.quantize(Decimal('0.01')),
        }
    except Exception as e:
        messages.error(f'Erro na otimização do trator: {e}')
        return None

# --- Views ---
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

            # --- FLUXO DE CÁLCULO DO IMPLEMENTO ---
            if implemento.tipo == 'dente':
                D_implemento, profundidade_critica = _calculate_tine_force(
                    solo, implemento, incluir_velocidade, velocidade_kmh
                )
            elif implemento.tipo == 'disco':
                D_implemento, _, _ = _calculate_disc_force(solo, implemento)
            else:
                raise ValueError("Tipo de implemento inválido.")

            # --- FLUXO DE OTIMIZAÇÃO TRATOR-IMPLEMENTO ---
            if trator and velocidade_kmh:
                resultado_trator = _optimize_tractor(trator, D_implemento, velocidade_kmh)
            
            # Arredondar e salvar o resultado
            resultado_implemento = f"Força de Tração Total: {D_implemento:.2f} kN"
            resultado_db = D_implemento

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
            
            context.update({
                'form': form,
                'resultado': resultado_implemento, 
                'profundidade_critica': profundidade_critica,
                'velocidade_kmh': velocidade_kmh,
                'resultado_trator': resultado_trator
            })
            return render(request, 'calculos/realizar_calculo.html', context)
            
        except (ValueError, TypeError, ZeroDivisionError) as e:
            mensagem_erro = f"Ocorreu um erro no cálculo. Verifique se os dados de entrada são válidos. Detalhe técnico: {e}"
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
    story.append(Paragraph("Relatório de Otimização de Tração", styles['TitleStyle']))
    story.append(Paragraph(f"<b>Gerado para:</b> {request.user.get_full_name()}", styles['BodyStyle']))
    story.append(Paragraph(f"<b>Data:</b> {calculo.data_criacao.strftime('%d/%m/%Y %H:%M')}", styles['BodyStyle']))
    story.append(Spacer(1, 12))

    # Informações do Solo
    story.append(Paragraph("<b>Dados do Solo</b>", styles['SubtitleStyle']))
    solo_data = [
        ["Nome:", calculo.solo.nome],
        ["Coesão (kPa):", calculo.solo.coesao],
        ["Ângulo de Atrito Interno (º):", calculo.solo.angulo_atrito_interno],
        ["Peso Específico (kN/m³):", calculo.solo.peso_especifico],
        ["Sobrecarga (kPa):", calculo.solo.sobrecarga],
        ["Adesão (kPa):", calculo.solo.adesao]
    ]
    solo_table = Table(solo_data)
    solo_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold')
    ]))
    story.append(solo_table)
    story.append(Spacer(1, 12))

    # Informações do Implemento e Classificação
    story.append(Paragraph("<b>Dados do Implemento</b>", styles['SubtitleStyle']))
    implemento_data = [
        ["Nome:", calculo.implemento.nome],
        ["Largura (m):", calculo.implemento.largura],
        ["Profundidade (m):", calculo.implemento.profundidade]
    ]
    if calculo.implemento.tipo:
        implemento_data.append(["Tipo:", calculo.implemento.tipo])
    if calculo.implemento.numero_ferramentas:
        implemento_data.append(["Número de Ferramentas:", calculo.implemento.numero_ferramentas])
    if calculo.implemento.espacamento:
        implemento_data.append(["Espaçamento (m):", calculo.implemento.espacamento])
    
    implemento_table = Table(implemento_data)
    implemento_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold')
    ]))
    story.append(implemento_table)
    story.append(Spacer(1, 12))
    
    # Classificação da ferramenta
    if calculo.implemento.tipo == 'dente':
        d_over_w = calculo.implemento.profundidade / calculo.implemento.largura if calculo.implemento.largura > 0 else Decimal('inf')
        tipo_ferramenta = ""
        if d_over_w < Decimal('0.5'):
            tipo_ferramenta = "Ferramenta Larga (d/w < 0.5)"
        elif Decimal('1') <= d_over_w <= Decimal('6'):
            tipo_ferramenta = "Ferramenta Estreita (1 <= d/w <= 6)"
        else:
            tipo_ferramenta = "Ferramenta Muito Estreita (d/w > 6)"
        story.append(Paragraph(f"<b>Classificação da Ferramenta:</b> {tipo_ferramenta}", styles['BodyStyle']))
        story.append(Spacer(1, 12))

    # Resultados e Condições do Cálculo
    story.append(Paragraph("<b>Resultados do Cálculo do Implemento</b>", styles['SubtitleStyle']))
    story.append(Paragraph(f"<b>Força de Tração Total:</b> {calculo.resultado:.2f} kN", styles['BodyStyle']))
    
    if calculo.profundidade_critica:
        story.append(Paragraph(f"<b>Profundidade Crítica:</b> {calculo.profundidade_critica:.2f} m", styles['BodyStyle']))
    
    if calculo.velocidade_kmh:
        story.append(Paragraph(f"<b>Velocidade de Operação Utilizada:</b> {calculo.velocidade_kmh:.2f} km/h", styles['BodyStyle']))
        story.append(Paragraph("O cálculo da força de tração considerou o efeito da velocidade.", styles['BodyStyle']))
    else:
        story.append(Paragraph("O cálculo da força de tração não considerou o efeito da velocidade de operação.", styles['BodyStyle']))
    story.append(Spacer(1, 12))
    
    # Resultados do Trator
    if calculo.trator:
        story.append(Paragraph("<b>Resultados da Otimização do Trator</b>", styles['SubtitleStyle']))
        trator_data = [
            ["Patinagem Calculada:", f"{calculo.patinagem_calculada:.2f} %"],
            ["Eficiência de Tração:", f"{calculo.eficiencia_tracao_calculada:.2f} %"],
            ["Potência Necessária:", f"{calculo.potencia_necessaria_cv:.2f} CV"],
            ["Lastro Ideal:", f"{calculo.lastro_ideal_kg:.2f} kg"]
        ]
        trator_table = Table(trator_data)
        trator_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold')
        ]))
        story.append(trator_table)
        story.append(Spacer(1, 12))

    # Gráfico de Potência vs. Velocidade
    story.append(Paragraph("<b>Potência de Tração vs. Velocidade de Operação</b>", styles['SubtitleStyle']))
    story.append(Paragraph("O gráfico abaixo ilustra a potência de tração necessária em função da velocidade, calculada com base nos parâmetros de solo e implemento fornecidos.", styles['BodyStyle']))
    
    try:
        velocidades_kmh = [Decimal(i) for i in range(1, 11)]
        dados_potencia = []
        for v_kmh in velocidades_kmh:
            if calculo.implemento.tipo == 'dente':
                P_total, _ = _calculate_tine_force(calculo.solo, calculo.implemento, True, v_kmh)
            elif calculo.implemento.tipo == 'disco':
                P_total, _, _ = _calculate_disc_force(calculo.solo, calculo.implemento)
            
            v_ms = v_kmh / Decimal('3.6')
            potencia_kW = (P_total * v_ms) / Decimal('1000')
            dados_potencia.append(float(potencia_kW))

        drawing = Drawing(400, 200)
        chart = SampleHorizontalLineChart()
        chart.x = 50
        chart.y = 30
        chart.height = 125
        chart.width = 300
        chart.data = [dados_potencia]
        chart.lines[0].strokeColor = colors.red
        chart.lines[0].name = 'Potência em kW'
        chart.categoryAxis.categoryNames = [f'{v} km/h' for v in velocidades_kmh]
        chart.categoryAxis.labels.boxAnchor = 'n'
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = max(dados_potencia) * 1.2 if dados_potencia else 10
        chart.valueAxis.valueStep = max(dados_potencia) / 5 if max(dados_potencia) > 0 else 2
        chart.categoryAxis.labels.fontName = 'Helvetica'
        drawing.add(chart)
        story.append(drawing)
    
    except Exception as e:
        story.append(Paragraph(f"<i>Erro ao gerar gráfico: {str(e)}</i>", styles['BodyStyle']))

    doc.build(story)
    return response