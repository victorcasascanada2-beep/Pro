import base64


def imagen_a_base64(ruta_imagen):
    """Convierte el logo transparente en código para el HTML"""
    try:
        with open(ruta_imagen, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error cargando logo: {e}")
        return ""


def generar_informe_html(marca, modelo, informe_ia, fotos_bytes, gps_coords):
    # 1. Cargamos el logo transparente
    logo_b64 = imagen_a_base64("Transparente.png")

    # 2. Procesamos las fotos del tractor
    fotos_html = ""
    for b in fotos_bytes:
        b64 = base64.b64encode(b).decode()
        fotos_html += f'<img src="data:image/jpeg;base64,{b64}" style="width:45%; margin:5px; border-radius:8px;">'

    # 3. El Template con tu estilo John Deere
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; color: #333; background-color: #f4f4f4; }}
            .container {{ background-color: white; max-width: 850px; margin: auto; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
            .logo-header {{ text-align: center; margin-bottom: 20px; }}
            .logo-header img {{ max-width: 250px; }}
            .header {{ text-align: center; border-bottom: 5px solid #367C2B; padding-bottom: 20px; margin-bottom: 30px; }}
            .header h1 {{ color: #367C2B; margin: 0; font-size: 28px; text-transform: uppercase; }}
            .header .sub {{ color: #FFDE00; font-weight: bold; background: #367C2B; display: inline-block; padding: 2px 10px; border-radius: 4px; margin-top: 5px; }}
            .content {{ line-height: 1.6; font-size: 15px; color: #444; white-space: pre-wrap; }}
            .gallery {{ text-align: center; margin-top: 30px; padding: 20px; border: 1px solid #eee; border-radius: 10px; }}
            .footer {{ margin-top: 50px; text-align: center; border-top: 1px solid #eee; padding-top: 20px; color: #888; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo-header">
                <img src="data:image/png;base64,{logo_b64}">
            </div>
            <div class="header">
                <h1>Informe de Tasación Profesional</h1>
                <div class="sub">{marca.upper()} {modelo.upper()}</div>
            </div>
            <div class="content">{informe_ia}</div>
            <div class="gallery">
                <h3>Registro Fotográfico</h3>
                {fotos_html}
            </div>
            <div class="footer">
                <p>Agrícola Noroeste - Departamento de Ocasión</p>
                <p style="font-family: monospace; font-size: 10px;">Ref: {gps_coords}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template