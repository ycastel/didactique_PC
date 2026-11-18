import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
from docx import Document
import base64
import io

st.set_page_config(page_title="Didactique PC - Analyse", page_icon="🔬", layout="wide")

if "reset" not in st.session_state:
    st.session_state.reset = 0

def nouvelle_analyse():
    st.session_state.reset += 1

def creer_docx(niveau, support, contenu_markdown):
    doc = Document()
    doc.add_heading("Analyse Didactique Approfondie - Physique-Chimie", level=1)
    p = doc.add_paragraph()
    p.add_run(f"Niveau : {niveau} | Support : {support}").italic = True
    
    for ligne in contenu_markdown.split("\n"):
        l = ligne.strip()
        if not l:
            continue
        elif l.startswith("### "):
            doc.add_heading(l.replace("### ", ""), level=2)
        elif l.startswith("#### "):
            doc.add_heading(l.replace("#### ", ""), level=3)
        else:
            doc.add_paragraph(l.replace("**", ""))
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")
st.markdown("*Outil de formation (INSPE / Master M2E / Formation continue) fondé sur la didactique des sciences et les travaux de l'IGÉSR.*")

with st.expander("ℹ️ Mode d'emploi, principe de l'outil et références mobilisées (Cliquez pour ouvrir)"):
    st.markdown("""
    ### 🎯 Quel est le principe de cet outil ?
    Cet assistant n'est **pas** destiné aux élèves : c'est un **miroir réflexif pour les enseignants et étudiants en Master MEEF (M2E)**. Il permet d'analyser une consigne d'exercice ou un protocole de TP pour repérer tout ce qui reste **implicite** (les sous-entendus méthodologiques, les sauts conceptuels et les gestes expérimentaux non formulés) et qui pénalise en priorité les élèves les plus fragiles.
    
    ### 🛠️ Comment l'utiliser en formation ou en préparation de cours ?
    1. **Paramétrez le contexte** dans le menu de gauche (niveau scolaire et type d'activité : exercice écrit ou TP/ECE).
    2. **Soumettez votre support** : collez directement le texte d'une consigne, importez un sujet en PDF ou chargez une capture d'écran (PNG/JPG).
    3. **Lisez le diagnostic** : l'outil décortique les obstacles didactiques, simule les blocages probables d'un élève, puis vous propose **3 versions réécrites** (de la tâche ouverte clarifiée au guidage pas à pas).
    4. **Exportez votre fiche** au format Word (`.docx`) pour retravailler vos supports de classe ou vos analyses de séance.
    
    ### 📚 Cadres théoriques et institutionnels intégrés
    - **Rapport de l'Inspection Générale (IGÉSR) sur l'enseignement explicite :** Clarté cognitive, explicitation des procédures intellectuelles invisibles, définition des critères de réussite et prévention des inégalités scolaires.
    - **Gaston Bachelard :** Repérage des obstacles épistémologiques, du sens commun et des ruptures lexicales.
    - **Alex Johnstone & Andrée Tiberghien :** Articulation entre niveaux macroscopique, microscopique et symbolique (chimie) et entre monde des objets et des modèles (physique).
    - **Élisabeth Bautier & Patrick Rayou :** Identification des malentendus socio-cognitifs (confusion entre exécuter une tâche matérielle et s'approprier un savoir).
    - **John Sweller :** Gestion de la charge cognitive extrinsèque et de l'attention partagée lors des manipulations en TP.
    """)

niveau = st.sidebar.selectbox("Niveau :", ("Collège (Cycle 4)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC)", "Lycée Technologique (STL / STI2D)"))
support = st.sidebar.radio("Support :", ("Exercice / Évaluation", "TP / Démarche expérimentale / ECE"))
st.sidebar.divider()
st.sidebar.button("🔄 Nouvelle analyse", key="reset_side", on_click=nouvelle_analyse, use_container_width=True)

