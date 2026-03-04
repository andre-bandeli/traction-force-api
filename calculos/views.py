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

G = Decimal('9.81')

SOLO_REF_DATA = {
    'argiloso': {
        'coesao': Decimal('17.5'), 'adesao': Decimal('15'),
        'peso_especifico': Decimal('17.0'), 'angulo_atrito_interno': Decimal('18'),
        'sobrecarga': Decimal('15'), 'indice_cone': Decimal('800'),
    },
    'arenoso': {
        'coesao': Decimal('2.5'), 'adesao': Decimal('0'),
        'peso_especifico': Decimal('16.0'), 'angulo_atrito_interno': Decimal('32'),
        'sobrecarga': Decimal('10'), 'indice_cone': Decimal('350'),
    },
    'siltoso': {
        'coesao': Decimal('10.0'), 'adesao': Decimal('8.0'),
        'peso_especifico': Decimal('14.5'), 'angulo_atrito_interno': Decimal('27'),
        'sobrecarga': Decimal('12'), 'indice_cone': Decimal('600'),
    },
    'franco_arenoso': {
        'coesao': Decimal('5.0'), 'adesao': Decimal('2.0'),
        'peso_especifico': Decimal('15.5'), 'angulo_atrito_interno': Decimal('29'),
        'sobrecarga': Decimal('10'), 'indice_cone': Decimal('450'),
    },
    'franco_siltoso': {
        'coesao': Decimal('12.0'), 'adesao': Decimal('10.0'),
        'peso_especifico': Decimal('14.0'), 'angulo_atrito_interno': Decimal('25'),
        'sobrecarga': Decimal('12'), 'indice_cone': Decimal('700'),
    },
    'franco_argiloso': {
        'coesao': Decimal('15.0'), 'adesao': Decimal('12.0'),
        'peso_especifico': Decimal('16.0'), 'angulo_atrito_interno': Decimal('20'),
        'sobrecarga': Decimal('15'), 'indice_cone': Decimal('1000'),
    },
    'pesado_argiloso': {
        'coesao': Decimal('20.0'), 'adesao': Decimal('18.0'),
        'peso_especifico': Decimal('19.0'), 'angulo_atrito_interno': Decimal('18'),
        'sobrecarga': Decimal('20'), 'indice_cone': Decimal('1200'),
    },
    'seco_arenoso': {
        'coesao': Decimal('1.0'), 'adesao': Decimal('0'),
        'peso_especifico': Decimal('17.0'), 'angulo_atrito_interno': Decimal('35'),
        'sobrecarga': Decimal('8'), 'indice_cone': Decimal('500'),
    },
    'humus': {
        'coesao': Decimal('8.0'), 'adesao': Decimal('6.0'),
        'peso_especifico': Decimal('11.0'), 'angulo_atrito_interno': Decimal('30'),
        'sobrecarga': Decimal('5'), 'indice_cone': Decimal('300'),
    },
}

TRATOR_REF_DATA = {
    'John Deere 6100J':     {'potencia_motor': Decimal('100'), 'massa_trator': Decimal('5300'),  'raio_roda': Decimal('0.762')},
    'John Deere 7200J':     {'potencia_motor': Decimal('200'), 'massa_trator': Decimal('8500'),  'raio_roda': Decimal('0.867')},
    'Massey Ferguson 4292': {'potencia_motor': Decimal('92'),  'massa_trator': Decimal('4000'),  'raio_roda': Decimal('0.762')},
    'John Deere 8370R':     {'potencia_motor': Decimal('370'), 'massa_trator': Decimal('14000'), 'raio_roda': Decimal('0.972')},
    'Case IH Magnum 340':   {'potencia_motor': Decimal('340'), 'massa_trator': Decimal('12000'), 'raio_roda': Decimal('0.972')},
    'Valtra A840':          {'potencia_motor': Decimal('85'),  'massa_trator': Decimal('3200'),  'raio_roda': Decimal('0.660')},
    'New Holland TL75E':    {'potencia_motor': Decimal('75'),  'massa_trator': Decimal('3000'),  'raio_roda': Decimal('0.762')},
    'Fendt 1050 Vario':     {'potencia_motor': Decimal('517'), 'massa_trator': Decimal('14000'), 'raio_roda': Decimal('1.038')},

}

