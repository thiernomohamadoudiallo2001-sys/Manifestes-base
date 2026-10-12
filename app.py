import streamlit as st
import pandas as pd
from datetime import datetime
import io
import json
import base64

# Pour utiliser GPT-4o (ou un modèle vision)
# Pensez à installer la bibliothèque : pip install openai
from openai import OpenAI

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Manifeste IA - Capture & Rapports",
    page_icon="🚢",
    layout="wide"
)

# --- BLOC DE SÉCURITÉ ET D'AUTHENTIFICATION ---
def check_password():
    """Vérifie le mot de passe avant de donner accès à l'application."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 Connexion Sécurisée")
        st.markdown("Veuillez saisir le mot de passe pour accéder à la plateforme de gestion du manifeste.")
        
        with st.form("login_form"):
            password_input = st.text_input("Mot de passe", type="password")
            submit_login = st.form_submit_button("Se connecter")
            
            if submit_login:
                if password_input == "Admin2026!":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Mot de passe incorrect. Accès refusé.")
        return False
    return True

# --- FONCTION D'EXTRACTION AUTOMATIQUE PAR IA ---
def extract_data_from_image(image_bytes, api_key):
    """Envoie l'image à l'IA pour extraire automatiquement les informations du document maritime."""
    client = OpenAI(api_key=api_key)
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    prompt = """
    Tu es un expert en traitement de documents maritimes (B/L, Manifestes, Avis d'arrivée).
    Analyse l'image fournie et extrais les informations suivantes au format JSON strict avec ces clés exactes :
    - "MONTHS": au format "AAAA-MM-01" (date du document ou mois en cours)
    - "Ligne": nom de la ligne maritime parmi ["MAERSK", "CMA CGM", "MSC", "COSCO", "ONE", "HAPAG-LLOYD", "AUTRE"]
    - "VESSEL": nom du navire
    - "LOADING PORT": port de chargement
    - "consignee": nom du destinataire / consignataire
    - "COMMODITIES": description des marchandises
    - "20_DV": nombre de conteneurs 20 pieds (entier)
    - "40_HC": nombre de conteneurs 40 pieds (entier)
    - "Trade": zone commerciale (ex: "20-MIDDLE EAST", "ASIA", etc.)
    - "Commodity-category": catégorie globale de marchandise

    Ne réponds QUE par l'objet JSON, sans aucun texte autour.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }
        ],
        max_tokens=500,
    )

    result_text = response.choices[0].message.content
    return json.loads(result_text)

