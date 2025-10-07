import streamlit as st
import pandas as pd
import openai
import json
import time
from typing import Dict, List, Optional
import io
import base64
import os
from datetime import datetime

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
        """Genera contenuti per un singolo prodotto con retry logic"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                prompt = self.create_prompt(product_data, site_info, column_mapping, additional_instructions)
                
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
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
                        if attempt == max_retries - 1:
                            st.warning(f"⚠️ Errore parsing JSON dopo {max_retries} tentativi")
                        continue
                        
            except Exception as e:
                if attempt == max_retries - 1:
                    st.warning(f"❌ Errore generazione contenuto dopo {max_retries} tentativi: {e}")
                    return None
                else:
                    # Aspetta prima di ritentare
                    time.sleep(retry_delay * (attempt + 1))
                    continue
        
        return None

def initialize_session_state():
    """Inizializza lo stato della sessione"""
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = 'idle'  # idle, processing, paused, completed
    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'total_products' not in st.session_state:
        st.session_state.total_products = 0
    if 'batch_size' not in st.session_state:
        st.session_state.batch_size = 10
    if 'processing_session_id' not in st.session_state:
        st.session_state.processing_session_id = None

def reset_processing_state():
    """Reset dello stato di elaborazione"""
    st.session_state.processing_status = 'idle'
    st.session_state.results = []
    st.session_state.current_index = 0
    st.session_state.total_products = 0
    st.session_state.processing_session_id = None

def save_checkpoint(results: List[Dict], session_id: str):
    """Salva un checkpoint dei risultati"""
    checkpoint_data = {
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'current_index': len(results)
    }
    
    # Salva in session state (persistente durante la sessione)
    st.session_state.checkpoint_data = checkpoint_data

def load_checkpoint():
    """Carica l'ultimo checkpoint"""
    return st.session_state.get('checkpoint_data', None)

def process_batch(generator, batch_data, site_info, column_mapping, additional_instructions, code_column, start_index):
    """Elabora un batch di prodotti"""
    batch_results = []
    
    for i, (_, row) in enumerate(batch_data.iterrows()):
        current_index = start_index + i
        product_code = row[code_column] if code_column else f"PROD_{current_index+1}"
        
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
            batch_results.append(result_row)
        else:
            # Anche se fallisce, aggiungi una riga vuota per mantenere l'ordine
            result_row = {
                'codice_prodotto': product_code,
                'titolo': 'ERRORE - NON GENERATO',
                'descrizione': '',
                'meta_title': '',
                'meta_description': ''
            }
            batch_results.append(result_row)
        
        # Pausa tra le chiamate
        time.sleep(0.5)
    
    return batch_results

def main():
    # Inizializza session state
    initialize_session_state()
    
    # Header
    st.title("🛍️ Generatore Schede Prodotto E-commerce")
    st.markdown("**Versione Migliorata - Supporta file grandi con checkpoint automatici**")
    st.markdown("---")
    
    st.markdown("""
    **Questo sistema genererà automaticamente:**
    - ✨ Titoli prodotto ottimizzati  
    - 📝 Descrizioni accattivanti
    - 🔍 Meta-title SEO
    - 📊 Meta-description SEO
    
    **✨ Nuove funzionalità:**
    - 🔄 Elaborazione a batch per file grandi
    - 💾 Salvataggio automatico del progresso
    - ▶️ Possibilità di riprendere l'elaborazione
    - 📥 Download risultati parziali
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
        
        # Configurazione batch
        st.subheader("⚙️ Impostazioni Elaborazione")
        batch_size = st.slider("Dimensione batch:", 5, 50, st.session_state.batch_size, 5, 
                              help="Numero di prodotti da elaborare per volta")
        st.session_state.batch_size = batch_size
        
        delay_between_batches = st.slider("Pausa tra batch (secondi):", 1, 10, 3,
                                        help="Pausa tra i batch per evitare rate limiting")
        
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
    
    # Mostra stato elaborazione se in corso
    if st.session_state.processing_status != 'idle':
        st.markdown("---")
        st.subheader("📊 Stato Elaborazione")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📋 Prodotti totali", st.session_state.total_products)
        with col2:
            st.metric("✅ Elaborati", st.session_state.current_index)
        with col3:
            progress_pct = (st.session_state.current_index / st.session_state.total_products * 100) if st.session_state.total_products > 0 else 0
            st.metric("📈 Progresso", f"{progress_pct:.1f}%")
        with col4:
            remaining = st.session_state.total_products - st.session_state.current_index
            st.metric("⏳ Rimanenti", remaining)
        
        # Progress bar
        progress_value = st.session_state.current_index / st.session_state.total_products if st.session_state.total_products > 0 else 0
        st.progress(progress_value)
        
        # Pulsanti controllo
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⏸️ Pausa", disabled=(st.session_state.processing_status != 'processing')):
                st.session_state.processing_status = 'paused'
                st.rerun()
        with col2:
            if st.button("▶️ Riprendi", disabled=(st.session_state.processing_status != 'paused')):
                st.session_state.processing_status = 'processing'
                st.rerun()
        with col3:
            if st.button("⏹️ Stop e Reset"):
                reset_processing_state()
                st.rerun()
        
        # Download risultati parziali
        if st.session_state.results:
            st.markdown("---")
            st.subheader("📥 Download Risultati Parziali")
            
            df_partial = pd.DataFrame(st.session_state.results)
            csv_buffer = io.StringIO()
            df_partial.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_string = csv_buffer.getvalue()
            
            st.download_button(
                label=f"📥 Scarica {len(st.session_state.results)} risultati parziali",
                data=csv_string,
                file_name=f"risultati_parziali_{int(time.time())}.csv",
                mime="text/csv"
            )
    
    # Area principale
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 Caricamento Catalogo")
        
        # Upload CSV
        uploaded_file = st.file_uploader(
            "Carica il file CSV del catalogo prodotti",
            type=['csv'],
            help="Carica un file CSV contenente i dati dei tuoi prodotti",
            disabled=(st.session_state.processing_status == 'processing')
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
                            key=f"mapping_{i}",
                            disabled=(st.session_state.processing_status == 'processing')
                        )
                        
                        if var_name == "Custom":
                            var_name = st.text_input(f"Nome personalizzato per '{column}':", 
                                                   key=f"custom_{i}",
                                                   disabled=(st.session_state.processing_status == 'processing'))
                        
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
                
            # Stima tempo
            estimated_time = len(csv_data) * 2  # 2 secondi per prodotto circa
            st.metric("⏱️ Tempo stimato", f"{estimated_time//60}m {estimated_time%60}s")
        
        st.markdown("---")
        st.markdown("""
        **💡 Suggerimenti:**
        - ✅ File grandi ora supportati
        - 💾 Progresso salvato automaticamente
        - ⏸️ Puoi mettere in pausa e riprendere
        - 📥 Download risultati parziali disponibile
        - 🔄 Elaborazione a batch per stabilità
        """)
        
        # Checkpoint info
        checkpoint = load_checkpoint()
        if checkpoint and st.session_state.processing_status == 'idle':
            st.markdown("---")
            st.subheader("🔄 Ripristino Sessione")
            st.info(f"Trovata sessione precedente con {checkpoint['current_index']} prodotti elaborati")
            if st.button("🔄 Ripristina Sessione Precedente"):
                st.session_state.results = checkpoint['results']
                st.session_state.current_index = checkpoint['current_index']
                st.rerun()
    
    # Pulsante per avviare la generazione
    if ('csv_data' in locals() and column_mapping and site_name and site_url and 
        st.session_state.processing_status == 'idle'):
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Avvia Generazione Schede", type="primary", use_container_width=True):
                
                # Conferma finale
                st.subheader("🔍 Riepilogo Configurazione")
                st.write(f"**Sito:** {site_name} ({site_url})")
                st.write(f"**Tone:** {tone_of_voice}")
                st.write(f"**Prodotti da elaborare:** {len(csv_data)}")
                st.write(f"**Dimensione batch:** {batch_size}")
                st.write(f"**Colonne mappate:** {len(column_mapping)}")
                
                # Inizializza elaborazione
                st.session_state.processing_status = 'processing'
                st.session_state.total_products = len(csv_data)
                st.session_state.current_index = 0
                st.session_state.results = []
                st.session_state.processing_session_id = f"session_{int(time.time())}"
                
                st.rerun()
    
    # Elaborazione in corso
    if st.session_state.processing_status == 'processing' and 'csv_data' in locals():
        
        site_info = {
            'site_name': site_name,
            'site_url': site_url,
            'tone_of_voice': tone_of_voice
        }
        
        # Trova colonna codice prodotto
        code_column = None
        for csv_col, var_name in column_mapping.items():
            if any(keyword in var_name.lower() for keyword in ['codice', 'code', 'id']):
                code_column = csv_col
                break
        
        # Elabora batch corrente
        start_idx = st.session_state.current_index
        end_idx = min(start_idx + batch_size, len(csv_data))
        
        if start_idx < len(csv_data):
            st.markdown("---")
            st.subheader(f"🚀 Elaborazione Batch {start_idx//batch_size + 1}")
            
            batch_data = csv_data.iloc[start_idx:end_idx]
            
            with st.spinner(f"Elaborando prodotti {start_idx+1}-{end_idx}..."):
                batch_results = process_batch(
                    generator, batch_data, site_info, column_mapping, 
                    additional_instructions, code_column, start_idx
                )
                
                # Aggiungi risultati
                st.session_state.results.extend(batch_results)
                st.session_state.current_index = end_idx
                
                # Salva checkpoint
                save_checkpoint(st.session_state.results, st.session_state.processing_session_id)
                
                st.success(f"✅ Batch completato! Elaborati {len(batch_results)} prodotti.")
            
            # Pausa tra batch
            if st.session_state.current_index < len(csv_data):
                time.sleep(delay_between_batches)
                st.rerun()
            else:
                # Elaborazione completata
                st.session_state.processing_status = 'completed'
                st.rerun()
    
    # Elaborazione completata
    if st.session_state.processing_status == 'completed' and st.session_state.results:
        st.markdown("---")
        st.success(f"🎉 Elaborazione completata! {len(st.session_state.results)} prodotti elaborati.")
        
        # Crea DataFrame risultati
        df_results = pd.DataFrame(st.session_state.results)
        
        # Mostra preview risultati
        st.subheader("👀 Risultati Finali")
        st.dataframe(df_results)
        
        # Download button
        csv_buffer = io.StringIO()
        df_results.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_string = csv_buffer.getvalue()
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Scarica Risultati Completi CSV",
                data=csv_string,
                file_name=f"schede_prodotto_{site_name.replace(' ', '_').lower()}_{int(time.time())}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
        with col2:
            if st.button("🔄 Nuova Elaborazione", use_container_width=True):
                reset_processing_state()
                st.rerun()
        
        # Statistiche finali
        st.subheader("📊 Statistiche Finali")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("✅ Prodotti elaborati", len(st.session_state.results))
        with col2:
            valid_titles = [r for r in st.session_state.results if r['titolo'] and r['titolo'] != 'ERRORE - NON GENERATO']
            avg_title_len = sum(len(r['titolo']) for r in valid_titles) / len(valid_titles) if valid_titles else 0
            st.metric("📏 Lunghezza media titolo", f"{avg_title_len:.0f} caratteri")
        with col3:
            valid_descs = [r for r in st.session_state.results if r['descrizione']]
            avg_desc_len = sum(len(r['descrizione']) for r in valid_descs) / len(valid_descs) if valid_descs else 0
            st.metric("📝 Lunghezza media descrizione", f"{avg_desc_len:.0f} caratteri")
        with col4:
            success_count = len([r for r in st.session_state.results if r['titolo'] and r['titolo'] != 'ERRORE - NON GENERATO'])
            success_rate = (success_count / len(st.session_state.results)) * 100 if st.session_state.results else 0
            st.metric("📊 Tasso successo", f"{success_rate:.1f}%")
    
    # Casi di input incompleto
    elif st.session_state.processing_status == 'idle':
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
        <p>SEO Product Card Generator v2.0 - Elaborazione batch con checkpoint automatici<br>
        Supporta file grandi con salvataggio automatico del progresso<br>
        Sviluppato da Daniele Pisciottano e il suo amico Claude 🦕</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
