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

💰 Top Faturamento → forte nos últimos 3 meses + forte no mês atual  
🔥 Produto da Vez → forte no último mês + cresceu em relação ao mês anterior  
💵 Oportunidade → muitos pedidos + baixa quantidade  
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

file = st.file_uploader("📂 Envie sua base Excel")

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
    x = d.groupby(["Mes", "UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    meses = sorted(x["Mes"].unique())
    if len(meses) < 2:
        base = x.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
        return base
    ultimos = meses[-4:]
    base = x[x["Mes"].isin(ultimos)]
    resumo = base.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    atual = x[x["Mes"] == meses[-1]].groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    merged = resumo.merge(atual, on=["UF", "Marca", "Cod", "Produto"], how="left", suffixes=("_hist", "_atual"))
    merged["Valor_atual"] = merged["Valor_atual"].fillna(0)
    merged["score"] = merged["Valor_hist"] * 0.6 + merged["Valor_atual"] * 0.4
    return pick_best(merged, "Marca", "score")

# =========================
# PRODUTO DA VEZ (CRESCIMENTO)
# =========================
def produto_vez(d):
    # Agrupa por mês, UF, marca, código e produto
    x = d.groupby(["Mes", "UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
    
    # Filtra os meses
    meses = sorted(x["Mes"].unique())

    # Se não houver dois meses completos, simplesmente retorna os produtos com maior valor
    if len(meses) < 2:
        base = x.groupby(["UF", "Marca", "Cod", "Produto"], as_index=False)["Valor"].sum()
        return base

    # Se houver pelo menos dois meses completos, considera o mês atual e o anterior
    atual = x[x["Mes"] == meses[-1]]  # Último mês (atual)
    ant = x[x["Mes"] == meses[-2]]    # Mês anterior

    # Merge entre os dados do mês atual e do mês anterior
    merged = atual.merge(ant, on=["UF", "Marca", "Cod", "Produto"], how="left", suffixes=("_atual", "_ant"))

    # Preenche valores faltantes com 0 para o mês anterior (caso algum valor não tenha sido registrado)
    merged["Valor_ant"] = merged["Valor_ant"].fillna(0)

    # Agora, apenas pegamos o produto com maior valor em ambos os meses
    return pick_best(merged, "Marca", "Valor_atual")  # Seleciona o produto com maior faturamento no mês atual

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
