import streamlit as st
import pandas as pd
from io import BytesIO
import requests
import zipfile

st.set_page_config(layout="wide")

st.title("Análise de Produtos Copa Nacional")

# =========================
# TEXTO ÚNICO (ORIGINAL)
# =========================
st.markdown("""
### 📌 Categorias

💰 Top Faturamento → maior valor faturado nos últimos 3 meses + maior valor faturado no mês atual  
🔥 Produto da Vez → maior valor faturado no mês anterior + maior valor faturado no mês atual  
💵 Oportunidade → maior nº de pedidos nos últimos 3 meses + baixa quantidade  
""")

# =========================
# CONFIG
# =========================
MARCAS = [
    "3M", "HERC", "KRONA", "ROMA", "DINAIDER SCHNEIDER", "SCHNEIDER", "STECK",
    "MISTER ABRASIVOS", "MISTER ELETRICOS", "MISTER FERRAMENTAS",
    "MISTER GERAL", "MISTER PARAFUSOS"
]

ESTADOS = ["RS", "SC", "PR"]

file = st.file_uploader("📂 Envie seu arquivo em .xlsx")
st.markdown("🔔 **Observação:** Certifique-se de que a base de dados esteja no formato correto, com as colunas **UF**, **Marca**, **Cod**, **Produto**, **Pedidos**, **Mes**, **Valor**, e **Qtd**.")

# =========================
# FUNÇÕES DE CÁLCULO (IGUAIS)
# =========================
def pick_best(df, group="Marca", score_col=None):
    if df.empty: return df
    if score_col is None: score_col = df.columns[-1]
    df = df.sort_values(score_col, ascending=False)
    return df.groupby(group).head(1)

