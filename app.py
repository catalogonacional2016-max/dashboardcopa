import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(layout="wide")

st.title("Análise de Produtos Copa Nacional")

# =========================
# TEXTO ÚNICO (EXATAMENTE O QUE VOCÊ QUER)
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
# APP
# =========================
if file:

    df = pd.read_excel(file)

    # limpeza
    df.columns = df.columns.str.strip()

    df["Marca"] = df["Marca"].astype(str).str.strip().str.upper()
    df["UF"] = df["UF"].astype(str).str.strip().str.upper()
    df["Produto"] = df["Produto"].astype(str).str.strip()

    df = df[df["UF"].isin(ESTADOS)]
    df = df[df["Marca"].isin(MARCAS)]

    # consolidação correta
    df = df.groupby(
        ["UF","Marca","Cod","Produto","Mes"],
        as_index=False
    ).agg({
        "Valor":"sum",
        "Qtd":"sum",
        "Pedidos":"sum"
    })

    def label(r):
        return f"{r['Cod']} - {r['Produto']}"

    # =========================
    # TOP FATURAMENTO (ROBUSTO)
    # =========================
    def top_faturamento(d):
        x = d.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()
        if x.empty:
            return x
        return x.sort_values("Valor", ascending=False)

    # =========================
    # PRODUTO DA VEZ (CRESCIMENTO)
    # =========================
    def produto_vez(d):

        x = d.groupby(["Mes","UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()
        meses = sorted(x["Mes"].unique())

        if len(meses) < 2:
            return x.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        atual = meses[-1]
        ant = meses[-2]

        a = x[x["Mes"] == atual]
        b = x[x["Mes"] == ant]

        m = a.merge(
            b,
            on=["UF","Marca","Cod","Produto"],
            how="left",
            suffixes=("_a","_b")
        )

        m["Valor_b"] = m["Valor_b"].fillna(0)
        m["crescimento"] = m["Valor_a"] - m["Valor_b"]

        return m.sort_values(["Valor_a","crescimento"], ascending=False)

    # =========================
    # OPORTUNIDADE
    # =========================
    def oportunidade(d):

        x = d.groupby(["UF","Marca","Cod","Produto"], as_index=False).agg({
            "Pedidos":"sum",
            "Qtd":"sum"
        })

        x["score"] = x["Pedidos"] / (x["Qtd"] + 1)

        return x.sort_values("score", ascending=False)

    # =========================
    # RENDER
    # =========================
    def render(uf):

        st.markdown(f"## {uf}")

        d = df[df["UF"] == uf]

        marcas = pd.DataFrame({"Marca": MARCAS})

        top = top_faturamento(d)
        if not top.empty:
            top = top.groupby("Marca").head(1)
            top["val"] = top.apply(label, axis=1)

        hot = produto_vez(d)
        if not hot.empty:
            hot = hot.groupby("Marca").head(1)
            hot["val"] = hot.apply(label, axis=1)

        opp = oportunidade(d)
        opp = opp.groupby("Marca").head(1)
        opp["val"] = opp.apply(label, axis=1)

        final = marcas.merge(top[["Marca","val"]], on="Marca", how="left")
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

    st.download_button(
        "📥 Baixar relatório completo",
        excel,
        "relatorio.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
