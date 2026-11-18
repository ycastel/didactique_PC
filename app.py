import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
import base64
import io
import re

st.set_page_config(page_title="Didactique PC - Implicites", page_icon="🔬", layout="wide")

if "analyse_resultat" not in st.session_state:
    st.session_state.analyse_resultat = ""
if "dernier_contexte" not in st.session_state:
    st.session_state.dernier_contexte = {}
if "compteur_reset" not in st.session_state:
    st.session_state.compteur_reset = 0

def reinitialiser_application():
    st.session_state.analyse_resultat = ""
    st.session_state.dernier_contexte = {}
    st.session_state.compteur_reset += 1

def nettoyer_texte_xml(texte):
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texte)

def generer_docx(contexte, texte_analyse):
    try:
        from docx import Document
        doc = Document()
        doc.add_heading("Expertise Didactique et Conseils d'Explicitation - Physique-Chimie", level=1)
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
            elif ligne_propre.startswith("#### "):
                doc.add_heading(ligne_propre.replace("#### ", ""), level=3)
            elif ligne_propre:
                doc.add_paragraph(ligne_propre.replace("**", ""))
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception:
        return None

def interroger_mistral(api_key, niveau, type_activite, texte_consigne, liste_images):
    lignes = [
        "Tu es un formateur expert en didactique de la physique-chimie (INSPE / Master MEEF et formation continue).",
        f"Contexte : Niveau {niveau} | Support : {type_activite}.",
        "RÈGLE DE RÉDACTION TRÈS IMPORTANTE : Évite les longues listes à puces abstraites. Rédige des paragraphes clairs, pédagogiques et fluides. À chaque fois que tu repères un implicite, cite explicitement les mots exacts de la consigne, explique simplement ce que l'élève doit deviner tout seul, et montre comment le rendre explicite.",
        "Ne résous jamais l'exercice. Structure ton analyse en 4 parties en Markdown :",
        "### 1. Ce qui est caché dans la consigne (Analyse des implicites)",
        "Rédige 2 ou 3 courts paragraphes qui décortiquent les passages problématiques du texte. Identifie les verbes d'action à protocole caché (ex. justifier, vérifier, conclure), les sauts implicites entre observation macroscopique et modèle microscopique/mathématique, ainsi que les non-dits matériels ou de sécurité en TP.",
        "### 2. Pourquoi un élève risque de bloquer (Point de vue élève)",
        "Explique sous forme de court récit ou d'exemples concrets les malentendus probables d'un élève en difficulté (confusion entre la tâche matérielle à faire et le savoir scientifique visé, interprétation littérale, mot du quotidien pris au sens courant).",
        "### 3. Comment expliciter la consigne (3 niveaux d'étayage concrets)",
        f"Propose trois réécritures complètes et directement utilisables en classe de {niveau}, accompagnées d'une phrase expliquant l'intérêt pédagogique de chaque version :",
        "#### Niveau 1 : Consigne ouverte (Tâche complexe clarifiée)",
        "La consigne d'origine débarrassée des ambiguïtés de langage, mais qui laisse l'élève chercher la démarche en autonomie.",
        "#### Niveau 2 : Étayage intermédiaire (Coup de pouce méthodologique)",
        "La même consigne enrichie d'indices sur les ressources à mobiliser ou la structure de réponse attendue, sans donner les étapes.",
        "#### Niveau 3 : Explicitation maximale (Guidage pas à pas)",
        "La consigne décomposée en étapes chronologiques simples, avec des verbes univoques et des critères de réussite visibles.",
        "### 4. Question réflexive pour le professeur",
        "Termine par une question courte et percutante pour aider l'enseignant à choisir entre ces 3 versions selon ce qu'il souhaite réellement évaluer."
    ]
    prompt_sys = "\n\n".join(lignes)

    if liste_images:
        contenu_visuel = [{"type": "text", "text": "Analyse les implicites didactiques des consignes présentes sur ce document :"}]
        for img_b64 in liste_images:
            contenu_visuel.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_b64}"})
        messages_api = [
            {"role": "system", "content": prompt_sys},
            {"role": "user", "content": contenu_visuel}
        ]
        modele = "pixtral-12b-latest"
    else:
        messages_api = [
            {"role": "system", "content": prompt_sys},
            {"role": "user", "content": texte_consigne[:12000]}
        ]
        modele = "mistral-small-latest"

    url_api = "https://mistral.ai"
    headers_api = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": modele,
        "messages": messages_api,
        "temperature": 0.3
    }

    try:
        reponse = requests.post(url_api, headers=headers_api, json=payload, timeout=60)
        if reponse.status_code != 200:
            return False, f"Code erreur API ({reponse.status_code}) : {reponse.text}"
        data = reponse.json()
        texte_reponse = data["choices"][0]["message"]["content"]
        return True, texte_reponse
    except Exception as e:
        return False, f"Erreur technique lors de l'appel à Mistral : {e}"

