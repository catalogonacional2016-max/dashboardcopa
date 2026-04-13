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

    final.columns = ["Marca","Top Faturamento","Produto da Vez","Oportunidade"]

    # 🚨 REMOVE QUALQUER CARA DE TABELA (SEM SCROLL)
    html = final.to_html(index=False, escape=False)

    st.markdown(
        f"""
        <style>
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background-color: #111;
            color: white;
            padding: 8px;
            text-align: left;
        }}
        td {{
            padding: 8px;
            border-bottom: 1px solid #ddd;
        }}
        </style>
        {html}
        """,
        unsafe_allow_html=True
    )

    return final
