import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
import base64

st.set_page_config(page_title="Didactique PC", page_icon="🔬", layout="wide")
st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")

niveau = st.sidebar.selectbox("Niveau :", ("Collège (Cycle 4)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC)", "Lycée Technologique (STL / STI2D)"))
support = st.sidebar.radio("Support :", ("Exercice / Évaluation", "TP / Démarche expérimentale"))

texte = st.text_area("1. Collez une consigne :", height=120, placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure.")
fichier = st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :")

if st.button("🔍 Lancer l'analyse", type="primary"):
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
                export_md = f"# Expertise Didactique - Physique-Chimie\n- **Niveau :** {niveau}\n- **Support :** {support}\n\n---\n\n{resultat}"
                st.download_button(
                    "📝 Télécharger l'analyse (.md)",
                    data=export_md,
                    file_name=f"analyse_PC_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown"
                )
            else:
                st.error(f"Erreur Mistral ({rep.status_code}) : {rep.text}")
        except Exception as e:
            st.error(f"Erreur d'exécution : {e}")
