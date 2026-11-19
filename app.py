import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
from docx import Document
import base64
import io

st.set_page_config(page_title="Didactique PC - Albert API", page_icon="🔬", layout="wide")
st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")

if "reset" not in st.session_state:
    st.session_state.reset = 0

with st.expander("ℹ️ Mode d'emploi et principes didactiques"):
    st.write("Cet outil analyse les implicites d'une consigne en adaptant strictement sa grille au support (Exercice écrit vs TP expérimental). Il repère les questions fermées propices aux réponses de sens commun, n'invente jamais de données absentes et propose 3 niveaux d'étayage basés sur des verbes d'action.")

mode_profil = st.sidebar.radio("Public / Niveau de détail :", ("⚡ Pratique de classe (Équilibré)", "🎓 Analyse approfondie (Formation / INSPE)"))
st.sidebar.divider()
niveau = st.sidebar.selectbox("Niveau :", ("Collège (Cycle 4)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC)", "Lycée Technologique (STL / STI2D)"))
support = st.sidebar.radio("Support :", ("Exercice / Évaluation", "TP / Démarche expérimentale / ECE"))

texte = st.text_area("1. Collez une consigne :", height=120, key=f"texte_{st.session_state.reset}", placeholder="Exemple : Question : cette boisson est-elle adaptée à un effort physique intense ?")
fichier = st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :", key=f"fichier_{st.session_state.reset}")

col1, col2 = st.columns(2)
lancer = col1.button("🔍 Lancer l'analyse", type="primary", use_container_width=True)
if col2.button("🔄 Nouvelle analyse", use_container_width=True):
    st.session_state.reset += 1
    st.rerun()

if lancer:
    contenu_texte = texte.strip()
    image_b64 = ""

    if fichier is not None:
        if fichier.name.lower().endswith(".pdf"):
            lecteur = PdfReader(fichier)
            pages = list()
            for p in lecteur.pages:
                t = p.extract_text()
                if t:
                    pages.append(t)
            contenu_texte = "\n".join(pages).strip()
            if not contenu_texte:
                st.error("⚠️ PDF scanné sans texte. Importez une capture d'écran (PNG/JPG).")
                st.stop()
        else:
            image_b64 = base64.b64encode(fichier.read()).decode("utf-8")

    if not contenu_texte and not image_b64:
        st.warning("⚠️ Saisissez une consigne ou chargez un fichier.")
        st.stop()

    api_key = st.secrets["ALBERT_API_KEY"].strip()

    regle_anti_hallucination = "RÈGLE ANTI-INVENTION ABSOLUE : N'invente JAMAIS de valeurs numériques, de volumes, de masses ou de documents qui ne figurent pas explicitement dans l'entrée fournie. Si la consigne fait référence à un document ou une étiquette non fourni(e), indique explicitement '(documents annexes non fournis)' et utilise des crochets génériques comme [valeur du document] sans jamais inventer de chiffres."

    if support == "Exercice / Évaluation":
        consigne_support = "CONTEXTE EXCLUSIF : EXERCICE ÉCRIT OU ÉVALUATION SUR TABLE (aucune manipulation). Analyse : la forme grammaticale (repère si une question fermée ou interrogative incite l'élève à répondre par son vécu ou le sens commun au lieu d'une démarche scientifique), l'extraction de données dans les documents, les verbes opérateurs à protocole caché et les attentes rédactionnelles implicites. Interdiction de parler de paillasse, de verrerie ou de TP."
    else:
        consigne_support = "CONTEXTE EXCLUSIF : SÉANCE EXPÉRIMENTALE / TP / ECE EN LABORATOIRE. Analyse : la démarche expérimentale, les gestes et matériels non nommés (verrerie, appareil, calibre), l'oubli du témoin ou du blanc, la sécurité implicite, l'articulation entre l'observation à la paillasse et le modèle théorique attendu pour conclure, et la surcharge cognitive pendant la manipulation."

    regle_verbes = "CONTRAINTE SUR LES 3 NIVEAUX DE REFORMULATION (ZÉRO QUESTION '?') : Bannir toute phrase interrogative. Utilise uniquement des verbes d'action précis à l'infinitif ou à l'impératif. Respecte strictement cette progression : Niveau 1 (Consigne ouverte clarifiée) = UNE SEULE phrase globale avec verbe d'action qui préserve l'autonomie de la tâche complexe sans dévoiler les étapes de calcul ; Niveau 2 (Étayage méthodologique) = 2 ou 3 étapes indiquant la démarche générale (extraire, calculer, comparer) sans donner les formules ni les facteurs de conversion ; Niveau 3 (Guidage pas à pas) = décomposition en actions élémentaires univoques avec verbes d'action."

    if "Pratique" in mode_profil:
        prompt = f"Tu es un formateur pragmatique en physique-chimie. Tu t'adresses à un enseignant préparant sa séance en {niveau}. {regle_anti_hallucination} {consigne_support} {regle_verbes} Ne résous jamais l'exercice. Rédige des paragraphes fluides et précis en citant les mots exacts de la consigne, structurés en 4 parties Markdown : ### 1. Compétences officielles engagées ({niveau}) ; ### 2. Analyse des implicites (forme de la question, appel au sens commun vs démarche scientifique, étapes cachées) ; ### 3. Risques de blocage ou de réponse hors-sujet pour les élèves ; ### 4. Trois niveaux de reformulation avec verbes d'action."
    else:
        prompt = f"Tu es un formateur spécialiste en didactique de la physique-chimie (INSPE / formation continue). Niveau : {niveau}. {regle_anti_hallucination} {consigne_support} {regle_verbes} Distingue les prérequis légitimes du programme (BO) des implicites parasites, sans juger l'enseignant. Ne résous jamais l'exercice. Rédige des paragraphes fluides en citant les mots exacts de la consigne, structurés en 6 parties Markdown : ### 1. Compétences officielles du programme engagées ({niveau}) ; ### 2. Clarté cognitive et cadre IGÉSR (forme interrogative vs verbe d'action, critères de réussite) ; ### 3. Obstacles épistémologiques (Bachelard : sens commun et vécu quotidien) et ruptures de registres (Johnstone / Tiberghien) ; ### 4. Contrat didactique (Brousseau), malentendus socio-cognitifs (Bautier & Rayou) et charge cognitive (Sweller) ; ### 5. Gradation d'explicitation en 3 niveaux avec verbes d'action (et vigilance face à l'effet Topaze) ; ### 6. Nuances, contre-arguments légitimes et question réflexive."

    messages = list()
    messages.append({"role": "system", "content": prompt})

    if image_b64:
        modele = "gemma-4-31b-it"
        contenu_visuel = list()
        contenu_visuel.append({"type": "text", "text": "Analyse les implicites de ce document sans inventer de données absentes de l'image :"})
        contenu_visuel.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"})
        messages.append({"role": "user", "content": contenu_visuel})
    else:
        modele = "mistral-small-3-2-24b-instruct-2506"
        messages.append({"role": "user", "content": contenu_texte[:12000]})

    with st.spinner("Analyse didactique en cours via Albert API..."):
        base_url = "https://" + "albert.api.etalab.gouv.fr" + "/v1"
        headers_api = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        rep = requests.post(
            base_url + "/chat/completions",
            headers=headers_api,
            json={"model": modele, "messages": messages, "temperature": 0.15},
            timeout=120
        )
        if rep.status_code == 200:
            data = rep.json()
            premier_choix = next(iter(data["choices"]))
            resultat = premier_choix["message"]["content"]
            st.markdown(resultat)
            st.divider()
            
            bo = "📜 **Référence BO :** "
            if "Cycle 4" in niveau:
                bo += "Programme du cycle 4 (BOEN n° 31 du 30 juillet 2020) — Pratiquer des démarches scientifiques et des langages, transition qualitative vers le modèle particulaire."
            elif "Seconde" in niveau:
                bo += "Programme de Seconde GT (BOEN spécial n° 1 du 22 janvier 2019) — Compétences APP, ANA, REA, VAL, COM, modélisation mathématique et incertitudes."
            elif "Spécialité" in niveau:
                bo += "Programmes de Spécialité PC Première et Terminale (BOEN n° 1 du 22 janv. 2019 et n° 8 du 25 juil. 2019) & notes de service ECE — Autonomie de protocole et analyse critique."
            else:
                bo += "Programmes des séries technologiques STL-SPCL et STI2D (BOEN 2019) — Démarche de projet, contextualisation technique et chaînes de mesure."
            st.info(bo)

            doc = Document()
            doc.add_heading(f"Analyse Didactique PC ({niveau} - {support})", level=1)
            for ligne in (resultat + "\n\n" + bo).split("\n"):
                if ligne.strip():
                    doc.add_paragraph(ligne.replace("#", "").replace("*", "").strip())
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            st.download_button("📘 Télécharger en Word (.docx)", data=buf, file_name=f"analyse_PC_{datetime.now().strftime('%Y%m%d_%H%M')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            st.error(f"Erreur Albert API ({rep.status_code}) : {rep.text}")
