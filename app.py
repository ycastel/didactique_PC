import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
import fitz
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
st.markdown("*Outil de formation (INSPE / Formation continue) pour analyser les obstacles langagiers, méthodologiques et expérimentaux.*")

with st.sidebar:
    st.header("⚙️ Contexte pédagogique")
    options_niveau = list()
    options_niveau.append("Collège (Cycle 4 : 5e, 4e, 3e)")
    options_niveau.append("Lycée Général (Seconde)")
    options_niveau.append("Lycée Général (Spécialité PC - 1ère / Terminale)")
    options_niveau.append("Lycée Technologique (STL / STI2D)")
    niveau = st.selectbox("Niveau d'enseignement :", options_niveau)
    
    options_support = list()
    options_support.append("Exercice écrit / Évaluation sommative")
    options_support.append("Travaux Pratiques (TP) / Démarche expérimentale / ECE")
    type_activite = st.radio("Type de support :", options_support)
    
    st.divider()
    st.button("🔄 Soumettre une autre analyse", key="btn_reset_sidebar", on_click=reinitialiser_application, use_container_width=True)
    
    st.divider()
    st.info("Cadres mobilisés : Compétences (APP, ANA, REA, VAL, COM), Triangle de Johnstone, Modélisation, Malentendus socio-cognitifs et Charge cognitive.")

noms_onglets = list()
noms_onglets.append("✍️ Saisir un texte")
noms_onglets.append("📄 Importer un PDF (texte)")
noms_onglets.append("📸 Photo ou PDF scanné (Vision)")
onglet_texte, onglet_pdf, onglet_image = st.tabs(noms_onglets)

texte_saisi = ""
texte_pdf = ""
images_base64 = list()

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
        type="pdf",
        key=f"upload_pdf_{st.session_state.compteur_reset}"
    )
    if fichier_pdf is not None:
        try:
            lecteur = PdfReader(fichier_pdf)
            pages_texte = list()
            for page in lecteur.pages:
                extrait = page.extract_text()
                if extrait:
                    pages_texte.append(extrait)
            texte_pdf = "\n".join(pages_texte).strip()
            if texte_pdf:
                st.success(f"✅ PDF lu ({len(lecteur.pages)} page(s)).")
                with st.expander("Aperçu du texte extrait"):
                    st.text(texte_pdf[:1500])
            else:
                st.warning("⚠️ Aucun texte sélectionnable détecté. Utilisez l'onglet « 📸 Photo ou PDF scanné ».")
        except Exception as e:
            st.error(f"Erreur PDF : {e}")

with onglet_image:
    types_acceptes = list()
    types_acceptes.append("png")
    types_acceptes.append("jpg")
    types_acceptes.append("jpeg")
    types_acceptes.append("pdf")
    fichier_visuel = st.file_uploader(
        "Importez une photo (PNG, JPG) ou un PDF scanné (les 2 premières pages seront analysées) :",
        type=types_acceptes,
        key=f"upload_visuel_{st.session_state.compteur_reset}"
    )
    if fichier_visuel is not None:
        try:
            if fichier_visuel.type == "application/pdf":
                doc_fitz = fitz.open(stream=fichier_visuel.read(), filetype="pdf")
                compteur_pages = 0
                for page_fitz in doc_fitz:
                    if compteur_pages >= 2:
                        break
                    pix = page_fitz.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("jpeg")
                    images_base64.append(base64.b64encode(img_bytes).decode("utf-8"))
                    compteur_pages += 1
                st.success(f"✅ PDF scanné converti en image ({compteur_pages} page(s) prête(s)).")
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
                api_key = st.secrets.get("MISTRAL_API_KEY", "").strip()
                
                lignes_prompt = list()
                lignes_prompt.append("Tu es un formateur expert et chercheur en didactique de la physique-chimie intervenant en INSPE (Master MEEF) et en formation continue.")
                lignes_prompt.append(f"Contexte : Niveau {niveau} | Type : {type_activite}.")
                lignes_prompt.append("Produis une expertise didactique rigoureuse de la consigne ou du document fourni (ne résous jamais l'exercice). Structure ta réponse en 5 parties en Markdown :")
                lignes_prompt.append("### 1. 🎯 Compétences cachées et « consignes-valises »")
                lignes_prompt.append("Identifie les compétences de la démarche scientifique (S'approprier, Analyser/Raisonner, Réaliser, Valider, Communiquer) imbriquées implicitement, ainsi que les verbes d'action à protocole caché (justifier, exploiter, vérifier, conclure).")
                lignes_prompt.append("### 2. ⚛️ Ruptures de registres et modélisation")
                lignes_prompt.append("Analyse les sauts implicites : en chimie entre macroscopique, microscopique et symbolique (Triangle de Johnstone) ; en physique entre objets/mesures et modèles/lois mathématiques (Tiberghien), ou changement de registre (texte, schéma, graphique, équation).")
                lignes_prompt.append("### 3. 🧪 Implicites expérimentaux et charge cognitive (TP / Évaluation)")
                lignes_prompt.append("Repère les non-dits matériels (verrerie, réactifs, témoin, sécurité, incertitudes) et les risques de surcharge cognitive (attention partagée entre manipulation et lecture).")
                lignes_prompt.append("### 4. 🧠 Malentendus socio-cognitifs (« Point de vue élève »)")
                lignes_prompt.append("Décris 2 ou 3 malentendus probables chez un élève en difficulté (confusion entre tâche matérielle et enjeu de savoir, interprétation littérale, polysémie).")
                lignes_prompt.append("### 5. 🪜 Gradation d'explicitation et question réflexive")
                lignes_prompt.append(f"Propose trois réécritures graduées adaptées au niveau {niveau} : Niveau 1 (Tâche complexe / Ouverte sans ambiguïté langagière), Niveau 2 (Étayage intermédiaire / Coup de pouce), Niveau 3 (Explicitation maximale / Pas à pas). Termine par une Question réflexive pour l'enseignant.")
                prompt_systeme = "\n\n".join(lignes_prompt)

                url_api = "https://" + "api.mistral.ai" + "/v1/chat/completions"

                messages_api = list()
                msg_sys = {"role": "system", "content": prompt_systeme}
                messages_api.append(msg_sys)

                if images_base64:
                    contenu_utilisateur = list()
                    contenu_utilisateur.append({"type": "text", "text": "Analyse les implicites didactiques des consignes présentes sur ce document :"})
                    for img_b64 in images_base64:
                        contenu_utilisateur.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_b64}"})
                    msg_user = {"role": "user", "content": contenu_utilisateur}
