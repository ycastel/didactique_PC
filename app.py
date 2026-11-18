import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
from docx import Document
import base64
import io

st.set_page_config(page_title="Didactique PC - Analyse", page_icon="🔬", layout="wide")

if "reset" not in st.session_state:
    st.session_state.reset = 0

def nouvelle_analyse():
    st.session_state.reset += 1

def obtenir_references_bo(niveau):
    lignes = list()
    if niveau == "Collège (Cycle 4)":
        lignes.append("### 📜 Ancrage institutionnel — Programme de Physique-Chimie (Cycle 4)")
        lignes.append("- **Texte de référence :** Programme d'enseignement du cycle des approfondissements (cycle 4) — *BOEN n° 31 du 30 juillet 2020*.")
        lignes.append("- **Compétences travaillées :** Pratiquer des démarches scientifiques, s'approprier des outils et des méthodes, pratiquer des langages.")
        lignes.append("- **Vigilance BO :** Au cycle 4, la modélisation reste qualitative ; le passage entre le monde des objets (macroscopique) et le monde des modèles (atomes, molécules, ions) doit être explicitement accompagné.")
    elif niveau == "Lycée Général (Seconde)":
        lignes.append("### 📜 Ancrage institutionnel — Programme de Physique-Chimie (Seconde GT)")
        lignes.append("- **Texte de référence :** Programme de physique-chimie de seconde générale et technologique — *BOEN spécial n° 1 du 22 janvier 2019*.")
        lignes.append("- **Compétences :** S'approprier (APP), Analyser/Raisonner (ANA), Réaliser (REA), Valider (VAL), Communiquer (COM).")
        lignes.append("- **Vigilance BO :** Transition vers la modélisation mathématique et l'usage rigoureux des grandeurs, unités, chiffres significatifs et incertitudes de mesure.")
    elif niveau == "Lycée Général (Spécialité PC - 1ère / Terminale)":
        lignes.append("### 📜 Ancrage institutionnel — Programme de Spécialité Physique-Chimie (Cycle Terminal)")
        lignes.append("- **Textes de référence :** Programmes de Première (*BOEN spécial n° 1 du 22 janvier 2019*) et de Terminale (*BOEN spécial n° 8 du 25 juillet 2019*), et notes de service **ECE**.")
        lignes.append("- **Compétences :** APP, ANA, REA, VAL, COM — autonomie dans la conception de protocoles et analyse critique des résultats (incertitudes-types, écart normalisé).")
        lignes.append("- **Vigilance BO :** Les capacités exigibles distinguent les tâches guidées des tâches complexes (résolution de problème, ECE).")
    else:
        lignes.append("### 📜 Ancrage institutionnel — Programmes des séries technologiques (STL-SPCL / STI2D)")
        lignes.append("- **Textes de référence :** Programmes de STI2D et STL-SPCL (*BOEN spécial n° 1 du 22 janvier 2019* et *BOEN spécial n° 8 du 25 juillet 2019*).")
        lignes.append("- **Compétences :** Démarche de projet, approche technologique et expérimentale contextualisée, maîtrise des chaînes de mesure.")
        lignes.append("- **Vigilance BO :** Lever les implicites liés au contexte technique tout en maintenant l'exigence sur la modélisation.")
    return "\n".join(lignes)

def creer_docx(niveau, support, contenu_markdown, texte_bo):
    doc = Document()
    doc.add_heading("Analyse Didactique Approfondie - Physique-Chimie", level=1)
    p = doc.add_paragraph()
    p.add_run(f"Niveau : {niveau} | Support : {support}").italic = True
    texte_complet = contenu_markdown + "\n\n" + texte_bo
    for ligne in texte_complet.split("\n"):
        l = ligne.strip()
        if not l:
            continue
        elif l.startswith("### "):
            doc.add_heading(l.replace("### ", ""), level=2)
        elif l.startswith("#### "):
            doc.add_heading(l.replace("#### ", ""), level=3)
        elif l.startswith("- "):
            doc.add_paragraph(l.replace("- ", "").replace("**", ""), style="List Bullet")
        else:
            doc.add_paragraph(l.replace("**", ""))
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")
st.markdown("*Outil de formation (INSPE / Master M2E / Formation continue) fondé sur la didactique des sciences et les travaux de l'IGÉSR.*")

