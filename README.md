# 🚜 Tractor-Implement: Web System to Estimate Efficiency Torque and Lastro calculator

O **TractionLab** é uma plataforma de engenharia especializada, desenvolvida em Django, para modelar e otimizar a interação entre tratores agrícolas e implementos de tração. Utilizando teorias clássicas da mecânica dos solos, o sistema prediz a força de tração, a patinagem e a eficiência tratória global.

---

## 🔬 Fundamentação Científica

O motor de cálculo deste projeto implementa modelos matemáticos consolidados para a interação solo-ferramenta:

* **Equação de Falha do Solo de Reece**: Utilizada para cálculos fundamentais de resistência do solo.
* **Teoria de Godwin & Spoor**: Aplicada para ferramentas estreitas (hastes), incluindo o cálculo da **Profundidade Crítica (dc)** para identificar a transição entre a falha crescente e a falha lateral do solo.
* **Mecânica de Discos**: Modelagem especializada para implementos de disco, considerando ângulos de varredura (sweep) e clareira (clearance).
* **Eficiência de Tração**: Algoritmos de otimização para lastreamento ideal, patinagem e demanda de potência.

## 🚀 Funcionalidades

* **Banco de Dados de Solos Dinâmico**: Gerencie propriedades como coesão ($c$), ângulo de atrito interno ($\phi$) e peso específico ($\gamma$).
* **Modelagem Inteligente de Implementos**: Suporte para **Hastes/Dentes** e **Discos** com entradas geométricas específicas (ângulo de ataque, valor m, raio).
* **Otimização de Performance**: Calcula:
    * Eficiência Trativa (%)
    * Patinagem Otimizada
    * Lastreamento Ideal (kg)
    * Potência Requerida no Motor (cv)
* **Relatórios Técnicos**: Geração automatizada de laudos em PDF via *ReportLab*.

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python 3.x / Django 4.x
* **Cálculos:** NumPy / Decimal API (para alta precisão numérica)
* **Relatórios:** ReportLab
* **Arquitetura:** MVC com camadas de serviço especializadas para a modelagem matemática.

## 🔧 Instalação

1. **Clone o repositório**:
   ```bash
   git clone [https://github.com/andre-bandeli/traction-lab.git](https://github.com/andre-bandeli/traction-lab.git)

2. **Configure o Ambiente**:
   ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # No Windows: venv\Scripts\activate
    pip install -r requirements.txt

2. **Execute as Migrações e o Servidor**:
   ```bash
    python manage.py migrate
    python manage.py runserver
    python manage.py createsuperuser
## 📈 Roadmap

[ ] Integração com dados de GPS/GIS para mapeamento espacial de tração.

[ ] Endpoints de API para integração com sensores IoT (AgTech).

[ ] Implementação de testes unitários para casos de borda em falhas de solo.

---
> Desenvolvido por André L. Bandeli Jr – Graduando em Engenharia Agrícola (UNICAMP) | Técnico Mecatrônico (Cotuca/Unicamp).