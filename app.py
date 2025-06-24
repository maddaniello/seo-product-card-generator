import streamlit as st
import pandas as pd
import openai
import json
import time
from typing import Dict, List, Optional
import io
import base64

# Configurazione pagina
st.set_page_config(
    page_title="🛍️ Generatore Schede Prodotto E-commerce",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

class ProductCardGenerator:
    def __init__(self):
        self.openai_client = None
        
    def setup_openai(self, api_key: str) -> bool:
        """Configura il client OpenAI"""
        try:
            self.openai_client = openai.OpenAI(api_key=api_key)
            # Test della connessione
            self.openai_client.models.list()
            return True
        except Exception as e:
            st.error(f"❌ Errore nella configurazione OpenAI: {e}")
            return False
    
    def create_prompt(self, product_data: Dict, site_info: Dict, column_mapping: Dict, additional_instructions: str) -> str:
        """Crea il prompt per OpenAI basato sui dati del prodotto"""
        
        # Costruisce le informazioni del prodotto
        product_info = []
        for csv_col, var_name in column_mapping.items():
            value = product_data.get(csv_col, "")
            if pd.notna(value) and str(value).strip():
                product_info.append(f"{var_name}: {value}")
        
        product_info_str = "\n".join(product_info)
        
        prompt = f"""Sei un esperto copywriter specializzato in e-commerce e SEO.

INFORMAZIONI SITO:
- Nome sito: {site_info['site_name']}
- URL: {site_info['site_url']}
- Tone of voice: {site_info['tone_of_voice']}

DATI PRODOTTO:
{product_info_str}

ISTRUZIONI AGGIUNTIVE:
{additional_instructions if additional_instructions else "Nessuna istruzione specifica"}

COMPITO:
Genera ESATTAMENTE i seguenti 4 elementi per questo prodotto, seguendo il formato JSON specificato:

1. TITOLO DEL PRODOTTO: Accattivante e informativo, max 80 caratteri
2. DESCRIZIONE DEL PRODOTTO: Coinvolgente e persuasiva, MAX 500 caratteri
3. META-TITLE SEO: Ottimizzato per i motori di ricerca, max 60 caratteri
4. META-DESCRIPTION SEO: Ottimizzata per CTR, max 155 caratteri

FORMATO RISPOSTA (JSON):
{{
    "titolo": "...",
    "descrizione": "...",
    "meta_title": "...",
    "meta_description": "..."
}}

Importante: Rispondi SOLO con il JSON, senza testo aggiuntivo."""

        return prompt
    
    def generate_product_content(self, product_data: Dict, site_info: Dict, column_mapping: Dict, additional_instructions: str) -> Optional[Dict]:
        """Genera contenuti per un singolo prodotto"""
        try:
            prompt = self.create_prompt(product_data, site_info, column_mapping, additional_instructions)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Modello più economico e veloce
                messages=[
                    {"role": "system", "content": "Sei un esperto copywriter per e-commerce. Rispondi sempre e solo in formato JSON valido."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            
            # Prova a parsare il JSON
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # Se non è JSON valido, prova a estrarre il JSON dal testo
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
                else:
                    st.error(f"⚠️ Errore parsing JSON. Risposta: {content}")
                    return None
                    
        except Exception as e:
            st.error(f"❌ Errore generazione contenuto: {e}")
            return None

def main():
    # Header
    st.title("🛍️ Generatore Schede Prodotto E-commerce")
    st.markdown("---")
    
    st.markdown("""
    **Questo sistema genererà automaticamente:**
    - ✨ Titoli prodotto ottimizzati  
    - 📝 Descrizioni accattivanti
    - 🔍 Meta-title SEO
    - 📊 Meta-description SEO
    """)
    
    # Inizializza il generatore
    generator = ProductCardGenerator()
    
    # Sidebar per configurazione
    with st.sidebar:
        st.header("⚙️ Configurazione")
        
        # Step 1: API Key OpenAI
        st.subheader("🔑 API Key OpenAI")
        api_key = st.text_input("Inserisci la tua API Key OpenAI:", type="password", help="La tua API Key non viene salvata")
        
        if api_key:
            if generator.setup_openai(api_key):
                st.success("✅ OpenAI configurato correttamente!")
            else:
                st.stop()
        else:
            st.warning("⚠️ Inserisci la tua API Key per continuare")
            st.stop()
        
        st.markdown("---")
        
        # Step 2: Informazioni sito
        st.subheader("🌐 Informazioni Sito")
        site_name = st.text_input("Nome del sito e-commerce:", placeholder="es. MyShop")
        site_url = st.text_input("URL del sito:", placeholder="es. https://myshop.com")
        
        tone_options = {
            "Professionale e formale": "professionale e formale",
            "Amichevole e casual": "amichevole e casual", 
            "Tecnico e dettagliato": "tecnico e dettagliato",
            "Moderno e trendy": "moderno e trendy",
            "Personalizzato": "personalizzato"
        }
        
        tone_choice = st.selectbox("Tone of voice:", list(tone_options.keys()))
        
        if tone_choice == "Personalizzato":
            tone_of_voice = st.text_area("Descrivi il tone of voice desiderato:", placeholder="es. Elegante e sofisticato...")
        else:
            tone_of_voice = tone_options[tone_choice]
        
        # Step 3: Istruzioni aggiuntive
        st.subheader("📝 Istruzioni Aggiuntive")
        additional_instructions = st.text_area(
            "Inserisci eventuali istruzioni specifiche:",
            placeholder="""Esempi:
- Usa 'x' al posto degli asterischi
- Includi sempre il materiale nel titolo
- Evita parole come 'fantastico', 'incredibile'
- Lunghezza titolo max 60 caratteri""",
            help="Istruzioni opzionali per personalizzare la generazione"
        )
    
    # Area principale
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 Caricamento Catalogo")
        
        # Upload CSV
        uploaded_file = st.file_uploader(
            "Carica il file CSV del catalogo prodotti",
            type=['csv'],
            help="Carica un file CSV contenente i dati dei tuoi prodotti"
        )
        
        if uploaded_file is not None:
            try:
                # Leggi CSV
                csv_data = pd.read_csv(uploaded_file)
                st.success(f"✅ CSV caricato con successo! ({len(csv_data)} prodotti)")
                
                # Mostra preview
                with st.expander("👀 Preview dati", expanded=True):
                    st.dataframe(csv_data.head())
                
                # Step 4: Mappatura colonne
                st.header("🔗 Mappatura Colonne")
                st.markdown("Associa ogni colonna del CSV a una variabile per la generazione dei contenuti.")
                
                # Variabili suggerite
                suggested_vars = [
                    "codice_prodotto", "nome_prodotto", "categoria", "marca", 
                    "materiale", "colore", "dimensioni", "peso", "prezzo", 
                    "caratteristiche", "descrizione_breve"
                ]
                
                column_mapping = {}
                
                # Crea mapping dinamico
                cols = st.columns(2)
                for i, column in enumerate(csv_data.columns):
                    with cols[i % 2]:
                        st.markdown(f"**Colonna CSV:** `{column}`")
                        example_value = csv_data[column].iloc[0] if not csv_data[column].empty else 'N/A'
                        st.caption(f"Esempio: {str(example_value)[:50]}{'...' if len(str(example_value)) > 50 else ''}")
                        
                        var_name = st.selectbox(
                            f"Variabile per '{column}':",
                            [""] + suggested_vars + ["Custom"],
                            key=f"mapping_{i}"
                        )
                        
                        if var_name == "Custom":
                            var_name = st.text_input(f"Nome personalizzato per '{column}':", key=f"custom_{i}")
                        
                        if var_name and var_name != "":
                            column_mapping[column] = var_name
                        
                        st.markdown("---")
                
                # Mostra mappatura finale
                if column_mapping:
                    st.subheader("📋 Mappatura Finale")
                    mapping_df = pd.DataFrame([
                        {"Colonna CSV": k, "Variabile": v} 
                        for k, v in column_mapping.items()
                    ])
                    st.dataframe(mapping_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"❌ Errore nel caricamento del CSV: {e}")
                st.stop()
    
    with col2:
        st.header("ℹ️ Informazioni")
        
        if 'csv_data' in locals() and not csv_data.empty:
            st.metric("📊 Prodotti totali", len(csv_data))
            st.metric("📋 Colonne disponibili", len(csv_data.columns))
            if column_mapping:
                st.metric("🔗 Colonne mappate", len(column_mapping))
        
        st.markdown("---")
        st.markdown("""
        **💡 Suggerimenti:**
        - Assicurati che il CSV contenga tutte le informazioni necessarie
        - Mappa almeno nome prodotto e categoria
        - Le istruzioni aggiuntive possono migliorare i risultati
        - Il processo può richiedere alcuni minuti
        """)
    
    # Pulsante per avviare la generazione
    if 'csv_data' in locals() and column_mapping and site_name and site_url:
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Genera Schede Prodotto", type="primary", use_container_width=True):
                
                # Conferma finale
                st.subheader("🔍 Riepilogo Configurazione")
                st.write(f"**Sito:** {site_name} ({site_url})")
                st.write(f"**Tone:** {tone_of_voice}")
                st.write(f"**Prodotti da elaborare:** {len(csv_data)}")
                st.write(f"**Colonne mappate:** {len(column_mapping)}")
                
                # Inizia elaborazione
                st.markdown("---")
                st.subheader("🚀 Generazione in Corso...")
                
                site_info = {
                    'site_name': site_name,
                    'site_url': site_url,
                    'tone_of_voice': tone_of_voice
                }
                
                results = []
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Trova colonna codice prodotto
                code_column = None
                for csv_col, var_name in column_mapping.items():
                    if any(keyword in var_name.lower() for keyword in ['codice', 'code', 'id']):
                        code_column = csv_col
                        break
                
                # Elabora prodotti
                for index, row in csv_data.iterrows():
                    product_code = row[code_column] if code_column else f"PROD_{index+1}"
                    
                    # Aggiorna progress
                    progress = (index + 1) / len(csv_data)
                    progress_bar.progress(progress)
                    status_text.text(f"⚙️ Elaborando prodotto {index+1}/{len(csv_data)}: {product_code}")
                    
                    # Genera contenuto
                    generated_content = generator.generate_product_content(
                        row.to_dict(), site_info, column_mapping, additional_instructions
                    )
                    
                    if generated_content:
                        result_row = {
                            'codice_prodotto': product_code,
                            'titolo': generated_content.get('titolo', ''),
                            'descrizione': generated_content.get('descrizione', ''),
                            'meta_title': generated_content.get('meta_title', ''),
                            'meta_description': generated_content.get('meta_description', '')
                        }
                        results.append(result_row)
                    
                    # Pausa per rate limiting
                    time.sleep(0.5)
                
                # Completa progress bar
                progress_bar.progress(1.0)
                status_text.text("✅ Elaborazione completata!")
                
                # Mostra risultati
                if results:
                    st.success(f"🎉 Generazione completata! {len(results)} prodotti elaborati.")
                    
                    # Crea DataFrame risultati
                    df_results = pd.DataFrame(results)
                    
                    # Mostra preview risultati
                    st.subheader("👀 Preview Risultati")
                    st.dataframe(df_results)
                    
                    # Download button
                    csv_buffer = io.StringIO()
                    df_results.to_csv(csv_buffer, index=False, encoding='utf-8')
                    csv_string = csv_buffer.getvalue()
                    
                    st.download_button(
                        label="📥 Scarica Risultati CSV",
                        data=csv_string,
                        file_name=f"schede_prodotto_{site_name.replace(' ', '_').lower()}_{int(time.time())}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                    
                    # Statistiche finali
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("✅ Prodotti elaborati", len(results))
                    with col2:
                        avg_title_len = sum(len(r['titolo']) for r in results) / len(results)
                        st.metric("📏 Lunghezza media titolo", f"{avg_title_len:.0f} caratteri")
                    with col3:
                        avg_desc_len = sum(len(r['descrizione']) for r in results) / len(results)
                        st.metric("📝 Lunghezza media descrizione", f"{avg_desc_len:.0f} caratteri")
                    with col4:
                        success_rate = (len(results) / len(csv_data)) * 100
                        st.metric("📊 Tasso successo", f"{success_rate:.1f}%")
                
                else:
                    st.error("❌ Nessun risultato generato. Controlla la configurazione.")
    
    else:
        if 'csv_data' not in locals():
            st.info("📁 Carica un file CSV per iniziare")
        elif not column_mapping:
            st.info("🔗 Mappa almeno una colonna per continuare")
        elif not site_name or not site_url:
            st.info("🌐 Completa le informazioni del sito nella sidebar")

 # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>SEO Product Card Generator - Crea schede prodotto e-commerce ottimizzate partendo da un catalogo - Sviluppato da Daniele Pisciottano e il suo amico Claude 🦕</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
