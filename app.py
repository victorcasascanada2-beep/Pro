import streamlit as st
import os
import io
import re
from datetime import datetime
from PIL import Image
# Importaciones de tus módulos locales
import ia_engine
from estilos    import aplicar_estilo_john_deere
import html_generator
import google_drive_manager
import location_manager
from streamlit_js_eval import get_geolocation

# ==========================================
# 1. CONFIGURACIÓN Y ESTADO
# ==========================================
st.set_page_config(page_title="Tasador Pro", layout="centered", page_icon="🚜")
if os.path.exists("Transparente.png"): st.image("Transparente.png", width=320)

aplicar_estilo_john_deere()

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "ref_gps_b64" not in st.session_state: st.session_state["ref_gps_b64"] = "PENDIENTE"

# CAPTURA ÚNICA DE GPS (Sin el prefijo erróneo)
loc_data = get_geolocation(component_key="gps_v1_noroeste")
if loc_data and 'coords' in loc_data:
    lat, lon = loc_data['coords']['latitude'], loc_data['coords']['longitude']
    st.session_state["ref_gps_b64"] = location_manager.codificar_coordenadas(lat, lon)




# ==========================================
# 2. FUNCIONES DE APOYO
# ==========================================

def extraer_precio_ia(texto, clave):
    patron = rf"{clave}.*?:\s*\*?\*?([\d\.]+)"
    match = re.search(patron, texto, re.IGNORECASE)
    if match:
        num_limpio = match.group(1).replace(".", "")
        try:
            return float(num_limpio)
        except:
            return None
    return None


def calcular_extras(cv, pala, anclajes, trip, tdf, aire, autoguiado, v_g, v_p):
    total = 0.0
    cv_f = float(cv) if cv else 0.0
    if pala: total += (41.6 * cv_f)
    if anclajes: total += (16.6 * cv_f)
    if tdf:
        total += (25.0 * cv_f)
    elif trip:
        total += (20.8 * cv_f)
    if aire: total += 1000.0
    if autoguiado: total += 4000.0  # <--- Nuevo extra: Autoguiado
    penal_g = (1.0 - (v_g / 100.0)) * 50.0 * cv_f
    penal_p = (1.0 - (v_p / 100.0)) * 20.0 * cv_f
    return total - (penal_g + penal_p)


# ==========================================
# 3. CONTROL DE ACCESO (VERSIÓN ANTI-HISTORIAL)
# ==========================================
# Intenta pillar los secretos de Streamlit, si no, busca en variables de entorno de Cloud Run
if "google" in st.secrets:
    CREDS = dict(st.secrets["google"])
elif os.environ.get("google"):
    import json
    CREDS = json.loads(os.environ.get("google"))
else:
    CREDS = None

# 1. Comprobación de URL (Para que no tengan que escribir nada si ya entraron una vez)
agente_url = st.query_params.get("agente")

if not st.session_state.get("logged_in") and agente_url:
    v_lista = google_drive_manager.leer_vendedores(CREDS)
    if agente_url.lower() in [v.lower() for v in v_lista]:
        st.session_state.vendedor = [v for v in v_lista if v.lower() == agente_url.lower()][0]
        st.session_state.logged_in = True

if not st.session_state.get("logged_in"):
    #st.markdown('<div class="hero"><h1>Tasador Pro</h1><p>Acceso Agentes</p></div>', unsafe_allow_html=True)
    st.markdown("""
            <div style="background-color: #367C2B; padding: 40px; border-radius: 0px; border-left: 10px solid #FFDE00; margin-bottom: 20px;">
                <h1 style="color: white; font-family: 'Inter', sans-serif; margin: 0; font-size: 3em;">Tasador Pro</h1>
                <p style="color: white; font-family: 'Inter', sans-serif; font-size: 1.2em; opacity: 0.9;">Acceso Agentes</p>
            </div>
        """, unsafe_allow_html=True)
    v_lista = google_drive_manager.leer_vendedores(CREDS)

    # TRUCO 1: Cambiamos la 'key' a algo aleatorio cada vez que quieras resetearlo
    # TRUCO 2: type="password" ocultará el texto y hará que el navegador no lo trate como un nombre de usuario común
    v_input = st.text_input(
        "Introduce tu código o nombre de acceso:",
        type="password",
        key="identificador_agente_v4",  # Si sigue saliendo la lista, cambia este v4 por v5
        help="El texto está oculto por privacidad."
    ).strip()

    if st.button("ENTRAR"):
        if v_input.lower() in [v.lower() for v in v_lista]:
            nombre_oficial = [v for v in v_lista if v.lower() == v_input.lower()][0]
            st.session_state.vendedor = nombre_oficial
            st.session_state.logged_in = True

            # Guardamos en la URL para que no tenga que volver a escribirlo en este móvil
            st.query_params["agente"] = nombre_oficial
            st.rerun()
        else:
            st.error("⚠️ Acceso denegado.")
    st.stop()

# Botón para cerrar sesión (opcional, por si otro agente usa el mismo móvil)


# ==========================================
# 4. FORMULARIO Y PROCESO
# ==========================================
st.markdown(f'<div class="hero"><h1>Tasador Pro</h1><p>Agente: {st.session_state.vendedor}</p></div>',
            unsafe_allow_html=True)



if "result" not in st.session_state:
    with st.form("main_form"):
        st.markdown("### 📋 Datos del Tractor") # Esto saldrá como banner verde JD
        c1, c2 = st.columns(2)
        marca, modelo = c1.text_input("Marca", "John Deere"), c2.text_input("Modelo", "6175m")
        anio, horas = c1.text_input("Año", "2018"), c2.text_input("Horas", "9988")
        cv, obs = st.text_input("Potencia (CV)"), st.text_area("Observaciones")

        st.markdown("### 🛠️ Extras y Neumáticos") # Otro banner verde JD
        e1, e2, e3 = st.columns(3)
        pala, anclajes = e1.checkbox("Pala"), e1.checkbox("Anclajes")
        trip, tdf = e2.checkbox("Tripuntal"), e2.checkbox("TDF Del.")
        aire = e3.checkbox("Frenos Aire")
        autoguiado = e3.checkbox("Autoguiado")  # <--- Añade esto aquí
        v_g, v_p = st.slider("Traseros %", 0, 100, 80), st.slider("Delanteros %", 0, 100, 80)

        fotos = st.file_uploader("Fotos (mín. 4)", accept_multiple_files=True)
        enviar = st.form_submit_button("🚀 REALIZAR TASACIÓN")
        
        # ==========================================
        # 4. PROCESO CON CHIVATOS AGUAS ARRIBA
        # ==========================================
        if enviar:
            print("\n--- INICIO DE DEPURACIÓN AGUAS ARRIBA ---")
            if not modelo or len(fotos or []) < 4:
                st.error("⚠️ Faltan datos críticos o fotos.")
                print("DEBUG 0: Validación fallida (falta modelo o fotos)")
            else:
                with st.spinner("Analizando y guardando..."):
                    try:
                        client = ia_engine.conectar_vertex(CREDS)

                        fotos_raw = [{"name": f.name, "data": f.getvalue(), "type": f.type} for f in fotos]
                        inf = ia_engine.realizar_peritaje(client, marca, modelo, anio, horas, obs, fotos_raw)
                        # --- AQUÍ METEMOS LA LIMPIEZA DEL TRUÑO ---
                        inf_limpio = inf
                        inf_limpio = inf_limpio.replace("BLOQUE: RESUMEN_FOTOS",
                                                        "<h4 style='color:#367C2B;'>📸 Resumen de Inspección Visual</h4>")
                        inf_limpio = inf_limpio.replace("BLOQUE: RESULTADO_FINAL",
                                                        "<h4 style='color:#367C2B;'>💰 Conclusión de Valoración</h4>")
                        inf_limpio = inf_limpio.replace("BLOQUE: COMPARABLES_TABLA",
                                                        "<h4 style='color:#367C2B;'>📊 Referencias de Mercado</h4>")
                        inf_limpio = inf_limpio.replace(" - Foto", "<br><br><b>Foto</b>")
                        inf_limpio = inf_limpio.replace("VALOR_BASE:", "<br><b>Valor Base:</b>")
                        inf_limpio = inf_limpio.replace("VALOR_MERCADO:", "<br><b>Valor Mercado:</b>")
                        # ------------------------------------------

                        # 1. Precios (Usamos el 'inf' original para extraer números, es más seguro)
                        vm = extraer_precio_ia(inf, "VALOR_MERCADO")
                        vv = extraer_precio_ia(inf, "PRECIO_VENTA")
                        vc = extraer_precio_ia(inf, "PRECIO_COMPRA")
                        cv_ia = extraer_precio_ia(inf, "POTENCIA_TECNICA")
                        # 2. Potencia
                        cv_final = 0.0
                        if cv and cv.strip() != "":
                            try:
                                cv_final = float(cv)
                            except:
                                cv_final = 0.0
                        else:
                            cv_ia = extraer_precio_ia(inf, "POTENCIA_TECNICA")
                            cv_final = cv_ia if cv_ia else 0.0
                        # IMPORTANTE: Asegúrate de que todas estas variables existan arriba en el form
                        ajuste_inf = calcular_extras(cv_final, pala, anclajes, trip, tdf, aire, autoguiado, v_g, v_p)

                        if vm:
                            gps_coords = st.session_state.get("ref_gps_b64", "No disponible")

                            # Fila Excel (10 campos)
                            fila = [
                                st.session_state.vendedor,
                                datetime.now().strftime("%d/%m/%Y %H:%M"),
                                marca, modelo, horas, cv_final, vm, vc, vv, gps_coords
                            ]

                            # LLAMADA AL EXCEL
                            resultado_excel = google_drive_manager.registrar_en_historial_excel(CREDS, fila)

                            # HTML y Drive
                            html_out = html_generator.generar_informe_html(marca, modelo, inf,
                                                                           [f.getvalue() for f in fotos], gps_coords)
                            google_drive_manager.subir_informe(CREDS, f"Tasacion_{marca}_{modelo}.html", html_out,
                                                               st.session_state.vendedor)

                            st.session_state.result = {
                                "inf": inf_limpio,  # <--- Guardamos la versión bonita
                                "vm": vm, "vv": vv, "vc": vc,
                                "ajuste": ajuste_inf, "mod": modelo, "html": html_out
                            }
                            st.rerun()
                        else:
                            st.error("La IA no pudo determinar un precio base.")

                    except Exception as e:
                        # El chivato más importante: ¿Qué rompió el proceso?
                        print(f"DEBUG ERROR CRÍTICO: {str(e)}")
                        st.error(f"Se ha producido un error técnico: {e}")

            print("--- FIN DE DEPURACIÓN ---\n")

