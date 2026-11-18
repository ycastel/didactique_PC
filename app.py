import streamlit as st
import requests
from datetime import datetime
from pypdf import PdfReader
import io
import re

st.set_page_config(page_title="Didactique PC - Implicites", page_icon="🔬", layout="wide")

if "analyse_resultat" not in st.session_state:
    st.session_state.analyse_resultat = None
if "dernier_contexte" not in st.session_state:
    st.session_state.dernier_contexte = {}

def nettoyer_texte_xml(texte):
    # Supprime les caractères de contrôle invisibles des PDF incompatibles avec Word
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', texte)

def generer_docx(contexte, texte_analyse):
    from docx import Document
    doc = Document()
    doc.add_heading("Fiche d'Analyse Didactique - Physique-Chimie", level=1)
    
    p_meta = doc.add_paragraph()
    p_meta.add_run("Date : ").bold = True
    p_meta.add_run(f"{contexte.get('date', '')}\n")
    p_meta.add_run("Niveau : ").bold = True
    p_meta.add_run(f"{contexte.get('niveau', '')}\n")
    p_meta.add_run("Support : ").bold = True
    p_meta.add_run(f"{contexte.get('type', '')}")
    
    doc.add_heading("Consigne / Document analysé", level=2)
    doc.add_paragraph(nettoyer_texte_xml(contexte.get("consigne", "")))
    
    doc.add_heading("Diagnostic des implicites et conseils d'explicitation", level=2)
    texte_propre = nettoyer_texte_xml(texte_analyse)
    for ligne in texte_propre.split("\n"):
        ligne_propre = ligne.strip()
        if ligne_propre.startswith("### "):
            doc.add_heading(ligne_propre.replace("### ", ""), level=3)
        elif ligne_propre.startswith("- "):
            doc.add_paragraph(ligne_propre.replace("- ", "").replace("**", ""), style="List Bullet")
        elif ligne_propre:
            doc.add_paragraph(ligne_propre.replace("**", ""))
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

st.title("🔬 Didactique PC : Détecteur d'Implicites dans les Consignes")
st.markdown("*Outil de formation (INSPE / Formation continue) pour analyser les obstacles langagiers, méthodologiques et expérimentaux.*")

with st.sidebar:
    st.header("⚙️ Contexte pédagogique")
    niveau = st.selectbox(
        "Niveau d'enseignement :",
        [
            "Collège (Cycle 4 : 5e, 4e, 3e)",
            "Lycée Général (Seconde)",
            "Lycée Général (Spécialité PC - 1ère / Terminale)",
            "Lycée Technologique (STL / STI2D)"
        ]
    )
    type_activite = st.radio(
        "Type de support :",
        ["Exercice écrit / Évaluation", "Travaux Pratiques (TP) / Démarche expérimentale"]
    )
    
    st.divider()
    st.info("""
    **💡 Piste d'exploitation en formation :**
    1. Importez un PDF de TP/sujet ou collez une consigne.
    2. Observez les blocages potentiels côté élève.
    3. Téléchargez la fiche d'analyse en Word ou Markdown pour vos préparations.
    """)

onglet_texte, onglet_pdf = st.tabs(["✍️ Saisir ou coller un texte", "📄 Importer un fichier PDF"])

texte_saisi = ""
texte_pdf = ""

with onglet_texte:
    texte_saisi = st.text_area(
        "Collez ici la consigne ou l'extrait de fiche TP à analyser :",
        height=140,
        placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure."
    )

with onglet_pdf:
    fichier_pdf = st.file_uploader("Déposez votre sujet d'exercice ou votre fiche de TP (format PDF) :", type=["pdf"])
    if fichier_pdf is not None:
        try:
            lecteur = PdfReader(fichier_pdf)
            pages_texte = []
            for page in lecteur.pages:
                extrait = page.extract_text()
                if extrait:
                    pages_texte.append(extrait)
            texte_pdf = "\n".join(pages_texte).strip()
            if texte_pdf:
                st.success(f"✅ PDF lu avec succès ({len(lecteur.pages)} page(s), {len(texte_pdf)} caractères extraits).")
                with st.expander("Aperçu du texte extrait du PDF"):
                    st.text(texte_pdf[:1500] + ("..." if len(texte_pdf) > 1500 else ""))
            else:
                st.warning("⚠️ Ce PDF semble être une image scannée sans texte sélectionnable.")
        except Exception as e:
            st.error(f"Erreur lors de la lecture du PDF : {e}")

