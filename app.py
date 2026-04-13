import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(layout="wide")

st.title("Análise de Produtos Copa Nacional")

# =========================
# TEXTO (SUBSTITUÍDO CORRETAMENTE)
# =========================
st.markdown("""
### 📌 Categorias

💰 Top Faturamento → forte nos últimos 3 meses + forte no mês atual  
🔥 Produto da Vez → forte no último mês + cresceu em relação ao mês anterior  
💵 Oportunidade → muitos pedidos + baixa quantidade  

---

### 📌 Regras do sistema

💰 Top Faturamento → forte nos últimos 3 meses + ativo no mês atual  
🔥 Produto da Vez → segundo melhor produto (não repete o Top)  
💵 Oportunidade → muitos pedidos com baixa eficiência de volume  
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
# EXCEL EXPORT
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

    df.columns = df.columns.str.strip()

    df["Marca"] = df["Marca"].astype(str).str.strip().str.upper()
    df["UF"] = df["UF"].astype(str).str.strip().str.upper()
    df["Produto"] = df["Produto"].astype(str).str.strip()

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

    def label(r):
        return f"{r['Cod']} - {r['Produto']}"

    def top_faturamento(d):
        x = d.groupby(["Mes","UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()
        meses = sorted(x["Mes"].unique())
        if len(meses) < 4:
            return x.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        ultimos_3 = meses[-4:-1]
        atual = meses[-1]

        hist = x[x["Mes"].isin(ultimos_3)]
        atual_df = x[x["Mes"] == atual]

        hist_sum = hist.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()
        atual_sum = atual_df.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        merged = hist_sum.merge(
            atual_sum,
            on=["UF","Marca","Cod","Produto"],
            how="inner",
            suffixes=("_hist","_atual")
        )

        if not merged.empty:
            merged["Score"] = merged["Valor_hist"] * 0.6 + merged["Valor_atual"] * 0.4
            return merged.sort_values("Score", ascending=False)

        return x.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

    def produto_vez(d):

        x = d.groupby(["Mes","UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        meses = sorted(x["Mes"].unique())
        if len(meses) < 2:
            return x.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        atual = meses[-1]
        anterior = meses[-2]

        a = x[x["Mes"] == atual]
        b = x[x["Mes"] == anterior]

        m = a.merge(
            b,
            on=["UF","Marca","Cod","Produto"],
            how="left",
            suffixes=("_atual","_ant")
        )

        m["Valor_ant"] = m["Valor_ant"].fillna(0)
        m["crescimento"] = m["Valor_atual"] - m["Valor_ant"]

        m = m.sort_values(["Valor_atual","crescimento"], ascending=False)

        return m.groupby("Marca").head(1)

    def oportunidade(d):

        x = d.groupby(["UF","Marca","Cod","Produto"], as_index=False).agg({
            "Pedidos":"sum",
            "Qtd":"sum"
        })

        x["Score"] = x["Pedidos"] / (x["Qtd"] + 1)

        return x.sort_values("Score", ascending=False)

    def render(uf):

        st.markdown(f"## {uf}")

        d = df[df["UF"] == uf]

        marcas_df = pd.DataFrame({"Marca": MARCAS})

        top = top_faturamento(d)
        if not top.empty:
            top = top.groupby("Marca").head(1)
            top["VAL"] = top.apply(label, axis=1)

        hot = produto_vez(d)
        if not hot.empty:
            hot["VAL"] = hot.apply(label, axis=1)

        opp = oportunidade(d)
        opp = opp.groupby("Marca").head(1)
        opp["VAL"] = opp.apply(label, axis=1)

        final = marcas_df.merge(top[["Marca","VAL"]], on="Marca", how="left")
        final = final.merge(hot[["Marca","VAL"]], on="Marca", how="left")
        final = final.merge(opp[["Marca","VAL"]], on="Marca", how="left")

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
        "📥 Baixar relatório completo (Excel)",
        excel,
        "relatorio_copa_nacional.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
