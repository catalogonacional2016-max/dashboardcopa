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
def top_faturamento(d):
    # Agrupa por mês, UF, marca, código e produto
    x = d.groupby(["Mes", "UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    
    # Ordena e pega os últimos 3 meses
    meses = sorted(x["Mes"].unique())
    if len(meses) < 3:
        return x.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()  # Se não houver 3 meses completos

    ultimos_3_meses = meses[-3:]
    base_3_meses = x[x["Mes"].isin(ultimos_3_meses)]
    
    # Soma o faturamento nos últimos 3 meses
    resumo = base_3_meses.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    
    # Pega o faturamento do mês atual
    atual = x[x["Mes"] == meses[-1]].groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    
    # Merge entre os dados dos últimos 3 meses e o mês atual
    merged = resumo.merge(atual, on=["UF", "Marca", "Cod", "Produto"], how="left", suffixes=("_hist", "_atual"))
    merged["Valor_atual"] = merged["Valor_atual"].fillna(0)
    
    # Calcula o score (peso 60% nos últimos 3 meses e 40% no mês atual)
    merged["score"] = merged["Valor_hist"] * 0.6 + merged["Valor_atual"] * 0.4
    
    # Retorna o melhor produto com base no score
    return pick_best(merged, "Marca", "score")

# =========================
# PRODUTO DA VEZ (MAIOR FATURAMENTO NO MÊS ATUAL E MÊS ANTERIOR)
# =========================
def produto_vez(d, top_fat):
    # Agrupa por mês, UF, marca, código e produto
    x = d.groupby(["Mes", "UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    
    # Filtra os meses
    meses = sorted(x["Mes"].unique())
    
    if len(meses) < 2:
        return x.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()

    # Pega o mês atual e anterior
    atual = x[x["Mes"] == meses[-1]]  # Último mês (atual)
    ant = x[x["Mes"] == meses[-2]]    # Mês anterior
    
    # Merge entre os dados do mês atual e do mês anterior
    merged = atual.merge(ant, on=["UF", "Marca", "Cod", "Produto"], how="left", suffixes=("_atual", "_ant"))
    merged["Valor_ant"] = merged["Valor_ant"].fillna(0)
    
    # Calcula o faturamento do mês atual e do mês anterior
    merged["score"] = merged[["Valor_atual", "Valor_ant"]].max(axis=1)
    
    # Seleciona o produto com maior faturamento entre os dois meses
    produto_vez = pick_best(merged, "Marca", "score")

    # Garante que o Produto da Vez não seja o mesmo que o Top Faturamento
    if not produto_vez.empty and produto_vez.iloc[0]["Produto"] == top_fat.iloc[0]["Produto"]:
        # Substitui o produto da vez por outro produto
        merged = merged[merged["Produto"] != top_fat.iloc[0]["Produto"]]  # Exclui o produto do Top Faturamento
        produto_vez = pick_best(merged, "Marca", "score")  # Recalcula o produto da vez
    
    return produto_vez

# =========================
# OPORTUNIDADE (Ajustado)
# =========================
def oportunidade(d):
    x = d.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False).agg({
        "Pedidos": "sum",  # Total de pedidos
        "Qtd": "sum",      # Total de unidades vendidas
        "Valor": "sum"     # Faturamento (não será utilizado diretamente)
    })
    x["score"] = x["Pedidos"] / (x["Qtd"] + 1)  # Adiciona 1 para evitar divisão por zero
    x = x.sort_values(by=["score", "Qtd"], ascending=[False, True])  # Ordena pelo score e pela menor quantidade
    return pick_best(x, "Marca", "score")

# =========================
# RENDER
# =========================
def render(uf):
    st.markdown(f"## {uf}")
    d = df[df["UF"] == uf]
    marcas = pd.DataFrame({"Marca": MARCAS})

    # Verificar se as marcas estão presentes na base
    marcas_presentes = d["Marca"].unique()

    for marca in MARCAS:
        if marca not in marcas_presentes:
            st.warning(f"🔔 Não há dados para a marca **{marca}** no estado {uf}.")

    # Calcular Top Faturamento
    top = top_faturamento(d)
    top = top.groupby("Marca").head(1)
    top["val"] = top.apply(lambda r: f"{r['Cod']} - {r['Produto']}", axis=1)

    # Calcular Produto da Vez
    hot = produto_vez(d)
    hot = hot.groupby("Marca").head(1)
    hot["val"] = hot.apply(lambda r: f"{r['Cod']} - {r['Produto']}", axis=1)

    # Garantir que o Produto da Vez não seja o mesmo que o Top Faturamento
    hot = garantir_produto_diferente(top, hot)

    # Calcular Oportunidade
    opp = oportunidade(d)
    opp = opp.groupby("Marca").head(1)
    opp["val"] = opp.apply(lambda r: f"{r['Cod']} - {r['Produto']}", axis=1)

    # Combinar os resultados
    final = marcas.merge(top[["Marca", "val"]], on="Marca", how="left")
    final = final.merge(hot[["Marca", "val"]], on="Marca", how="left")
    final = final.merge(opp[["Marca", "val"]], on="Marca", how="left")

    final.columns = [
        "Marca",
        "💰 Top Faturamento",
        "🔥 Produto da Vez",
        "💵 Oportunidade"
    ]

    final = final.fillna("—")
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
