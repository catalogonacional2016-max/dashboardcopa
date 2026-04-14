import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(layout="wide")

st.title("Análise de Produtos Copa Nacional")

# =========================
# SEU TEXTO ORIGINAL RESTAURADO
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

# SUA OBSERVAÇÃO RESTAURADA
st.markdown("🔔 **Observação:** Certifique-se de que a base de dados esteja no formato correto, com as colunas **UF**, **Marca**, **Cod**, **Produto**, **Pedidos**, **Mes**, **Valor**, e **Qtd**.")

# =========================
# FUNÇÕES DE CÁLCULO (MANTIDAS)
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
        codigos_proibidos = top_fat["Cod"].unique()
        merged = merged[~merged["Cod"].isin(codigos_proibidos)]
    
    return pick_best(merged, "Marca", "score")

def oportunidade(d):
    x = d.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False).agg({"Pedidos": "sum", "Qtd": "sum"})
    x["score"] = x["Pedidos"] / (x["Qtd"] + 1)
    return pick_best(x, "Marca", "score")

# =========================
# RENDER (COM AS MELHORIAS PEDIDAS)
# =========================
def render(uf, df_global):
    st.markdown(f"## {uf}")
    d_uf = df_global[df_global["UF"] == uf].copy()
    
    # 1. AVISO DE MARCAS AUSENTES (CONFORME PEDIDO)
    marcas_na_base = d_uf["Marca"].unique()
    for m in MARCAS:
        if m not in marcas_na_base:
            st.warning(f"⚠️ Não há dados para a marca **{m}** no estado {uf}.")

    # Cálculos
    top = top_faturamento(d_uf)
    hot = produto_vez(d_uf, top)
    opp = oportunidade(d_uf)

    # 2. MONTAGEM PARA O EXCEL (COLUNAS SEPARADAS)
    resultado = []
    for marca in MARCAS:
        row = {"Marca": marca}
        for nome, df_rank in [("Top", top), ("Vez", hot), ("Opp", opp)]:
            match = df_rank[df_rank["Marca"] == marca]
            if not match.empty:
                row[f"{nome}_Cod"] = match.iloc[0]["Cod"]
                row[f"{nome}_Prod"] = match.iloc[0]["Produto"]
            else:
                row[f"{nome}_Cod"] = "—"
                row[f"{nome}_Prod"] = "—"
        resultado.append(row)

    final_df = pd.DataFrame(resultado)

    # 3. FÓRMULA DE IMAGEM
    for i, row in final_df.iterrows():
        idx = i + 2
        final_df.loc[i, "📸 Foto Top"] = f'=IMAGEM("https://sambaled.com.br/app_imagem/" & B{idx} & ".jpg")' if row["Top_Cod"] != "—" else "—"
        final_df.loc[i, "📸 Foto Vez"] = f'=IMAGEM("https://sambaled.com.br/app_imagem/" & E{idx} & ".jpg")' if row["Vez_Cod"] != "—" else "—"
        final_df.loc[i, "📸 Foto Opp"] = f'=IMAGEM("https://sambaled.com.br/app_imagem/" & H{idx} & ".jpg")' if row["Opp_Cod"] != "—" else "—"

    # Reordenar colunas para o Excel e Streamlit
    ordem = ["Marca", "Top_Cod", "Top_Prod", "📸 Foto Top", "Vez_Cod", "Vez_Prod", "📸 Foto Vez", "Opp_Cod", "Opp_Prod", "📸 Foto Opp"]
    final_df = final_df[ordem]

    st.dataframe(final_df, use_container_width=True, hide_index=True)
    return final_df

# =========================
# EXECUÇÃO
# =========================
if file:
    df_input = pd.read_excel(file)
    df_input.columns = df_input.columns.str.strip()
    for c in ["Marca", "UF", "Produto"]:
        if c in df_input.columns:
            df_input[c] = df_input[c].astype(str).str.strip().str.upper()

    df_input = df_input[df_input["UF"].isin(ESTADOS)]

    # Processa os estados
    relatorios = {}
    relatorios["RS"] = render("RS", df_input)
    relatorios["SC"] = render("SC", df_input)
    relatorios["PR"] = render("PR", df_input)

    # Gerar Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for uf, data in relatorios.items():
            data.to_excel(writer, index=False, sheet_name=uf)
    
    st.download_button(
        "📥 Baixar relatório completo",
        output.getvalue(),
        "relatorio_analise.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
