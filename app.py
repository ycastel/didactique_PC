import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
import fitz  # PyMuPDF pour convertir les PDF scannés en images
import base64
import io
import re

st.set_page_config(page_title="Didactique PC - Implicites", page_icon="🔬", layout="wide")

if "analyse_resultat" not in st.session_state:
    st.session_state.analyse_resultat = None
if "dernier_contexte" not in st.session_state:
    st.session_state.dernier_contexte = {}
if "compteur_reset" not in st.session_state:
    st.session_state.compteur_reset = 0

def reinitialiser_application():
    st.session_state.analyse_resultat = None
    st.session_state.dernier_contexte = {}
    st.session_state.compteur_reset += 1

def nettoyer_texte_xml(texte):
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texte)

def generer_docx(contexte, texte_analyse):
    from docx import Document
    doc = Document()
    doc.add_heading("Diagnostic Didactique et Conseils d'Explicitation - Physique-Chimie", level=1)
    
    p_meta = doc.add_paragraph()
    p_meta.add_run("Date : ").bold = True
    p_meta.add_run(f"{contexte.get('date', '')}\n")
    p_meta.add_run("Niveau : ").bold = True
    p_meta.add_run(f"{contexte.get('niveau', '')}\n")
    p_meta.add_run("Support : ").bold = True
    p_meta.add_run(f"{contexte.get('type', '')}")
    
    texte_propre = nettoyer_texte_xml(texte_analyse)
    for ligne in texte_propre.split("\n"):
        ligne_propre = ligne.strip()
        if ligne_propre.startswith("### "):
            doc.add_heading(ligne_propre.replace("### ", ""), level=2)
        elif ligne_propre.startswith("- "):
            doc.add_paragraph(ligne_propre.replace("- ", "").replace("**", ""), style="List Bullet")
        elif ligne_propre:
            doc.add_paragraph(ligne_propre.replace("**", ""))
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")
st.markdown("*Outil d'analyse réflexive (INSPE / Formation continue) fondé sur la didactique de la physique-chimie.*")

with st.sidebar:
    st.header("⚙️ Contexte pédagogique")
    niveau = st.selectbox(
        "Niveau d'enseignement :",
        [
            "Collège (Cycle 4 : 5e, 4e, 3e)",
            "Lycée Général (Seconde)",
            "Lycée Général (Spécialité PC - 1ère / Terminale)",
            "Lycée Technologique (STL / STI2D)"
        ]
    )
    type_activite = st.radio(
        "Type de support :",
        [
            "Exercice écrit / Évaluation sommative",
            "Travaux Pratiques (TP) / Démarche expérimentale / ECE"
        ]
    )
    
    st.divider()
    st.button("🔄 Soumettre une autre analyse", key="btn_reset_sidebar", on_click=reinitialiser_application, use_container_width=True)
    
    st.divider()
    st.info("""
    **📚 Cadres didactiques mobilisés :**
    - Compétences de la démarche scientifique (APP, ANA, REA, VAL, COM)
    - Registres de représentation (Triangle de Johnstone / Modélisation)
    - Malentendus socio-cognitifs (tâche vs enjeu de savoir)
    - Charge cognitive et étayage gradué
    """)

onglet_texte, onglet_pdf, onglet_image = st.tabs([
    "✍️ Saisir un texte",
    "📄 Importer un PDF (texte)",
    "📸 Photo ou PDF scanné (Vision)"
])

texte_saisi = ""
texte_pdf = ""
images_base64 = []

with onglet_texte:
    texte_saisi = st.text_area(
        "Collez ici la consigne ou l'extrait de fiche TP à analyser :",
        height=140,
        key=f"zone_texte_{st.session_state.compteur_reset}",
        placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure."
    )

with onglet_pdf:
    fichier_pdf = st.file_uploader(
        "Déposez votre sujet d'exercice ou votre fiche de TP (PDF natif) :",
        type=["pdf"],
        key=f"upload_pdf_{st.session_state.compteur_reset}"
    )
    if fichier_pdf is not None:
        try:
            lecteur = PdfReader(fichier_pdf)
            pages_texte = []
            for page in lecteur.pages:
                extrait = page.extract_text()
                if extrait:
                    pages_texte.append(extrait)
            texte_pdf = "\n".join(pages_texte).strip()
            if texte_pdf:
                st.success(f"✅ PDF lu ({len(lecteur.pages)} page(s)).")
                with st.expander("Aperçu du texte extrait"):
                    st.text(texte_pdf[:1500] + ("..." if len(texte_pdf) > 1500 else ""))
            else:
                st.warning("⚠️ Aucun texte sélectionnable détecté. Utilisez l'onglet « 📸 Photo ou PDF scanné » juste à côté.")
        except Exception as e:
            st.error(f"Erreur PDF : {e}")