consigne_finale = texte_pdf if texte_pdf else texte_saisi.strip()

if st.button("🔍 Analyser les implicites didactiques", type="primary"):
    if not consigne_finale:
        st.warning("⚠️ Veuillez saisir une consigne ou importer un fichier PDF contenant du texte.")
    else:
        with st.spinner("Analyse didactique en cours..."):
            try:
                api_key = st.secrets["MISTRAL_API_KEY"].strip()
                
                prompt_systeme = f"""Tu es un formateur expert en didactique de la physique-chimie intervenant en INSPE (Master MEEF) et en formation continue.
Contexte : Niveau {niveau} | Type : {type_activite}.
Analyse uniquement la formulation des consignes fournie (ne résous pas l'exercice) en 4 parties claires en Markdown :

### 1. 🕵️ Diagnostic des implicites
- **Implicites méthodologiques** (verbes d'action à protocole caché : justifier, exploiter, vérifier...).
- **Implicites de la démarche expérimentale** (matériel non nommé, témoin, sécurité, grandeur mesurée vs calculée).
- **Implicites cognitifs et prérequis** (savoirs antérieurs non rappelés, changement de registre texte/schéma/graphique/équation).
- **Implicites langagiers et polysémie** (vocabulaire courant vs scientifique, double tâche).

### 2. 🧠 Simulation « Point de vue élève »
Donne 2 ou 3 exemples concrets d'erreurs ou de blocages probables d'un élève en difficulté ou à besoins particuliers.

### 3. 🪜 Gradation d'explicitation (Propositions de réécriture et conseils)
Propose trois versions de la consigne adaptées au niveau {niveau} :
- **Niveau 1 (Tâche complexe / Ouverte)** : Consigne d'origine débarrassée des ambiguïtés langagières.
- **Niveau 2 (Étayage intermédiaire)** : Ajout d'indices sur la démarche sans donner les étapes.
- **Niveau 3 (Explicitation maximale / Pas à pas)** : Décomposition en tâches élémentaires univoques.

### 4. 💡 Question réflexive pour le formateur / stagiaire
Termine par une question courte pour interroger l'intention pédagogique de l'enseignant."""

                url_api = "https://" + "api.mistral.ai" + "/v1/chat/completions"

                response = requests.post(
                    url_api,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "mistral-small-latest",
                        "messages": [
                            {"role": "system", "content": prompt_systeme},
                            {"role": "user", "content": consigne_finale[:12000]}
                        ],
                        "temperature": 0.3
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    premier_choix = next(iter(data["choices"]))
                    st.session_state.analyse_resultat = premier_choix["message"]["content"]
                    st.session_state.dernier_contexte = {
                        "niveau": niveau,
                        "type": type_activite,
                        "consigne": consigne_finale,
                        "date": datetime.now().strftime("%d/%m/%Y à %H:%M")
                    }
                else:
                    st.error(f"Code erreur API : {response.status_code}")
                    st.code(response.text)
                    
            except Exception as e:
                st.error(f"Erreur technique : {e}")

if st.session_state.analyse_resultat:
    st.divider()
    st.markdown(st.session_state.analyse_resultat)
    
    st.divider()
    st.subheader("📥 Exporter le diagnostic et les conseils")
    ctx = st.session_state.dernier_contexte
    horodatage = datetime.now().strftime('%Y%m%d_%H%M')
    
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            fichier_word = generer_docx(ctx, st.session_state.analyse_resultat)
            st.download_button(
                label="📘 Télécharger au format Word (.docx)",
                data=fichier_word,
                file_name=f"analyse_implicites_PC_{horodatage}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.warning(f"Export Word indisponible ({e}). Utilisez l'export Texte ci-contre.")
        
    with col2:
        contenu_md = f"""# Fiche d'Analyse Didactique - Physique-Chimie
- **Date :** {ctx.get('date', '')}
- **Niveau :** {ctx.get('niveau', '')}
- **Support :** {ctx.get('type', '')}

## Consigne / Document analysé
> {ctx.get('consigne', '')}

---

{st.session_state.analyse_resultat}
"""
        st.download_button(
            label="📝 Télécharger au format Texte / Markdown (.md)",
            data=contenu_md,
            file_name=f"analyse_implicites_PC_{horodatage}.md",
            mime="text/markdown"
        )