# --- INTERFACE ---
st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")
st.markdown("*Outil de formation (INSPE / Formation continue) pour repérer les non-dits des consignes et ajuster son étayage.*")

st.sidebar.header("⚙️ Contexte pédagogique")
niveau = st.sidebar.selectbox(
    "Niveau d'enseignement :",
    [
        "Collège (Cycle 4 : 5e, 4e, 3e)",
        "Lycée Général (Seconde)",
        "Lycée Général (Spécialité PC - 1ère / Terminale)",
        "Lycée Technologique (STL / STI2D)"
    ]
)
type_activite = st.sidebar.radio(
    "Type de support :",
    [
        "Exercice écrit / Évaluation sommative",
        "Travaux Pratiques (TP) / Démarche expérimentale / ECE"
    ]
)
st.sidebar.divider()
st.sidebar.button("🔄 Soumettre une autre analyse", key="btn_reset_sidebar", on_click=reinitialiser_application, use_container_width=True)

cle_txt = f"txt_{st.session_state.compteur_reset}"
cle_fich = f"fich_{st.session_state.compteur_reset}"

texte_saisi = st.text_area(
    "1. Saisissez ou collez une consigne :",
    height=130,
    key=cle_txt,
    placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure."
)
fichier_charge = st.file_uploader(
    "2. OU importez un fichier (PDF, PNG, JPG) :",
    type=["pdf", "png", "jpg", "jpeg"],
    key=cle_fich
)

col_btn1, col_btn2 = st.columns(2)
lancer = col_btn1.button("🔍 Lancer l'expertise didactique", type="primary", use_container_width=True)
col_btn2.button("🔄 Nouvelle analyse", key="btn_reset_haut", on_click=reinitialiser_application, use_container_width=True)

if lancer:
    texte_final = texte_saisi.strip()
    images_finales = []

    if fichier_charge is not None:
        fichier_charge.seek(0)
        nom_fichier = fichier_charge.name.lower()
        if nom_fichier.endswith(".pdf"):
            try:
                lecteur = PdfReader(fichier_charge)
                pages = [p.extract_text() for p in lecteur.pages if p.extract_text()]
                texte_extrait = "\n".join(pages).strip()
                if texte_extrait:
                    texte_final = texte_extrait
                else:
                    import fitz
                    fichier_charge.seek(0)
                    doc_fitz = fitz.open(stream=fichier_charge.read(), filetype="pdf")
                    for i, page_fitz in enumerate(doc_fitz):
                        if i >= 2:
                            break
                        pix = page_fitz.get_pixmap(dpi=150)
                        images_finales.append(base64.b64encode(pix.tobytes("jpeg")).decode("utf-8"))
            except Exception as e:
                st.error(f"Erreur de lecture du PDF : {e}")
        else:
            images_finales.append(base64.b64encode(fichier_charge.read()).decode("utf-8"))

    cle_api = st.secrets.get("MISTRAL_API_KEY", "").strip()

    if not cle_api:
        st.error("⚠️ Clé API introuvable : vérifiez MISTRAL_API_KEY dans les Secrets de Streamlit.")
    elif not texte_final and not images_finales:
        st.warning("⚠️ Veuillez saisir une consigne ou importer un fichier avant de lancer l'analyse.")
    else:
        with st.spinner("Rédaction de l'expertise didactique en cours..."):
            succes, resultat = interroger_mistral(cle_api, niveau, type_activite, texte_final, images_finales)
        if succes and resultat:
            st.session_state.analyse_resultat = resultat
            st.session_state.dernier_contexte = {
                "niveau": niveau,
                "type": type_activite,
                "date": datetime.now().strftime("%d/%m/%Y à %H:%M")
            }
        elif succes and not resultat:
            st.warning("⚠️ Mistral a renvoyé une réponse vide. Réessayez.")
        else:
            st.error(resultat)

# --- AFFICHAGE ET EXPORTATION ---
if st.session_state.analyse_resultat:
    st.divider()
    ctx = st.session_state.dernier_contexte