with onglet_image:
    fichier_visuel = st.file_uploader(
        "Importez une photo (PNG, JPG) ou un PDF scanné (les 2 premières pages seront analysées) :",
        type=["png", "jpg", "jpeg", "pdf"],
        key=f"upload_visuel_{st.session_state.compteur_reset}"
    )
    if fichier_visuel is not None:
        try:
            if fichier_visuel.type == "application/pdf":
                doc_fitz = fitz.open(stream=fichier_visuel.read(), filetype="pdf")
                nb_pages = min(2, len(doc_fitz))
                for i in range(nb_pages):
                    pix = doc_fitz[i].get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("jpeg")
                    images_base64.append(base64.b64encode(img_bytes).decode("utf-8"))
                st.success(f"✅ PDF scanné converti en image ({nb_pages} page(s) prête(s) pour l'analyse visuelle).")
            else:
                img_bytes = fichier_visuel.read()
                images_base64.append(base64.b64encode(img_bytes).decode("utf-8"))
                st.image(img_bytes, caption="Document importé", width=350)
        except Exception as e:
            st.error(f"Erreur lors du traitement de l'image : {e}")

consigne_finale = texte_pdf if texte_pdf else texte_saisi.strip()

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    lancer = st.button("🔍 Lancer l'expertise didactique", type="primary", use_container_width=True)
with col_btn2:
    st.button("🔄 Nouvelle analyse", key="btn_reset_haut", on_click=reinitialiser_application, use_container_width=True)

if lancer:
    if not consigne_finale and not images_base64:
        st.warning("⚠️ Veuillez saisir un texte, importer un PDF ou charger une image.")
    else:
        with st.spinner("Analyse didactique approfondie en cours..."):
            try:
                api_key = st.secrets["MISTRAL_API_KEY"].strip()
                
                prompt_systeme = f"""Tu es un formateur expert et chercheur en didactique de la physique-chimie intervenant en INSPE (Master MEEF) et en formation continue.
Contexte : Niveau {niveau} | Type : {type_activite}.

Ta mission est de produire une expertise didactique rigoureuse de la consigne ou du document fourni (ne résous jamais l'exercice). Structure impérativement ta réponse en 5 parties en Markdown :

### 1. 🎯 Compétences cachées et « consignes-valises »
Identifie les compétences de la démarche scientifique (S'approprier, Analyser/Raisonner, Réaliser, Valider, Communiquer) imbriquées implicitement dans une même question, ainsi que les verbes d'action à protocole caché (ex. : justifier, exploiter, vérifier, conclure).

### 2. ⚛️ Ruptures de registres et modélisation
Analyse les sauts implicites imposés à l'élève :
- En chimie : passage non explicité entre les niveaux macroscopique, microscopique et symbolique (Triangle de Johnstone).
- En physique : passage entre le monde des objets/mesures et le monde des modèles/lois mathématiques (Tiberghien), ou changement de registre (texte, schéma normalisé, graphique, équation).

### 3. 🧪 Implicites expérimentaux et charge cognitive (TP / Évaluation)
Repère les non-dits matériels (verrerie, réactifs, témoin, sécurité, incertitudes/chiffres significatifs) et les risques de surcharge cognitive (attention partagée entre manipulation et lecture, consignes ambiguës).

### 4. 🧠 Malentendus socio-cognitifs (« Point de vue élève »)
Décris 2 ou 3 malentendus probables chez un élève en difficulté (confusion entre la tâche matérielle à exécuter et l'enjeu de savoir visé, interprétation littérale, polysémie du lexique scientifique).

### 5. 🪜 Gradation d'explicitation et question réflexive
Propose trois réécritures graduées adaptées au niveau {niveau} :
- **Niveau 1 (Tâche complexe / Ouverte)** : Formulation débarrassée des ambiguïtés langagières mais préservant l'autonomie de raisonnement.
- **Niveau 2 (Étayage intermédiaire / Coup de pouce)** : Ajout d'indices sur les ressources ou la stratégie attendue.
- **Niveau 3 (Explicitation maximale / Pas à pas)** : Décomposition en tâches élémentaires univoques avec critères de réussite visibles.

Termine par une **Question réflexive** destinée au professeur/stagiaire pour interroger l'alignement entre sa consigne et son intention d'évaluation."""

                url_api = "https://" + "api.mistral.ai" + "/v1/chat/completions"

                if images_base64:
                    # Utilisation du modèle vision Pixtral si une image ou un PDF scanné est fourni
                    contenu_utilisateur = [
                        {"type": "text", "text": "Analyse les implicites didactiques des consignes présentes sur ce document :"}
                    ]
                    for img_b64 in images_base64:
                        contenu_utilisateur.append({
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{img_b64}"
                        })
                    payload = {
                        "model": "pixtral-12b-latest",
                        "messages": [
                            {"role": "system", "content": prompt_systeme},
                            {"role": "user", "content": contenu_utilisateur}
