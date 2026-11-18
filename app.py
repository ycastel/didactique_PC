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
    lignes = list()
    lignes.append("Tu es un formateur expert en didactique de la physique-chimie (INSPE / Master MEEF et formation continue).")
    lignes.append(f"Contexte : Niveau {niveau} | Support : {type_activite}.")
    lignes.append("RÈGLE DE RÉDACTION TRÈS IMPORTANTE : Évite les longues listes à puces abstraites. Rédige des paragraphes clairs, pédagogiques et fluides. À chaque fois que tu repères un implicite, cite explicitement les mots exacts de la consigne, explique simplement ce que l'élève doit deviner tout seul, et montre comment le rendre explicite.")
    lignes.append("Ne résous jamais l'exercice. Structure ton analyse en 4 parties en Markdown :")
    lignes.append("### 1. Ce qui est caché dans la consigne (Analyse des implicites)")
    lignes.append("Rédige 2 ou 3 courts paragraphes qui décortiquent les passages problématiques du texte. Identifie les verbes d'action à protocole caché (ex. justifier, vérifier, conclure), les sauts implicites entre observation macroscopique et modèle microscopique/mathématique, ainsi que les non-dits matériels ou de sécurité en TP.")
    lignes.append("### 2. Pourquoi un élève risque de bloquer (Point de vue élève)")
    lignes.append("Explique sous forme de court récit ou d'exemples concrets les malentendus probables d'un élève en difficulté (confusion entre la tâche matérielle à faire et le savoir scientifique visé, interprétation littérale, mot du quotidien pris au sens courant).")
    lignes.append("### 3. Comment expliciter la consigne (3 niveaux d'étayage concrets)")
    lignes.append(f"Propose trois réécritures complètes et directement utilisables en classe de {niveau}, accompagnées d'une phrase expliquant l'intérêt pédagogique de chaque version :")
    lignes.append("#### Niveau 1 : Consigne ouverte (Tâche complexe clarifiée)")
    lignes.append("La consigne d'origine débarrassée des ambiguïtés de langage, mais qui laisse l'élève chercher la démarche en autonomie.")
    lignes.append("#### Niveau 2 : Étayage intermédiaire (Coup de pouce méthodologique)")
    lignes.append("La même consigne enrichie d'indices sur les ressources à mobiliser ou la structure de réponse attendue, sans donner les étapes.")
    lignes.append("#### Niveau 3 : Explicitation maximale (Guidage pas à pas)")
    lignes.append("La consigne décomposée en étapes chronologiques simples, avec des verbes univoques et des critères de réussite visibles.")
    lignes.append("### 4. Question réflexive pour le professeur")
    lignes.append("Termine par une question courte et percutante pour aider l'enseignant à choisir entre ces 3 versions selon ce qu'il souhaite réellement évaluer.")
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

    try:
        reponse = requests.post(url_api, headers=headers_api, json=payload, timeout=60)
        if reponse.status_code != 200:
            return False, f"Code erreur API ({reponse.status_code}) : {reponse.text}"
        data = reponse.json()
        premier_choix = next(iter(data.get("choices", ())))
        return True, premier_choix.get("message", {}).get("content", "")
    except Exception as e:
        return False, f"Erreur de connexion : {e}"

st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")
st.markdown("*Outil de formation (INSPE / Formation continue) pour repérer les non-dits des consignes et ajuster son étayage.*")

with st.sidebar:
    st.header("⚙️ Contexte pédagogique")
    niveau = st.selectbox("Niveau d'enseignement :", ("Collège (Cycle 4 : 5e, 4e, 3e)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC - 1ère / Terminale)", "Lycée Technologique (STL / STI2D)"))
    type_activite = st.radio("Type de support :", ("Exercice écrit / Évaluation sommative", "Travaux Pratiques (TP) / Démarche expérimentale / ECE"))
    st.divider()
    st.button("🔄 Soumettre une autre analyse", key="btn_reset_sidebar", on_click=reinitialiser_application, use_container_width=True)

mode_saisie = st.radio("Mode d'importation :", ("✍️ Texte", "📄 PDF (texte)", "📸 Image ou PDF scanné"), horizontal=True)

cle_widget_texte = f"txt_{st.session_state.compteur_reset}"
cle_widget_pdf = f"pdf_{st.session_state.compteur_reset}"
cle_widget_img = f"img_{st.session_state.compteur_reset}"

if mode_saisie == "✍️ Texte":
    st.text_area("Collez ici la consigne ou l'extrait de fiche TP :", height=140, key=cle_widget_texte, placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole...")
elif mode_saisie == "📄 PDF (texte)":
    st.file_uploader("Déposez votre sujet ou fiche de TP (PDF) :", type="pdf", key=cle_widget_pdf)
else:
    st.file_uploader("Importez une photo (PNG, JPG) ou un PDF scanné :", type=("png", "jpg", "jpeg", "pdf"), key=cle_widget_img)

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    lancer = st.button("🔍 Lancer l'expertise didactique", type="primary", use_container_width=True)
with col_btn2:
    st.button("🔄 Nouvelle analyse", key="btn_reset_haut", on_click=reinitialiser_application, use_container_width=True)

if lancer:
    texte_final = ""
    images_finales = list()

    if mode_saisie == "✍️ Texte":
        texte_final = st.session_state.get(cle_widget_texte, "").strip()
    elif mode_saisie == "📄 PDF (texte)":
        f_pdf = st.session_state.get(cle_widget_pdf)
        if f_pdf is not None:
            f_pdf.seek(0)
            lecteur = PdfReader(f_pdf)
            pages = list()
            for p in lecteur.pages:
                t = p.extract_text()
                if t:
                    pages.append(t)
            texte_final = "\n".join(pages).strip()
    elif mode_saisie == "📸 Image ou PDF scanné":
        f_visuel = st.session_state.get(cle_widget_img)
        if f_visuel is not None:
            f_visuel.seek(0)
            if f_visuel.type == "application/pdf":
                try:
                    import fitz
                    doc_fitz = fitz.open(stream=f_visuel.read(), filetype="pdf")
                    c = 0
                    for page_fitz in doc_fitz:
                        if c >= 2:
                            break
                        pix = page_fitz.get_pixmap(dpi=150)
                        images_finales.append(base64.b64encode(pix.tobytes("jpeg")).decode("utf-8"))
                        c += 1
                except Exception as e:
                    st.error(f"Erreur lecture PDF scanné : {e}")
            else:
                images_finales.append(base64.b64encode(f_visuel.read()).decode("utf-8"))

    if not texte_final and not images_finales:
        st.warning("⚠️ Aucun contenu détecté. Vérifiez que vous avez bien saisi un texte ou chargé un fichier valide.")
    else:
        with st.spinner("Rédaction de l'expertise didactique en cours..."):
            cle_api = st.secrets.get("MISTRAL_API_KEY", "").strip()
            if not cle_api:
                st.error("⚠️ Clé MISTRAL_API_KEY introuvable dans les Secrets de Streamlit.")
            else:
