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
    st.session_state.dernier_contexte = dict()
if "compteur_reset" not in st.session_state:
    st.session_state.compteur_reset = 0

def reinitialiser_application():
    st.session_state.analyse_resultat = ""
    st.session_state.dernier_contexte = dict()
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
        p_meta.add_run(contexte.get("date", "") + "\n")
        p_meta.add_run("Niveau : ").bold = True
        p_meta.add_run(contexte.get("niveau", "") + "\n")
        p_meta.add_run("Support : ").bold = True
        p_meta.add_run(contexte.get("type", ""))
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
    lignes.append("Contexte : Niveau " + niveau + " | Support : " + type_activite + ".")
    lignes.append("RÈGLE DE RÉDACTION TRÈS IMPORTANTE : Évite les longues listes à puces abstraites. Rédige des paragraphes clairs, pédagogiques et fluides. À chaque fois que tu repères un implicite, cite explicitement les mots exacts de la consigne, explique simplement ce que l'élève doit deviner tout seul, et montre comment le rendre explicite.")
    lignes.append("Ne résous jamais l'exercice. Structure ton analyse en 4 parties en Markdown :")
    lignes.append("### 1. Ce qui est caché dans la consigne (Analyse des implicites)")
    lignes.append("Rédige 2 ou 3 courts paragraphes qui décortiquent les passages problématiques du texte. Identifie les verbes d'action à protocole caché (ex. justifier, vérifier, conclure), les sauts implicites entre observation macroscopique et modèle microscopique/mathématique, ainsi que les non-dits matériels ou de sécurité en TP.")
    lignes.append("### 2. Pourquoi un élève risque de bloquer (Point de vue élève)")
    lignes.append("Explique sous forme de court récit ou d'exemples concrets les malentendus probables d'un élève en difficulté (confusion entre la tâche matérielle à faire et le savoir scientifique visé, interprétation littérale, mot du quotidien pris au sens courant).")
    lignes.append("### 3. Comment expliciter la consigne (3 niveaux d'étayage concrets)")
    lignes.append("Propose trois réécritures complètes et directement utilisables en classe de " + niveau + ", accompagnées d'une phrase expliquant l'intérêt pédagogique de chaque version :")
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
    messages_api.append(dict(role="system", content=prompt_sys))
    modele = "mistral-small-latest"

    if liste_images:
        contenu_visuel = list()
        contenu_visuel.append(dict(type="text", text="Analyse les implicites didactiques des consignes présentes sur ce document :"))
        for img_b64 in liste_images:
            url_data = "data:image/jpeg;base64," + img_b64
            contenu_visuel.append(dict(type="image_url", image_url=url_data))
        messages_api.append(dict(role="user", content=contenu_visuel))
        modele = "pixtral-12b-latest"
    else:
        messages_api.append(dict(role="user", content=texte_consigne[:12000]))

    url_api = "https://" + "api.mistral.ai" + "/v1/chat/completions"
    headers_api = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
    payload = dict(model=modele, messages=messages_api, temperature=0.3)

    try:
        reponse = requests.post(url_api, headers=headers_api, json=payload, timeout=60)
        if reponse.status_code != 200:
            return False, "Code erreur API (" + str(reponse.status_code) + ") : " + reponse.text
        data = reponse.json()
        premier_choix = next(iter(data.get("choices", ())))
        texte_reponse = premier_choix.get("message", dict()).get("content", "")
        return True, texte_reponse
    except Exception as e:
        return False, "Erreur technique : " + str(e)

st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")
st.markdown("*Outil de formation (INSPE / Formation continue) pour repérer les non-dits des consignes et ajuster son étayage.*")

st.sidebar.header("⚙️ Contexte pédagogique")
opts_niv = ("Collège (Cycle 4 : 5e, 4e, 3e)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC - 1ère / Terminale)", "Lycée Technologique (STL / STI2D)")
niveau = st.sidebar.selectbox("Niveau d'enseignement :", opts_niv)
opts_sup = ("Exercice écrit / Évaluation sommative", "Travaux Pratiques (TP) / Démarche expérimentale / ECE")
type_activite = st.sidebar.radio("Type de support :", opts_sup)
st.sidebar.divider()
st.sidebar.button("🔄 Soumettre une autre analyse", key="btn_reset_sidebar", on_click=reinitialiser_application, use_container_width=True)

cle_txt = "txt_" + str(st.session_state.compteur_reset)
cle_fich = "fich_" + str(st.session_state.compteur_reset)

texte_saisi = st.text_area("1. Saisissez ou collez une consigne :", height=130, key=cle_txt, placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole...")
fichier_charge = st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :", type=("pdf", "png", "jpg", "jpeg"), key=cle_fich)

col_btn1, col_btn2 = st.columns(2)
lancer = col_btn1.button("🔍 Lancer l'expertise didactique", type="primary", use_container_width=True)
col_btn2.button("🔄 Nouvelle analyse", key="btn_reset_haut", on_click=reinitialiser_application, use_container_width=True)

if lancer:
    texte_final = texte_saisi.strip()
    images_finales = list()

    if fichier_charge is not None:
        fichier_charge.seek(0)
        nom_fichier = fichier_charge.name.lower()
        if nom_fichier.endswith(".pdf"):
            try:
                lecteur = PdfReader(fichier_charge)
                pages = list()
                for p in lecteur.pages:
                    t = p.extract_text()
                    if t:
                        pages.append(t)
                texte_extrait = "\n".join(pages).strip()
                if texte_extrait:
                    texte_final = texte_extrait
                else:
                    import fitz
                    fichier_charge.seek(0)
                    doc_fitz = fitz.open(stream=fichier_charge.read(), filetype="pdf")
                    c = 0
                    for page_fitz in doc_fitz:
                        if c >= 2:
                            break
                        pix = page_fitz.get_pixmap(dpi=150)
                        images_finales.append(base64.b64encode(pix.tobytes("jpeg")).decode("utf-8"))
                        c += 1
            except Exception as e:
                st.error("Erreur de lecture du PDF : " + str(e))
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
            date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
            st.session_state.dernier_contexte = dict(niveau=niveau, type=type_activite, date=date_str)
        elif succes and not resultat:
