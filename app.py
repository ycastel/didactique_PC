import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
from docx import Document
import base64
import io

st.set_page_config(page_title="Didactique PC - Albert API", page_icon="🔬", layout="wide")
st.title("🔬 Didactique PC : Analyseur d'Implicites et d'Étayage")

for cle, defaut in [("reset", 0), ("resultat", ""), ("bo", ""), ("meta", ("", ""))]:
    if cle not in st.session_state:
        st.session_state[cle] = defaut

with st.expander("ℹ️ Mode d'emploi et principes didactiques"):
    st.write("Analyse les implicites d'une consigne en adaptant sa grille au support (Écrit vs TP) et au niveau scolaire (Cycle 4 vs Lycée), avec 3 niveaux d'étayage basés sur des verbes d'action.")

mode_profil = st.sidebar.radio("Public / Détail :", ("⚡ Pratique de classe (Équilibré)", "🎓 Analyse approfondie (Formation / INSPE)"))
st.sidebar.divider()
niveau = st.sidebar.selectbox("Niveau :", ("Collège (Cycle 4)", "Lycée Général (Seconde)", "Lycée Général (Spécialité PC)", "Lycée Technologique (STL / STI2D)"))
support = st.sidebar.radio("Support :", ("Exercice / Évaluation", "TP / Démarche expérimentale / ECE"))

texte = st.text_area("1. Collez une consigne :", height=120, key=f"t_{st.session_state.reset}", placeholder="Exemple : Question : cette boisson est-elle adaptée à un effort physique intense ?")
fichier = st.file_uploader("2. OU importez un fichier (PDF, PNG, JPG) :", key=f"f_{st.session_state.reset}")

col1, col2 = st.columns(2)
lancer = col1.button("🔍 Lancer l'analyse", type="primary", use_container_width=True)
if col2.button("🔄 Nouvelle analyse", use_container_width=True):
    st.session_state.reset += 1
    st.session_state.resultat = ""
    st.session_state.bo = ""
    st.rerun()

