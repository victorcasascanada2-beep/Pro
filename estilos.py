def aplicar_estilo_john_deere():
    import streamlit as st

    # Paleta de colores JD
    VERDE_SUAVE = "#f1f4f0"
    VERDE_JD = "#367C2B"
    AMARILLO_JD = "#FFDE00"
    VERDE_OSCURO = "#22491D"

    st.markdown(f"""
        <style>
            /* 1. ESTO ES LO QUE TE FALTA: El fondo de toda la página */
            [data-testid="stAppViewContainer"] {{
                background-color: {VERDE_SUAVE};
                background-image: radial-gradient(#d1d8d0 0.5px, transparent 0.5px);
                background-size: 20px 20px; /* Puntitos tipo papel técnico */
            }}

            /* 2. LIMPIEZA DE CABECERAS */
            [data-testid="stHeader"], footer {{
                visibility: hidden;
            }}

            /* 3. EL CONTENEDOR PRINCIPAL (Donde está el formulario) */
            .main .block-container {{
                padding-top: 2rem !important;
                background-color: transparent;
            }}

            /* 4. EL LOGO CENTRADO (Clase que definimos antes) */
            .logo-container {{
                display: flex;
                justify-content: center;
                width: 100%;
                margin-bottom: 20px;
            }}
            .logo-container img {{
                width: 320px !important;
            }}

            /* 5. EL FORMULARIO (Blanco para que resalte sobre el verde suave) */
            [data-testid="stForm"] {{
                background-color: #ffffff !important;
                border-radius: 15px !important;
                border: 1px solid #e0e0e0 !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
                padding: 30px !important;
            }}

            /* 6. EL BOTÓN JD */
            div.stButton > button {{
                background: linear-gradient(180deg, {VERDE_JD} 0%, {VERDE_OSCURO} 100%) !important;
                color: {AMARILLO_JD} !important;
                border-radius: 25px !important;
                font-weight: bold !important;
                border: none !important;
                width: 100%;
            }}


            /* Convertir subheaders en Banners Verdes */
            .stMarkdown h2, .stMarkdown h3 {{
                background-color: {VERDE_JD};
                color: white !important;
                padding: 15px;
                border-left: 10px solid {AMARILLO_JD};
                border-radius: 0px;
                font-family: 'Inter', sans-serif;
            }}
            /* --- ESTILOS DE RESULTADOS --- */
        
        /* Tarjetas de Métricas (Precios) */
        [data-testid="stMetricValue"] {{
            color: {VERDE_JD} !important;
            font-size: 2rem !important;
            font-weight: bold !important;
        }}
        
        [data-testid="stMetricLabel"] {{
            color: #555555 !important;
            font-weight: bold !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
        }}

        /* El contenedor del informe de IA */
        .ia-report {{
            background-color: white !important;
            padding: 25px !important;
            border-radius: 15px !important;
            border: 1px solid #d1d8d0 !important;
            border-top: 8px solid {VERDE_JD} !important; /* Ceja verde JD */
            box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
            margin-bottom: 20px !important;
            font-family: 'Inter', sans-serif !important;
        }}
        </style>
    """, unsafe_allow_html=True)