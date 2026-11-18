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

def interroger_mistral(api_key, niveau, type_activite, texte_consigne, liste_images):
    lignes = list()
    lignes.append("Tu es un formateur expert et chercheur en didactique de la physique-chimie intervenant en INSPE (Master MEEF) et en formation continue.")
    lignes.append(f"Contexte : Niveau {niveau} | Type : {type_activite}.")
    lignes.append("Produis une expertise didactique rigoureuse de la consigne ou du document fourni (ne resous jamais l'exercice). Structure ta reponse en 5 parties en Markdown :")
    lignes.append("### 1. Compétences cachées et consignes-valises")
    lignes.append("Identifie les compétences de la démarche scientifique (S'approprier, Analyser/Raisonner, Réaliser, Valider, Communiquer) imbriquées implicitement, ainsi que les verbes d'action à protocole caché (justifier, exploiter, vérifier, conclure).")
    lignes.append("### 2. Ruptures de registres et modélisation")
    lignes.append("Analyse les sauts implicites : en chimie entre macroscopique, microscopique et symbolique (Triangle de Johnstone) ; en physique entre objets/mesures et modèles/lois mathématiques (Tiberghien), ou changement de registre (texte, schéma, graphique, équation).")
    lignes.append("### 3. Implicites expérimentaux et charge cognitive")
    lignes.append("Repère les non-dits matériels (verrerie, réactifs, témoin, sécurité, incertitudes) et les risques de surcharge cognitive (attention partagée entre manipulation et lecture).")
    lignes.append("### 4. Malentendus socio-cognitifs (Point de vue élève)")
    lignes.append("Décris 2 ou 3 malentendus probables chez un élève en difficulté (confusion entre tâche matérielle et enjeu de savoir, interprétation littérale, polysémie).")
    lignes.append("### 5. Gradation d'explicitation et question réflexive")
    lignes.append(f"Propose trois réécritures graduées adaptées au niveau {niveau} : Niveau 1 (Tâche complexe / Ouverte sans ambiguïté langagière), Niveau 2 (Étayage intermédiaire / Coup de pouce), Niveau 3 (Explicitation maximale / Pas à pas). Termine par une Question réflexive pour l'enseignant.")
    prompt_sys = "\n\n".join(lignes)

    messages_api = list()
    messages_api.append({"role": "system", "content": prompt_sys})

    if liste_images:
        contenu_visuel = list()
        contenu_visuel.append({"type": "text", "text": "Analyse les implicites didactiques des consignes présentes sur ce document :"})
        for img_b64 in liste_images:
            contenu_visuel.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_b64}"})
        messages_api.append({"role": "user", "content": contenu_visuel})
        modele = "pixtral-12b-latest"
    else:
        messages_api.append({"role": "user", "content": texte_consigne[:12000]})
        modele = "mistral-small-latest"

    url_api = "https://" + "api.mistral.ai" + "/v1/chat/completions"
    headers_api = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": modele, "messages": messages_api, "temperature": 0.3}

    reponse = requests.post(url_api, headers=headers_api, json=payload)
    if reponse.status_code != 200:
        return False, f"Code erreur API ({reponse.status_code}) : {reponse.text}"
    data = reponse.json()
    premier_choix = next(iter(data.get("choices", ())))
    return True, premier_choix.get("message", {}).get("content", "")

st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")
st.markdown("*Outil de formation (INSPE / Formation continue) pour analyser les obstacles langagiers, méthodologiques et expérimentaux.*")

with st.sidebar:
    st.header("⚙️ Contexte pédagogique")
    options_niveau = ("Collège (Cycle 4 : 5e, 4e, 3e)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC - 1ère / Terminale)", "Lycée Technologique (STL / STI2D)")
    niveau = st.selectbox("Niveau d'enseignement :", options_niveau)
    options_support = ("Exercice écrit / Évaluation sommative", "Travaux Pratiques (TP) / Démarche expérimentale / ECE")
    type_activite = st.radio("Type de support :", options_support)
    st.divider()
    st.button("🔄 Soumettre une autre analyse", key="btn_reset_sidebar", on_click=reinitialiser_application, use_container_width=True)
    st.divider()
    st.info("Cadres mobilisés : Compétences (APP, ANA, REA, VAL, COM), Triangle de Johnstone, Modélisation, Malentendus socio-cognitifs et Charge cognitive.")

onglet_texte, onglet_pdf, onglet_image = st.tabs(("✍️ Saisir un texte", "📄 Importer un PDF (texte)", "📸 Photo ou PDF scanné (Vision)"))

texte_saisi = ""
texte_pdf = ""
images_base64 = list()

with onglet_texte:
    texte_saisi = st.text_area("Collez ici la consigne ou l'extrait de fiche TP à analyser :", height=140, key=f"zone_texte_{st.session_state.compteur_reset}")

with onglet_pdf:
    fichier_pdf = st.file_uploader("Déposez votre sujet ou fiche de TP (PDF natif) :", type="pdf", key=f"upload_pdf_{st.session_state.compteur_reset}")
    if fichier_pdf is not None:
        lecteur = PdfReader(fichier_pdf)
        pages_texte = list()
        for page in lecteur.pages:
            extrait = page.extract_text()
            if extrait:
                pages_texte.append(extrait)
        texte_pdf = "\n".join(pages_texte).strip()
        if texte_pdf:
            st.success(f"✅ PDF lu ({len(lecteur.pages)} page(s)).")
        else:
            st.warning("⚠️ Aucun texte détecté. Utilisez l'onglet « 📸 Photo ou PDF scanné ».")

with onglet_image:
    fichier_visuel = st.file_uploader("Importez une photo (PNG, JPG) ou un PDF scanné :", type=("png", "jpg", "jpeg", "pdf"), key=f"upload_visuel_{st.session_state.compteur_reset}")
    if fichier_visuel is not None:
        if fichier_visuel.type == "application/pdf":
            doc_fitz = fitz.open(stream=fichier_visuel.read(), filetype="pdf")
            compteur_pages = 0
            for page_fitz in doc_fitz:
                if compteur_pages >= 2:
                    break
                pix = page_fitz.get_pixmap(dpi=150)
                images_base64.append(base64.b64encode(pix.tobytes("jpeg")).decode("utf-8"))
                compteur_pages += 1
            st.success(f"✅ PDF scanné converti ({compteur_pages} page(s)).")
        else:
            img_bytes = fichier_visuel.read()
            images_base64.append(base64.b64encode(img_bytes).decode("utf-8"))
            st.image(img_bytes, caption="Document importé", width=350)

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
                cle = st.secrets.get("MISTRAL_API_KEY", "").strip()
                succes, resultat = interroger_mistral(cle, niveau, type_activite, consigne_finale, images_base64)
                if succes:
                    st.session_state.analyse_resultat = resultat
                    st.session_state.dernier_contexte = {"niveau": niveau, "type": type_activite, "date": datetime.now().strftime("%d/%m/%Y à %H:%M")}
                else:
                    st.error(resultat)
            except Exception as e:
                st.error(f"Erreur technique : {e}")

if st.session_state.analyse_resultat:
    st.divider()
    st.markdown(st.session_state.analyse_resultat)
    st.divider()
    st.subheader("📥 Exporter le diagnostic et les conseils")
    ctx = st.session_state.dernier_contexte
    horodatage = datetime.now().strftime('%Y%m%d_%H%M')
    col1, col2, col3 = st.columns(3)
    with col1:
        fichier_word = generer_docx(ctx, st.session_state.analyse_resultat)