IMPLEMENTO_REF_DATA = {
    'arado_aiveca': {
        'tipo': 'dente',
        'nome': 'Arado de Aiveca',
        'angulo_ataque': Decimal('45'),
        'angulo_atrito_implemento': Decimal('15'),
        'm_val': Decimal('2.5')
    },
    'escarificador': {
        'tipo': 'dente',
        'nome': 'Escarificador',
        'angulo_ataque': Decimal('25'),
        'angulo_atrito_implemento': Decimal('15'),
        'm_val': Decimal('3.2')
    },
    'grade_disco': {
        'tipo': 'disco',
        'nome': 'Grade de Disco',
        'raio_disco': Decimal('30'),
        'angulo_varredura': Decimal('20'),
        'angulo_clareira': Decimal('45'),
        'angulo_ataque': Decimal('20'),
        'angulo_atrito_implemento': Decimal('10')
    },
    'subsolador': {
        'tipo': 'dente',
        'nome': 'Subsolador',
        'angulo_ataque': Decimal('25'),
        'angulo_atrito_implemento': Decimal('15'),
        'm_val': Decimal('3.5')
    },
    'enxada_rotativa': {
        'tipo': 'dente',
        'nome': 'Enxada Rotativa',
        'angulo_ataque': Decimal('30'),
        'angulo_atrito_implemento': Decimal('12'),
        'm_val': Decimal('2.0')
    },
    'arado_de_disco': {
        'tipo': 'disco',
        'nome': 'Arado de Disco',
        'raio_disco': Decimal('40'),
        'angulo_varredura': Decimal('15'),
        'angulo_clareira': Decimal('40'),
        'angulo_ataque': Decimal('25'),
        'angulo_atrito_implemento': Decimal('12')
    },
    'arado_fixo': {
        'tipo': 'dente',
        'nome': 'Arado Fixo',
        'angulo_ataque': Decimal('50'),
        'angulo_atrito_implemento': Decimal('15'),
        'm_val': Decimal('2.8')
    },
    'cultivador': {
        'tipo': 'dente',
        'nome': 'Cultivador',
        'angulo_ataque': Decimal('20'),
        'angulo_atrito_implemento': Decimal('10'),
        'm_val': Decimal('3.0')
    },
    'grade_niveladora': {
        'tipo': 'disco',
        'nome': 'Grade Niveladora',
        'raio_disco': Decimal('25'),
        'angulo_varredura': Decimal('15'),
        'angulo_clareira': Decimal('30'),
        'angulo_ataque': Decimal('15'),
        'angulo_atrito_implemento': Decimal('8')
    },
    'sulcador': {
        'tipo': 'dente',
        'nome': 'Sulcador',
        'angulo_ataque': Decimal('35'),
        'angulo_atrito_implemento': Decimal('15'),
        'm_val': Decimal('2.5')
    }
}


def _calculate_beta_critico(m, alpha):
    try:
        cot_alpha = Decimal(1) / Decimal(math.tan(alpha)) if math.tan(alpha) != 0 else Decimal('inf')
        if m <= cot_alpha:
            raise ValueError("m deve ser maior que cot(α) para calcular βcrit")
        beta_crit = Decimal(math.atan(1 / (m - cot_alpha)))
        return beta_crit
    except (ValueError, ZeroDivisionError) as e:
        raise Exception(f"Erro no cálculo de βcrit: {str(e)}")


