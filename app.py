import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
import base64
import io
import re

st.set_page_config(page_title="Didactique PC - Implicites", page_icon="🔬", layout="wide")

if "analyse_resultat" not in st.session_state: st.session_state.analyse_resultat = ""
if "dernier_contexte" not in st.session_state: st.session_state.dernier_contexte = dict()
if "compteur_reset" not in st.session_state: st.session_state.compteur_reset = 0

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
            lp = ligne.strip()
            if lp.startswith("### "): doc.add_heading(lp.replace("### ", ""), level=2)
            elif lp.startswith("#### "): doc.add_heading(lp.replace("#### ", ""), level=3)
            elif lp: doc.add_paragraph(lp.replace("**", ""))
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
    lignes.append("RÈGLE DE RÉDACTION : Évite les longues listes à puces abstraites. Rédige des paragraphes clairs, pédagogiques et fluides. Cite les mots exacts de la consigne, explique ce que l'élève doit deviner tout seul, et montre comment le rendre explicite.")
    lignes.append("Ne résous jamais l'exercice. Structure ta réponse en 4 parties en Markdown :")
    lignes.append("### 1. Ce qui est caché dans la consigne (Analyse des implicites)")
    lignes.append("Rédige 2 ou 3 courts paragraphes décortiquant les passages problématiques : verbes d'action à protocole caché, sauts entre observation macroscopique et modèle microscopique/mathématique, non-dits matériels ou de sécurité en TP.")
    lignes.append("### 2. Pourquoi un élève risque de bloquer (Point de vue élève)")
    lignes.append("Explique sous forme d'exemples concrets les malentendus probables d'un élève en difficulté (confusion entre tâche matérielle et savoir scientifique visé, interprétation littérale, polysémie).")
    lignes.append("### 3. Comment expliciter la consigne (3 niveaux d'étayage)")
    lignes.append("Propose trois réécritures complètes pour la classe de " + niveau + " accompagnées d'une phrase expliquant l'intérêt pédagogique de chaque version :")
    lignes.append("#### Niveau 1 : Consigne ouverte (Tâche complexe clarifiée)")
    lignes.append("Consigne d'origine débarrassée des ambiguïtés langagières, laissant l'autonomie de démarche.")
    lignes.append("#### Niveau 2 : Étayage intermédiaire (Coup de pouce méthodologique)")
    lignes.append("Consigne enrichie d'indices sur les ressources ou la structure attendue, sans donner les étapes.")
    lignes.append("#### Niveau 3 : Explicitation maximale (Guidage pas à pas)")
    lignes.append("Consigne décomposée en étapes chronologiques simples, avec verbes univoques et critères de réussite visibles.")
    lignes.append("### 4. Question réflexive pour le professeur")
    lignes.append("Termine par une question courte pour aider l'enseignant à choisir selon ce qu'il souhaite évaluer.")
    prompt_sys = "\n\n".join(lignes)

    messages_api = list()
    messages_api.append({"role": "system", "content": prompt_sys})
    modele = "mistral-small-latest"

    if liste_images:
        contenu_visuel = list()
        contenu_visuel.append({"type": "text", "text": "Analyse les implicites didactiques des consignes présentes sur ce document :"})
        for img_b64 in liste_images: contenu_visuel.append({"type": "image_url", "image_url": "data:image/jpeg;base64," + img_b64})
        messages_api.append({"role": "user", "content": contenu_visuel})
        modele = "pixtral-12b-latest"

    if not liste_images: messages_api.append({"role": "user", "content": texte_consigne[:12000]})

    url_api = "https://" + "api.mistral.ai" + "/v1/chat/completions"
    headers_api = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
    payload = {"model": modele, "messages": messages_api, "temperature": 0.3}

    try:
        reponse = requests.post(url_api, headers=headers_api, json=payload, timeout=60)
        if reponse.status_code != 200: return False, "Code erreur API (" + str(reponse.status_code) + ") : " + reponse.text
        data = reponse.json()
        choix_liste = data.get("choices", list())
        if not choix_liste: return False, "Réponse vide de Mistral : " + str(data)
        premier_choix = choix_liste.pop(0)
        contenu_texte = premier_choix.get("message", dict()).get("content", "")
        if not contenu_texte: return False, "Contenu vide reçu : " + str(premier_choix)
        return True, contenu_texte
    except Exception as e:
        return False, "Erreur technique : " + str(e)

def executer_analyse(cle_api, niveau, type_activite, cle_txt, cle_fich):
    texte_final = str(st.session_state.get(cle_txt, "")).strip()
    fichier_charge = st.session_state.get(cle_fich)
    images_finales = list()

    if fichier_charge is not None:
        fichier_charge.seek(0)
        nom = fichier_charge.name.lower()
        if nom.endswith(".pdf"):
            try:
                lecteur = PdfReader(fichier_charge)
                pages = list()
                for p in lecteur.pages:
                    t = p.extract_text()
                    if t: pages.append(t)
                texte_extrait = "\n".join(pages).strip()
                if texte_extrait: texte_final = texte_extrait
                if not texte_extrait:
                    import fitz
                    fichier_charge.seek(0)
                    doc_fitz = fitz.open(stream=fichier_charge.read(), filetype="pdf")
                    c = 0
                    for page_fitz in doc_fitz:
                        if c >= 2: break
                        pix = page_fitz.get_pixmap(dpi=150)
                        images_finales.append(base64.b64encode(pix.tobytes("jpeg")).decode("utf-8"))
                        c += 1
            except Exception as e:
                st.error("Erreur lecture PDF : " + str(e))
                return
        if not nom.endswith(".pdf"): images_finales.append(base64.b64encode(fichier_charge.read()).decode("utf-8"))

    if not cle_api:
        st.error("⚠️ Clé API introuvable dans les Secrets de Streamlit.")
        return
    if not texte_final and not images_finales:
        st.warning("⚠️ Veuillez saisir une consigne ou importer un fichier.")
        return

    with st.spinner("Rédaction de l'expertise didactique en cours..."):
        succes, resultat = interroger_mistral(cle_api, niveau, type_activite, texte_final, images_finales)
    if succes:
        st.session_state.analyse_resultat = resultat
        st.session_state.dernier_contexte = {"niveau": niveau, "type": type_activite, "date": datetime.now().strftime("%d/%m/%Y à %H:%M")}
    if not succes:
        st.error(resultat)

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

st.text_area("1. Saisissez ou collez une consigne :", height=130, key=cle_txt, placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole...")
st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :", key=cle_fich)

col_btn1, col_btn2 = st.columns(2)
lancer = col_btn1.button("🔍 Lancer l'expertise didactique", type="primary", use_container_width=True)
col_btn2.button("🔄 Nouvelle analyse", key="btn_reset_haut", on_click=reinitialiser_application, use_container_width=True)

if lancer: executer_analyse(st.secrets.get("MISTRAL_API_KEY", "").strip(), niveau, type_activite, cle_txt, cle_fich)

if st.session_state.analyse_resultat:
    st.divider()
    ctx = st.session_state.dernier_contexte
    horodatage = datetime.now().strftime("%Y%m%d_%H%M")
    entete_md = "# Expertise Didactique - Physique-Chimie\n- **Date :** " + ctx.get("date", "") + "\n- **Niveau :** " + ctx.get("niveau", "") + "\n- **Support :** " + ctx.get("type", "") + "\n\n---\n\n"
