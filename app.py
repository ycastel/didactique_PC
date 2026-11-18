import streamlit as st
import requests

st.set_page_config(page_title="Didactique PC - Implicites", page_icon="🔬", layout="wide")

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

consigne = st.text_area(
    "Collez ici la consigne ou l'extrait de fiche TP à analyser :",
    height=130,
    placeholder="Exemple : À partir du matériel sur la paillasse, proposer un protocole pour vérifier si l'eau du robinet contient des ions chlorure, puis conclure."
)

if st.button("🔍 Analyser les implicites didactiques", type="primary"):
    if not consigne.strip():
        st.warning("⚠️ Veuillez saisir une consigne à analyser.")
    else:
        with st.spinner("Analyse didactique en cours..."):
            try:
                api_key = st.secrets["MISTRAL_API_KEY"]
                
                prompt_systeme = f"""Tu es un formateur expert en didactique de la physique-chimie intervenant en INSPE (Master MEEF) et en formation continue.
Contexte : Niveau {niveau} | Type : {type_activite}.
Analyse uniquement la formulation de la consigne fournie (ne résous pas l'exercice) en 4 parties en Markdown :

### 1. 🕵️ Diagnostic des implicites
- **Implicites méthodologiques** (verbes d'action à protocole caché : justifier, exploiter, vérifier...).
- **Implicites de la démarche expérimentale** (matériel non nommé, témoin, sécurité, grandeur mesurée vs calculée).
- **Implicites cognitifs et prérequis** (savoirs antérieurs non rappelés, changement de registre texte/schéma/graphique/équation).
- **Implicites langagiers et polysémie** (vocabulaire courant vs scientifique, double tâche).

### 2. 🧠 Simulation « Point de vue élève »
Donne 2 ou 3 exemples concrets d'erreurs ou de blocages probables d'un élève en difficulté.

### 3. 🪜 Gradation d'explicitation (Propositions de réécriture)
- **Niveau 1 (Tâche complexe / Ouverte)** : Consigne d'origine débarrassée des ambiguïtés langagières.
- **Niveau 2 (Étayage intermédiaire)** : Ajout d'indices sur la démarche sans donner les étapes.
- **Niveau 3 (Explicitation maximale / Pas à pas)** : Décomposition en tâches élémentaires univoques.

### 4. 💡 Question réflexive pour le formateur / stagiaire
Termine par une question courte pour interroger l'intention pédagogique de l'enseignant."""

                response = requests.post(
                    "https://mistral.ai",
                    headers={
                        "Authorization": f"Bearer {api_key.strip()}",
                        "Content-Type": "application/json"
                    },
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
                    st.markdown(data["choices"]["message"]["content"])
                else:
                    st.error(f"Code erreur API : {response.status_code}")
                    st.code(response.text)
                    
            except Exception as e:
                st.error(f"Erreur technique : {e}")