def _calculate_coefficients(solo, implemento, d, w):
    try:
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

        beta = _calculate_beta_critico(m, float(alpha_rad))

        cot_alpha = Decimal(1) / Decimal(math.tan(float(alpha_rad))) if math.tan(float(alpha_rad)) != 0 else Decimal('inf')
        cot_beta_fi = Decimal(1) / Decimal(math.tan(float(beta + fi_rad))) if math.tan(float(beta + fi_rad)) != 0 else Decimal('inf')

        cos_alpha_delta = Decimal(math.cos(float(alpha_rad + delta_rad)))
        sin_alpha_delta = Decimal(math.sin(float(alpha_rad + delta_rad)))

        denominador = (cos_alpha_delta + sin_alpha_delta * cot_beta_fi)
        if denominador == 0:
            raise ZeroDivisionError("Denominador zero no cálculo dos coeficientes.")

        r = d_dec * (cot_alpha + cot_beta_fi)

        Ny = (r / (Decimal('2') * d_dec)) / denominador
        Nc = (Decimal('1') + (Decimal('1') / Decimal(math.tan(float(beta)))) * cot_beta_fi) / denominador if math.tan(float(beta)) != 0 else Decimal('inf')
        Nq = (r / d_dec) / denominador
        Na = (Decimal('1') - cot_alpha * cot_beta_fi) / denominador

        sin_fi = Decimal(math.sin(float(fi_rad)))
        tan_fi = Decimal(math.tan(float(fi_rad))) if math.tan(float(fi_rad)) != 0 else Decimal('0.001')

        Kp = (Decimal('1') + sin_fi) / (Decimal('1') - sin_fi)
        exp_pi_tan_fi = Decimal(math.exp(math.pi * float(tan_fi)))

        Nc_prime = ((Kp * exp_pi_tan_fi) - Decimal('1')) / tan_fi
        Nq_prime = Kp

        eta = (Decimal(math.pi) / Decimal('4')) - (fi_rad / Decimal('2'))
        Nq_prime_eta = Kp * Decimal(math.exp(math.pi * math.tan(float(eta))))

        return Ny, Nc, Nq, Na, Nc_prime, Nq_prime, Nq_prime_eta, beta
    except Exception as e:
        raise Exception(f"Erro nos cálculos de coeficientes: {str(e)}")


def _calculate_velocidade_critica(w, d):
    try:
        vcrit = Decimal(math.sqrt(5 * float(G) * float(w + Decimal('0.6') * d)))
        return vcrit
    except Exception as e:
        raise Exception(f"Erro no cálculo da velocidade crítica: {str(e)}")


