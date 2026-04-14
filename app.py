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
st.markdown("🔔 **Observação:** Certifique-se de que a base de dados esteja no formato correto, com as colunas **UF**, **Marca**, **Cod**, **Produto**, **Pedidos**, **Mes**, **Valor**, e **Qtd**.")

# =========================
# EXPORT EXCEL
# =========================
def gerar_excel(rs, sc, pr):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        rs.to_excel(writer, index=False, sheet_name="RS")
        sc.to_excel(writer, index=False, sheet_name="SC")
        pr.to_excel(writer, index=False, sheet_name="PR")
    return output.getvalue()

# =========================
# FUNÇÃO: FALLBACK POR RANKING (NÃO MUDA REGRA, SÓ ESCOLHE PRÓXIMO)
# =========================
def pick_best(df, group="Marca", score_col=None):
    if df.empty:
        return df
    if score_col is None:
        score_col = df.columns[-1]
    df = df.sort_values(score_col, ascending=False)
    result = []
    for m in df[group].unique():
        sub = df[df[group] == m]
        if not sub.empty:
            result.append(sub.head(1))
    return pd.concat(result) if result else df

# =========================
# TOP FATURAMENTO (REGRA ORIGINAL + SCORE)
# =========================
# =========================
# FUNÇÃO: ESCOLHER O MELHOR (RANKING)
# =========================
def pick_best(df, group="Marca", score_col=None):
    if df.empty:
        return df
    if score_col is None:
        score_col = df.columns[-1]
    
    # Ordena pelo score do maior para o menor
    df = df.sort_values(score_col, ascending=False)
    
    # Agrupa por Marca e pega o primeiro de cada (que será o maior score disponível)
    return df.groupby(group).head(1)

# =========================
# TOP FATURAMENTO
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
# PRODUTO DA VEZ (COM FILTRO DE EXCLUSÃO)
# =========================
def produto_vez(d, top_fat_df):
    x = d.groupby(["Mes", "UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    meses = sorted(x["Mes"].unique())
    
    if len(meses) < 2:
        return pd.DataFrame()

    atual = x[x["Mes"] == meses[-1]]
    ant = x[x["Mes"] == meses[-2]]
    
    merged = atual.merge(ant, on=["UF", "Marca", "Cod", "Produto"], how="left", suffixes=("_atual", "_ant"))
    merged["Valor_ant"] = merged["Valor_ant"].fillna(0)
    merged["score"] = merged[["Valor_atual", "Valor_ant"]].max(axis=1)

    # --- LÓGICA DE EXCLUSÃO ---
    # Pegamos os códigos que já ganharam no Top Faturamento
    codigos_proibidos = top_fat_df["Cod"].unique()
    
    # Filtramos para remover esses códigos antes de escolher o melhor
    merged_filtrado = merged[~merged["Cod"].isin(codigos_proibidos)].copy()
    
    # Se sobrar algo após o filtro, escolhemos o melhor. Se não, usamos o original.
    df_para_escolha = merged_filtrado if not merged_filtrado.empty else merged
    
    return pick_best(df_para_escolha, "Marca", "score")

# =========================
# OPORTUNIDADE
# =========================
def oportunidade(d):
    x = d.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False).agg({
        "Pedidos": "sum",
        "Qtd": "sum"
    })
    x["score"] = x["Pedidos"] / (x["Qtd"] + 1)
    return pick_best(x, "Marca", "score")

# =========================
# RENDER (O CORAÇÃO DO RELATÓRIO)
# =========================
def render(uf):
    st.markdown(f"## {uf}")
    
    # Filtra os dados apenas para o estado atual
    d_uf = df[df["UF"] == uf].copy()
    
    # 1. Calcula Top Faturamento
    top = top_faturamento(d_uf)
    # Criamos a string de exibição "Cod - Nome"
    top["val"] = top.apply(lambda r: f"{r['Cod']} - {r['Produto']}", axis=1)

    # 2. Calcula Produto da Vez (passando os resultados do 'top' para serem excluídos)
    hot = produto_vez(d_uf, top)
    hot["val"] = hot.apply(lambda r: f"{r['Cod']} - {r['Produto']}", axis=1)

    # 3. Calcula Oportunidade
    opp = oportunidade(d_uf)
    opp["val"] = opp.apply(lambda r: f"{r['Cod']} - {r['Produto']}", axis=1)

    # 4. Montagem da Tabela Final por Marca
    marcas_base = pd.DataFrame({"Marca": MARCAS})
    
    # Fazemos os merges para unir as colunas
    final = marcas_base.merge(top[["Marca", "val"]], on="Marca", how="left")
    final = final.merge(hot[["Marca", "val"]], on="Marca", how="left", suffixes=("_top", "_hot"))
    final = final.merge(opp[["Marca", "val"]], on="Marca", how="left")

    # Renomeia colunas para o Streamlit
    final.columns = [
        "Marca",
        "💰 Top Faturamento",
        "🔥 Produto da Vez",
        "💵 Oportunidade"
    ]

    # Preenche o que estiver vazio com traço
    final = final.fillna("—")
    
    # Renderiza na tela
    st.dataframe(final, use_container_width=True, hide_index=True)

    return final
# =========================
# EXECUÇÃO
# =========================
if file:
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()
    df["Marca"] = df["Marca"].astype(str).str.strip().str.upper()
    df["UF"] = df["UF"].astype(str).str.strip().str.upper()
    df["Produto"] = df["Produto"].astype(str).str.strip()
    df = df[df["UF"].isin(ESTADOS)]
    df = df[df["Marca"].isin(MARCAS)]

    df = df.groupby(
        ["UF", "Marca", "Cod", "Produto", "Mes"],
        as_index=False
    ).agg({
        "Valor": "sum",
        "Qtd": "sum",
        "Pedidos": "sum"
    })

    # Gerar relatório para cada estado
    rs = render("RS")
    sc = render("SC")
    pr = render("PR")

    # Gerar e permitir download do Excel
    excel = gerar_excel(rs, sc, pr)

    st.download_button(
        "📥 Baixar relatório completo",
        excel,
        "relatorio.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