if lancer:
    contenu_texte = texte.strip()
    image_b64 = ""
    if fichier is not None:
        if fichier.name.lower().endswith(".pdf"):
            lecteur = PdfReader(fichier)
            contenu_texte = "\n".join([p.extract_text() for p in lecteur.pages if p.extract_text()]).strip()
            if not contenu_texte:
                st.error("⚠️ PDF scanné sans texte. Importez une capture d'écran (PNG/JPG).")
                st.stop()
        else:
            image_b64 = base64.b64encode(fichier.read()).decode("utf-8")

    if not contenu_texte and not image_b64:
        st.warning("⚠️ Saisissez une consigne ou chargez un fichier.")
        st.stop()

    api_key = st.secrets["ALBERT_API_KEY"].strip()

    if "Cycle 4" in niveau:
        r_niv = "DISCIPLINE : PHYSIQUE-CHIMIE CYCLE 4 uniquement (interdiction de citer la SVT). Thèmes : Organisation et transformations de la matière, Mouvement, Énergie. Compétences : Pratiquer des démarches scientifiques, S'approprier des outils, Pratiquer des langages. Conversions (mg/g, cL/L) et proportionnalité sont des obstacles légitimes."
    elif "Seconde" in niveau:
        r_niv = "DISCIPLINE : PHYSIQUE-CHIMIE SECONDE GT uniquement (interdiction de citer la SVT). Compétences exactes du BO : S'approprier (APP), Analyser/Raisonner (ANA), Réaliser (REA), Valider (VAL), Communiquer (COM). Enjeux : concentration en masse, protocole de dissolution/dilution, chiffres significatifs."
    else:
        r_niv = f"DISCIPLINE : PHYSIQUE-CHIMIE {niveau} uniquement (interdiction de citer la SVT). Compétences exactes du BO : S'approprier (APP), Analyser/Raisonner (ANA), Réaliser (REA), Valider (VAL), Communiquer (COM). CALIBRAGE DE NIVEAU : Si l'énoncé fourni est un exercice élémentaire de collège/seconde (simple conversion mg/g, cL/L ou proportionnalité), signale explicitement dès le début qu'il est sous-dimensionné pour le niveau {niveau} et propose des pistes pour l'élever (concentration en quantité de matière, incertitudes-types, protocole expérimental)."

    r_hallu = "ANTI-HALLUCINATION : N'invente AUCUNE valeur numérique (ni en chiffres comme 310 ou 50, ni en toutes lettres comme 'trois cent dix' ou 'cinquante') absente du texte. Si les documents manquent, écris '[donnée du document]'."
    r_sup = "CONTEXTE ÉCRIT : Critique explicitement l'absence de verbe d'action et la forme interrogative fermée ('...est-elle... ?') qui pousse l'élève à répondre par 'Oui/Non' via son vécu/sens commun au lieu d'une preuve scientifique." if "Exercice" in support else "CONTEXTE TP : Critique l'absence de verbes opératoires, les implicites matériels (verrerie, calibre, témoin, sécurité) et la rupture non explicitée entre observation à la paillasse et modèle théorique."
    r_verb = "REFORMULATIONS (ZÉRO '?') : Uniquement des verbes d'action (infinitif/impératif). Niveau 1 = UNE SEULE phrase globale ouverte ; Niveau 2 = 2-3 étapes méthodologiques générales ; Niveau 3 = guidage pas à pas univoque sans inventer de valeurs."

    if "Pratique" in mode_profil:
        prompt = f"Formateur expert en didactique PC ({niveau}). {r_niv} {r_hallu} {r_sup} {r_verb} Ne résous jamais l'exercice. Cite les mots exacts. Structure en 4 parties Markdown : ### 1. Compétences officielles de Physique-Chimie engagées ({niveau}) ; ### 2. Analyse langagière et implicite didactique (paragraphe 1 : forme interrogative vs verbe d'action et piège du sens commun ; paragraphe 2 : procédures scientifiques cachées) ; ### 3. Risques de blocage adaptés au niveau {niveau} ; ### 4. Trois niveaux de reformulation avec verbes d'action."
    else:
        prompt = f"Formateur didactique PC (INSPE). {r_niv} {r_hallu} {r_sup} {r_verb} Ne résous jamais l'exercice. Cite les mots exacts. Structure en 6 parties Markdown : ### 1. Compétences officielles PC ({niveau}) ; ### 2. Clarté cognitive et cadre IGÉSR ; ### 3. Obstacles épistémologiques (Bachelard : sens commun) et registres (Johnstone/Tiberghien) ; ### 4. Contrat didactique (Brousseau), malentendus socio-cognitifs (Bautier & Rayou) et charge cognitive (Sweller) ; ### 5. Gradation d'explicitation avec verbes d'action (vigilance effet Topaze) ; ### 6. Nuances, contre-arguments légitimes et question réflexive."

    messages = [{"role": "system", "content": prompt}]
    if image_b64:
        modele = "gemma-4-31b-it"
        messages.append({"role": "user", "content": [{"type": "text", "text": "Analyse les implicites PC de ce document sans inventer de données :"}, {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"}]})
    else:
        modele = "mistral-small-3-2-24b-instruct-2506"
        messages.append({"role": "user", "content": contenu_texte[:12000]})

    with st.spinner("Analyse didactique en cours via Albert API..."):
        url = "https://" + "albert.api.etalab.gouv.fr" + "/v1/chat/completions"
        rep = requests.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json={"model": modele, "messages": messages, "temperature": 0.1}, timeout=120)
        if rep.status_code == 200:
            st.session_state.resultat = next(iter(rep.json()["choices"]))["message"]["content"]
            if "Cycle 4" in niveau: st.session_state.bo = "📜 **Référence BO :** Cycle 4 (BOEN n° 31 du 30 juillet 2020) — Organisation et transformations de la matière, démarches scientifiques et langages."
            elif "Seconde" in niveau: st.session_state.bo = "📜 **Référence BO :** Seconde GT (BOEN spécial n° 1 du 22 janvier 2019) — Compétences APP, ANA, REA, VAL, COM, concentration en masse et incertitudes."
            elif "Spécialité" in niveau: st.session_state.bo = "📜 **Référence BO :** Spécialité PC Première et Terminale (BOEN 2019) & notes ECE — Autonomie de protocole, quantité de matière et analyse critique."
            else: st.session_state.bo = "📜 **Référence BO :** Séries technologiques STL-SPCL et STI2D (BOEN 2019) — Démarche de projet, contextualisation technique et chaînes de mesure."
            st.session_state.meta = (niveau, support)
        else:
            st.error(f"Erreur Albert API ({rep.status_code}) : {rep.text}")

if st.session_state.resultat:
    st.divider()
    st.markdown(st.session_state.resultat)
    st.divider()
    st.info(st.session_state.bo)
    st.divider()
    niv_d, sup_d = st.session_state.meta
    doc = Document()
    doc.add_heading(f"Analyse Didactique PC ({niv_d} - {sup_d})", level=1)
    for ligne in (st.session_state.resultat + "\n\n" + st.session_state.bo).split("\n"):
        if ligne.strip(): doc.add_paragraph(ligne.replace("#", "").replace("*", "").strip())
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    st.download_button("📘 Télécharger l'analyse en Word (.docx)", data=buf, file_name=f"analyse_PC_{datetime.now().strftime('%Y%m%d_%H%M')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
