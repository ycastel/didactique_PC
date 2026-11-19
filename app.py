import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
from docx import Document
import base64
import io

st.set_page_config(page_title="Didactique PC - Albert API", page_icon="🔬", layout="wide")
st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")

with st.expander("ℹ️ Mode d'emploi et principes didactiques"):
    st.write("Cet outil analyse les implicites d'une consigne en adaptant strictement sa grille au support (Exercice écrit vs TP expérimental). Les reformulations bannissent les formes interrogatives au profit de verbes d'action univoques.")

mode_profil = st.sidebar.radio("Public / Niveau de détail :", ("⚡ Pratique de classe (Équilibré)", "🎓 Analyse approfondie (Formation / INSPE)"))
st.sidebar.divider()
niveau = st.sidebar.selectbox("Niveau :", ("Collège (Cycle 4)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC)", "Lycée Technologique (STL / STI2D)"))
support = st.sidebar.radio("Support :", ("Exercice / Évaluation", "TP / Démarche expérimentale / ECE"))

texte = st.text_area("1. Collez une consigne :", height=120, placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure.")
fichier = st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :")

col1, col2 = st.columns(2)
lancer = col1.button("🔍 Lancer l'analyse", type="primary", use_container_width=True)
if col2.button("🔄 Nouvelle analyse", use_container_width=True):
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

    if support == "Exercice / Évaluation":
        consigne_support = "CONTEXTE EXCLUSIF : EXERCICE ÉCRIT OU ÉVALUATION SUR TABLE (aucune manipulation). Analyse uniquement : la compréhension de l'énoncé écrit, l'extraction d'informations dans les documents, les verbes opérateurs à protocole caché (justifier, déduire, commenter), le passage texte/schéma/formule/graphique, et les attentes rédactionnelles implicites (expression littérale avant calcul, unités, chiffres significatifs). Interdiction de parler de paillasse, de verrerie ou de TP."
    else:
        consigne_support = "CONTEXTE EXCLUSIF : SÉANCE EXPÉRIMENTALE / TP / ECE EN LABORATOIRE. Analyse uniquement : la démarche expérimentale, les gestes et matériels non nommés (verrerie, appareil, calibre), l'oubli du témoin ou du blanc, la sécurité implicite, l'articulation entre l'observation/mesure à la paillasse et le modèle théorique attendu pour conclure, et la surcharge cognitive liée à la lecture de la fiche pendant la manipulation."

    regle_verbes = "CONTRAINTE ABSOLUE SUR LES REFORMULATIONS : Interdiction totale d'utiliser des phrases interrogatives (aucun point d'interrogation '?') dans les consignes réécrites, surtout au Niveau 3. Utilise uniquement des verbes d'action précis à l'infinitif ou à l'impératif (Identifier, Schématiser, Prélever, Mesurer, Calculer, Comparer, Rédiger) qui indiquent explicitement l'action mentale ou matérielle attendue."

    if "Pratique" in mode_profil:
        prompt = f"Tu es un formateur pragmatique en physique-chimie. Tu t'adresses à un enseignant préparant sa séance en {niveau}. {consigne_support} {regle_verbes} RÈGLE DE SOBRIÉTÉ : Sois chirurgical, n'invente aucun faux problème et n'analyse que les implicites réellement présents dans le texte fourni. Ne résous jamais l'exercice. Rédige des paragraphes fluides et précis en citant les mots exacts de la consigne, structurés en 4 parties Markdown : ### 1. Compétences officielles engagées ({niveau}) ; ### 2. Analyse des implicites réels de la consigne ; ### 3. Risques de blocage concret pour les élèves ; ### 4. Trois niveaux de reformulation avec verbes d'action (Niveau 1 : consigne ouverte clarifiée ; Niveau 2 : étayage méthodologique ; Niveau 3 : guidage pas à pas uniquement avec des verbes d'action, zéro question)."
    else:
        prompt = f"Tu es un formateur spécialiste en didactique de la physique-chimie (INSPE / formation continue). Niveau : {niveau}. {consigne_support} {regle_verbes} RÈGLE DE SOBRIÉTÉ : Sois chirurgical, ne sur-interprète pas l'énoncé et ne juge pas l'enseignant ; distingue les prérequis légitimes du programme (BO) des implicites parasites. Ne résous jamais l'exercice. Rédige des paragraphes fluides en citant les mots exacts de la consigne, structurés en 6 parties Markdown : ### 1. Compétences officielles du programme engagées ({niveau}) ; ### 2. Clarté cognitive et cadre IGÉSR ; ### 3. Obstacles épistémologiques (Bachelard) et ruptures de registres (Johnstone / Tiberghien) ; ### 4. Contrat didactique (Brousseau), malentendus socio-cognitifs (Bautier & Rayou) et charge cognitive (Sweller) ; ### 5. Gradation d'explicitation avec verbes d'action (Niveau 1 : ouverte clarifiée ; Niveau 2 : étayage intermédiaire ; Niveau 3 : pas à pas uniquement avec des verbes d'action sans forme interrogative, et vigilance face à l'effet Topaze) ; ### 6. Nuances, contre-arguments légitimes et question réflexive."

    messages = list()
    messages.append({"role": "system", "content": prompt})

    if image_b64:
        modele = "gemma-4-31b-it"
        contenu_visuel = list()
        contenu_visuel.append({"type": "text", "text": "Analyse les implicites de ce document :"})
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
            json={"model": modele, "messages": messages, "temperature": 0.2},
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