# ==========================================
# 5. RESULTADOS
# ==========================================
else:
    res = st.session_state.result
    # Banner de éxito corporativo
    st.markdown(f"""
            <div style="background-color: #367C2B; padding: 20px; border-radius: 10px; border-left: 10px solid #FFDE00; margin-bottom: 25px;">
                <h2 style="color: white; margin: 0;">✅ Tasación Finalizada</h2>
                <p style="color: white; opacity: 0.8; margin: 0;">Informe generado correctamente para {res['mod']}</p>
            </div>
        """, unsafe_allow_html=True)

    # Métricas estilizadas
    st.markdown('<div style="background-color:white; padding:20px; border-radius:15px; border:1px solid #d1d8d0;">',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("MERCADO", f"{int(res['vm']):,} €".replace(",", "."))
    c2.metric("VENTA", f"{int(res['vv']):,} €".replace(",", "."))
    c3.metric("COMPRA", f"{int(res['vc']):,} €".replace(",", "."))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # El informe (que ya guardamos con HTML arriba)
    st.markdown(f'<div class="ia-report">{res["inf"]}</div>', unsafe_allow_html=True)

    # Botones
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("👁️ DESCARGAR INFORME", res["html"], f"Informe_{res['mod']}.html", "text/html",
                           use_container_width=True)
    with col2:
        if st.button("🔄 NUEVA TASACIÓN", use_container_width=True):
            del st.session_state.result
        st.rerun()
