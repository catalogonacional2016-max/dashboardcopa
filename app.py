import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(layout="wide")

st.title("Análise de Produtos Copa Nacional")

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
    "3M","HERC","KRONA","ROMA","DINAIDER SCHNEIDER","SCHNEIDER","STECK",
    "MISTER ABRASIVOS","MISTER ELETRICOS","MISTER FERRAMENTAS",
    "MISTER GERAL","MISTER PARAFUSOS"
]

ESTADOS = ["RS","SC","PR"]

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
# PICK BEST
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
# RENDER
# =========================
def render(uf):

    st.markdown(f"## {uf}")

    d = df[df["UF"] == uf]
    marcas = pd.DataFrame({"Marca": MARCAS})

    # TOP
    top = top_faturamento(d)
    if top.empty:
        st.warning(f"Não há dados de 'Top Faturamento' para {uf}!")
        top = pd.DataFrame(columns=["Marca","val"])
    else:
        top["val"] = top.apply(label, axis=1)

    # HOT
    hot = produto_vez(d)
    if hot.empty:
        st.warning(f"Não há dados de 'Produto da Vez' para {uf}!")
        hot = pd.DataFrame(columns=["Marca","val"])
    else:
        hot["val"] = hot.apply(label, axis=1)

    # OPORTUNIDADE
    opp = oportunidade(d)
    if opp.empty:
        st.warning(f"Não há dados de 'Oportunidade' para {uf}!")
        opp = pd.DataFrame(columns=["Marca","val"])
    else:
        opp["val"] = opp.apply(label, axis=1)

    # Verificar se alguma marca tem dados para o estado
    marcas_com_dados = pd.concat([top["Marca"], hot["Marca"], opp["Marca"]]).unique()

    if not any(marcas_com_dados == "DINAIDER SCHNEIDER"):
        st.warning("A marca 'Dinaider Schneider' não possui dados para este estado!")

    # Caso não haja dados para nenhuma marca, exibir mensagem
    if len(marcas_com_dados) == 0:
        st.warning(f"Não há dados disponíveis para nenhuma marca no estado {uf}!")

    final = marcas.copy()

    final = final.merge(top[["Marca","val"]], on="Marca", how="left")
    final = final.merge(hot[["Marca","val"]], on="Marca", how="left")
    final = final.merge(opp[["Marca","val"]], on="Marca", how="left")

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

    required_cols = ["UF","Marca","Cod","Produto","Mes","Valor","Qtd","Pedidos"]
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        st.error(f"Colunas faltando: {missing}")
        st.stop()

    # LIMPEZA
    df["Marca"] = df["Marca"].astype(str).str.strip().str.upper()
    df["UF"] = df["UF"].astype(str).str.strip().str.upper()
    df["Produto"] = df["Produto"].astype(str).str.strip()

    df["Mes"] = pd.to_numeric(df["Mes"], errors="coerce")
    df = df.dropna(subset=["Mes"])

    df = df[df["UF"].isin(ESTADOS)]
    df = df[df["Marca"].isin(MARCAS)]

    df = df.groupby(
        ["UF","Marca","Cod","Produto","Mes"],
        as_index=False
    ).agg({
        "Valor":"sum",
        "Qtd":"sum",
        "Pedidos":"sum"
    })

    # 🔴 BASE CONSOLIDADA (PARA MÉTRICAS)
    base_resumo = df.groupby(
        ["UF","Marca","Cod","Produto"],
        as_index=False
    ).agg({
        "Valor":"sum",
        "Qtd":"sum",
        "Pedidos":"sum"
    })

    # Geração das métricas para cada estado
    rs = render("RS")
    sc = render("SC")
    pr = render("PR")

    excel = gerar_excel(rs, sc, pr)

    st.download_button(
        "📥 Baixar relatório completo",
        excel,
        "relatorio.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