def _calculate_profundidade_critica(solo, implemento, d, w):
    try:
        c = Decimal(str(solo.coesao))
        fi = math.radians(Decimal(str(solo.angulo_atrito_interno)))
        gama = Decimal(str(solo.peso_especifico))
        q_sobrecarga = Decimal(str(solo.sobrecarga))
        ca = Decimal(str(solo.adesao))
        alpha = math.radians(Decimal(str(implemento.angulo_ataque)))
        delta = math.radians(Decimal(str(implemento.angulo_atrito_implemento)))
        m = Decimal(str(implemento.m_val))

        Ny, Nc, Nq, Na, Nc_prime, Nq_prime, Nq_prime_eta, beta = _calculate_coefficients(solo, implemento, d, w)

        cot_alpha = Decimal(1) / Decimal(math.tan(alpha)) if math.tan(alpha) != 0 else Decimal('inf')

        sin_acos_term = Decimal(math.sin(math.acos(float(cot_alpha / m)))) if m != 0 and abs(cot_alpha / m) <= 1 else Decimal(0)

        a = Decimal('3') * gama * Ny * Decimal(math.sin(alpha + delta)) * m * sin_acos_term

        sin_fi = Decimal(math.sin(fi))
        b = (Decimal('2') * (c * Nc + q_sobrecarga * Nq) * m * sin_acos_term * Decimal(math.sin(alpha + delta)) +
             Decimal('2') * gama * Ny * Decimal(math.sin(alpha + delta)) * w -
             (Decimal('1') - sin_fi) * gama * w * Nq_prime)

        c_prime = ((c * Nc + ca * Na + q_sobrecarga * Nq) * Decimal(math.sin(alpha + delta)) * w +
                   ca * c * Decimal(math.cos(alpha)) - w * c * Nc_prime)

        discriminant = b**2 - Decimal('4') * a * c_prime

        if discriminant < 0:
            return d

        sqrt_discriminant = Decimal(math.sqrt(float(discriminant)))

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

    if d_over_w < Decimal('0.5'):
        Ny, Nc, Nq, _, _, _, _, _ = _calculate_coefficients(solo, implemento, d, w)
        P = (gama * d**2 * Ny + c * d * Nc + q_sobrecarga * d * Nq) * w

    elif Decimal('1') <= d_over_w <= Decimal('6'):
        largura_efetiva = w + d * (m - (Decimal('1') / Decimal('3')) * (m - Decimal('1')))

        if incluir_velocidade and velocidade_kmh is not None:
            v_ms = Decimal(str(velocidade_kmh)) / Decimal('3.6')
            v_crit = _calculate_velocidade_critica(w, d)
            Ny, Nc, Nq, Na, _, _, _, _ = _calculate_coefficients(solo, implemento, d, w)

            if v_ms < v_crit:
                P = (gama * d**2 * Ny + c * d * Nc) * largura_efetiva * Decimal(math.sin(alpha + delta))
            else:
                termo_estatico = (gama * d**2 * Ny + c * d * Nc) * largura_efetiva
                termo_velocidade = (gama * v_ms**2 / G) * Na * d * (w + Decimal('0.6') * d)
                P = (termo_estatico + termo_velocidade) * Decimal(math.sin(alpha + delta))
        else:
            Ny, Nc, Nq, Na, _, _, _, _ = _calculate_coefficients(solo, implemento, d, w)
            P = (gama * d**2 * Ny + c * d * Nc + ca * d * Na + q_sobrecarga * d * Nq) * largura_efetiva * Decimal(math.sin(alpha + delta))

    else:
        dc = _calculate_profundidade_critica(solo, implemento, d, w)
        profundidade_critica = dc

        Ny, Nc, Nq, Na, Nc_prime, Nq_prime, _, _ = _calculate_coefficients(solo, implemento, dc, w)
        largura_efetiva = w + dc * (m - (Decimal('1') / Decimal('3')) * (m - Decimal('1')))

        if dc >= d:
            if incluir_velocidade and velocidade_kmh is not None:
                v_ms = Decimal(str(velocidade_kmh)) / Decimal('3.6')
                v_crit = _calculate_velocidade_critica(w, d)

                if v_ms < v_crit:
                    P = (gama * dc**2 * Ny + c * dc * Nc) * largura_efetiva * Decimal(math.sin(alpha + delta))
                else:
                    termo_estatico = (gama * dc**2 * Ny + c * dc * Nc) * largura_efetiva
                    termo_velocidade = (gama * v_ms**2 / G) * Na * dc * (w + Decimal('0.6') * dc)
                    P = (termo_estatico + termo_velocidade) * Decimal(math.sin(alpha + delta))
            else:
                P = (gama * dc**2 * Ny + c * dc * Nc + ca * dc * Na + q_sobrecarga * dc * Nq) * largura_efetiva * Decimal(math.sin(alpha + delta))
        else:
            if incluir_velocidade and velocidade_kmh is not None:
                v_ms = Decimal(str(velocidade_kmh)) / Decimal('3.6')
                v_crit = _calculate_velocidade_critica(w, d)

                if v_ms < v_crit:
                    H = (gama * dc**2 * Ny + c * dc * Nc) * largura_efetiva * Decimal(math.sin(alpha + delta))
                else:
                    termo_estatico = (gama * dc**2 * Ny + c * dc * Nc) * largura_efetiva
                    termo_velocidade = (gama * v_ms**2 / G) * Na * dc * (w + Decimal('0.6') * dc)
                    H = (termo_estatico + termo_velocidade) * Decimal(math.sin(alpha + delta))
            else:
                H = (gama * dc**2 * Ny + c * dc * Nc + ca * dc * Na + q_sobrecarga * dc * Nq) * largura_efetiva * Decimal(math.sin(alpha + delta))

            sin_fi = Decimal(math.sin(fi))
            Q = (w * c * Nc_prime * (d - dc) +
                 Decimal('0.5') * (Decimal('1') - sin_fi) * gama * w * Nq_prime * (d**2 - dc**2))

            P = H + Q

    return P, profundidade_critica


def _calculate_multiple_tines(solo, implemento, P_single, profundidade_utilizada):
    n = implemento.numero_ferramentas
    s = Decimal(str(implemento.espacamento))
    d = profundidade_utilizada

    if d < s / Decimal('2'):
        D = P_single * n
        return D
    else:
        d_i = d - s / Decimal('2')

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
        D = (P_single * n) - ((n - 1) * P_virtual)
        return D


