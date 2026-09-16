import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import sys
import subprocess
import os
import math
import tempfile
from fpdf import FPDF


def processar_ensaio(dados_curva, d0, L0, df, Lf):
    # Cálculo da área para seção circular
    A0 = (math.pi * (d0 ** 2)) / 4
    Af = (math.pi * (df ** 2)) / 4

    alongamento_pct = ((Lf - L0) / L0) * 100
    estriccao_pct = ((A0 - Af) / A0) * 100

    carga_max_n = 0.0
    desloc_max = 0.0
    
    historico_tensoes = []
    historico_deformacoes = []

    for carga_kn, desloc_mm in dados_curva:
        carga_n = carga_kn * 1000
        tensao_n_mm2 = carga_n / A0
        deformacao_pct = (desloc_mm / L0) * 100
        
        historico_tensoes.append(tensao_n_mm2)
        historico_deformacoes.append(deformacao_pct)

        if carga_n > carga_max_n:
            carga_max_n = carga_n
        if desloc_mm > desloc_max:
            desloc_max = desloc_mm

    sigma_max = carga_max_n / A0

    tensao_escoamento = 0.0
    deformacao_escoamento = 0.0
    if len(historico_tensoes) > 5:
        delta_sigma = historico_tensoes[5] - historico_tensoes[1]
        delta_eps = (historico_deformacoes[5] - historico_deformacoes[1]) / 100
        E = delta_sigma / delta_eps if delta_eps != 0 else 0

        for eps_pct, sigma in zip(historico_deformacoes, historico_tensoes):
            eps_abs = eps_pct / 100
            sigma_reta = E * (eps_abs - 0.002) 
            if sigma_reta >= sigma and eps_abs > 0.002:
                tensao_escoamento = sigma
                deformacao_escoamento = eps_pct
                break
                
    if tensao_escoamento == 0.0:
        tensao_escoamento = sigma_max 
        deformacao_escoamento = historico_deformacoes[historico_tensoes.index(sigma_max)]

    carga_escoamento_n = tensao_escoamento * A0
    razao_elastica = tensao_escoamento / sigma_max if sigma_max > 0 else 0

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(historico_deformacoes, historico_tensoes, color='#1f77b4', linewidth=2, label='Curva de Tração')
    
    idx_max = historico_tensoes.index(sigma_max)
    ax.scatter(historico_deformacoes[idx_max], sigma_max, color='red', zorder=5, 
               label=f'Tensão Máxima ({sigma_max:.1f} N/mm²)')
    ax.scatter(deformacao_escoamento, tensao_escoamento, color='orange', zorder=5, 
               label=f'Escoamento 0.2% ({tensao_escoamento:.1f} N/mm²)')

    ax.set_title('Curva Tensão-Deformação de Engenharia (Corpo Cilíndrico)', fontsize=13, fontweight='bold')
    ax.set_xlabel('Deformação (%)', fontsize=11)
    ax.set_ylabel('Tensão (N/mm²)', fontsize=11)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(loc='lower right')
    fig.tight_layout()

    resultados = {
        "A0": A0, "Af": Af,
        "carga_max_n": carga_max_n,
        "carga_escoamento_n": carga_escoamento_n,
        "sigma_max": sigma_max,
        "tensao_escoamento": tensao_escoamento,
        "razao_elastica": razao_elastica,
        "desloc_max": desloc_max,
        "alongamento_pct": alongamento_pct,
        "estriccao_pct": estriccao_pct
    }
    
    return resultados, fig


