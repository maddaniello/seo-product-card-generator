import streamlit as st
import pandas as pd
import openai
import anthropic
import json
import time
from typing import Dict, List, Optional, Tuple
import io
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import zipfile
import base64
from pathlib import Path
from PIL import Image

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
        self.anthropic_client = None
        self.serper_api_key = None
        self.ai_provider = None
        self.model = None
        self.product_images = {}  # Dizionario per memorizzare le immagini
        
    def setup_ai(self, provider: str, api_key: str, model: str) -> bool:
        """Configura il client AI (OpenAI o Claude)"""
        try:
            self.ai_provider = provider
            self.model = model
            
            if provider == "OpenAI":
                self.openai_client = openai.OpenAI(api_key=api_key)
                # Test della connessione
                self.openai_client.models.list()
                return True
            elif provider == "Claude":
                self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                # Test della connessione
                self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}]
                )
                return True
        except Exception as e:
            st.error(f"❌ Errore nella configurazione {provider}: {e}")
            return False
    
    def setup_serper(self, api_key: str) -> bool:
        """Configura Serper.dev API"""
        try:
            self.serper_api_key = api_key
            # Test connessione
            response = requests.post(
                'https://google.serper.dev/search',
                headers={'X-API-KEY': api_key, 'Content-Type': 'application/json'},
                json={'q': 'test', 'num': 1}
            )
            return response.status_code == 200
        except Exception as e:
            st.error(f"❌ Errore configurazione Serper: {e}")
            return False
    
    def load_images_from_zip(self, zip_file) -> Dict[str, bytes]:
        """Carica immagini da file ZIP e le associa ai codici prodotto"""
        images_dict = {}
        supported_formats = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']
        
        total_files = 0
        skipped_files = 0
        invalid_images = 0
        
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                for file_name in file_list:
                    total_files += 1
                    
                    # Salta cartelle e file nascosti/sistema
                    if (file_name.endswith('/') or 
                        file_name.startswith('__MACOSX') or 
                        '/__MACOSX' in file_name or
                        file_name.startswith('.') or
                        '/.DS_Store' in file_name or
                        file_name.endswith('.DS_Store') or
                        '._' in file_name):
                        skipped_files += 1
                        continue
                    
                    # Estrai estensione
                    file_ext = Path(file_name).suffix.lower()
                    
                    # Verifica se è un'immagine supportata
                    if file_ext in supported_formats:
                        # Estrai il nome del file senza estensione (= codice prodotto)
                        # Gestisce anche percorsi con cartelle (es: "immagini/PROD123.jpg")
                        product_code = Path(file_name).stem
                        
                        # Leggi l'immagine
                        image_data = zip_ref.read(file_name)
                        
                        # Verifica che sia un'immagine valida
                        try:
                            img = Image.open(io.BytesIO(image_data))
                            img.verify()  # Verifica integrità
                            
                            # Salva immagine nel dizionario
                            images_dict[product_code] = image_data
                            
                        except Exception as e:
                            invalid_images += 1
                            st.warning(f"⚠️ File {file_name} non è un'immagine valida: {e}")
                            continue
                    else:
                        skipped_files += 1
                
                self.product_images = images_dict
                
                # Messaggio dettagliato
                st.success(f"✅ Caricate **{len(images_dict)}** immagini valide")
                st.caption(f"📦 File totali nello ZIP: {total_files} | ✅ Immagini valide: {len(images_dict)} | ⏭️ File ignorati: {skipped_files} | ❌ Immagini invalide: {invalid_images}")
                
                # Mostra preview
                if images_dict:
                    with st.expander("👀 Preview Immagini Caricate", expanded=False):
                        # Mostra info dettagliate
                        st.markdown(f"**Codici prodotto trovati:** {', '.join(list(images_dict.keys())[:10])}")
                        if len(images_dict) > 10:
                            st.caption(f"... e altri {len(images_dict) - 10} codici")
                        
                        st.markdown("---")
                        
                        # Preview immagini
                        cols = st.columns(5)
                        for i, (code, img_data) in enumerate(list(images_dict.items())[:10]):
                            with cols[i % 5]:
                                st.image(img_data, caption=code, use_container_width=True)
                        
                        if len(images_dict) > 10:
                            st.caption(f"... e altre {len(images_dict) - 10} immagini")
                
                return images_dict
                
        except Exception as e:
            st.error(f"❌ Errore nel caricamento dello ZIP: {e}")
            return {}
    
    def encode_image_to_base64(self, image_data: bytes) -> str:
        """Converte immagine in base64 per API"""
        return base64.b64encode(image_data).decode('utf-8')
    
    def analyze_image_with_openai(self, image_data: bytes) -> str:
        """Analizza immagine con GPT-4 Vision"""
        try:
            base64_image = self.encode_image_to_base64(image_data)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Usa sempre gpt-4o per la visione
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analizza questa immagine prodotto in modo dettagliato. Descrivi:
1. Tipo di prodotto e categoria
2. Caratteristiche visibili (colori, materiali, dimensioni apparenti)
3. Design e stile
4. Dettagli distintivi o particolari
5. Contesto d'uso suggerito
6. Qualità percepita

