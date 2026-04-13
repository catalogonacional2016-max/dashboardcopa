import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("Análise de Produtos Copa Nacional")

# =========================
# MARCAS E ESTADOS FIXOS
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
    # LIMPEZA SEGURA
    # =========================
    df.columns = df.columns.str.strip()

    df["Marca"] = df["Marca"].astype(str).str.strip().str.upper()
    df["UF"] = df["UF"].astype(str).str.strip().str.upper()

    # normaliza espaços duplos
    df["Marca"] = df["Marca"].str.replace(r"\s+", " ", regex=True)

    # força marca correta
    df["Marca"] = df["Marca"].replace({
        "DINAIDER SCHNEIDER": "DINAIDER SCHNEIDER"
    })

    # filtros base
    df = df[df["Marca"].isin(MARCAS)]
    df = df[df["UF"].isin(ESTADOS)]

    # =========================
    # FUNÇÃO AUXILIAR
    # =========================
    def label(row):
        return f"{row['Cod']} - {row['Produto']}"

    # =========================
    # ⚡ TOP FATURAMENTO
    # =========================
    def top_faturamento(d):
        x = d.groupby(["UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()
        x = x.sort_values("Valor", ascending=False)
        x = x.groupby(["UF","Marca"]).head(1)
        return x

    # =========================
    # 🚀 PRODUTO DA VEZ
    # =========================
    def produto_vez(d):

        x = d.groupby(["Mes","UF","Marca","Cod","Produto"], as_index=False)["Valor"].sum()

        meses = sorted(x["Mes"].unique())

        if len(meses) < 2:
            return pd.DataFrame()

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

        m = m.groupby(["UF","Marca"]).head(1)

        return m

    # =========================
    # 🟢 OPORTUNIDADE
    # =========================
    def oportunidade(d):

        x = d.groupby(["UF","Marca","Cod","Produto"], as_index=False).agg({
            "Pedidos":"sum",
            "Qtd":"sum"
        })

        x["Score"] = x["Pedidos"] / (x["Qtd"] + 1)

        x = x.sort_values("Score", ascending=False)

        x = x.groupby(["UF","Marca"]).head(1)

        return x

    # =========================
    # RENDER POR ESTADO
    # =========================
    def render(uf):

        st.header(f"🇧🇷 {uf}")

        d = df[df["UF"] == uf]

        # TOP
        top = top_faturamento(d)
        top["Top"] = top.apply(label, axis=1)

        # VEZ
        hot = produto_vez(d)
        if not hot.empty:
            hot["Hot"] = hot.apply(label, axis=1)

        # OPORTUNIDADE
        opp = oportunidade(d)
        opp["Opp"] = opp.apply(label, axis=1)

        marcas = pd.DataFrame({"Marca": MARCAS})

        final = marcas.merge(
            top[["UF","Marca","Top"]],
            on="Marca",
            how="left"
        )

        final = final.merge(
            hot[["Marca","Hot"]],
            on="Marca",
            how="left"
        )

        final = final.merge(
            opp[["Marca","Opp"]],
            on="Marca",
            how="left"
        )

        final = final.rename(columns={
            "Top":"⚡ 💰 Top Faturamento",
            "Hot":"🔥🚀 Produto da Vez",
            "Opp":"💵🟢 Oportunidade"
        })

        st.dataframe(final, use_container_width=True)

    # =========================
    # EXECUTA
    # =========================
    render("RS")
    render("SC")
    render("PR")
