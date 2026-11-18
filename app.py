import streamlit as st
import requests
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="Didactique PC - Détecteur d'Implicites",
    page_icon="🔬",
    layout="wide"
)

# Initialisation de la mémoire de session pour conserver l'analyse lors du téléchargement
if "analyse_resultat" not in st.session_state:
    st.session_state.analyse_resultat = None
if "dernier_contexte" not in st.session_state:
    st.session_state.dernier_contexte = {}

# En-tête
st.title("🔬 Didactique PC : Détecteur d'Implicites dans les Consignes")
st.markdown("""
*Outil de formation (INSPE / Formation continue) pour analyser les obstacles langagiers, 
méthodologiques et expérimentaux des consignes en physique-chimie.*
""")

# Barre latérale épurée
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
    1. Soumettez une consigne brute issue d'un manuel ou d'un TP.
    2. Observez les blocages potentiels côté élève.
    3. Choisissez le niveau d'étayage (1, 2 ou 3) adapté à votre objectif d'évaluation.
    """)

# Zone de saisie
consigne = st.text_area(
    "Collez ici la consigne ou l'extrait de fiche TP à analyser :",
    height=140,
    placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole permettant de vérifier si l'eau du robinet contient des ions chlorure, puis conclure."
)

# Bouton d'analyse
if st.button("🔍 Analyser les implicites didactiques", type="primary"):
    if not consigne.strip():
        st.warning("⚠️ Veuillez saisir une consigne à analyser.")
    else:
        with st.spinner("Analyse didactique en cours..."):
            try:
                api_key = st.secrets["MISTRAL_API_KEY"].strip()
                
                prompt_systeme = f"""Tu es un formateur expert en didactique de la physique-chimie intervenant en INSPE (Master MEEF) et en formation continue.
Contexte : Niveau {niveau} | Type : {type_activite}.
Analyse uniquement la formulation de la consigne fournie (ne résous pas l'exercice). Structure ta réponse en 4 parties claires en Markdown :

### 1. 🕵️ Diagnostic des implicites
Classe les obstacles potentiels pour un élève de ce niveau :
- **Implicites méthodologiques** (verbes d'action à protocole caché : justifier, exploiter, vérifier...).
- **Implicites de la démarche expérimentale** (matériel non nommé, témoin, sécurité, grandeur mesurée vs calculée).
- **Implicites cognitifs et prérequis** (savoirs antérieurs non rappelés, changement de registre texte/schéma/graphique/équation).
- **Implicites langagiers et polysémie** (vocabulaire courant vs scientifique, double tâche).

### 2. 🧠 Simulation « Point de vue élève »
Donne 2 ou 3 exemples concrets d'erreurs, de blocages ou d'interprétations littérales qu'un élève en difficulté ou à besoins éducatifs particuliers risque de produire.

### 3. 🪜 Gradation d'explicitation (Propositions de réécriture)
Propose trois versions de la consigne adaptées au niveau {niveau} :
- **Niveau 1 (Tâche complexe / Ouverte)** : Consigne d'origine simplement débarrassée des ambiguïtés langagières.
- **Niveau 2 (Étayage intermédiaire)** : Ajout d'indices sur la démarche ou les ressources sans donner les étapes.
- **Niveau 3 (Explicitation maximale / Pas à pas)** : Décomposition en tâches élémentaires univoques.

### 4. 💡 Question réflexive pour le formateur / stagiaire
Termine par une question courte pour interroger l'intention pédagogique de l'enseignant (évaluation de l'autonomie vs maîtrise d'une procédure)."""

                url = "https://mistral.ai"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # Appel principal sur le modèle le plus précis (mistral-large-latest)
                response = requests.post(
                    url,
                    headers=headers,
                    json={
                        "model": "mistral-large-latest",
                        "messages": [
                            {"role": "system", "content": prompt_systeme},
                            {"role": "user", "content": consigne}
                        ],
                        "temperature": 0.3
                    }
                )
                
                # Repli automatique sur mistral-small-latest si large n'est pas actif sur le compte
                if response.status_code == 404:
                    response = requests.post(
                        url,
                        headers=headers,
                        json={
                            "model": "mistral-small-latest",
                            "messages": [
                                {"role": "system", "content": prompt_systeme},
                                {"role": "user", "content": consigne}
                            ],
                            "temperature": 0.3
                        }
                    )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.analyse_resultat = data["choices"][0]["message"]["content"]
                    st.session_state.dernier_contexte = {
                        "niveau": niveau,
                        "type": type_activite,
                        "consigne": consigne,
                        "date": datetime.now().strftime("%d/%m/%Y à %H:%M")
                    }
                else:
                    st.error(f"Erreur API Mistral ({response.status_code}) : {response.text}")
                    
            except Exception as e:
                st.error(f"Erreur technique : {e}")

# Affichage du résultat et bouton d'exportation
if st.session_state.analyse_resultat:
    st.divider()
    st.markdown(st.session_state.analyse_resultat)
    
    st.divider()
    ctx = st.session_state.dernier_contexte
    contenu_export = f"""# Fiche d'Analyse Didactique - Physique-Chimie
- **Date :** {ctx.get('date', '')}
- **Niveau :** {ctx.get('niveau', '')}
- **Support :** {ctx.get('type', '')}

## Consigne analysée
> {ctx.get('consigne', '')}

---

{st.session_state.analyse_resultat}
"""
    
    st.download_button(
        label="📥 Télécharger la fiche d'analyse (.md)",
        data=contenu_export,
        file_name=f"analyse_implicites_PC_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown"
    )