Sii specifico e dettagliato. Rispondi in italiano."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            st.warning(f"⚠️ Errore analisi immagine OpenAI: {e}")
            return ""
    
    def analyze_image_with_claude(self, image_data: bytes) -> str:
        """Analizza immagine con Claude Vision"""
        try:
            base64_image = self.encode_image_to_base64(image_data)
            
            # Determina il media_type dall'immagine
            img = Image.open(io.BytesIO(image_data))
            format_map = {
                'JPEG': 'image/jpeg',
                'PNG': 'image/png',
                'WEBP': 'image/webp',
                'GIF': 'image/gif'
            }
            media_type = format_map.get(img.format, 'image/jpeg')
            
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": """Analizza questa immagine prodotto in modo dettagliato. Descrivi:
1. Tipo di prodotto e categoria
2. Caratteristiche visibili (colori, materiali, dimensioni apparenti)
3. Design e stile
4. Dettagli distintivi o particolari
5. Contesto d'uso suggerito
6. Qualità percepita

Sii specifico e dettagliato. Rispondi in italiano."""
                            }
                        ]
                    }
                ],
            )
            
            return response.content[0].text
            
        except Exception as e:
            st.warning(f"⚠️ Errore analisi immagine Claude: {e}")
            return ""
    
    def analyze_product_image(self, product_code: str) -> Tuple[Optional[bytes], str]:
        """Analizza l'immagine del prodotto se disponibile"""
        if product_code not in self.product_images:
            return None, ""
        
        image_data = self.product_images[product_code]
        
        st.info(f"🖼️ Analisi immagine per prodotto: {product_code}")
        
        # Mostra l'immagine
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(image_data, caption=f"Prodotto: {product_code}", use_container_width=True)
        
        # Analizza con AI appropriata
        with col2:
            with st.spinner("🤖 Analisi AI in corso..."):
                if self.ai_provider == "OpenAI":
                    analysis = self.analyze_image_with_openai(image_data)
                elif self.ai_provider == "Claude":
                    analysis = self.analyze_image_with_claude(image_data)
                else:
                    analysis = ""
                
                if analysis:
                    st.success("✅ Analisi completata!")
                    with st.expander("👁️ Analisi AI dell'immagine", expanded=False):
                        st.write(analysis)
        
        return image_data, analysis
    
    def search_ean_on_google(self, ean: str, num_results: int = 5) -> List[str]:
        """Cerca EAN su Google e restituisce gli URL dei risultati"""
        if not self.serper_api_key:
            return []
        
        try:
            response = requests.post(
                'https://google.serper.dev/search',
                headers={
                    'X-API-KEY': self.serper_api_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'q': f'{ean} prodotto',
                    'num': num_results,
                    'gl': 'it',
                    'hl': 'it'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                urls = []
                
                # Estrai URL dai risultati organici
                if 'organic' in data:
                    for result in data['organic'][:num_results]:
                        if 'link' in result:
                            urls.append(result['link'])
                
                return urls
            else:
                st.warning(f"⚠️ Serper API error: {response.status_code}")
                return []
                
        except Exception as e:
            st.warning(f"⚠️ Errore ricerca EAN: {e}")
            return []
    
    def scrape_product_page(self, url: str) -> str:
        """Scrape contenuto da una pagina prodotto"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Rimuovi script e style
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Estrai testo
                text = soup.get_text(separator=' ', strip=True)
                
                # Pulisci testo
                text = re.sub(r'\s+', ' ', text)
                
                # Limita lunghezza (max 1000 caratteri per pagina)
                return text[:1000]
            else:
                return ""
        except Exception as e:
            return ""
    
    def get_ean_context(self, ean: str, product_code: str = None) -> str:
        """Ottieni contesto da ricerca EAN su Google"""
        st.info(f"🔍 Ricerca informazioni per EAN: {ean}")
        
        # Inizializza log per questo EAN
        ean_log = {
            'timestamp': datetime.now().isoformat(),
            'ean': ean,
            'product_code': product_code or 'N/A',
            'search_results': [],
            'scraped_data': [],
            'total_characters': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0
        }
        
        # Cerca su Google
        urls = self.search_ean_on_google(ean)
        
        if not urls:
            st.warning("⚠️ Nessun risultato trovato per questo EAN")
            ean_log['status'] = 'no_results'
            st.session_state.ean_logs.append(ean_log)
            return ""
        
        st.success(f"✅ Trovati {len(urls)} risultati")
        ean_log['search_results'] = urls
        
        # Scrape contenuto
        contexts = []
        progress_bar = st.progress(0)
        
        # Expander per mostrare il progresso in tempo reale
        with st.expander(f"📊 Log Estrazione EAN: {ean}", expanded=False):
            for i, url in enumerate(urls):
                st.markdown(f"**{i+1}. {url}**")
                
                content = self.scrape_product_page(url)
                
                scrape_log = {
                    'url': url,
                    'position': i + 1,
                    'characters_extracted': len(content),
                    'success': bool(content)
                }
                
                if content:
                    contexts.append(content)
                    ean_log['successful_scrapes'] += 1
                    st.success(f"✅ Estratti {len(content)} caratteri")
                    
                    # Mostra preview del contenuto
                    st.caption(f"Preview: {content[:200]}...")
                    scrape_log['preview'] = content[:200]
                else:
                    ean_log['failed_scrapes'] += 1
                    st.warning("❌ Estrazione fallita")
                    scrape_log['preview'] = None
                
                ean_log['scraped_data'].append(scrape_log)
                progress_bar.progress((i + 1) / len(urls))
                time.sleep(0.5)
        
        progress_bar.empty()
        
        # Combina contesti
        combined_context = "\n\n".join(contexts)
        ean_log['total_characters'] = len(combined_context)
        
        if combined_context:
            st.success(f"✅ Estratti {len(contexts)} contenuti ({len(combined_context)} caratteri)")
            ean_log['status'] = 'success'
        else:
            st.warning("⚠️ Nessun contenuto estratto")
            ean_log['status'] = 'failed'
        
        # Salva log in session state
        st.session_state.ean_logs.append(ean_log)
        
        return combined_context
    
    def create_prompt(self, product_data: Dict, site_info: Dict, column_mapping: Dict, 
                     additional_instructions: str, fields_to_generate: List[str], 
                     ean_context: str = "", image_analysis: str = "") -> str:
        """Crea il prompt per l'AI basato sui dati del prodotto"""
        
        # Costruisce le informazioni del prodotto
        product_info = []
        for csv_col, var_name in column_mapping.items():
            value = product_data.get(csv_col, "")
            if pd.notna(value) and str(value).strip():
                product_info.append(f"{var_name}: {value}")
        
        product_info_str = "\n".join(product_info)
        
        # Aggiungi contesto EAN se disponibile
        ean_section = ""
        if ean_context:
            ean_section = f"""
INFORMAZIONI DA RICERCA EAN (Usa queste info per arricchire il contenuto):
{ean_context[:3000]}  # Limita a 3000 caratteri
"""
        
        # Aggiungi analisi immagine se disponibile
        image_section = ""
        if image_analysis:
            image_section = f"""
ANALISI VISIVA DEL PRODOTTO (Informazioni estratte dall'immagine):
{image_analysis}

IMPORTANTE: Utilizza le informazioni visive per:
- Arricchire le descrizioni con dettagli sul design e l'aspetto
- Evidenziare caratteristiche estetiche uniche
- Descrivere colori, materiali e finiture con precisione
- Suggerire il contesto d'uso appropriato
"""
        
        # Genera istruzioni per i campi richiesti
        fields_instructions = []
        fields_json = {}
        
        if "Titolo Prodotto" in fields_to_generate:
            fields_instructions.append("1. TITOLO PRODOTTO: Accattivante e informativo, max 80 caratteri")
            fields_json["titolo"] = "..."
        
        if "Short Description" in fields_to_generate:
            fields_instructions.append("2. SHORT DESCRIPTION: Breve e coinvolgente, max 160 caratteri")
            fields_json["short_description"] = "..."
        
        if "Description" in fields_to_generate:
            fields_instructions.append("3. DESCRIPTION: Completa e dettagliata, max 1000 caratteri")
            fields_json["description"] = "..."
        
        if "Bullet Points" in fields_to_generate:
            fields_instructions.append("4. BULLET POINTS: 5 punti chiave caratteristiche/benefici")
            fields_json["bullet_points"] = ["...", "...", "...", "...", "..."]
        
        if "Meta Title" in fields_to_generate:
            fields_instructions.append("5. META-TITLE SEO: Ottimizzato per motori di ricerca, max 60 caratteri")
            fields_json["meta_title"] = "..."
        
        if "Meta Description" in fields_to_generate:
            fields_instructions.append("6. META-DESCRIPTION SEO: Ottimizzata per CTR, max 155 caratteri")
            fields_json["meta_description"] = "..."
        
        if "URL" in fields_to_generate:
            fields_instructions.append("7. URL SLUG: URL-friendly, solo minuscole e trattini, max 80 caratteri")
            fields_json["url_slug"] = "..."
        
        fields_instructions_str = "\n".join(fields_instructions)
        
        prompt = f"""Sei un esperto copywriter specializzato in e-commerce e SEO.

INFORMAZIONI SITO:
- Nome sito: {site_info['site_name']}
- URL: {site_info['site_url']}
- Tone of voice: {site_info['tone_of_voice']}

DATI PRODOTTO:
{product_info_str}
{ean_section}
{image_section}

ISTRUZIONI AGGIUNTIVE:
{additional_instructions if additional_instructions else "Nessuna istruzione specifica"}

COMPITO:
Genera ESATTAMENTE i seguenti elementi per questo prodotto:

{fields_instructions_str}

FORMATO RISPOSTA (JSON):
{json.dumps(fields_json, indent=2, ensure_ascii=False)}

Importante: Rispondi SOLO con il JSON, senza testo aggiuntivo."""

        return prompt
    
    def generate_with_openai(self, prompt: str) -> Optional[str]:
        """Genera contenuto con OpenAI"""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Sei un esperto copywriter per e-commerce. Rispondi sempre e solo in formato JSON valido."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            st.warning(f"❌ Errore OpenAI: {e}")
            return None
    
    def generate_with_claude(self, prompt: str) -> Optional[str]:
        """Genera contenuto con Claude"""
        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                system="Sei un esperto copywriter per e-commerce. Rispondi sempre e solo in formato JSON valido.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
        except Exception as e:
            st.warning(f"❌ Errore Claude: {e}")
            return None
    
    def generate_product_content(self, product_data: Dict, site_info: Dict, 
                                column_mapping: Dict, additional_instructions: str,
                                fields_to_generate: List[str], ean_column: str = None,
                                product_code: str = None, use_image_analysis: bool = False) -> Optional[Dict]:
        """Genera contenuti per un singolo prodotto con retry logic"""
        max_retries = 3
        retry_delay = 1
        
        # Gestione analisi immagine
        image_analysis = ""
        if use_image_analysis and product_code:
            image_data, image_analysis = self.analyze_product_image(product_code)
        
        # Gestione EAN context
        ean_context = ""
        if ean_column and ean_column in product_data:
            ean = str(product_data[ean_column])
            if ean and ean.strip() and ean != 'nan':
                ean_context = self.get_ean_context(ean, product_code)
        
        for attempt in range(max_retries):
            try:
                prompt = self.create_prompt(product_data, site_info, column_mapping, 
                                          additional_instructions, fields_to_generate, 
                                          ean_context, image_analysis)
                
                # Genera con provider selezionato
                if self.ai_provider == "OpenAI":
                    content = self.generate_with_openai(prompt)
                elif self.ai_provider == "Claude":
                    content = self.generate_with_claude(prompt)
                else:
                    return None
                
                if not content:
                    continue
                
                # Prova a parsare il JSON
                try:
                    result = json.loads(content)
                    return result
                except json.JSONDecodeError:
                    # Se non è JSON valido, prova a estrarre il JSON dal testo
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
                    time.sleep(retry_delay * (attempt + 1))
                    continue
        
        return None

def initialize_session_state():
    """Inizializza lo stato della sessione"""
    if 'processing_status' not in st.session_state:
        st.session_state.processing_status = 'idle'
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
    if 'fields_to_generate' not in st.session_state:
        st.session_state.fields_to_generate = ["Titolo Prodotto", "Description", "Meta Title", "Meta Description"]
    if 'ean_logs' not in st.session_state:
        st.session_state.ean_logs = []
    if 'use_image_analysis' not in st.session_state:
        st.session_state.use_image_analysis = False
    if 'images_loaded' not in st.session_state:
        st.session_state.images_loaded = False

def reset_processing_state():
    """Reset dello stato di elaborazione"""
    st.session_state.processing_status = 'idle'
    st.session_state.results = []
    st.session_state.current_index = 0
    st.session_state.total_products = 0
    st.session_state.processing_session_id = None
    st.session_state.ean_logs = []

def save_checkpoint(results: List[Dict], session_id: str):
    """Salva un checkpoint dei risultati"""
    checkpoint_data = {
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'current_index': len(results)
    }
    st.session_state.checkpoint_data = checkpoint_data

def load_checkpoint():
    """Carica l'ultimo checkpoint"""
    return st.session_state.get('checkpoint_data', None)

def process_batch(generator, batch_data, site_info, column_mapping, additional_instructions, 
                 code_column, start_index, fields_to_generate, ean_column, use_image_analysis):
    """Elabora un batch di prodotti"""
    batch_results = []
    
    for i, (_, row) in enumerate(batch_data.iterrows()):
        current_index = start_index + i
        product_code = row[code_column] if code_column else f"PROD_{current_index+1}"
        
        # Genera contenuto
        generated_content = generator.generate_product_content(
            row.to_dict(), site_info, column_mapping, additional_instructions,
            fields_to_generate, ean_column, product_code, use_image_analysis
        )
        
        if generated_content:
            result_row = {'codice_prodotto': product_code}
            
            # Aggiungi solo i campi generati
            if "Titolo Prodotto" in fields_to_generate:
                result_row['titolo'] = generated_content.get('titolo', '')
            if "Short Description" in fields_to_generate:
                result_row['short_description'] = generated_content.get('short_description', '')
            if "Description" in fields_to_generate:
                result_row['description'] = generated_content.get('description', '')
            if "Bullet Points" in fields_to_generate:
                bullets = generated_content.get('bullet_points', [])
                result_row['bullet_points'] = ' | '.join(bullets) if isinstance(bullets, list) else bullets
            if "Meta Title" in fields_to_generate:
                result_row['meta_title'] = generated_content.get('meta_title', '')
            if "Meta Description" in fields_to_generate:
                result_row['meta_description'] = generated_content.get('meta_description', '')
            if "URL" in fields_to_generate:
                result_row['url_slug'] = generated_content.get('url_slug', '')
            
            batch_results.append(result_row)
        else:
            result_row = {
                'codice_prodotto': product_code,
                'errore': 'ERRORE - NON GENERATO'
            }
            batch_results.append(result_row)
        
        time.sleep(0.5)
    
    return batch_results

def main():
    initialize_session_state()
    
    # Header
    st.title("🛍️ Generatore Schede Prodotto E-commerce")
    st.markdown("**Versione 3.0 - Multi-AI con Ricerca EAN**")
    st.markdown("---")
    
    st.markdown("""
    **✨ Funzionalità:**
    - 🤖 Supporto OpenAI e Claude
    - 🔍 Ricerca automatica EAN su Google
    - ⚙️ Campi personalizzabili
    - 🔄 Elaborazione a batch
    - 💾 Salvataggio automatico
    """)
    
    generator = ProductCardGenerator()
    
    # Sidebar configurazione
    with st.sidebar:
        st.header("⚙️ Configurazione")
        
        # Selezione AI Provider
        st.subheader("🤖 AI Provider")
        ai_provider = st.selectbox(
            "Scegli il provider AI:",
            ["OpenAI", "Claude"],
            help="Seleziona quale AI utilizzare"
        )
        
        # Selezione modello in base al provider
        if ai_provider == "OpenAI":
            model_options = {
                "GPT-4o": "gpt-4o",
                "GPT-4o Mini": "gpt-4o-mini",
                "GPT-4 Turbo": "gpt-4-turbo-preview"
            }
        else:  # Claude
            model_options = {
                "Claude 4 Sonnet": "claude-sonnet-4-20250514",
                "Claude 3.7 Sonnet": "claude-3-7-sonnet-20250219",
                "Claude 3.5 Sonnet": "claude-3-5-sonnet-20241022",
                "Claude 3 Opus": "claude-3-opus-20240229"
            }
        
        selected_model_name = st.selectbox(
            "Scegli il modello:",
            list(model_options.keys())
        )
        selected_model = model_options[selected_model_name]
        
        # API Key
        st.subheader("🔑 API Keys")
        api_key = st.text_input(
            f"API Key {ai_provider}:",
            type="password",
            help=f"Inserisci la tua API Key {ai_provider}"
        )
        
        if api_key:
            if generator.setup_ai(ai_provider, api_key, selected_model):
                st.success(f"✅ {ai_provider} configurato!")
            else:
                st.stop()
        else:
            st.warning("⚠️ Inserisci l'API Key per continuare")
            st.stop()
        
        # Serper API (opzionale)
        st.subheader("🔍 Serper.dev (Opzionale)")
        serper_key = st.text_input(
            "API Key Serper.dev:",
            type="password",
            help="Necessaria solo per la ricerca EAN"
        )
        
        if serper_key:
            if generator.setup_serper(serper_key):
                st.success("✅ Serper configurato!")
        
        st.markdown("---")
        
        # Selezione campi da generare
        st.subheader("📝 Campi da Generare")
        
        all_fields = [
            "Titolo Prodotto",
            "Short Description",
            "Description",
            "Bullet Points",
            "Meta Title",
            "Meta Description",
            "URL"
        ]
        
        selected_fields = []
        for field in all_fields:
            default = field in st.session_state.fields_to_generate
            if st.checkbox(field, value=default, key=f"field_{field}"):
                selected_fields.append(field)
        
        st.session_state.fields_to_generate = selected_fields
        
        if not selected_fields:
            st.warning("⚠️ Seleziona almeno un campo!")
        
        st.markdown("---")
        
        # Configurazione batch
        st.subheader("⚙️ Impostazioni Elaborazione")
        batch_size = st.slider("Dimensione batch:", 5, 50, st.session_state.batch_size, 5)
        st.session_state.batch_size = batch_size
        
        delay_between_batches = st.slider("Pausa tra batch (secondi):", 1, 10, 3)
        
        st.markdown("---")
        
        # Informazioni sito
        st.subheader("🌐 Informazioni Sito")
        site_name = st.text_input("Nome del sito:", placeholder="MyShop")
        site_url = st.text_input("URL del sito:", placeholder="https://myshop.com")
        
        tone_options = {
            "Professionale e formale": "professionale e formale",
            "Amichevole e casual": "amichevole e casual",
            "Tecnico e dettagliato": "tecnico e dettagliato",
            "Moderno e trendy": "moderno e trendy",
            "Personalizzato": "personalizzato"
        }
        
        tone_choice = st.selectbox("Tone of voice:", list(tone_options.keys()))
        
        if tone_choice == "Personalizzato":
            tone_of_voice = st.text_area("Descrivi il tone of voice:")
        else:
            tone_of_voice = tone_options[tone_choice]
        
        # Istruzioni aggiuntive
        st.subheader("📝 Istruzioni Aggiuntive")
        additional_instructions = st.text_area(
            "Istruzioni specifiche (opzionale):",
            placeholder="Esempi:\n- Usa emoji\n- Includi materiale nel titolo\n- Max 60 caratteri per titolo"
        )
        
        st.markdown("---")
        
        # Feature Analisi Immagini
        st.subheader("🖼️ Analisi Immagini (Opzionale)")
        st.markdown("Carica un file ZIP con immagini prodotto per arricchire i contenuti")
        
        use_images = st.checkbox(
            "Attiva analisi immagini",
            value=st.session_state.use_image_analysis,
            help="Le immagini devono avere come nome il codice prodotto",
            disabled=(st.session_state.processing_status == 'processing')
        )
        st.session_state.use_image_analysis = use_images
        
        if use_images:
            images_zip = st.file_uploader(
                "Carica ZIP con immagini prodotti",
                type=['zip'],
                help="Formato: codice_prodotto.jpg/png/webp",
                disabled=(st.session_state.processing_status == 'processing')
            )
            
            if images_zip and not st.session_state.images_loaded:
                with st.spinner("📦 Caricamento immagini..."):
                    images_dict = generator.load_images_from_zip(images_zip)
                    if images_dict:
                        st.session_state.images_loaded = True
                        st.info(f"🎨 **Formati supportati:** JPG, PNG, WEBP, GIF, BMP")
                        st.info(f"📝 **Nota:** Le immagini verranno analizzate automaticamente durante la generazione")
    
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
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label=f"📥 Scarica {len(st.session_state.results)} risultati parziali",
                    data=csv_string,
                    file_name=f"risultati_parziali_{int(time.time())}.csv",
                    mime="text/csv"
                )
            with col2:
                # Download log EAN parziali
                if st.session_state.ean_logs:
                    json_logs = json.dumps(st.session_state.ean_logs, indent=2, ensure_ascii=False)
                    st.download_button(
                        label=f"📊 Scarica {len(st.session_state.ean_logs)} log EAN parziali",
                        data=json_logs,
                        file_name=f"ean_logs_parziali_{int(time.time())}.json",
                        mime="application/json"
                    )
    
    # Area principale
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📁 Caricamento Catalogo")
        
        uploaded_file = st.file_uploader(
            "Carica il file CSV del catalogo prodotti",
            type=['csv'],
            disabled=(st.session_state.processing_status == 'processing')
        )
        
        if uploaded_file is not None:
            try:
                csv_data = pd.read_csv(uploaded_file)
                st.success(f"✅ CSV caricato! ({len(csv_data)} prodotti)")
                
                with st.expander("👀 Preview dati", expanded=True):
                    st.dataframe(csv_data.head())
                
                # Mappatura colonne
                st.header("🔗 Mappatura Colonne")
                
                suggested_vars = [
                    "codice_prodotto", "nome_prodotto", "categoria", "marca",
                    "materiale", "colore", "dimensioni", "peso", "prezzo",
                    "caratteristiche", "descrizione_breve", "ean"
                ]
                
                column_mapping = {}
                ean_column = None
                
                cols = st.columns(2)
                for i, column in enumerate(csv_data.columns):
                    with cols[i % 2]:
                        st.markdown(f"**Colonna CSV:** `{column}`")
                        example_value = csv_data[column].iloc[0] if not csv_data[column].empty else 'N/A'
                        st.caption(f"Esempio: {str(example_value)[:50]}")
                        
                        var_name = st.selectbox(
                            f"Variabile per '{column}':",
                            [""] + suggested_vars + ["Custom"],
                            key=f"mapping_{i}",
                            disabled=(st.session_state.processing_status == 'processing')
                        )
                        
                        if var_name == "Custom":
                            var_name = st.text_input(
                                f"Nome personalizzato per '{column}':",
                                key=f"custom_{i}",
                                disabled=(st.session_state.processing_status == 'processing')
                            )
                        
                        if var_name and var_name != "":
                            column_mapping[column] = var_name
                            
                            # Identifica colonna EAN
                            if var_name.lower() == "ean":
                                ean_column = column
                        
                        st.markdown("---")
                
                # Mostra mappatura finale
                if column_mapping:
                    st.subheader("📋 Mappatura Finale")
                    mapping_df = pd.DataFrame([
                        {"Colonna CSV": k, "Variabile": v}
                        for k, v in column_mapping.items()
                    ])
                    st.dataframe(mapping_df, use_container_width=True)
                    
                    # Trova e mostra colonna codice identificata
                    code_column_identified = None
                    for csv_col, var_name in column_mapping.items():
                        if any(keyword in var_name.lower() for keyword in ['codice', 'code', 'id', 'sku']):
                            code_column_identified = csv_col
                            break
                    
                    if code_column_identified:
                        st.info(f"🔑 **Colonna Codice Identificata:** `{code_column_identified}` → `{column_mapping[code_column_identified]}`")
                    else:
                        st.warning("⚠️ Nessuna colonna codice identificata. Mappa una colonna con 'codice', 'code', 'id' o 'sku'")
                
                # Verifica corrispondenze immagini (sempre alla fine)
                if st.session_state.use_image_analysis and st.session_state.images_loaded and column_mapping:
                    st.markdown("---")
                    
                    # Ri-trova code_column per sicurezza
                    final_code_column = None
                    for csv_col, var_name in column_mapping.items():
                        if any(keyword in var_name.lower() for keyword in ['codice', 'code', 'id', 'sku']):
                            final_code_column = csv_col
                            break
                    
                    if final_code_column:
                        st.subheader("🖼️ Verifica Corrispondenze Immagini")
                        
                        product_codes = set(csv_data[final_code_column].astype(str))
                        image_codes = set(generator.product_images.keys())
                        matches = product_codes & image_codes
                        missing_images = product_codes - image_codes
                        extra_images = image_codes - product_codes
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📦 Prodotti CSV", len(product_codes))
                        with col2:
                            st.metric("🖼️ Immagini ZIP", len(image_codes))
                        with col3:
                            if matches:
                                match_pct = (len(matches) / len(product_codes)) * 100
                                st.metric("✅ Corrispondenze", f"{len(matches)} ({match_pct:.1f}%)")
                            else:
                                st.metric("✅ Corrispondenze", "0 (0%)")
                        
                        if matches:
                            st.success(f"✅ {len(matches)} immagini corrispondono ai prodotti!")
                            with st.expander("👀 Codici con Immagine", expanded=False):
                                st.write(", ".join(sorted(list(matches))[:20]))
                                if len(matches) > 20:
                                    st.caption(f"... e altri {len(matches) - 20}")
                        
                        if missing_images:
                            st.warning(f"⚠️ {len(missing_images)} prodotti senza immagine")
                            with st.expander("📋 Prodotti Senza Immagine", expanded=False):
                                st.write(", ".join(sorted(list(missing_images))[:20]))
                                if len(missing_images) > 20:
                                    st.caption(f"... e altri {len(missing_images) - 20}")
                        
                        if extra_images:
                            st.info(f"ℹ️ {len(extra_images)} immagini senza prodotto corrispondente")
                            with st.expander("🖼️ Immagini Extra", expanded=False):
                                st.write(", ".join(sorted(list(extra_images))[:20]))
                                if len(extra_images) > 20:
                                    st.caption(f"... e altri {len(extra_images) - 20}")
                        
                        if not matches:
                            st.error("❌ Nessuna corrispondenza trovata!")
                            st.markdown("""
                            **Possibili cause:**
                            - I nomi delle immagini non corrispondono ai codici prodotto
                            - Verifica che i nomi file siano esattamente uguali ai codici (es: `SKU123.jpg` per codice `SKU123`)
                            - Controlla maiuscole/minuscole
                            """)
                            
                            # Mostra alcuni esempi per debug
                            st.markdown("**Debug Info:**")
                            st.caption(f"Primi 5 codici CSV: {list(product_codes)[:5]}")
                            st.caption(f"Primi 5 nomi immagini: {list(image_codes)[:5]}")
                    else:
                        st.warning("⚠️ Mappa una colonna come 'codice_prodotto' per verificare le corrispondenze")
                
            except Exception as e:
                st.error(f"❌ Errore caricamento CSV: {e}")
                st.stop()
    
    with col2:
        st.header("ℹ️ Informazioni")
        
        if 'csv_data' in locals() and not csv_data.empty:
            st.metric("📊 Prodotti totali", len(csv_data))
            st.metric("📋 Colonne disponibili", len(csv_data.columns))
            if column_mapping:
                st.metric("🔗 Colonne mappate", len(column_mapping))
            
            st.metric("📝 Campi da generare", len(selected_fields))
            
            # Stima tempo
            base_time = 2  # tempo base per prodotto
            if serper_key and ean_column:
                base_time += 8  # +8 secondi per ricerca EAN
            if st.session_state.use_image_analysis and st.session_state.images_loaded:
                base_time += 3  # +3 secondi per analisi immagine
            
            estimated_time = len(csv_data) * base_time
            st.metric("⏱️ Tempo stimato", f"{estimated_time//60}m")
        
        st.markdown("---")
        st.markdown(f"""
        **💡 Configurazione:**
        - 🤖 AI: {ai_provider}
        - 🔧 Modello: {selected_model_name}
        - 🔍 Serper: {'✅ Attivo' if serper_key else '❌ Non attivo'}
        - 📝 Campi: {len(selected_fields)}
        - 🖼️ Immagini: {'✅ Attive' if st.session_state.use_image_analysis else '❌ Non attive'}
        """)
        
        # Statistiche immagini se caricate
        if st.session_state.use_image_analysis and st.session_state.images_loaded:
            st.markdown("---")
            st.subheader("🖼️ Statistiche Immagini")
            st.metric("📸 Immagini caricate", len(generator.product_images))
            
            # Mostra distribuzione formati
            if generator.product_images:
                formats = {}
                for img_data in generator.product_images.values():
                    try:
                        img = Image.open(io.BytesIO(img_data))
                        fmt = img.format
                        formats[fmt] = formats.get(fmt, 0) + 1
                    except:
                        pass
                
                if formats:
                    st.caption("**Formati:**")
                    for fmt, count in formats.items():
                        st.caption(f"- {fmt}: {count}")
        
        # Log EAN in tempo reale (durante elaborazione)
        if st.session_state.ean_logs and st.session_state.processing_status != 'idle':
            st.markdown("---")
            st.subheader("📊 Log EAN Live")
            st.metric("🔍 EAN Processati", len(st.session_state.ean_logs))
            
            if st.session_state.ean_logs:
                last_log = st.session_state.ean_logs[-1]
                st.caption(f"**Ultimo EAN:** {last_log.get('ean', 'N/A')}")
                st.caption(f"**Status:** {last_log.get('status', 'N/A')}")
                st.caption(f"**Caratteri:** {last_log.get('total_characters', 0):,}")
    
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
    
    # Pulsante avvio generazione
    if ('csv_data' in locals() and column_mapping and site_name and site_url and
        selected_fields and st.session_state.processing_status == 'idle'):
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Avvia Generazione Schede", type="primary", use_container_width=True):
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
        
        # Trova colonna codice
        code_column = None
        for csv_col, var_name in column_mapping.items():
            if any(keyword in var_name.lower() for keyword in ['codice', 'code', 'id']):
                code_column = csv_col
                break
        
        # Elabora batch
        start_idx = st.session_state.current_index
        end_idx = min(start_idx + batch_size, len(csv_data))
        
        if start_idx < len(csv_data):
            st.markdown("---")
            st.subheader(f"🚀 Elaborazione Batch {start_idx//batch_size + 1}")
            
            batch_data = csv_data.iloc[start_idx:end_idx]
            
            with st.spinner(f"Elaborando prodotti {start_idx+1}-{end_idx}..."):
                batch_results = process_batch(
                    generator, batch_data, site_info, column_mapping,
                    additional_instructions, code_column, start_idx,
                    selected_fields, ean_column if serper_key else None,
                    st.session_state.use_image_analysis
                )
                
                st.session_state.results.extend(batch_results)
                st.session_state.current_index = end_idx
                
                save_checkpoint(st.session_state.results, st.session_state.processing_session_id)
                
                st.success(f"✅ Batch completato! Elaborati {len(batch_results)} prodotti.")
            
            if st.session_state.current_index < len(csv_data):
                time.sleep(delay_between_batches)
                st.rerun()
            else:
                st.session_state.processing_status = 'completed'
                st.rerun()
    
    # Elaborazione completata
    if st.session_state.processing_status == 'completed' and st.session_state.results:
        st.markdown("---")
        st.success(f"🎉 Elaborazione completata! {len(st.session_state.results)} prodotti elaborati.")
        
        df_results = pd.DataFrame(st.session_state.results)
        
        st.subheader("👀 Risultati Finali")
        st.dataframe(df_results)
        
        csv_buffer = io.StringIO()
        df_results.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_string = csv_buffer.getvalue()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                label="📥 Scarica Risultati CSV",
                data=csv_string,
                file_name=f"schede_prodotto_{int(time.time())}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
        with col2:
            # Download log EAN se disponibili
            if st.session_state.ean_logs:
                json_logs = json.dumps(st.session_state.ean_logs, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📊 Scarica Log EAN (JSON)",
                    data=json_logs,
                    file_name=f"ean_logs_{int(time.time())}.json",
                    mime="application/json",
                    use_container_width=True
                )
        with col3:
            if st.button("🔄 Nuova Elaborazione", use_container_width=True):
                reset_processing_state()
                st.rerun()
        
        # Statistiche EAN se disponibili
        if st.session_state.ean_logs:
            st.markdown("---")
            st.subheader("🔍 Statistiche Ricerca EAN")
            
            total_ean = len(st.session_state.ean_logs)
            successful = len([log for log in st.session_state.ean_logs if log.get('status') == 'success'])
            failed = len([log for log in st.session_state.ean_logs if log.get('status') == 'failed'])
            no_results = len([log for log in st.session_state.ean_logs if log.get('status') == 'no_results'])
            
            total_scraped = sum(log.get('successful_scrapes', 0) for log in st.session_state.ean_logs)
            total_failed_scrapes = sum(log.get('failed_scrapes', 0) for log in st.session_state.ean_logs)
            total_chars = sum(log.get('total_characters', 0) for log in st.session_state.ean_logs)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🔍 EAN Processati", total_ean)
            with col2:
                st.metric("✅ Successi", successful)
            with col3:
                st.metric("📄 Pagine Estratte", total_scraped)
            with col4:
                st.metric("📊 Caratteri Totali", f"{total_chars:,}")
            
            # Log dettagliato EAN
            with st.expander("📋 Log Dettagliato Ricerche EAN", expanded=False):
                for i, log in enumerate(st.session_state.ean_logs):
                    st.markdown(f"### {i+1}. EAN: `{log['ean']}` - Prodotto: `{log['product_code']}`")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        status_emoji = {
                            'success': '✅',
                            'failed': '❌',
                            'no_results': '⚠️'
                        }
                        st.write(f"**Status:** {status_emoji.get(log.get('status', ''), '❓')} {log.get('status', 'unknown')}")
                    with col2:
                        st.write(f"**URL Trovati:** {len(log.get('search_results', []))}")
                    with col3:
                        st.write(f"**Scraping Riusciti:** {log.get('successful_scrapes', 0)}/{log.get('successful_scrapes', 0) + log.get('failed_scrapes', 0)}")
                    
                    st.write(f"**Caratteri Estratti:** {log.get('total_characters', 0):,}")
                    st.write(f"**Timestamp:** {log.get('timestamp', 'N/A')}")
                    
                    # Mostra URL e risultati scraping
                    if log.get('scraped_data'):
                        st.markdown("**Dettagli Scraping:**")
                        for scrape in log['scraped_data']:
                            icon = "✅" if scrape['success'] else "❌"
                            st.markdown(f"{icon} **{scrape['position']}.** [{scrape['url']}]({scrape['url']})")
                            if scrape['success']:
                                st.caption(f"└─ Estratti {scrape['characters_extracted']} caratteri")
                                if scrape.get('preview'):
                                    with st.expander("👁️ Preview contenuto", expanded=False):
                                        st.text(scrape['preview'])
                    
                    st.markdown("---")
        
        # Statistiche finali prodotti
        st.subheader("📊 Statistiche Prodotti")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("✅ Prodotti elaborati", len(st.session_state.results))
        with col2:
            valid_titles = [r for r in st.session_state.results if r.get('titolo') and r.get('titolo') != 'ERRORE - NON GENERATO']
            avg_title_len = sum(len(str(r.get('titolo', ''))) for r in valid_titles) / len(valid_titles) if valid_titles else 0
            st.metric("📏 Lunghezza media titolo", f"{avg_title_len:.0f} caratteri")
        with col3:
            valid_descs = [r for r in st.session_state.results if r.get('description')]
            avg_desc_len = sum(len(str(r.get('description', ''))) for r in valid_descs) / len(valid_descs) if valid_descs else 0
            st.metric("📝 Lunghezza media descrizione", f"{avg_desc_len:.0f} caratteri")
        with col4:
            success_count = len([r for r in st.session_state.results if not r.get('errore')])
            success_rate = (success_count / len(st.session_state.results)) * 100 if st.session_state.results else 0
            st.metric("📊 Tasso successo", f"{success_rate:.1f}%")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>SEO Product Card Generator v3.0 - Multi-AI con EAN Search & Image Analysis<br>
        Supporta OpenAI, Claude, ricerca automatica su Google e analisi visiva AI<br>
        Sviluppato da Daniele Pisciottano 🚀</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
