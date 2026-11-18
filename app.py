import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
from docx import Document
import base64
import io

st.set_page_config(page_title="Didactique PC", page_icon="🔬", layout="wide")

if "reset" not in st.session_state:
    st.session_state.reset = 0

def nouvelle_analyse():
    st.session_state.reset += 1

def creer_docx(niveau, support, contenu_markdown):
    doc = Document()
    doc.add_heading("Expertise Didactique - Physique-Chimie", level=1)
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

niveau = st.sidebar.selectbox("Niveau :", ("Collège (Cycle 4)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC)", "Lycée Technologique (STL / STI2D)"))
support = st.sidebar.radio("Support :", ("Exercice / Évaluation", "TP / Démarche expérimentale"))
st.sidebar.divider()
st.sidebar.button("🔄 Nouvelle analyse", key="reset_side", on_click=nouvelle_analyse, use_container_width=True)

texte = st.text_area("1. Collez une consigne :", height=120, key=f"t_{st.session_state.reset}", placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure.")
fichier = st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :", key=f"f_{st.session_state.reset}")

col1, col2 = st.columns(2)
lancer = col1.button("🔍 Lancer l'analyse", type="primary", use_container_width=True)
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
    prompt = f"""Tu es un formateur expert en didactique de la physique-chimie (INSPE / formation continue). Niveau : {niveau}. Support : {support}.
Ne résous jamais l'exercice. Rédige des paragraphes clairs, pédagogiques et fluides (évite les longues listes à puces abstraites). Cite les mots exacts de la consigne.
Structure en 4 parties en Markdown :
### 1. Ce qui est caché dans la consigne (Analyse des implicites)
Explique en 2 ou 3 paragraphes les verbes à protocole caché, les sauts implicites (macroscopique / microscopique / modèle mathématique) et les non-dits de TP.
### 2. Pourquoi un élève risque de bloquer (Point de vue élève)
Donne des exemples concrets de malentendus probables (tâche matérielle vs savoir scientifique visé, interprétation littérale, polysémie).
### 3. Comment expliciter la consigne (3 niveaux d'étayage)
Propose 3 réécritures utilisables en classe de {niveau} (Niveau 1 : ouverte clarifiée ; Niveau 2 : étayage intermédiaire ; Niveau 3 : guidage pas à pas) avec une phrase sur l'intérêt de chaque version.
### 4. Question réflexive pour l'enseignant"""

    messages = list()
    messages.append({"role": "system", "content": prompt})

    if image_b64:
        modele = "pixtral-12b-latest"
        contenu_visuel = list()
        contenu_visuel.append({"type": "text", "text": "Analyse les implicites de ce document :"})
        contenu_visuel.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"})
        messages.append({"role": "user", "content": contenu_visuel})
    else:
        modele = "mistral-small-latest"
        messages.append({"role": "user", "content": contenu_texte[:12000]})

    with st.spinner("Rédaction de l'analyse didactique en cours..."):
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
                fichier_doc = creer_docx(niveau, support, resultat)
                st.download_button(
                    "📘 Télécharger l'analyse en Word (.docx)",
                    data=fichier_doc,
                    file_name=f"expertise_PC_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                st.error(f"Erreur Mistral ({rep.status_code}) : {rep.text}")
        except Exception as e:
            st.error(f"Erreur d'exécution : {e}")