def _calculate_disc_force(solo, implemento):
    try:
        R = float(implemento.raio_disco)
        theta_deg = float(implemento.angulo_varredura)
        theta_rad = math.radians(theta_deg)
        lambd_deg = float(implemento.angulo_clareira)
        lambd_rad = math.radians(lambd_deg)
        d = float(implemento.profundidade)

        if hasattr(implemento, 'largura') and implemento.largura:
            x = float(implemento.largura)
        else:
            x = R

        c = float(solo.coesao)
        fi_rad = math.radians(float(solo.angulo_atrito_interno))
        gama = float(solo.peso_especifico)
        ca = float(solo.adesao)

        alpha_disc_rad = math.radians(float(implemento.angulo_ataque))
        delta_disc_rad = math.radians(float(implemento.angulo_atrito_implemento))

        W = 2 * math.sqrt(2 * R * d - d**2)
        l = W * math.sin(theta_rad)

        if hasattr(implemento, 'm_val') and implemento.m_val:
            m_disc = float(implemento.m_val)
        else:
            cot_alpha_est = math.cos(alpha_disc_rad) / math.sin(alpha_disc_rad) if math.sin(alpha_disc_rad) != 0 else 10.0
            m_disc = max(cot_alpha_est + 1.01, 1.5)

        tan_fi = math.tan(fi_rad)
        cot_alpha = math.cos(alpha_disc_rad) / math.sin(alpha_disc_rad) if math.sin(alpha_disc_rad) != 0 else 0.001

        beta_crit = math.atan(1.0 / (m_disc - cot_alpha))

        cot_beta_fi = 1.0 / math.tan(beta_crit + fi_rad) if math.tan(beta_crit + fi_rad) != 0 else 0.001

        r = d * (cot_alpha + 1.0 / math.tan(beta_crit))
        denom = math.cos(alpha_disc_rad + delta_disc_rad) + math.sin(alpha_disc_rad + delta_disc_rad) * cot_beta_fi

        if denom == 0:
            raise ZeroDivisionError("Denominador zero no cálculo dos coeficientes do disco.")

        Ny = (r / (2.0 * d)) / denom
        Nc = (1.0 + (1.0 / math.tan(beta_crit)) * cot_beta_fi) / denom if math.tan(beta_crit) != 0 else 0.0
        Nq = (r / d) / denom
        Nca = (1.0 - cot_alpha * cot_beta_fi) / denom

        q_surface = (R - d) * gama * math.sin(theta_rad)

        P_interno = (gama * d**2 * Ny + c * d * Nc + ca * d * Nca + q_surface * d * Nq) * l

        Dp_interno = P_interno * math.sin(alpha_disc_rad + delta_disc_rad) * math.sin(theta_rad)
        Vp_interno = -P_interno * math.cos(alpha_disc_rad + delta_disc_rad)
        Sp_interno = P_interno * math.sin(alpha_disc_rad + delta_disc_rad) * math.cos(theta_rad)

        A = math.pi * R * x
        sin_fi = math.sin(fi_rad)
        Kp = (1 + sin_fi) / (1 - sin_fi)
        exp_term = math.exp(math.pi * tan_fi)
        Nc_prime = ((Kp * exp_term) - 1) / tan_fi if tan_fi != 0 else 0
        q_prime = Nc_prime * c

        if theta_deg < lambd_deg:
            Vs_externo = q_prime * A * math.sin(math.pi * (lambd_deg - theta_deg) / (2 * lambd_deg))
        else:
            Vs_externo = 0

        Hs_externo = Vs_externo * math.tan(alpha_disc_rad - delta_disc_rad)
        Ds_externo = Hs_externo * math.sin(lambd_rad - theta_rad)
        Ss_externo = Hs_externo * math.cos(lambd_rad - theta_rad)

        D_total = Decimal(str(Dp_interno + Ds_externo))
        V_total = Decimal(str(Vp_interno + Vs_externo))
        S_total = Decimal(str(Sp_interno - Ss_externo))

        return D_total, V_total, S_total

    except Exception as e:
        raise Exception(f"Erro nos cálculos para implementos de disco: {str(e)}")