def gerar_pdf_relatorio(resultados, d0, L0, df, Lf, fig):
    """Gera um relatório PDF formatado com tabelas e o gráfico da curva."""
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "RELATÓRIO DE ENSAIO DE TRAÇÃO", ln=True, align="C")
    pdf.set_font("Helvetica", 'I', 11)
    pdf.cell(0, 6, "Norma ASTM E8 / E8M - Corpo de Prova Cilíndrico", ln=True, align="C")
    pdf.ln(6)
    
    # Seção 1: Geometria
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, "1. Dimensões do Corpo de Prova", ln=True)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(60, 7, "Parâmetro", border=1, fill=True)
    pdf.cell(45, 7, "Inicial", border=1, fill=True, align='C')
    pdf.cell(45, 7, "Final", border=1, fill=True, align='C')
    pdf.cell(40, 7, "Variação", border=1, fill=True, align='C', ln=True)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(60, 6, "Diâmetro (mm)", border=1)
    pdf.cell(45, 6, f"{d0:.2f}", border=1, align='C')
    pdf.cell(45, 6, f"{df:.2f}", border=1, align='C')
    pdf.cell(40, 6, f"{df - d0:+.2f}", border=1, align='C', ln=True)
    
    pdf.cell(60, 6, "Comprimento Útil (mm)", border=1)
    pdf.cell(45, 6, f"{L0:.2f}", border=1, align='C')
    pdf.cell(45, 6, f"{Lf:.2f}", border=1, align='C')
    pdf.cell(40, 6, f"{Lf - L0:+.2f}", border=1, align='C', ln=True)
    
    pdf.cell(60, 6, "Área Transversal (mm²)", border=1)
    pdf.cell(45, 6, f"{resultados['A0']:.2f}", border=1, align='C')
    pdf.cell(45, 6, f"{resultados['Af']:.2f}", border=1, align='C')
    pdf.cell(40, 6, f"{resultados['Af'] - resultados['A0']:+.2f}", border=1, align='C', ln=True)
    
    pdf.ln(6)
    
    # Seção 2: Propriedades Mecânicas
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, "2. Propriedades Mecânicas Obtidas", ln=True)
    
    pdf.set_font("Helvetica", 'B', 9)
    pdf.cell(90, 7, "Propriedade Analisada", border=1, fill=True)
    pdf.cell(50, 7, "Valor Obtido", border=1, fill=True, align='C')
    pdf.cell(50, 7, "Unidade de Medida", border=1, fill=True, align='C', ln=True)
    
    pdf.set_font("Helvetica", "", 9)
    propriedades = [
        ("Área Inicial (A0)", f"{resultados['A0']:.2f}", "mm²"),
        ("Carga de Escoamento (Fe)", f"{resultados['carga_escoamento_n']:.1f}", "N"),
        ("Carga Máxima (Fmax)", f"{resultados['carga_max_n']:.1f}", "N"),
        ("Tensão de Escoamento (0,2%)", f"{resultados['tensao_escoamento']:.1f}", "N/mm² (MPa)"),
        ("Tensão Máxima (UTS / σ_max)", f"{resultados['sigma_max']:.1f}", "N/mm² (MPa)"),
        ("Razão Elástica", f"{resultados['razao_elastica']:.2f}", "-"),
        ("Alongamento Final (EL)", f"{resultados['alongamento_pct']:.1f}", "%"),
        ("Estricção / Redução de Área (RA)", f"{resultados['estriccao_pct']:.1f}", "%")
    ]
    
    for prop, val, uni in propriedades:
        pdf.cell(90, 6, prop, border=1)
        pdf.cell(50, 6, val, border=1, align='C')
        pdf.cell(50, 6, uni, border=1, align='C', ln=True)
        
    pdf.ln(6)
    
    # Seção 3: Gráfico Tensão x Deformação
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 8, "3. Curva Tensão - Deformação de Engenharia", ln=True)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        fig.savefig(tmpfile.name, format="png", dpi=200, bbox_inches="tight")
        tmp_path = tmpfile.name
        
    pdf.image(tmp_path, x=15, w=180)
    os.remove(tmp_path)
    
    pdf_out = pdf.output()
    if isinstance(pdf_out, str):
        return pdf_out.encode('latin1')
    return bytes(pdf_out)


# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Análise de Ensaio de Tração - Cilíndrico", layout="wide")

st.title("📈 Análise de Ensaio de Tração - Cilíndrico (ASTM E8M)")

st.sidebar.header("Parâmetros Iniciais e Finais")
d0 = st.sidebar.number_input("Diâmetro Inicial - d0 (mm)", value=12.50, step=0.01)
L0 = st.sidebar.number_input("Comprimento Útil Inicial - L0 (mm)", value=50.00, step=0.10)
st.sidebar.divider()
df = st.sidebar.number_input("Diâmetro Final - df (mm)", value=8.50, step=0.01)
Lf = st.sidebar.number_input("Comprimento Útil Final - Lf (mm)", value=58.20, step=0.10)

