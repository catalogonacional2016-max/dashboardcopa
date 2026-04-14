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
# APP
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

    def label(r):
        return f"{r['Cod']} - {r['Produto']}"

    # =========================
    # TOP FATURAMENTO
    # =========================
    def top_faturamento(d):

        x = d.groupby(["Mes","UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        if x.empty:
            return x

        meses = sorted(x["Mes"].unique())

        if len(meses) < 2:
            ultimos = meses[-3:]
            base = x[x["Mes"].isin(ultimos)]
            resumo = base.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()
            return pick_best(resumo, "Marca", "Valor")

        ultimos = meses[-4:]
        base = x[x["Mes"].isin(ultimos)]

        resumo = base.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()
        atual = x[x["Mes"] == meses[-1]].groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        merged = resumo.merge(atual, on=["UF","Marca","Cod","Produto"], how="left", suffixes=("_hist","_atual"))
        merged["Valor_atual"] = merged["Valor_atual"].fillna(0)

        merged["score"] = merged["Valor_hist"] * 0.6 + merged["Valor_atual"] * 0.4

        if merged["score"].max() <= 0:
            ultimos = meses[-3:]
            base = x[x["Mes"].isin(ultimos)]
            resumo = base.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()
            return pick_best(resumo, "Marca", "Valor")

        return pick_best(merged, "Marca", "score")

    # =========================
    # PRODUTO DA VEZ
    # =========================
    def produto_vez(d):

        x = d.groupby(["Mes","UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        if x.empty:
            return x

        meses = sorted(x["Mes"].unique())

        if len(meses) < 2:
            atual = x[x["Mes"] == meses[-1]]
            return pick_best(atual, "Marca", "Valor")

        atual = x[x["Mes"] == meses[-1]]
        ant = x[x["Mes"] == meses[-2]]

        m = atual.merge(ant, on=["UF","Marca","Cod","Produto"], how="left", suffixes=("_a","_b"))
        m["Valor_b"] = m["Valor_b"].fillna(0)

        m["crescimento"] = m["Valor_a"] - m["Valor_b"]

        if m["crescimento"].max() <= 0:
            return pick_best(atual, "Marca", "Valor")

        return pick_best(m, "Marca", "crescimento")

    # =========================
    # OPORTUNIDADE
    # =========================
    def oportunidade(d):

        x = d.groupby(["Mes","UF","Marca","Cod","Produto"], as_index=False).agg({
            "Pedidos":"sum",
            "Qtd":"sum",
            "Valor":"sum"
        })

        if x.empty:
            return x

        meses = sorted(x["Mes"].unique())
        ultimo_mes = meses[-1]

        base_total = x.groupby(["UF","Marca","Cod","Produto"], as_index=False).agg({
            "Pedidos":"sum",
            "Qtd":"sum",
            "Valor":"sum"
        })

        base_total["score"] = base_total["Pedidos"] / (base_total["Qtd"].clip(lower=5))

        ultimo = x[x["Mes"] == ultimo_mes]

        if base_total["score"].isna().all() or base_total["score"].max() <= 0:
            return pick_best(ultimo, "Marca", "Pedidos")

        return pick_best(base_total, "Marca", "score")

    # =========================
    # RENDER
    # =========================
    def render(uf):

        st.markdown(f"## {uf}")

        d = df[df["UF"] == uf]
        resumo = base_resumo[base_resumo["UF"] == uf]

        marcas = pd.DataFrame({"Marca": MARCAS})

        # TOP
        top = top_faturamento(d)
        if not top.empty:
            top["val"] = top.apply(label, axis=1)
        else:
            top = pd.DataFrame(columns=["Marca","val"])

        # HOT
        hot = produto_vez(d)
        if not hot.empty:
            hot["val"] = hot.apply(label, axis=1)
        else:
            hot = pd.DataFrame(columns=["Marca","val"])

        # OPORTUNIDADE
        opp = oportunidade(d)
        if not opp.empty:
            opp["val"] = opp.apply(label, axis=1)
        else:
            opp = pd.DataFrame(columns=["Marca","val"])

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

    rs = render("RS")
    sc = render("SC")
    pr = render("PR")

    excel = gerar_excel(rs, sc, pr)

    # Aqui está o fechamento do parêntese
    st.download_button(
        "📥 Baixar relatório completo",
        excel,
        "relatorio.xlsx",
        "application/vnd.openxmlformats
