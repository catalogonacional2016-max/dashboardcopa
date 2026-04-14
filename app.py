import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(layout="wide")

st.title("Análise de Produtos Copa Nacional")

# =========================
# TEXTO ÚNICO
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

# --- SUA OBSERVAÇÃO RECUPERADA ---
st.markdown("🔔 **Observação:** Certifique-se de que a base de dados esteja no formato correto, com as colunas **UF**, **Marca**, **Cod**, **Produto**, **Pedidos**, **Mes**, **Valor**, e **Qtd**.")

# =========================
# EXPORT EXCEL
# =========================
def gerar_excel(dic_dfs):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for uf, df_uf in dic_dfs.items():
            df_uf.to_excel(writer, index=False, sheet_name=uf)
    return output.getvalue()

# =========================
# FUNÇÃO: RANKING
# =========================
def pick_best(df, group="Marca", score_col=None):
    if df.empty:
        return df
    if score_col is None:
        score_col = df.columns[-1]
    df = df.sort_values(score_col, ascending=False)
    return df.groupby(group).head(1)

# =========================
# TOP FATURAMENTO (SUA REGRA ORIGINAL)
# =========================
def top_faturamento(d):
    x = d.groupby(["Mes", "UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    meses = sorted(x["Mes"].unique())
    if len(meses) < 3:
        resumo = x.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
        resumo["score"] = resumo["Valor"]
        return pick_best(resumo, "Marca", "score")

    ultimos_3_meses = meses[-3:]
    base_3_meses = x[x["Mes"].isin(ultimos_3_meses)]
    resumo = base_3_meses.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    atual = x[x["Mes"] == meses[-1]].groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    
    merged = resumo.merge(atual, on=["UF", "Marca", "Cod", "Produto"], how="left", suffixes=("_hist", "_atual"))
    merged["Valor_atual"] = merged["Valor_atual"].fillna(0)
    merged["score"] = merged["Valor_hist"] * 0.6 + merged["Valor_atual"] * 0.4
    
    return pick_best(merged, "Marca", "score")

# =========================
# PRODUTO DA VEZ (SUA REGRA + FILTRO DE REPETIÇÃO)
# =========================
def produto_vez(d, top_fat):
    x = d.groupby(["Mes", "UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    meses = sorted(x["Mes"].unique())
    if len(meses) < 2:
        return pd.DataFrame()

    atual = x[x["Mes"] == meses[-1]]
    ant = x[x["Mes"] == meses[-2]]
    
    merged = atual.merge(ant, on=["UF", "Marca", "Cod", "Produto"], how="left", suffixes=("_atual", "_ant"))
    merged["Valor_ant"] = merged["Valor_ant"].fillna(0)
    merged["score"] = merged[["Valor_atual", "Valor_ant"]].max(axis=1)

    # FILTRO: Não ser igual ao Top Faturamento
    codigos_proibidos = top_fat["Cod"].unique()
    merged_filtrado = merged[~merged["Cod"].isin(codigos_proibidos)].copy()
    
    df_para_escolha = merged_filtrado if not merged_filtrado.empty else merged
    return pick_best(df_para_escolha, "Marca", "score")

# =========================
# OPORTUNIDADE (SUA REGRA ORIGINAL)
# =========================
def oportunidade(d):
    x = d.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False).agg({
        "Pedidos": "sum",
        "Qtd": "sum"
    })
    x["score"] = x["Pedidos"] / (x["Qtd"] + 1)
    return pick_best(x, "Marca", "score")

# =========================
# RENDER
# =========================
def render(uf):
    st.markdown(f"## {uf}")
    d_uf = df[df["UF"] == uf].copy()
    
    # 1. MENSAGEM DE MARCAS AUSENTES
    marcas_na_base = d_uf["Marca"].unique()
    for m in MARCAS:
        if m not in marcas_na_base:
            st.warning(f"⚠️ Não há dados para a marca **{m}** no estado {uf}.")

    # Cálculos
    top = top_faturamento(d_uf)
    hot = produto_vez(d_uf, top)
    opp = oportunidade(d_uf)

    # 2. COLUNAS SEPARADAS
    resultado = []
    for marca in MARCAS:
        row = {"Marca": marca}
        
        m_top = top[top["Marca"] == marca]
        row["Top_Cod"] = m_top.iloc[0]["Cod"] if not m_top.empty else "—"
        row["Top_Prod"] = m_top.iloc[0]["Produto"] if not m_top.empty else "—"
        
        m_hot = hot[hot["Marca"] == marca]
        row["Vez_Cod"] = m_hot.iloc[0]["Cod"] if not m_hot.empty else "—"
        row["Vez_Prod"] = m_hot.iloc[0]["Produto"] if not m_hot.empty else "—"
        
        m_opp = opp[opp["Marca"] == marca]
        row["Opp_Cod"] = m_opp.iloc[0]["Cod"] if not m_opp.empty else "—"
        row["Opp_Prod"] = m_opp.iloc[0]["Produto"] if not m_opp.empty else "—"
        
        resultado.append(row)

    final_df = pd.DataFrame(resultado)

    # 3. FÓRMULA DE IMAGEM
    links_top, links_vez, links_opp = [], [], []
    for i, row in enumerate(resultado, start=2):
        links_top.append(f'=IMAGEM("https://sambaled.com.br/app_imagem/" & B{i} & ".jpg")' if row["Top_Cod"] != "—" else "—")
        links_vez.append(f'=IMAGEM("https://sambaled.com.br/app_imagem/" & E{i} & ".jpg")' if row["Vez_Cod"] != "—" else "—")
        links_opp.append(f'=IMAGEM("https://sambaled.com.br/app_imagem/" & H{i} & ".jpg")' if row["Opp_Cod"] != "—" else "—")

    final_df.insert(3, "📸 Foto Top", links_top)
    final_df.insert(7, "📸 Foto Vez", links_vez)
    final_df.insert(11, "📸 Foto Opp", links_opp)
    
    st.dataframe(final_df, use_container_width=True, hide_index=True)
    return final_df

# =========================
# EXECUÇÃO
# =========================
if file:
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["Marca"] = df["Marca"].astype(str).str.strip().str.upper()
    df["UF"] = df["UF"].astype(str).str.strip().str.upper()
    df["Produto"] = df["Produto"].astype(str).str.strip()
    
    df = df[df["UF"].isin(ESTADOS) & df["Marca"].isin(MARCAS)]

    relatorios = {}
    relatorios["RS"] = render("RS")
    relatorios["SC"] = render("SC")
    relatorios["PR"] = render("PR")

    excel_data = gerar_excel(relatorios)

    st.download_button(
        "📥 Baixar relatório completo",
        excel_data,
        "analise_copa.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