col_input, col_btn = st.columns([2, 1])

with col_input:
    st.subheader("Dados Brutos")
    dados_input = st.text_area(
        "Cole as colunas de Carga (kN) e Deslocamento (mm) separadas por espaço ou tabulação:",
        value="0.264  0.004\n0.613  0.010\n0.932  0.016\n1.251  0.022\n1.566  0.027", 
        height=200
    )

with col_btn:
    st.write("") 
    st.write("") 
    processar = st.button("Processar Ensaio", type="primary", use_container_width=True)

st.divider()

if processar and dados_input:
    dados_ensaio = []
    for linha in dados_input.strip().split("\n"):
        valores = linha.split()
        if len(valores) == 2:
            try:
                dados_ensaio.append((float(valores[0]), float(valores[1])))
            except ValueError:
                continue
    
    if len(dados_ensaio) > 0:
        resultados, fig = processar_ensaio(dados_ensaio, d0, L0, df, Lf)
        
        col_grafico, col_res1, col_res2 = st.columns([2, 1, 1])
        
        with col_grafico:
            st.pyplot(fig)
            
        with col_res1:
            st.subheader("Resultados Gerais")
            st.metric("Área Inicial (A0)", f"{resultados['A0']:.2f} mm²")
            st.metric("Carga Máxima", f"{resultados['carga_max_n']:.1f} N")
            st.metric("Tensão Máxima (UTS)", f"{resultados['sigma_max']:.1f} N/mm²")
            
        with col_res2:
            st.subheader("Escoamento e Fratura")
            st.metric("Carga Escoamento", f"{resultados['carga_escoamento_n']:.1f} N")
            st.metric("Tensão Escoamento", f"{resultados['tensao_escoamento']:.1f} N/mm²")
            st.metric("Razão Elástica", f"{resultados['razao_elastica']:.2f}")
            st.metric("Estricção (RA)", f"{resultados['estriccao_pct']:.1f} %")
            
        st.subheader("📋 Tabela Resumo")
        
        tabela_resultados = pd.DataFrame({
            "Propriedade Analisada": [
                "Área Inicial (A0)", 
                "Carga de Escoamento (Fe)",
                "Carga Máxima (Fmax)", 
                "Tensão de Escoamento (0,2%)", 
                "Tensão Máxima (UTS)", 
                "Razão Elástica", 
                "Alongamento Final (EL)",
                "Estricção / Redução de Área (RA)"
            ],
            "Valor Obtido": [
                f"{resultados['A0']:.2f}", 
                f"{resultados['carga_escoamento_n']:.1f}",
                f"{resultados['carga_max_n']:.1f}", 
                f"{resultados['tensao_escoamento']:.1f}", 
                f"{resultados['sigma_max']:.1f}", 
                f"{resultados['razao_elastica']:.2f}", 
                f"{resultados['alongamento_pct']:.1f}",
                f"{resultados['estriccao_pct']:.1f}"
            ],
            "Unidade de Medida": ["mm²", "N", "N", "N/mm²", "N/mm²", "-", "%", "%"]
        })
        
        st.table(tabela_resultados)
        
        st.divider()
        st.subheader("📄 Exportar Relatório")
        
        pdf_bytes = gerar_pdf_relatorio(resultados, d0, L0, df, Lf, fig)
        
        st.download_button(
            label="📥 Baixar Relatório em PDF",
            data=pdf_bytes,
            file_name="Relatorio_Ensaio_Tracao_Cilindrico.pdf",
            mime="application/pdf",
            type="primary"
        )
            
    else:
        st.error("Formato de dados inválido. Certifique-se de usar números separados por espaço.")

if __name__ == "__main__":
    if os.environ.get("STREAMLIT_RODANDO") != "true":
        os.environ["STREAMLIT_RODANDO"] = "true"
        subprocess.run([sys.executable, "-m", "streamlit", "run", sys.argv[0]])
        sys.exit()