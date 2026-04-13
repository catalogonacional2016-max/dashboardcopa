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

    # 🔥 remove NaN visual (evita bug de render)
    final = final.fillna("—")

    # 🔥 deixa mais compacto e sem “cara de planilha gigante”
    st.dataframe(
        final,
        use_container_width=True,
        height=420  # controla scroll (não some, mas fica pequeno)
    )

    return final
