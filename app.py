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
    references = {
        "Collège (Cycle 4)": (
            "### 📜 Ancrage institutionnel — Programme de Physique-Chimie (Cycle 4)\n"
            "- **Texte de référence :** Programme d'enseignement du cycle des approfondissements (cycle 4) — *BOEN n° 31 du 30 juillet 2020* (ajustements consolidés).\n"
            "- **Compétences travaillées :** Pratiquer des démarches scientifiques (formuler une question, proposer une expérience simple, interpréter un résultat), s'approprier des outils et des méthodes, pratiquer des langages (passer d'une forme de langage scientifique à une autre).\n"
            "- **Vigilance BO :** Au cycle 4, la modélisation reste qualitative et progressive ; le passage entre le monde des objets (observations macroscopiques) et le monde des modèles (atomes, molécules, ions) doit être explicitement accompagné."
        ),
        "Lycée Général (Seconde)": (
            "### 📜 Ancrage institutionnel — Programme de Physique-Chimie (Seconde GT)\n"
            "- **Texte de référence :** Programme de physique-chimie de seconde générale et technologique — *BOEN spécial n° 1 du 22 janvier 2019*.\n"
            "- **Compétences de la démarche scientifique :** S'approprier (APP), Analyser/Raisonner (ANA), Réaliser (REA), Valider (VAL), Communiquer (COM).\n"
            "- **Vigilance BO :** La classe de Seconde assure la transition vers la modélisation mathématique et l'usage rigoureux des grandeurs, unités, chiffres significatifs et incertitudes de mesure (approche statistique simple)."
        ),
        "Lycée Général (Spécialité PC - 1ère / Terminale)": (
            "### 📜 Ancrage institutionnel — Programme de Spécialité Physique-Chimie (Cycle Terminal)\n"
            "- **Textes de référence :** Programmes de spécialité physique-chimie de Première (*BOEN spécial n° 1 du 22 janvier 2019*) et de Terminale (*BOEN spécial n° 8 du 25 juillet 2019*), complétés par les notes de service sur les épreuves écrites et les **ECE**.\n"
            "- **Compétences de la démarche scientifique :** S'approprier (APP), Analyser/Raisonner (ANA), Réaliser (REA), Valider (VAL), Communiquer (COM) — avec un attendu fort sur l'autonomie dans la conception de protocoles et l'analyse critique des résultats (incertitudes-types, écart normalisé).\n"
            "- **Vigilance BO :** Les capacités exigibles distinguent explicitement les tâches guidées des tâches complexes (résolution de problème, ECE) où l'élève doit identifier lui-même les grandeurs pertinentes et les lois du modèle."
        ),
        "Lycée Technologique (STL / STI2D)": (
            "### 📜 Ancrage institutionnel — Programmes des séries technologiques (STL-SPCL / STI2D)\n"
            "- **Textes de référence :** Programmes de physique-chimie et mathématiques (STI2D) et de sciences physiques et chimiques en laboratoire (STL-SPCL) — *BOEN spécial n° 1 du 22 janvier 2019* et *BOEN spécial n° 8 du 25 juillet 2019*.\n"
            "- **Compétences et approche pédagogique :** Démarche de projet, approche technologique et expérimentale contextualisée, maîtrise des chaînes de mesure, analyse critique des protocoles et communication technique rigoureuse.\n"
            "- **Vigilance BO :** L'ancrage dans des systèmes réels ou des procédés de laboratoire exige de lever les implicites liés au contexte technique tout en maintenant l'exigence sur la modélisation physique et chimique."
        )
    }
    return references.get(niveau, "")

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
    st.markdown("""
    ### 🎯 Posture de l'outil : éclairer les choix, sans prescrire
    Expliciter une consigne ne signifie **pas** baisser le niveau d'exigence ni « mâcher le travail » (ce qui relèverait de l'**effet Topaze** décrit par Guy Brousseau). L'objectif est de distinguer les **obstacles cognitifs légitimes** (ce que l'on veut réellement faire chercher ou évaluer) des **implicites parasites** (ambiguïtés langagières, sauts de registres non signalés, non-dits matériels) qui pénalisent les élèves les plus fragiles.
    
    ### 🛠️ Différenciation selon le support choisi
    - **Mode Exercice / Évaluation :** Cible le contrat didactique d'évaluation (Brousseau), les verbes opérateurs à protocole caché, l'exploitation de documents et les attentes rédactionnelles implicites (expression littérale, unités, chiffres significatifs).
    - **Mode TP / Démarche expérimentale :** Cible les gestes et matériels non nommés, le rôle du témoin, la sécurité, la surcharge cognitive d'attention partagée à la paillasse (Sweller) et l'équilibre entre « TP-recette » et investigation ouverte.
    
    ### 📚 Cadres théoriques et institutionnels intégrés
    - **Inspection Générale (IGÉSR) & Bulletins Officiels (BO) :** Enseignement explicite, clarté cognitive et conformité aux attendus des programmes nationaux.
    - **Guy Brousseau :** Contrat didactique et vigilance face à l'effet Topaze (glissement vers un guidage mécanique).
    - **Gaston Bachelard :** Obstacles épistémologiques, sens commun et ruptures lexicales.
    - **Alex Johnstone & Andrée Tiberghien :** Articulation macroscopique / microscopique / symbolique (chimie) et objets / modèles (physique).
    - **Élisabeth Bautier & Patrick Rayou / John Sweller :** Malentendus socio-cognitifs et gestion de la charge cognitive.
    """)

options_niveaux = (
    "Collège (Cycle 4)",
    "Lycée Général (Seconde)",
    "Lycée Général (Spécialité PC - 1ère / Terminale)",
    "Lycée Technologique (STL / STI2D)"
)
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

    if support == "Exercice / Évaluation":
        focus_support = """SPÉCIFICITÉ ÉVALUATION ÉCRITE / EXERCICE :
        - Analyse le contrat didactique d'évaluation (Guy Brousseau) : ce que le professeur attend implicitement dans la rédaction (relation littérale avant le calcul, justification normée, conversion d'unités, chiffres significatifs, lien avec un document fourni).
        - Repère les verbes opérateurs à protocole caché (« déduire », « commenter », « exploiter », « montrer que ») et les questions à tiroirs où l'implicite d'une étape bloque la suivante.
        - Dans les 3 niveaux de réécriture, propose des formulations adaptées à un sujet de devoir écrit ou d'entraînement."""
    else:
        focus_support = """SPÉCIFICITÉ TP / DÉMARCHE EXPÉRIMENTALE / ECE :
        - Analyse les implicites matériels et gestuels : verrerie ou appareil de mesure non nommé, réglage de calibre, nécessité d'un témoin ou d'un blanc, précautions de sécurité non rappelées, gestion des incertitudes de mesure.
        - Évalue la charge cognitive d'attention partagée (John Sweller) : l'élève doit-il lire une consigne dense tout en manipulant ?
