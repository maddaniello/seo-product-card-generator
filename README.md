# 🛍️ Generatore Schede Prodotto E-commerce

Un'applicazione Streamlit per generare automaticamente schede prodotto ottimizzate per e-commerce utilizzando l'intelligenza artificiale di OpenAI.

## ✨ Caratteristiche

- **Generazione automatica** di contenuti per e-commerce
- **Ottimizzazione SEO** con meta-title e meta-description
- **Interfaccia web intuitiva** con Streamlit
- **Mappatura flessibile** delle colonne CSV
- **Tone of voice personalizzabile**
- **Export CSV** dei risultati

## 🚀 Deployment su Streamlit Cloud

### 1. Fork questo repository
Clicca sul pulsante "Fork" in alto a destra per creare una copia del repository nel tuo account GitHub.

### 2. Vai su Streamlit Cloud
- Visita [share.streamlit.io](https://share.streamlit.io)
- Accedi con il tuo account GitHub
- Clicca su "New app"

### 3. Configura l'app
- **Repository**: Seleziona il repository che hai appena forkato
- **Branch**: main
- **Main file path**: app.py
- Clicca su "Deploy!"

### 4. La tua app sarà disponibile all'URL generato da Streamlit Cloud

## 🛠️ Installazione Locale

### Prerequisiti
- Python 3.8+
- Account OpenAI con API Key

### Installazione
```bash
# Clona il repository
git clone https://github.com/tuousername/product-card-generator.git
cd product-card-generator

# Installa le dipendenze
pip install -r requirements.txt

# Avvia l'applicazione
streamlit run app.py
```

## 📖 Come Usare

### 1. Configurazione Iniziale
- Inserisci la tua **API Key OpenAI** nella sidebar
- Compila le **informazioni del sito** (nome, URL, tone of voice)
- Aggiungi eventuali **istruzioni aggiuntive**

### 2. Caricamento Dati
- Carica un file **CSV** contenente i dati dei tuoi prodotti
- Visualizza l'anteprima per verificare i dati

### 3. Mappatura Colonne
- Associa ogni colonna del CSV a una variabile
- Utilizza le variabili suggerite o creane di personalizzate

### 4. Generazione
- Clicca su "**Genera Schede Prodotto**"
- Attendi il completamento dell'elaborazione
- Scarica i risultati in formato CSV

## 📊 Formato CSV Input

Il tuo file CSV dovrebbe contenere colonne come:
- `codice_prodotto` - Codice univoco del prodotto
- `nome_prodotto` - Nome del prodotto
- `categoria` - Categoria merceologica
- `marca` - Brand del prodotto
- `prezzo` - Prezzo del prodotto
- `descrizione_breve` - Descrizione esistente (opzionale)
- `caratteristiche` - Caratteristiche tecniche
- Altri campi specifici del tuo catalogo

## 📋 Output Generato

Per ogni prodotto, l'app genera:
- **Titolo prodotto** (max 80 caratteri) - Accattivante e informativo
- **Descrizione prodotto** (max 500 caratteri) - Coinvolgente e persuasiva  
- **Meta-title SEO** (max 60 caratteri) - Ottimizzato per motori di ricerca
- **Meta-description SEO** (max 155 caratteri) - Ottimizzata per CTR

## ⚙️ Configurazione Avanzata

### Tone of Voice
Scegli tra:
- **Professionale e formale** - Per B2B e prodotti premium
- **Amichevole e casual** - Per target giovane e lifestyle  
- **Tecnico e dettagliato** - Per prodotti tecnici e specialistici
- **Moderno e trendy** - Per moda e tecnologia
- **Personalizzato** - Definisci il tuo stile

### Istruzioni Aggiuntive
Personalizza la generazione con regole specifiche:
```
- Usa 'x' al posto degli asterischi
- Includi sempre il materiale nel titolo  
- Evita parole come 'fantastico', 'incredibile'
- Lunghezza titolo max 60 caratteri
- Menziona sempre la marca
```

## 💰 Costi OpenAI

L'app utilizza il modello `gpt-4o-mini` per ottimizzare i costi:
- **Costo stimato**: ~$0.0015 per prodotto
- **1000 prodotti**: ~$1.50
- I costi dipendono dalla lunghezza dei contenuti input

## 🔒 Privacy e Sicurezza

- **API Key**: Non viene mai salvata, solo utilizzata temporaneamente
- **Dati prodotti**: Processati localmente, non salvati sui server
- **Risultati**: Scaricabili solo dall'utente

## 🐛 Troubleshooting

### Errore API Key
- Verifica che la chiave sia corretta
- Controlla i crediti disponibili su OpenAI
- Assicurati di avere accesso all'API

### Errore CSV
- Verifica che il file sia in formato CSV valido
- Controlla la codifica (UTF-8 raccomandato)
- Assicurati che ci siano dati nelle colonne mappate

### Errore di Generazione
- Controlla la connessione internet
- Verifica che i dati del prodotto siano completi
- Riduci il numero di prodotti per test


## 🔗 Link Utili

- [Streamlit Documentation](https://docs.streamlit.io)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Streamlit Cloud](https://share.streamlit.io)


---

Sviluppato da Daniele Pisciottano 🦕
