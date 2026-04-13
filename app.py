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

    final = final.fillna("—")

    # =========================
    # CARDS (SEM SCROLL)
    # =========================
    for _, row in final.iterrows():

        st.markdown(
            f"""
            <div style="
                border:1px solid #ddd;
                border-radius:10px;
                padding:10px;
                margin-bottom:10px;
            ">
                <b>{row['Marca']}</b><br><br>

                💰 Top Faturamento: {row['Top Faturamento']}<br>
                🔥 Produto da Vez: {row['Produto da Vez']}<br>
                💵 Oportunidade: {row['Oportunidade']}
            </div>
            """,
            unsafe_allow_html=True
        )