def top_faturamento(d):
    x = d.groupby(["Mes", "UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    meses = sorted(x["Mes"].unique())
    if len(meses) < 3:
        res = x.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
        res["score"] = res["Valor"]
    else:
        ultimos_3 = meses[-3:]
        resumo = x[x["Mes"].isin(ultimos_3)].groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
        atual = x[x["Mes"] == meses[-1]].groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
        merged = resumo.merge(atual, on=["UF", "Marca", "Cod", "Produto"], how="left", suffixes=("_hist", "_atual"))
        merged["Valor_atual"] = merged["Valor_atual"].fillna(0)
        merged["score"] = merged["Valor_hist"] * 0.6 + merged["Valor_atual"] * 0.4
        res = merged
    return pick_best(res, "Marca", "score")

def produto_vez(d, top_fat):
    x = d.groupby(["Mes", "UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    meses = sorted(x["Mes"].unique())
    if len(meses) < 2: return pd.DataFrame()
    atual = x[x["Mes"] == meses[-1]]
    ant = x[x["Mes"] == meses[-2]]
    merged = atual.merge(ant, on=["UF", "Marca", "Cod", "Produto"], how="left", suffixes=("_atual", "_ant"))
    merged["Valor_ant"] = merged["Valor_ant"].fillna(0)
    merged["score"] = merged[["Valor_atual", "Valor_ant"]].max(axis=1)
    if not top_fat.empty:
        cod_proibidos = top_fat["Cod"].unique()
        merged = merged[~merged["Cod"].isin(cod_proibidos)]
    return pick_best(merged, "Marca", "score")

def oportunidade(d):
    x = d.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False).agg({"Pedidos": "sum", "Qtd": "sum"})
    x["score"] = x["Pedidos"] / (x["Qtd"] + 1)
    return pick_best(x, "Marca", "score")

# =========================
# RENDER (IGUAL)
# =========================
def render(uf, df_global):
    st.markdown(f"## {uf}")
    d_uf = df_global[df_global["UF"] == uf].copy()
    
    marcas_presentes = d_uf["Marca"].unique()
    for m in MARCAS:
        if m not in marcas_presentes:
            st.warning(f"⚠️ Não há dados para a marca **{m}** no estado {uf}.")

    top = top_faturamento(d_uf)
    hot = produto_vez(d_uf, top)
    opp = oportunidade(d_uf)

    lista_excel = []
    lista_dash = []

    for marca in MARCAS:
        m_top = top[top["Marca"] == marca]
        m_hot = hot[hot["Marca"] == marca]
        m_opp = opp[opp["Marca"] == marca]

        cod_t = m_top.iloc[0]["Cod"] if not m_top.empty else "—"
        cod_v = m_hot.iloc[0]["Cod"] if not m_hot.empty else "—"
        cod_o = m_opp.iloc[0]["Cod"] if not m_opp.empty else "—"

        idx = len(lista_excel) + 2 
        
        lista_excel.append({
            "Marca": marca,
            "Top_Cod": cod_t,
            "Top_Prod": m_top.iloc[0]["Produto"] if not m_top.empty else "—",
            "📸 Foto Top": f'=IMAGEM("https://sambaled.com.br/app_imagem/" & B{idx} & ".jpg")' if cod_t != "—" else "—",
            "Vez_Cod": cod_v,
            "Vez_Prod": m_hot.iloc[0]["Produto"] if not m_hot.empty else "—",
            "📸 Foto Vez": f'=IMAGEM("https://sambaled.com.br/app_imagem/" & E{idx} & ".jpg")' if cod_v != "—" else "—",
            "Opp_Cod": cod_o,
            "Opp_Prod": m_opp.iloc[0]["Produto"] if not m_opp.empty else "—",
            "📸 Foto Opp": f'=IMAGEM("https://sambaled.com.br/app_imagem/" & H{idx} & ".jpg")' if cod_o != "—" else "—"
        })

        lista_dash.append({
            "Marca": marca,
            "💰 Top Faturamento": f"{cod_t} - {m_top.iloc[0]['Produto']}" if not m_top.empty else "—",
            "🔥 Produto da Vez": f"{cod_v} - {m_hot.iloc[0]['Produto']}" if not m_hot.empty else "—",
            "💵 Oportunidade": f"{cod_o} - {m_opp.iloc[0]['Produto']}" if not m_opp.empty else "—"
        })

    df_dash = pd.DataFrame(lista_dash)
    df_excel = pd.DataFrame(lista_excel)
    st.dataframe(df_dash, use_container_width=True, hide_index=True)
    return df_excel

# =========================
# EXECUÇÃO
# =========================
if file:
    df_in = pd.read_excel(file)
    df_in.columns = df_in.columns.str.strip()
    for c in ["Marca", "UF", "Produto"]:
        if c in df_in.columns: df_in[c] = df_in[c].astype(str).str.strip().str.upper()

    df_in = df_in[df_in["UF"].isin(ESTADOS)]

    relatorios = {}
    relatorios["RS"] = render("RS", df_in)
    relatorios["SC"] = render("SC", df_in)
    relatorios["PR"] = render("PR", df_in)

    # 1. EXCEL
    output_excel = BytesIO()
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        for uf, data in relatorios.items():
            data.to_excel(writer, index=False, sheet_name=uf)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 Baixar Relatório Excel", output_excel.getvalue(), "relatorio_copa.xlsx")

    # 2. ZIP DE IMAGENS (A NOVIDADE)
# ZIP de Fotos (VERSÃO OTIMIZADA COM CONTADOR)
        if col2.button("🖼️ Gerar ZIP de Fotos"):
            with st.spinner("Preparando..."):
                z_buf = BytesIO()
                # Coletar apenas códigos únicos e válidos
                todos_cods = set()
                for d in relatorios.values():
                    for col_name in ["Top_Cod", "Vez_Cod", "Opp_Cod"]:
                        cods_lista = d[col_name].tolist()
                        todos_cods.update([str(c) for c in cods_lista if str(c) != "—"])
                
                total = len(todos_cods)
                if total == 0:
                    st.warning("Nenhum produto encontrado para baixar fotos.")
                else:
                    progresso = st.empty() # Espaço para o contador
                    baixados = 0
                    
                    with zipfile.ZipFile(z_buf, "w") as zf:
                        for i, c in enumerate(todos_cods):
                            progresso.info(f"📥 Baixando imagem {i+1} de {total} (Cód: {c})")
                            try:
                                # Tenta baixar a imagem
                                r_img = requests.get(f"https://sambaled.com.br/app_imagem/{c}.jpg", timeout=2)
                                if r_img.status_code == 200:
                                    zf.writestr(f"{c}.jpg", r_img.content)
                                    baixados += 1
                            except:
                                continue
                    
                    progresso.empty() # Limpa o contador ao terminar
                    if baixados > 0:
                        st.success(f"✅ {baixados} fotos processadas com sucesso!")
                        st.download_button("💾 Baixar arquivo ZIP", z_buf.getvalue(), "fotos_copa.zip")
                    else:
                        st.error("❌ Não foi possível baixar nenhuma imagem. Verifique o link do servidor.")
                
                st.download_button(
                    label="💾 Clique para baixar o ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="fotos_produtos.zip",
                    mime="application/zip"
                )
