import streamlit as st
import pandas as pd
from io import BytesIO

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
# FUNÇÕES DE CÁLCULO
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
# RENDER
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

        lista_excel.append({
            "Marca": marca,
            "Top_Cod": m_top.iloc[0]["Cod"] if not m_top.empty else "—",
            "Top_Prod": m_top.iloc[0]["Produto"] if not m_top.empty else "—",
            "Vez_Cod": m_hot.iloc[0]["Cod"] if not m_hot.empty else "—",
            "Vez_Prod": m_hot.iloc[0]["Produto"] if not m_hot.empty else "—",
            "Opp_Cod": m_opp.iloc[0]["Cod"] if not m_opp.empty else "—",
            "Opp_Prod": m_opp.iloc[0]["Produto"] if not m_opp.empty else "—"
        })

        lista_dash.append({
            "Marca": marca,
            "💰 Top Faturamento": f"{m_top.iloc[0]['Cod']} - {m_top.iloc[0]['Produto']}" if not m_top.empty else "—",
            "🔥 Produto da Vez": f"{m_hot.iloc[0]['Cod']} - {m_hot.iloc[0]['Produto']}" if not m_hot.empty else "—",
            "💵 Oportunidade": f"{m_opp.iloc[0]['Cod']} - {m_opp.iloc[0]['Produto']}" if not m_opp.empty else "—"
        })

    df_dash = pd.DataFrame(lista_dash)
    df_excel = pd.DataFrame(lista_excel)

    # Inserir colunas de foto vazias (serão preenchidas via xlsxwriter no final)
    df_excel.insert(3, "📸 Foto Top", "")
    df_excel.insert(7, "📸 Foto Vez", "")
    df_excel.insert(11, "📸 Foto Opp", "")

    st.dataframe(df_dash, use_container_width=True, hide_index=True)
    return df_excel

# =========================
# EXECUÇÃO E GRAVAÇÃO ESPECIAL
# =========================
if file:
    df_in = pd.read_excel(file)
    df_in.columns = df_in.columns.str.strip()
    for c in ["Marca", "UF", "Produto"]:
        if c in df_in.columns: df_in[c] = df_in[c].astype(str).str.strip().str.upper()

    df_in = df_in[df_in["UF"].isin(ESTADOS)]

    relatorios_excel = {}
    relatorios_excel["RS"] = render("RS", df_in)
    relatorios_excel["SC"] = render("SC", df_in)
    relatorios_excel["PR"] = render("PR", df_in)

    output = BytesIO()
    # Mudança aqui: usamos o engine xlsxwriter para controlar as fórmulas
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for uf, data in relatorios_excel.items():
            data.to_excel(writer, index=False, sheet_name=uf)
            workbook = writer.book
            worksheet = writer.sheets[uf]
            
            # Varremos as linhas para escrever a fórmula nativa sem o @
            for i in range(len(data)):
                row_idx = i + 1 # +1 para pular o cabeçalho no xlsxwriter
                
                # Fórmulas (Colunas D=3, H=7, L=11 no índice 0 do Excel)
                # Foto Top (Coluna D usa o Cod da coluna B)
                cod_top = data.iloc[i]["Top_Cod"]
                if cod_top != "—":
                    formula = f'=IMAGEM("https://sambaled.com.br/app_imagem/" & B{row_idx+1} & ".jpg")'
                    worksheet.write_formula(row_idx, 3, formula)
                
                # Foto Vez (Coluna H usa o Cod da coluna F)
                cod_vez = data.iloc[i]["Vez_Cod"]
                if cod_vez != "—":
                    formula = f'=IMAGEM("https://sambaled.com.br/app_imagem/" & E{row_idx+1} & ".jpg")'
                    worksheet.write_formula(row_idx, 7, formula)
                
                # Foto Opp (Coluna L usa o Cod da coluna J)
                cod_opp = data.iloc[i]["Opp_Cod"]
                if cod_opp != "—":
                    formula = f'=IMAGEM("https://sambaled.com.br/app_imagem/" & H{row_idx+1} & ".jpg")'
                    worksheet.write_formula(row_idx, 11, formula)
    
    st.download_button(
        "📥 Baixar relatório completo",
        output.getvalue(),
        "relatorio_copa.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
