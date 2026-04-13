import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("Análise de Produtos Copa Nacional")

# =========================
# EXPLICAÇÃO
# =========================
st.markdown("""
### 📌 Como as categorias são calculadas

💰 **Top Faturamento**  
Produto com bom desempenho nos últimos 3 meses E que continua vendendo no mês atual.

🔥 **Produto da Vez**  
Produto com maior crescimento entre mês atual vs mês anterior.  
Se for igual ao Top Faturamento, traz o 2º colocado.

💵 **Oportunidade**  
Produtos com muitos pedidos, mas baixo volume vendido (eficiência de vendas).
""")

# =========================
# CONFIGURAÇÕES
# =========================
MARCAS = [
"3M","HERC","KRONA","ROMA","DINAIDER SCHNEIDER","SCHNEIDER","STECK",
"MISTER ABRASIVOS","MISTER ELETRICOS","MISTER FERRAMENTAS",
"MISTER GERAL","MISTER PARAFUSOS"
]

ESTADOS = ["RS","SC","PR"]

# =========================
# UPLOAD
# =========================
file = st.file_uploader("📂 Envie sua base Excel")

if file:

    df = pd.read_excel(file)

    # =========================
    # LIMPEZA
    # =========================
    df.columns = df.columns.str.strip()

    df["Marca"] = df["Marca"].astype(str).str.strip().str.upper()
    df["UF"] = df["UF"].astype(str).str.strip().str.upper()
    df["Marca"] = df["Marca"].str.replace(r"\s+", " ", regex=True)

    df = df[df["UF"].isin(ESTADOS)]
    df = df[df["Marca"].isin(MARCAS)]

    # =========================
    # LABEL
    # =========================
    def label(r):
        return f"{r['Cod']} - {r['Produto']}"

    # =========================
    # 💰 TOP FATURAMENTO (CORRETO)
    # =========================
    def top_faturamento(d):

        x = d.groupby(["Mes","UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        meses = sorted(x["Mes"].unique())

        if len(meses) < 4:
            return pd.DataFrame()

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

        merged["Score"] = merged["Valor_hist"] * 0.6 + merged["Valor_atual"] * 0.4

        return merged.sort_values("Score", ascending=False)

    # =========================
    # 🔥 PRODUTO DA VEZ
    # =========================
    def produto_vez(d):

        x = d.groupby(["Mes","UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        meses = sorted(x["Mes"].unique())
        if len(meses) < 2:
            return pd.DataFrame()

        atual, anterior = meses[-1], meses[-2]

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

        m = m.groupby(["UF","Marca"]).head(2)

        return m

    # =========================
    # 💵 OPORTUNIDADE
    # =========================
    def oportunidade(d):

        x = d.groupby(["UF","Marca","Cod","Produto"], as_index=False).agg({
            "Pedidos":"sum",
            "Qtd":"sum"
        })

        x["Score"] = x["Pedidos"] / (x["Qtd"] + 1)

        return x.sort_values("Score", ascending=False)

    # =========================
    # RENDER
    # =========================
    def render(uf):

        st.header(f"🇧🇷 {uf}")

        d = df[df["UF"] == uf]

        marcas_df = pd.DataFrame({
            "Nº": range(1, len(MARCAS)+1),
            "Marca": MARCAS
        })

        # TOP FATURAMENTO
        top = top_faturamento(d)
        if not top.empty:
            top = top.groupby(["Marca"]).head(1)
            top["VAL"] = top.apply(label, axis=1)

        # PRODUTO DA VEZ
        hot = produto_vez(d)
        if not hot.empty:
            hot["VAL"] = hot.apply(label, axis=1)
            hot = hot.groupby(["Marca"]).head(1)

        # OPORTUNIDADE
        opp = oportunidade(d)
        opp = opp.groupby(["Marca"]).head(1)
        opp["VAL"] = opp.apply(label, axis=1)

        final = marcas_df.merge(top[["Marca","VAL"]], on="Marca", how="left").rename(columns={"VAL":"💰 Top Faturamento"})
        final = final.merge(hot[["Marca","VAL"]], on="Marca", how="left").rename(columns={"VAL":"🔥 Produto da Vez"})
        final = final.merge(opp[["Marca","VAL"]], on="Marca", how="left").rename(columns={"VAL":"💵 Oportunidade"})

        st.dataframe(final, use_container_width=True)

        return final

    # =========================
    # EXECUTA
    # =========================
    rs = render("RS")
    sc = render("SC")
    pr = render("PR")

    # =========================
    # DOWNLOAD
    # =========================
    full = pd.concat([
        rs.assign(UF="RS"),
        sc.assign(UF="SC"),
        pr.assign(UF="PR")
    ])

    st.download_button(
        "📥 Baixar relatório completo",
        full.to_csv(index=False).encode("utf-8"),
        "relatorio_copa_nacional.csv",
        "text/csv"
    )
