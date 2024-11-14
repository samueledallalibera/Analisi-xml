import os
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st

# Funzione gestione errori
def gestisci_errore_parsing(filename, errore):
    st.write(f"Errore nel file {filename}: {errore}. Passo al file successivo.")

# Funzione di esplorazione ricorsiva per il parsing dei dati
def parse_element(element, parsed_data, parent_tag=""):
    for child in element:
        tag_name = f"{parent_tag}/{child.tag.split('}')[-1]}" if parent_tag else child.tag.split('}')[-1]
        
        if list(child):  # Se ha figli, chiamata ricorsiva
            parse_element(child, parsed_data, tag_name)
        else:  # Altrimenti, aggiunge il testo alla struttura dei dati
            parsed_data[tag_name] = child.text

# Funzione per estrarre e parsare il file XML
def parse_xml_file(xml_file_path, includi_dettaglio_linee=True):
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    # Estrazione del namespace
    namespace = root.tag.split("}")[0].strip("{") if '}' in root.tag else ""

    # Parsing dei dati generali della fattura senza namespace
    header_data = {}
    header = root.find(".//FatturaElettronicaHeader")
    if header is not None:
        parse_element(header, header_data)

    # Parsing di Data e Numero della Fattura nel corpo
    general_data = {}
    dati_generali = root.find(".//FatturaElettronicaBody//DatiGenerali//DatiGeneraliDocumento")
    if dati_generali is not None:
        parse_element(dati_generali, general_data)

    # Parsing dei riepiloghi, ad esempio Imponibile, IVA e Totale
    riepilogo_dati = {}
    riepiloghi = root.findall(".//FatturaElettronicaBody//DatiBeniServizi//DatiRiepilogo")
    for riepilogo in riepiloghi:
        parse_element(riepilogo, riepilogo_dati)

    # Parsing delle linee solo se `includi_dettaglio_linee` è True
    line_items = []
    descrizioni = []
    lines = root.findall(".//FatturaElettronicaBody//DettaglioLinee")
    for line in lines:
        line_data = {}
        parse_element(line, line_data)
        if "Descrizione" in line_data:
            descrizioni.append(line_data["Descrizione"])
        if includi_dettaglio_linee:
            line_items.append(line_data)

    # Organizzare i dati in modo che ogni fattura sia una riga e le linee siano separate
    all_data = []

    # Combina i dati generali e di riepilogo in una singola riga
    combined_data = {**header_data, **general_data, **riepilogo_dati}

    # Se `includi_dettaglio_linee` è False, combina le descrizioni in un'unica stringa
    if not includi_dettaglio_linee and descrizioni:
        combined_data["Descrizione"] = " | ".join(descrizioni)
        all_data.append(combined_data)
    elif line_items:
        # Se `includi_dettaglio_linee` è True, aggiungi la prima linea del dettaglio
        first_line_data = line_items[0]
        combined_data = {**combined_data, **first_line_data}
        all_data.append(combined_data)

        # Aggiungi le righe successive con solo i dati delle linee
        for line_data in line_items[1:]:
            line_row = {**{key: None for key in combined_data.keys()}, **line_data}
            all_data.append(line_row)
    else:
        # Solo i dati generali e di riepilogo, senza dettagli delle linee
        all_data.append(combined_data)

    return all_data

# Funzione per iterare su più file e compilare un unico DataFrame
def process_all_files(xml_folder_path, includi_dettaglio_linee=True):
    all_data_combined = []

    # Ciclo su tutti i file nella cartella specificata
    for filename in os.listdir(xml_folder_path):
        if filename.endswith('.xml'):
            xml_file_path = os.path.join(xml_folder_path, filename)
            st.write(f"Elaborando il file: {filename}")
            try:
                # Parse del file XML e aggiunta dei dati raccolti alla lista principale
                file_data = parse_xml_file(xml_file_path, includi_dettaglio_linee)
                all_data_combined.extend(file_data)
            except ET.ParseError as e:
                gestisci_errore_parsing(filename, e)  # Chiamata alla funzione di gestione errori

    # Creazione del DataFrame combinato con tutti i dati
    all_data_df = pd.DataFrame(all_data_combined)
    return all_data_df

# Funzione per selezionare le colonne da esportare
def seleziona_colonne(df, colonne_default):
    # Filtra le colonne di default per quelle che esistono nel DataFrame
    colonne_validi = [col for col in colonne_default if col in df.columns]
    
    colonne_selezionate = st.multiselect(
        "Seleziona le colonne da visualizzare",
        options=df.columns.tolist(),
        default=colonne_validi  # Imposta le colonne valide come predefinite
    )
    return colonne_selezionate

# Elenco delle colonne di default
colonne_default = [
    "CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdPaese",
    "CedentePrestatore/DatiAnagrafici/IdFiscaleIVA/IdCodice",
    "CedentePrestatore/DatiAnagrafici/Anagrafica/Denominazione",
    "CedentePrestatore/DatiAnagrafici/RegimeFiscale",
    "CedentePrestatore/Sede/Indirizzo",
    "CedentePrestatore/Sede/NumeroCivico",
    "CedentePrestatore/Sede/CAP",
    "CedentePrestatore/Sede/Comune",
    "TipoDocumento",
    "Data",
    "Numero",
    "ImportoTotaleDocumento",
    "AliquotaIVA",
    "ImponibileImporto",
    "Imposta",
    "Descrizione",
    "PrezzoTotale"
]

# Interfaccia utente con Streamlit
st.title("Analisi XML Fatture Elettroniche")

# Seleziona la cartella dei file XML
xml_folder_path = st.text_input("Inserisci il percorso della cartella contenente i file XML:", "")

# Chiede all'utente se includere o meno il dettaglio delle linee
includi_dettaglio_linee = st.radio(
    "Vuoi includere il dettaglio delle linee?",
    ("Sì", "No")
) == "Sì"

# Verifica se la cartella è stata fornita
if xml_folder_path:
    all_data_df = process_all_files(xml_folder_path, includi_dettaglio_linee)

    if not all_data_df.empty:
        # Selezione delle colonne da esportare
        colonne_da_esportare = seleziona_colonne(all_data_df, colonne_default)

        # Esportazione in un file Excel solo con le colonne selezionate, se esistono nel DataFrame
        if colonne_da_esportare:
            # Filtra solo le colonne che esistono nel DataFrame
            colonne_esistenti = [col for col in colonne_da_esportare if col in all_data_df.columns]
            
            if colonne_esistenti:
                output_path = 'fattura_dati_combinati_selezionati.xlsx'
                all_data_df[colonne_esistenti].to_excel(output_path, index=False)
                st.success(f"Tutti i dati selezionati sono stati esportati correttamente in '{output_path}'.")
            else:
                st.warning("Nessuna delle colonne selezionate esiste nel DataFrame per l'esportazione.")
        else:
            st.warning("Nessuna colonna è stata selezionata per l'esportazione.")
    else:
        st.warning("Non sono stati trovati dati nei file XML.")