if check_password():
    with st.sidebar:
        st.write("👤 **Session Active**")
        api_key = st.text_input("Clé API OpenAI (pour l'OCR automatique)", type="password")
        if st.button("🔴 Se déconnecter"):
            st.session_state.authenticated = False
            st.rerun()

    st.title("🚢 Manifeste IA - Numérisation & Gestion Maritime")
    st.markdown("Prenez en photo vos documents de transport pour enregistrer automatiquement vos données et générer vos rapports mensuels.")

    if "manifeste_df" not in st.session_state:
        st.session_state.manifeste_df = pd.DataFrame(columns=[
            "MONTHS", "Ligne", "VESSEL", "LOADING PORT", "consignee", 
            "COMMODITIES", "20'DV", "40'HC", "TEU's", "Trade", "Commodity-category"
        ])

    tab1, tab2, tab3 = st.tabs(["📷 Numériser un document", "📊 Rapports Mensuels", "📁 Base de Données / Export"])

    # --- ONGLET 1 : NUMÉRISATION AUTOMATIQUE ---
    with tab1:
        st.header("1. Capture et extraction automatique")
        
        col_cam, col_form = st.columns([1, 1])
        
        with col_cam:
            st.subheader("Prise de vue")
            camera_photo = st.camera_input("Prendre une photo du document")
            uploaded_file = st.file_uploader("Ou importer une image / scan", type=["png", "jpg", "jpeg"])
            
            target_file = camera_photo if camera_photo is not None else uploaded_file

        with col_form:
            st.subheader("Informations Extraintes par l'IA")
            
            extracted_data = {
                "MONTHS": datetime.now().strftime("%Y-%m-01"),
                "Ligne": "MAERSK",
                "VESSEL": "",
                "LOADING PORT": "",
                "consignee": "",
                "COMMODITIES": "",
                "20_DV": 0,
                "40_HC": 0,
                "Trade": "",
                "Commodity-category": ""
            }

            if target_file:
                if not api_key:
                    st.warning("⚠️ Veuillez entrer votre clé API OpenAI dans la barre latérale pour activer l'extraction automatique par photo.")
                else:
                    with st.spinner("🔍 Analyse automatique de la photo par l'IA en cours..."):
                        try:
                            image_bytes = target_file.getvalue()
                            extracted_data = extract_data_from_image(image_bytes, api_key)
                            st.success("✅ Extraction automatique réussie !")
                        except Exception as e:
                            st.error(f"Erreur lors de l'analyse automatique : {e}")

            # Formulaire pré-rempli automatiquement par l'IA
            with st.form("validation_form"):
                months = st.text_input("Mois (AAAA-MM-JJ)", value=extracted_data.get("MONTHS", datetime.now().strftime("%Y-%m-01")))
                
                lignes = ["MAERSK", "CMA CGM", "MSC", "COSCO", "ONE", "HAPAG-LLOYD", "AUTRE"]
                extracted_ligne = extracted_data.get("Ligne", "MAERSK")
                index_ligne = lignes.index(extracted_ligne) if extracted_ligne in lignes else 0
                ligne = st.selectbox("Ligne Maritime", lignes, index=index_ligne)
                
                vessel = st.text_input("Navire (VESSEL)", value=extracted_data.get("VESSEL", ""))
                loading_port = st.text_input("Port de Chargement (LOADING PORT)", value=extracted_data.get("LOADING PORT", ""))
                consignee = st.text_input("Consignataire (Consignee)", value=extracted_data.get("consignee", ""))
                commodities = st.text_input("Marchandises (COMMODITIES)", value=extracted_data.get("COMMODITIES", ""))
                
                c1, c2 = st.columns(2)
                with c1:
                    c_20 = st.number_input("Nombre Conteneurs 20'DV", min_value=0, value=int(extracted_data.get("20_DV", 0)), step=1)
                with c2:
                    c_40 = st.number_input("Nombre Conteneurs 40'HC", min_value=0, value=int(extracted_data.get("40_HC", 0)), step=1)
                
                calculated_teus = (c_20 * 1) + (c_40 * 2)
                st.info(f"**TEU's Calculés :** {calculated_teus}")
                
                trade = st.text_input("Trade", value=extracted_data.get("Trade", ""))
                category = st.text_input("Catégorie de Marchandise", value=extracted_data.get("Commodity-category", ""))
                
                btn_submit = st.form_submit_button("💾 Enregistrer dans le Manifeste")
                
                if btn_submit:
                    new_entry = {
                        "MONTHS": months,
                        "Ligne": ligne,
                        "VESSEL": vessel,
                        "LOADING PORT": loading_port,
                        "consignee": consignee,
                        "COMMODITIES": commodities,
                        "20'DV": c_20 if c_20 > 0 else None,
                        "40'HC": c_40 if c_40 > 0 else None,
                        "TEU's": calculated_teus,
                        "Trade": trade,
                        "Commodity-category": category
                    }
                    
                    st.session_state.manifeste_df = pd.concat(
                        [st.session_state.manifeste_df, pd.DataFrame([new_entry])], 
                        ignore_index=True
                    )
                    st.balloons()
                    st.success("L'enregistrement a été ajouté avec succès au manifeste !")

    # --- ONGLET 2 : RAPPORTS MENSUELS ---
    with tab2:
        st.header("📊 Rapports Mensuels & Statistiques")
        
        df = st.session_state.manifeste_df
        
        if df.empty:
            st.warning("Aucune donnée disponible. Veuillez enregistrer des conteneurs via l'onglet 'Numériser un document'.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total TEU's", int(df["TEU's"].sum()))
            col2.metric("Total 20'DV", int(df["20'DV"].fillna(0).sum()))
            col3.metric("Total 40'HC", int(df["40'HC"].fillna(0).sum()))
            col4.metric("Nombre d'expéditions", len(df))
            
            st.markdown("---")
            
            g1, g2 = st.columns(2)
            
            with g1:
                st.subheader("Volume TEUs par Ligne Maritime")
                trade_chart = df.groupby("Ligne")["TEU's"].sum()
                st.bar_chart(trade_chart)
                
            with g2:
                st.subheader("Répartition des TEUs par Trade")
                trade_summary = df.groupby("Trade")["TEU's"].sum()
                st.pie_chart(trade_summary)
                
            st.subheader("Top Consignataires (Consignees)")
            top_consignees = df.groupby("consignee")["TEU's"].sum().reset_index().sort_values(by="TEU's", ascending=False)
            st.dataframe(top_consignees, use_container_width=True)

    # --- ONGLET 3 : EXPORT EXCEL ---
    with tab3:
        st.header("📁 Base de Données du Manifeste")
        
        st.dataframe(st.session_state.manifeste_df, use_container_width=True)
        
        if not st.session_state.manifeste_df.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.manifeste_df.to_excel(writer, sheet_name='Manifest', index=False)
            processed_data = output.getvalue()
            
            st.download_button(
                label="📥 Télécharger le Manifeste en Excel (.xlsx)",
                data=processed_data,
                file_name=f"MANIFESTE_EXPORT_{datetime.now().strftime('%Y_%m_%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )