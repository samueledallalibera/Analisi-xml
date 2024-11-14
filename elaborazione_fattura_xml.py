# Streamlit UI
st.title("Elaborazione Fattura XML")

# Caricamento dei file XML
uploaded_files = st.file_uploader("Carica i file XML", type="xml", accept_multiple_files=True)

if uploaded_files:
    st.write(f"Caricati {len(uploaded_files)} file XML")

    # Chiede all'utente se includere o meno il dettaglio delle linee
    includi_dettaglio_linee = st.radio("Vuoi includere il dettaglio delle linee?", ["sì", "no"]) == "sì"

    # Esegui il parsing e crea il DataFrame
    all_data_df = process_all_files(uploaded_files, includi_dettaglio_linee)

    # Seleziona le colonne da visualizzare
    colonne_da_esportare = seleziona_colonne(all_data_df, colonne_default)

    if colonne_da_esportare:
        # Esportazione (questa parte era mancante di codice o di indentazione)
        # Codice per esportare i dati, ad esempio come file CSV
        st.write("Esportando i dati selezionati...")
        export_option = st.radio("Vuoi esportare come CSV o Excel?", ['CSV', 'Excel'])

        if export_option == "CSV":
            st.download_button(
                label="Scarica CSV",
                data=all_data_df[colonne_da_esportare].to_csv(index=False),
                file_name="elaborazione_fattura.csv",
                mime="text/csv",
            )
        elif export_option == "Excel":
            st.download_button(
                label="Scarica Excel",
                data=all_data_df[colonne_da_esportare].to_excel(index=False),
                file_name="elaborazione_fattura.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
