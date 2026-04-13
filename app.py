import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("📊 Análise de Produtos Copa Nacional")

MARCAS = [
"3M","HERC","KRONA","ROMA","DINAIDER","SCHNEIDER","STECK",
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

    df = df.dropna(subset=["UF","Marca","Cod Produto","Produto","Mes","Valor","Qtd","Pedidos"])

    df = df[df["Marca"].isin(MARCAS)]
    df = df[df["UF"].isin(ESTADOS)]

    # transforma mês em ordenável
    df["Mes"] = df["Mes"].astype(str)

    # =========================
    # FUNÇÕES AUX
    # =========================

    def cod_prod(row):
        return f"{row['Cod Produto']} - {row['Produto']}"

    # =========================
    # TOP FATURAMENTO
    # =========================
    def top_faturamento(df_uf):

        df_3m = df_uf.copy()

        top = df_3m.groupby(["Marca","Cod Produto","Produto","Mes"]).agg(
            Valor=("Valor","sum")
        ).reset_index()

        # soma total por produto
        top = top.groupby(["Marca","Cod Produto","Produto"]).agg(
            Valor=("Valor","sum")
        ).reset_index()

        # ranking
        top = top.sort_values("Valor", ascending=False)

        return top


    # =========================
    # PRODUTO DA VEZ (crescimento)
    # =========================
    def produto_vez(df_uf):

        monthly = df_uf.groupby(["Mes","Marca","Cod Produto","Produto"]).agg(
            Valor=("Valor","sum")
        ).reset_index()

        meses = sorted(monthly["Mes"].unique())

        if len(meses) < 2:
            return pd.DataFrame()

        atual = meses[-1]
        anterior = meses[-2]

        atual_df = monthly[monthly["Mes"] == atual]
        anterior_df = monthly[monthly["Mes"] == anterior]

        merged = pd.merge(
            atual_df,
            anterior_df,
            on=["Marca","Cod Produto","Produto"],
            how="left",
            suffixes=("_atual","_ant")
        )

        merged["ant"] = merged["Valor_ant"].fillna(0)
        merged["crescimento"] = merged["Valor_atual"] - merged["ant"]

        merged = merged.sort_values(["Valor_atual","crescimento"], ascending=False)

        return merged


    # =========================
    # OPORTUNIDADE
    # =========================
    def oportunidade(df_uf):

        opp = df_uf.groupby(["Marca","Cod Produto","Produto"]).agg(
            Pedidos=("Pedidos","sum"),
            Qtd=("Qtd","sum")
        ).reset_index()

        opp["Score"] = opp["Pedidos"] / (opp["Qtd"] + 1)

        return opp.sort_values("Score", ascending=False)


    # =========================
    # RENDER POR UF
    # =========================
    def render(uf):

        st.header(f"🇧🇷 {uf}")

        d = df[df["UF"] == uf]

        # -------- TOP FAT --------
        top = top_faturamento(d).groupby(["Marca"]).head(1)

        top["ProdutoFinal"] = top.apply(cod_prod, axis=1)
        top["Icone"] = "💰💰💰 ⚡ Top Faturamento"

        # -------- PRODUTO VEZ --------
        hot = produto_vez(d)

        if not hot.empty:
            hot["ProdutoFinal"] = hot.apply(lambda x: f"{x['Cod Produto']} - {x['Produto']}", axis=1)
            hot["Icone"] = "🔥🚀 Produto da Vez"

            hot = hot.groupby(["Marca"]).head(1)

        # -------- OPORTUNIDADE --------
        opp = oportunidade(d)
        opp = opp.groupby(["Marca"]).head(1)

        opp["ProdutoFinal"] = opp.apply(lambda x: f"{x['Cod Produto']} - {x['Produto']}", axis=1)
        opp["Icone"] = "💵🟢 Oportunidade"

        # -------- MERGE VISUAL --------
        marcas = pd.DataFrame({"Marca": MARCAS})

        final = marcas.merge(top[["Marca","ProdutoFinal","Icone"]], on="Marca", how="left")
        final = final.rename(columns={"ProdutoFinal":"⚡ Top Faturamento"})

        final = final.merge(
            hot[["Marca","ProdutoFinal"]],
            on="Marca", how="left"
        ).rename(columns={"ProdutoFinal":"🔥 Produto da Vez"})

        final = final.merge(
            opp[["Marca","ProdutoFinal"]],
            on="Marca", how="left"
        ).rename(columns={"ProdutoFinal":"💵 Oportunidade"})

        st.dataframe(final, use_container_width=True)

    # =========================
    # EXECUTA
    # =========================
    render("RS")
    render("SC")
    render("PR")


    # =========================
    # DOWNLOAD
    # =========================
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Baixar base tratada",
        csv,
        "relatorio_copa_nacional.csv",
        "text/csv"
    )
