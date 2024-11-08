import os
import xml.etree.ElementTree as ET
import pandas as pd
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import streamlit as st

# Carica le variabili d'ambiente
load_dotenv()

# Inizializza l'istanza LLM
llm = ChatOpenAI(
    api_key="lm-studio",
    base_url="http://127.0.0.1:1234/v1",
    temperature=0.5,
)

# Funzione gestione errori
def gestisci_errore_parsing(filename, errore):
    st.error(f"Errore nel file {filename}: {errore}. Passo al file successivo.")

# Funzione di esplorazione ricorsiva per il parsing dei dati
def parse_element(element, parsed_data, parent_tag=""):
    for child in element:
        tag_name = f"{parent_tag}/{child.tag.split('}')[-1]}" if parent_tag else child.tag.split('}')[-1]
        
        if list(child):  # Se ha figli, chiamata ricorsiva
            parse_element(child, parsed_data, tag_name)
        else:  # Altrimenti, aggiunge il testo alla struttura dei dati
            parsed_data[tag_name] = child.text

# Funzione per riassumere il contenuto della descrizione utilizzando l'IA
def riassumi_descrizione(descrizione_query):
    # Definisci il prompt
    prompt = PromptTemplate(
        template="Descrivi il contenuto della query in massimo 5 parole, la struttura della descrizione deve essere categoria del bene: eventuali dettagli, non ripetere la parola query. ad esempio una descrizione come Elettronici: Asciugacapelli va bene, una come La query descrive i servizi di manutenzione e installazione dei sistemi idraulici in edifici, inclusi filtri autopulenti per acqua, tubi flessibili, valvole a sfera, raccordi, miscelatori, portagomma e altri componenti non va bene\n{query}\n",
        input_variables=["query"]
    )
   
    # Chain del prompt con LLM
    chain = prompt | llm
    
    # Invochiamo la chain per ottenere la risposta
    response = chain.invoke({"query": descrizione_query})
    
    # Estrai solo il contenuto del testo dalla risposta, che è un oggetto AIMessage
    descrizione_riassunta = response.content.strip()  # Accedi al campo `content` dell'oggetto AIMessage
    
    return descrizione_riassunta

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

    # Se `includi_dettaglio_linee` è False, combina le descrizioni in un'unica stringa e riassumila
    if not includi_dettaglio_linee and descrizioni:
        descrizione_completa = " | ".join(descrizioni)
        descrizione_riassunta = riassumi_descrizione(descrizione_completa)
        combined_data["Descrizione"] = descrizione_riassunta
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
    st.write("Le seguenti colonne sono disponibili (default):")
    for col in colonne_default:
        st.write(f"- {col}")
    
    # Chiedi se vuoi usare le colonne di default o visualizzare tutte
    scelta = st.radio("Vuoi visualizzare tutte le colonne o usare quelle di default?", ['tutte', 'default'])
    
    if scelta == "tutte":
        st.write("Le seguenti colonne sono disponibili nel file XML:")
        for col in df.columns:
            st.write(f"- {col}")
        colonne_selezionate = st.text_input("Inserisci le colonne da visualizzare, separate da virgola:")
        colonne_selezionate = [col.strip() for col in colonne_selezionate.split(',')]
        
        # Verifica se tutte le colonne selezionate esistono nel DataFrame
        colonne_valide = [col for col in colonne_selezionate if col in df.columns]
        if len(colonne_valide) == 0:
            st.warning("Nessuna colonna valida selezionata.")
            return None
        return colonne_valide
    else:
        return colonne_default

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
        # Esportazione
