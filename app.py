import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
from docx import Document
import base64
import io

st.set_page_config(page_title="Didactique PC", page_icon="🔬", layout="wide")
st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")

with st.expander("ℹ️ Mode d'emploi et cadres théoriques (IGÉSR, Bachelard, Johnstone, Brousseau)"):
    st.write("Cet outil analyse les implicites des consignes (exercices et TP) en distinguant les prérequis légitimes du BO des implicites parasites, tout en veillant à éviter l'effet Topaze (guidage mécanique). Il propose 3 niveaux d'étayage exportables en Word.")

niveau = st.sidebar.selectbox("Niveau :", ("Collège (Cycle 4)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC)", "Lycée Technologique (STL / STI2D)"))
support = st.sidebar.radio("Support :", ("Exercice / Évaluation", "TP / Démarche expérimentale / ECE"))

texte = st.text_area("1. Collez une consigne :", height=120, placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure.")
fichier = st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :")

col1, col2 = st.columns(2)
lancer = col1.button("🔍 Lancer l'analyse didactique", type="primary", use_container_width=True)
if col2.button("🔄 Nouvelle analyse", use_container_width=True):
    st.rerun()

if lancer:
    contenu_texte = texte.strip()
    image_b64 = ""

    if fichier is not None:
        if fichier.name.lower().endswith(".pdf"):
            lecteur = PdfReader(fichier)
            contenu_texte = "\n".join([p.extract_text() for p in lecteur.pages if p.extract_text()]).strip()
            if not contenu_texte:
                st.error("⚠️ PDF scanné sans texte. Importez une capture d'écran (PNG/JPG).")
                st.stop()
        else:
            image_b64 = base64.b64encode(fichier.read()).decode("utf-8")

    if not contenu_texte and not image_b64:
        st.warning("⚠️ Saisissez une consigne ou chargez un fichier.")
        st.stop()

    api_key = st.secrets["MISTRAL_API_KEY"].strip()
    prompt = f"Tu es un formateur en didactique de la physique-chimie (INSPE / formation continue). Niveau : {niveau}. Support : {support}. Ne résous jamais l'exercice. Ne juge pas l'enseignant : distingue les prérequis légitimes du programme (BO) des implicites parasites. Rédige des paragraphes fluides et nuancés en citant les mots de la consigne. Structure en 5 parties Markdown : ### 1. Clarté cognitive et cadre IGÉSR (transparence des procédures et critères de réussite) ; ### 2. Obstacles épistémologiques (Gaston Bachelard) et ruptures de registres (macroscopique/microscopique/symbolique d'Alex Johnstone ou objets/modèles d'Andrée Tiberghien) ; ### 3. Contrat didactique (Guy Brousseau), malentendus socio-cognitifs (Bautier & Rayou) et charge cognitive (Sweller) adaptés au support {support} ; ### 4. Gradation d'explicitation en 3 niveaux pour {niveau} (Niveau 1 : ouverte clarifiée ; Niveau 2 : étayage intermédiaire ; Niveau 3 : pas à pas, en signalant le risque d'effet Topaze) ; ### 5. Nuances, contre-arguments légitimes (quand la consigne initiale est pertinente) et question réflexive."

    messages = [{"role": "system", "content": prompt}]
    if image_b64:
        modele = "pixtral-12b-latest"
        messages.append({"role": "user", "content": [{"type": "text", "text": "Analyse les implicites de ce document :"}, {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"}]})
    else:
        modele = "mistral-small-latest"
        messages.append({"role": "user", "content": contenu_texte[:12000]})

    with st.spinner("Analyse didactique en cours..."):
        url = "https://" + "api.mistral.ai" + "/v1/chat/completions"
        rep = requests.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json={"model": modele, "messages": messages, "temperature": 0.25}, timeout=120)
        if rep.status_code == 200:
            resultat = rep.json()["choices"][0]["message"]["content"]
            st.markdown(resultat)
            st.divider()
            
            bo = "📜 **Référence BO :** "
            if "Cycle 4" in niveau: bo += "Programme du cycle 4 (BOEN n° 31 du 30 juillet 2020) — Pratiquer des démarches scientifiques et des langages, transition qualitative vers le modèle particulaire."
            elif "Seconde" in niveau: bo += "Programme de Seconde GT (BOEN spécial n° 1 du 22 janvier 2019) — Compétences APP, ANA, REA, VAL, COM, modélisation mathématique et incertitudes."
            elif "Spécialité" in niveau: bo += "Programmes de Spécialité PC Première et Terminale (BOEN n° 1 du 22 janv. 2019 et n° 8 du 25 juil. 2019) & notes de service ECE — Autonomie de protocole et analyse critique."
            else: bo += "Programmes des séries technologiques STL-SPCL et STI2D (BOEN 2019) — Démarche de projet, contextualisation technique et chaînes de mesure."
            st.info(bo)

            doc = Document()
            doc.add_heading(f"Analyse Didactique PC ({niveau} - {support})", level=1)
            for ligne in (resultat + "\n\n" + bo).split("\n"):
                if ligne.strip(): doc.add_paragraph(ligne.replace("#", "").replace("*", "").strip())
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            st.download_button("📘 Télécharger en Word (.docx)", data=buf, file_name=f"analyse_PC_{datetime.now().strftime('%Y%m%d_%H%M')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            st.error(f"Erreur Mistral ({rep.status_code}) : {rep.text}")