texte = st.text_area("1. Collez une consigne :", height=120, key=f"t_{st.session_state.reset}", placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure.")
fichier = st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :", key=f"f_{st.session_state.reset}")

col1, col2 = st.columns(2)
lancer = col1.button("🔍 Lancer l'analyse didactique", type="primary", use_container_width=True)
col2.button("🔄 Nouvelle analyse", key="reset_top", on_click=nouvelle_analyse, use_container_width=True)

if lancer:
    contenu_texte = texte.strip()
    image_b64 = ""

    if fichier is not None:
        nom = fichier.name.lower()
        if nom.endswith(".pdf"):
            lecteur = PdfReader(fichier)
            pages = list()
            for p in lecteur.pages:
                t = p.extract_text()
                if t:
                    pages.append(t)
            contenu_texte = "\n".join(pages).strip()
            if not contenu_texte:
                st.error("⚠️ Ce PDF est une image scannée sans texte. Prenez une capture d'écran (PNG ou JPG) et importez-la ici.")
                st.stop()
        else:
            image_b64 = base64.b64encode(fichier.read()).decode("utf-8")

    if not contenu_texte and not image_b64:
        st.warning("⚠️ Veuillez écrire une consigne ou charger un fichier.")
        st.stop()

    api_key = st.secrets["MISTRAL_API_KEY"].strip()
    prompt = f"""Tu es un formateur spécialiste en didactique de la physique-chimie intervenant en INSPE (Master MEEF / M2E) et en formation continue.
Contexte : Niveau {niveau} | Support : {support}.

CONSIGNES DE RÉDACTION :
- Ne résous jamais l'exercice.
- Rédige des paragraphes fluides, rigoureux et pédagogiques (évite les listes à puces sèches).
- Cite explicitement les mots exacts de la consigne analysée et nomme clairement les cadres théoriques et institutionnels mobilisés.

Structure impérativement ton analyse en 5 parties en Markdown :

### 1. Enjeux de clarté cognitive et cadre de l'Inspection Générale (IGÉSR)
Analyse la consigne à la lumière des préconisations de l'Inspection Générale (IGÉSR) sur l'enseignement explicite : en quoi les procédures intellectuelles attendues restent-elles invisibles pour l'élève ? Les critères de réussite et l'objectif d'apprentissage sont-ils explicites ou laissés à la devinette ? Comment ce manque d'explicitation risque-t-il de creuser les inégalités scolaires ?

### 2. Obstacles épistémologiques et ruptures avec le sens commun (Gaston Bachelard)
Analyse en un paragraphe comment la consigne heurte ou réactive des conceptions initiales (sens commun, réalisme naïf, substantialisme, polysémie du vocabulaire courant vs scientifique comme poids/masse, chaleur/température, dissoudre/fondre).

### 3. Ruptures de registres et modélisation (Johnstone & Tiberghien)
Décortique les sauts conceptuels imposés sans être explicités :
- En chimie : passage implicite entre les niveaux macroscopique (observable), microscopique (entités) et symbolique (équations) du triangle d'Alex Johnstone.
- En physique : articulation implicite entre le monde des objets/événements (mesures, montage) et le monde des théories/modèles mathématiques (Andrée Tiberghien), ou changement de registre (texte, schéma, graphique).

### 4. Malentendus socio-cognitifs, compétences cachées et charge cognitive (Bautier & Rayou, Sweller)
Repère les « consignes-valises » qui empilent plusieurs compétences (S'approprier, Analyser, Réaliser, Valider, Communiquer) derrière un verbe à protocole caché (justifier, exploiter, vérifier, conclure). Explique comment un élève risque de confondre la tâche matérielle visible avec l'enjeu de savoir (malentendu socio-cognitif de Bautier & Rayou) et identifie les risques de surcharge cognitive ou d'attention partagée en TP (John Sweller).

### 5. Gradation d'explicitation et question réflexive
Propose trois réécritures complètes utilisables en classe de {niveau}, en précisant en une phrase l'intérêt didactique de chacune :
#### Niveau 1 : Consigne ouverte (Tâche complexe clarifiée)
Débarrassée des ambiguïtés langagières mais préservant l'autonomie de raisonnement et de modélisation.
#### Niveau 2 : Étayage intermédiaire (Coup de pouce méthodologique)
Enrichie d'indices sur les registres à mobiliser, les procédures attendues (IGÉSR) ou la structure de justification attendue, sans donner les étapes.
#### Niveau 3 : Explicitation maximale (Guidage pas à pas)
Décomposée en tâches élémentaires univoques avec critères de réussite explicites, réduisant la charge cognitive extrinsèque.

Termine par une **Question réflexive** destinée au professeur/stagiaire pour interroger l'alignement entre la formulation retenue et son intention d'évaluation."""

    messages = list()
    messages.append({"role": "system", "content": prompt})

    if image_b64:
        modele = "pixtral-12b-latest"
        contenu_visuel = list()
        contenu_visuel.append({"type": "text", "text": "Analyse les implicites didactiques de ce document :"})
        contenu_visuel.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"})
        messages.append({"role": "user", "content": contenu_visuel})
    else:
        modele = "mistral-large-latest"
        messages.append({"role": "user", "content": contenu_texte[:12000]})

    with st.spinner("Rédaction de l'analyse didactique approfondie en cours..."):
        try:
            url = "https://" + "api.mistral.ai" + "/v1/chat/completions"
            rep = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": modele, "messages": messages, "temperature": 0.3},
                timeout=60
            )
            if rep.status_code == 200:
                data = rep.json()
                premier_choix = next(iter(data["choices"]))
                resultat = premier_choix["message"]["content"]
                st.markdown(resultat)
                st.divider()
