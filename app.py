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
    st.write("Cet outil analyse les implicites langagiers, épistémologiques et méthodologiques d'une consigne en physique-chimie, en calibrant strictement l'exigence scientifique au niveau choisi (Cycle 4 vs Lycée) et en proposant 3 niveaux d'étayage basés sur des verbes d'action.")

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

    # 1. Cadrage disciplinaire et progression cognitive selon le niveau
    if "Cycle 4" in niveau:
        regle_niveau = "DISCIPLINE EXCLUSIVE : PHYSIQUE-CHIMIE AU COLLÈGE (CYCLE 4). Interdiction absolue de citer des thèmes de SVT (comme 'Corps humain et santé' ou 'fonctions de nutrition'). Rattache l'énoncé uniquement aux thèmes officiels de Physique-Chimie du Cycle 4 ('Organisation et transformations de la matière', 'Mouvement et interactions', 'L'énergie et ses conversions') et aux compétences : 'Pratiquer des démarches scientifiques', 'S'approprier des outils et des méthodes', 'Pratiquer des langages'. Niveau d'exigence : la proportionnalité, les conversions d'unités (mg en g, cL en L) et le vocabulaire chimique de base sont des obstacles légitimes à accompagner."
    elif "Seconde" in niveau:
        regle_niveau = "DISCIPLINE EXCLUSIVE : PHYSIQUE-CHIMIE EN SECONDE GT. Interdiction de citer la SVT. Rattache l'énoncé aux thèmes officiels de PC ('Constitution et transformations de la matière', 'Mouvement et interactions', 'Ondes et signaux') et aux compétences : 'S'approprier (APP)', 'Analyser/Raisonner (ANA)', 'Réaliser (REA)', 'Valider (VAL)', 'Communiquer (COM)'. Niveau d'exigence : les conversions simples sont des prérequis de collège ; l'enjeu porte sur la concentration en masse, le protocole de dissolution/dilution et les chiffres significatifs."
    else:
        regle_niveau = f"DISCIPLINE EXCLUSIVE : PHYSIQUE-CHIMIE EN {niveau}. Interdiction absolue de citer la SVT. Rattache l'énoncé aux thèmes officiels de PC et aux 5 compétences : 'S'approprier (APP)', 'Analyser/Raisonner (ANA)', 'Réaliser (REA)', 'Valider (VAL)', 'Communiquer (COM)'. Niveau d'exigence élevé : les conversions d'unités (mg en g, cL en L) et la proportionnalité sont des prérequis acquis (ne les présente jamais comme des obstacles majeurs). L'analyse doit cibler des enjeux de niveau lycée : concentration en quantité de matière, lien entre grandeur microscopique et macroscopique, exploitation critique de données, incertitudes-types ou écart normalisé."

    # 2. Verrou anti-hallucination (chiffres et toutes lettres)
    regle_anti_hallucination = "RÈGLE ANTI-INVENTION ABSOLUE : N'invente JAMAIS aucune valeur numérique, ni en chiffres (interdiction d'écrire 310, 50, 0,50, etc.), ni en toutes lettres (interdiction d'écrire 'trois cent dix' ou 'cinquante'), ni aucune plage de valeurs qui ne figure pas mot pour mot dans le texte fourni. Si les documents annexes sont absents, utilise uniquement des formulations génériques comme '[valeur indiquée sur le document]'."

    # 3. Cadrage selon le support (Écrit vs TP)
    if support == "Exercice / Évaluation":
        consigne_support = "CONTEXTE : EXERCICE ÉCRIT / ÉVALUATION. Analyse en priorité la syntaxe de la consigne : critique explicitement l'absence de verbe d'action et l'usage d'une forme interrogative fermée ('Est-ce que...', '...est-elle... ?') qui pousse l'élève à répondre par 'Oui/Non' en mobilisant son vécu quotidien ou le sens commun au lieu d'une démarche scientifique. Explique l'implicite du contrat didactique."
    else:
        consigne_support = "CONTEXTE : SÉANCE EXPÉRIMENTALE / TP / ECE. Analyse en priorité les implicites de la démarche expérimentale : absence de verbes d'action opératoires, gestes et matériels non nommés (verrerie, appareil, calibre), oubli du témoin ou du blanc, sécurité implicite, et rupture non explicitée entre l'observation à la paillasse et le modèle théorique."

    # 4. Contrainte verbes d'action
    regle_verbes = "CONTRAINTE SUR LES 3 REFORMULATIONS (ZÉRO '?') : Interdiction totale de phrases interrogatives. Utilise uniquement des verbes d'action précis à l'infinitif ou à l'impératif. Niveau 1 = UNE SEULE phrase globale avec verbe d'action préservant l'autonomie de la tâche complexe ; Niveau 2 = 2 ou 3 étapes méthodologiques générales avec verbes d'action ; Niveau 3 = guidage pas à pas en actions élémentaires univoques (sans inventer de valeurs absentes du texte)."

    if "Pratique" in mode_profil:
        prompt = f"Tu es un formateur expert en didactique de la physique-chimie. {regle_niveau} {regle_anti_hallucination} {consigne_support} {regle_verbes} Ne résous jamais l'exercice. Rédige des paragraphes fluides et précis en citant les mots exacts de la consigne, structurés en 4 parties Markdown : ### 1. Compétences officielles de Physique-Chimie engagées ({niveau}) ; ### 2. Analyse langagière et implicite didactique (Consacre un premier paragraphe à critiquer la forme grammaticale — forme interrogative vs absence de verbe d'action — et le piège du sens commun/vécu quotidien ; puis un second paragraphe sur les procédures scientifiques cachées derrière l'énoncé) ; ### 3. Risques de blocage ou de réponse hors-sujet adaptés au niveau {niveau} ; ### 4. Trois niveaux de reformulation avec verbes d'action."
    else:
        prompt = f"Tu es un formateur spécialiste en didactique de la physique-chimie (INSPE / formation continue). {regle_niveau} {regle_anti_hallucination} {consigne_support} {regle_verbes} Distingue les prérequis légitimes du programme (BO) des implicites parasites, sans juger l'enseignant. Ne résous jamais l'exercice. Rédige des paragraphes fluides en citant les mots exacts de la consigne, structurés en 6 parties Markdown : ### 1. Compétences officielles de Physique-Chimie engagées ({niveau}) ; ### 2. Clarté cognitive et cadre IGÉSR (critique de la forme interrogative, absence de verbe d'action opérateur et critères de réussite invisibles) ; ### 3. Obstacles épistémologiques (Bachelard : appel au sens commun et au vécu quotidien) et ruptures de registres (Johnstone / Tiberghien) ; ### 4. Contrat didactique (Brousseau : décalage entre la question posée et l'attente scientifique réelle), malentendus socio-cognitifs (Bautier & Rayou) et charge cognitive (Sweller) ; ### 5. Gradation d'explicitation en 3 niveaux avec verbes d'action (et vigilance face à l'effet Topaze) ; ### 6. Nuances, contre-arguments légitimes et question réflexive."

    messages = list()
    messages.append({"role": "system", "content": prompt})

    if image_b64:
        modele = "gemma-4-31b-it"
        contenu_visuel = list()
        contenu_visuel.append({"type": "text", "text": "Analyse les implicites langagiers et didactiques de ce document de Physique-Chimie sans inventer aucune donnée absente de l'image :"})
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
            json={"model": modele, "messages": messages, "temperature": 0.1},
            timeout=120
        )
        if rep.status_code == 200:
            data = rep.json()
            premier_choix = next(iter(data["choices"]))
            resultat = premier_choix["message"]["content"]
            st.markdown(resultat)
            st.divider()
            
            bo = "📜 **Référence BO :** "