with st.expander("ℹ️ Mode d'emploi, posture didactique et cadres mobilisés (Cliquez pour ouvrir)"):
    aide = list()
    aide.append("### 🎯 Posture de l'outil : éclairer les choix, sans prescrire")
    aide.append("Expliciter une consigne ne signifie **pas** baisser le niveau d'exigence ni « mâcher le travail » (ce qui relèverait de l'**effet Topaze** décrit par Guy Brousseau). L'objectif est de distinguer les **obstacles cognitifs légitimes** des **implicites parasites** qui pénalisent les élèves les plus fragiles.")
    aide.append("### 🛠️ Différenciation selon le support choisi")
    aide.append("- **Mode Exercice / Évaluation :** Contrat didactique d'évaluation (Brousseau), verbes opérateurs à protocole caché et attentes rédactionnelles implicites.")
    aide.append("- **Mode TP / Démarche expérimentale :** Gestes et matériels non nommés, témoin, sécurité, surcharge cognitive à la paillasse (Sweller) et équilibre entre « TP-recette » et investigation.")
    aide.append("### 📚 Cadres théoriques et institutionnels intégrés")
    aide.append("- **Inspection Générale (IGÉSR) & Bulletins Officiels (BO) :** Enseignement explicite, clarté cognitive et conformité aux programmes.")
    aide.append("- **Guy Brousseau, Gaston Bachelard, Alex Johnstone, Andrée Tiberghien, Bautier & Rayou, John Sweller.**")
    st.markdown("\n\n".join(aide))

options_niveaux = ("Collège (Cycle 4)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC - 1ère / Terminale)", "Lycée Technologique (STL / STI2D)")
niveau = st.sidebar.selectbox("Niveau :", options_niveaux)
support = st.sidebar.radio("Support :", ("Exercice / Évaluation", "TP / Démarche expérimentale / ECE"))
st.sidebar.divider()
st.sidebar.button("🔄 Nouvelle analyse", key="reset_side", on_click=nouvelle_analyse, use_container_width=True)

texte = st.text_area("1. Collez une consigne :", height=120, key=f"t_{st.session_state.reset}", placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure.")
fichier = st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :", key=f"f_{st.session_state.reset}")

col1, col2 = st.columns(2)
lancer = col1.button("🔍 Lancer l'analyse didactique", type="primary", use_container_width=True)
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

    lignes_focus = list()
    if support == "Exercice / Évaluation":
        lignes_focus.append("SPÉCIFICITÉ ÉVALUATION ÉCRITE / EXERCICE :")
        lignes_focus.append("- Analyse le contrat didactique d'évaluation (Guy Brousseau) : attentes implicites de rédaction (relation littérale, justification, unités, chiffres significatifs).")
        lignes_focus.append("- Repère les verbes opérateurs à protocole caché et les questions à tiroirs.")
    else:
        lignes_focus.append("SPÉCIFICITÉ TP / DÉMARCHE EXPÉRIMENTALE / ECE :")
        lignes_focus.append("- Analyse les implicites matériels et gestuels (verrerie, calibre, témoin, sécurité, incertitudes) et la charge cognitive d'attention partagée (Sweller).")
        lignes_focus.append("- Repère le piège du TP-recette versus une consigne d'investigation trop ouverte.")
    focus_support = "\n".join(lignes_focus)

    api_key = st.secrets["MISTRAL_API_KEY"].strip()
    lignes_prompt = list()
    lignes_prompt.append("Tu es un formateur spécialiste en didactique de la physique-chimie intervenant en INSPE (Master MEEF / M2E) et en formation continue.")
    lignes_prompt.append(f"Contexte : Niveau {niveau} | Type d'activité : {support}.")
    lignes_prompt.append("GARDE-FOUS : Ne juge jamais l'enseignant. Distingue les prérequis légitimes du programme (BO) des implicites parasites. Veille à l'effet Topaze (Guy Brousseau). Rédige en paragraphes fluides et nuancés, cite les mots exacts de la consigne, ne résous jamais l'exercice.")
    lignes_prompt.append(focus_support)
    lignes_prompt.append("Structure impérativement ton analyse en 5 parties en Markdown :")
    lignes_prompt.append("### 1. Clarté cognitive et cadre de l'Inspection Générale (IGÉSR)")
    lignes_prompt.append("Analyse la transparence des procédures intellectuelles ou expérimentales et des critères de réussite.")
    lignes_prompt.append("### 2. Obstacles épistémologiques et ruptures de registres (Bachelard, Johnstone, Tiberghien)")
    lignes_prompt.append("Décortique les obstacles épistémologiques (Bachelard) et les sauts implicites entre macroscopique, microscopique et symbolique (Johnstone) ou objets et modèles (Tiberghien).")
    lignes_prompt.append("### 3. Contrat didactique, malentendus socio-cognitifs et charge cognitive (Brousseau, Bautier & Rayou, Sweller)")