def _optimize_tractor(trator, solo, forca_tracao, velocidade_kmh):
    try:
        massa_kg = Decimal(str(trator.massa_trator))
        lastro = Decimal(str(trator.lastro_atual)) if trator.lastro_atual is not None else Decimal('0')
        raio_roda = Decimal(str(trator.raio_roda))
        h_barra = Decimal(str(trator.altura_barra_tracao))
        L = Decimal(str(trator.distancia_entre_eixos))
        peso_dianteiro = Decimal(str(trator.peso_dianteiro))
        indice_cone = Decimal(str(solo.indice_cone))
        b_pneu = raio_roda * Decimal('0.346')

        forca_N = forca_tracao * Decimal('1000')
        velocidade_ms = velocidade_kmh / Decimal('3.6')

        peso_total_kN = (massa_kg + lastro) * G / Decimal('1000')
        peso_traseiro_kN = peso_total_kN - peso_dianteiro

        Wd_kN = peso_traseiro_kN + (forca_tracao * h_barra / L)
        Wd_N = Wd_kN * Decimal('1000')

        d_pneu = raio_roda * Decimal('2')
        BN = (indice_cone * b_pneu * d_pneu) / Wd_kN

        GTR = Decimal('0.75') * (Decimal('1') - Decimal(str(math.exp(-0.3 * float(BN)))))
        MRR = Decimal('0.04') + Decimal('0.04') / BN

        NTR = forca_N / Wd_N
        GTR_real = NTR + MRR

        if GTR_real >= GTR:
            TRR = Decimal('1.0')
        else:
            ratio = min(GTR_real / GTR, Decimal('0.9999'))
            arg = Decimal('1') - ratio
            if arg <= 0:
                TRR = Decimal('1.0')
            else:
                TRR = -Decimal(str(math.log(float(arg)))) / Decimal('0.3') / BN

        TRR = max(Decimal('0'), min(TRR, Decimal('1')))

        patinagem = TRR * Decimal('100')
        TE = (NTR / GTR_real) * (Decimal('1') - TRR) if GTR_real > Decimal('0') else Decimal('0')
        TE_pct = max(min(TE * Decimal('100'), Decimal('100')), Decimal('0'))

        potencia_kW = (forca_N * velocidade_ms) / Decimal('1000')
        potencia_necessaria_cv = potencia_kW / Decimal('0.7457')

        NTR_otimo = Decimal('0.45')
        Wd_ideal_N = forca_N / NTR_otimo
        peso_traseiro_ideal_N = Wd_ideal_N - (forca_N * h_barra / L)
        lastro_ideal_kg = max(
            (peso_traseiro_ideal_N / G) - (massa_kg * Decimal('0.60')),
            Decimal('0')
        )

        return {
            'patinagem_calculada': patinagem.quantize(Decimal('0.01')),
            'eficiencia_tracao_calculada': TE_pct.quantize(Decimal('0.01')),
            'potencia_necessaria_cv': potencia_necessaria_cv.quantize(Decimal('0.01')),
            'lastro_ideal_kg': lastro_ideal_kg.quantize(Decimal('0.01')),
        }
    except Exception as e:
        raise Exception(f'Erro na otimização do trator: {e}')

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

            if implemento.tipo == 'dente':
                D_single, profundidade_critica = _calculate_tine_force(
                    solo, implemento, incluir_velocidade, velocidade_kmh
                )

                if implemento.numero_ferramentas and implemento.numero_ferramentas > 1:
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

            if trator and velocidade_kmh:
                resultado_trator = _optimize_tractor(trator, solo, D_implemento, velocidade_kmh)

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


class SimulatedObject:
    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)


def calculadora_simplificada(request):
    resultado_implemento = None
    resultado_trator = {}

    if request.method == 'POST':
        try:
            tipo_solo = request.POST.get('tipo_solo')
            modelo_trator = request.POST.get('modelo_trator')
            tipo_implemento = request.POST.get('tipo_implemento')

            profundidade_m = Decimal(request.POST.get('profundidade')) / Decimal('100')
            largura_m = Decimal(request.POST.get('largura')) / Decimal('100')
            espacamento_m = Decimal(request.POST.get('espacamento', '0')) / Decimal('100')

            numero_ferramentas = int(request.POST.get('numero_ferramentas', '1'))
            velocidade_kmh = Decimal(request.POST.get('velocidade_kmh'))
            lastro_user = Decimal(request.POST.get('lastro', '0'))

            if profundidade_m <= 0 or largura_m <= 0:
                messages.error(request, "Profundidade e Largura de Trabalho devem ser maiores que zero.")
                return redirect('calculadora_simplificada')

            if tipo_implemento == 'grade_disco' and espacamento_m <= 0:
                messages.error(request, "O espaçamento é obrigatório para implementos de disco.")
                return redirect('calculadora_simplificada')

            solo = SimulatedObject(SOLO_REF_DATA[tipo_solo])

            altura_barra = Decimal(request.POST.get('altura_barra_tracao', '0.500'))
            dist_eixos = Decimal(request.POST.get('distancia_entre_eixos', '2.500'))
            peso_dianteiro = Decimal(request.POST.get('peso_dianteiro', '0'))

            trator_data = dict(TRATOR_REF_DATA[modelo_trator])

            trator_data.update({
                'lastro_atual': lastro_user,
                'altura_barra_tracao': altura_barra,
                'distancia_entre_eixos': dist_eixos,
                'peso_dianteiro': peso_dianteiro,
            })
            trator = SimulatedObject(trator_data)

            implemento_data = dict(IMPLEMENTO_REF_DATA[tipo_implemento])
            implemento_data.update({
                'profundidade': profundidade_m,
                'largura': largura_m,
                'espacamento': espacamento_m,
                'numero_ferramentas': numero_ferramentas,
            })
            implemento = SimulatedObject(implemento_data)
            trator = SimulatedObject(trator_data)

            profundidade_critica = None
            if implemento.tipo == 'dente':
                D_single, profundidade_critica = _calculate_tine_force(
                    solo, implemento, True, velocidade_kmh
                )

                if implemento.numero_ferramentas and implemento.numero_ferramentas > 1:
                    w = Decimal(str(implemento.largura))
                    d = Decimal(str(implemento.profundidade))
                    d_over_w = d / w if w > 0 else Decimal('inf')
                    profundidade_para_multiplas = profundidade_critica if d_over_w > Decimal('6') else d
                    D_implemento = _calculate_multiple_tines(solo, implemento, D_single, profundidade_para_multiplas)
                else:
                    D_implemento = D_single
            elif implemento.tipo == 'disco':
                D_implemento, _, _ = _calculate_disc_force(solo, implemento)
            else:
                raise ValueError("Tipo de implemento inválido.")

            resultado_trator = _optimize_tractor(trator, solo, D_implemento, velocidade_kmh)

            context = {
                'solo_opcoes': SOLO_REF_DATA.keys(),
                'trator_opcoes': TRATOR_REF_DATA.keys(),
                'implemento_opcoes': IMPLEMENTO_REF_DATA.keys(),
                'solo': tipo_solo,
                'trator': modelo_trator,
                'implemento': implemento_data['nome'],
                'profundidade': profundidade_m * Decimal('100'),
                'largura': largura_m * Decimal('100'),
                'espacamento': espacamento_m * Decimal('100'),
                'numero_ferramentas': numero_ferramentas,
                'velocidade_kmh': velocidade_kmh,
                'lastro': lastro_user,
                'resultado_implemento': f"{D_implemento:.2f} kN",
                'resultado_trator': resultado_trator,
            }
            return render(request, 'calculos/calculadora_simplificada.html', context)

        except Exception as e:
            messages.error(request, f"Erro no cálculo. Verifique os dados de entrada. Detalhe: {e}")
            return redirect('calculadora_simplificada')

    context = {
        'solo_opcoes': SOLO_REF_DATA.keys(),
        'trator_opcoes': TRATOR_REF_DATA.keys(),
        'implemento_opcoes': IMPLEMENTO_REF_DATA.keys()
    }
    return render(request, 'calculos/calculadora_simplificada.html', context)


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

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='HeaderStyle', fontSize=24, alignment=1, spaceAfter=24, textColor=colors.darkblue, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='TitleStyle', fontSize=18, alignment=1, spaceAfter=12))
    styles.add(ParagraphStyle(name='SubtitleStyle', fontSize=12, alignment=0, spaceAfter=6, textColor=colors.darkblue, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='BodyStyle', fontSize=10, alignment=0, spaceAfter=4))

    story.append(Paragraph("DynaTech", styles['HeaderStyle']))
    story.append(Paragraph("Otimização Trator-Implemento", styles['HeaderStyle']))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Relatório de Cálculo", styles['TitleStyle']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Usuário:</b> {request.user.get_full_name()}", styles['BodyStyle']))
    story.append(Paragraph(f"<b>Data do Cálculo:</b> {calculo.data_criacao.strftime('%d/%m/%Y %H:%M')}", styles['BodyStyle']))
    story.append(Spacer(1, 12))

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
        velocidade_kmh = float(calculo.velocidade_kmh)
        velocidade_ms = velocidade_kmh / 3.6
        story.append(Paragraph(f"<b>Velocidade de Operação:</b> {velocidade_kmh:.2f} km/h ({velocidade_ms:.2f} m/s)", styles['BodyStyle']))

        if calculo.implemento.tipo == 'dente' and d_over_w >= Decimal('1'):
            try:
                v_crit = _calculate_velocidade_critica(w, d)
                v_ms = Decimal(str(calculo.velocidade_kmh)) / Decimal('3.6')
                story.append(Paragraph(f"<b>Velocidade Crítica (Vcrit):</b> {v_crit:.2f} m/s", styles['BodyStyle']))
                if v_ms >= v_crit:
                    story.append(Paragraph("Efeito da adesão por velocidade considerado — modelo Godwin/Wheeler (v ≥ Vcrit)", styles['BodyStyle']))
                else:
                    story.append(Paragraph("Efeito da adesão por velocidade não aplicado (v < Vcrit)", styles['BodyStyle']))
            except:
                pass

    if calculo.implemento.numero_ferramentas and calculo.implemento.numero_ferramentas > 1:
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Análise de Múltiplas Ferramentas:</b>", styles['SubtitleStyle']))
        story.append(Paragraph(f"<b>Número de ferramentas:</b> {calculo.implemento.numero_ferramentas}", styles['BodyStyle']))
        story.append(Paragraph(f"<b>Espaçamento:</b> {calculo.implemento.espacamento} m", styles['BodyStyle']))

        prof_analise = calculo.profundidade_critica if calculo.profundidade_critica else Decimal(str(calculo.implemento.profundidade))
        s = Decimal(str(calculo.implemento.espacamento))

        if prof_analise < s / Decimal('2'):
            story.append(Paragraph("Sem sobreposição entre flancos (d < s/2)", styles['BodyStyle']))
            story.append(Paragraph("Força total = Força unitária × Número de ferramentas", styles['BodyStyle']))
        else:
            story.append(Paragraph("⚠️ Com sobreposição entre flancos (d > s/2)", styles['BodyStyle']))
            story.append(Paragraph("Correção aplicada usando ferramenta virtual — Godwin & O'Dogherty", styles['BodyStyle']))

    story.append(Spacer(1, 12))

    if calculo.trator:
        story.append(Paragraph("<b>Otimização do Trator</b>", styles['SubtitleStyle']))
        story.append(Paragraph("Modelo de tração: Brixius (1987) simplificado — GTR = NTR + MRR, MRR = 0,04, GTR_max = 0,75", styles['BodyStyle']))
        trator_data_pdf = [
            ["Trator:", calculo.trator.nome],
            ["Massa [kg]:", f"{calculo.trator.massa_trator}"],
            ["Potência [CV]:", f"{calculo.trator.potencia_motor}"],
            ["", ""],
            ["Patinagem (TRR) [%]:", f"{calculo.patinagem_calculada:.2f}" if calculo.patinagem_calculada is not None else "N/A"],
            ["Eficiência de Tração (TE) [%]:", f"{calculo.eficiencia_tracao_calculada:.2f}" if calculo.eficiencia_tracao_calculada is not None else "N/A"],
            ["Potência Necessária [CV]:", f"{calculo.potencia_necessaria_cv:.2f}" if calculo.potencia_necessaria_cv is not None else "N/A"],
            ["Lastro Ideal [kg]:", f"{calculo.lastro_ideal_kg:.2f}" if calculo.lastro_ideal_kg is not None else "N/A"]
        ]
        trator_table = Table(trator_data_pdf, colWidths=[3*72, 2*72])
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

    story.append(Spacer(1, 20))
    story.append(Paragraph("Relatório gerado automaticamente pelo Sistema DynaTech.", styles['BodyStyle']))
    story.append(Paragraph("Elaborado por: André Luiz Bandeli Júnior.", styles['BodyStyle']))

    doc.build(story)
    return response