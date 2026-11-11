import streamlit as st
from supabase import create_client, Client
from streamlit_drawable_canvas import st_canvas
import base64
from PIL import Image
import numpy as np
import io

st.set_page_config(page_title="SGA - Flujo de Contratación Digital", layout="wide")

# 1. Conexión a Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["connections"]["supabase"]["SUPABASE_URL"].strip()
    key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"].strip()
    return create_client(url, key)

supabase: Client = init_connection()

st.title("📄 Sistema de Contratación Digital (Workflow)")
st.caption("Módulo de Firmas y Cadena de Aprobación Documental")

tab_empleado, tab_empresa, tab_historial = st.tabs([
    "✍️ 1. Firma Empleado", 
    "🏢 2. Aprobación Empresa (GH)", 
    "📊 Historial de Contratos"
])

# ==========================================
# PESTAÑA 1: FIRMA DEL EMPLEADO
# ==========================================
with tab_empleado:
    st.subheader("Paso 1: Diligenciamiento y Firma del Trabajador")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        emp_nombre = st.text_input("Nombre Completo del Trabajador", key="e_nombre")
        emp_cedula = st.text_input("Cédula de Ciudadanía", key="e_cedula")
    with col_d2:
        emp_cargo = st.text_input("Cargo a Desempeñar", value="Auxiliar Operativo", key="e_cargo")
        emp_salario = st.number_input("Salario Mensual ($)", value=1300000, step=50000, key="e_salario")

    st.markdown("---")
    st.markdown("#### Vista Previa del Documento Legal")
    
    texto_contrato = f"""
    <div style="background-color: #ffffff; color: #111111; padding: 30px; border-radius: 8px; border: 1px solid #cccccc; font-family: 'Times New Roman', serif; line-height: 1.6;">
        <h3 style="text-align: center; margin-bottom: 20px;">CONTRATO INDIVIDUAL DE TRABAJO A TÉRMINO INDEFINIDO</h3>
        <p>Conste por el presente documento que entre los suscritos a saber: <b>EMPRESA DEMO S.A.S.</b> y por la otra parte el ciudadano <b>{emp_nombre.upper() if emp_nombre else '_______________________'}</b>, identificado con C.C. N° <b>{emp_cedula if emp_cedula else '_______________________'}</b>, se ha celebrado el presente Contrato de Trabajo sujeto a las siguientes cláusulas:</p>
        <p><b>PRIMERA. OBJETO:</b> EL TRABAJADOR se obliga a prestar sus servicios personales como <b>{emp_cargo.upper()}</b>, ejecutando las tareas asignadas con diligencia y efectividad.</p>
        <p><b>SEGUNDA. REMUNERACIÓN:</b> LA EMPRESA pagará al TRABAJADOR una remuneración mensual de <b>${emp_salario:,.2f} COP</b>.</p>
        <p><b>TERCERA. DURACIÓN:</b> El presente contrato se celebra a término indefinido a partir de la fecha de su firma digital.</p>
    </div>
    """
    st.markdown(texto_contrato, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.form("form_firma_empleado"):
        st.write("##### Firma de Conformidad del Trabajador")
        st.caption("Traza tu firma en el recuadro a continuación para aceptar los términos del contrato:")
        
        canvas_emp = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#F5F5F5",
            height=160,
            width=400,
            drawing_mode="freedraw",
            key="canvas_emp_paso1",
        )
        
        btn_enviar_empleado = st.form_submit_button("🚀 Firmar y Enviar a Gestión Humana", use_container_width=True)

    if btn_enviar_empleado:
        if not emp_nombre or not emp_cedula:
            st.error("Por favor completa tu Nombre y Cédula antes de enviar.")
        else:
            firma_b64 = ""
            if canvas_emp.image_data is not None:
                try:
                    # Convertir matriz de datos del canvas a imagen PNG en Base64 de forma robusta
                    input_array = canvas_emp.image_data
                    img = Image.fromarray(input_array.astype('uint8'), mode="RGBA")
                    buffered = io.BytesIO()
                    img.save(buffered, format="PNG")
                    firma_b64 = base64.b64encode(buffered.getvalue()).decode()
                except Exception as e:
                    st.error(f"Error procesando la firma: {e}")

            datos_contrato = {
                "nombre_empleado": emp_nombre,
                "cedula_empleado": emp_cedula,
                "cargo": emp_cargo,
                "salario": emp_salario,
                "estado": "Pendiente_Empresa",
                "firma_empleado_b64": firma_b64,
                "fecha_firma_empleado": "now()"
            }
            res = supabase.table("contratos_laborales").insert(datos_contrato).execute()
            if res.data:
                nuevo_id = res.data[0]['id']
                st.success(f"✅ ¡Contrato #{nuevo_id} firmado con éxito por el trabajador! Ha pasado al turno de aprobación de la Empresa.")
            else:
                st.error("Hubo un error al guardar en la base de datos.")

# ==========================================
# PESTAÑA 2: APROBACIÓN DE LA EMPRESA
# ==========================================
with tab_empresa:
    st.subheader("Paso 2: Aprobación y Firma Representante Legal (GH)")
    
    try:
        pendientes = supabase.table("contratos_laborales").select("*").eq("estado", "Pendiente_Empresa").execute().data
    except Exception as e:
        pendientes = []

    if not pendientes:
        st.info("No hay contratos pendientes por firmar por parte de la empresa en este momento.")
    else:
        opciones_contratos = {f"Contrato #{c['id']} - {c['nombre_empleado']} ({c['cargo']})": c for c in pendientes}
        seleccion = st.selectbox("Selecciona el contrato a revisar:", list(opciones_contratos.keys()))
        contrato_actual = opciones_contratos[seleccion]

        st.markdown("---")
        
        # Mostrar la firma del empleado si existe en Base64
        if contrato_actual.get("firma_empleado_b64"):
            img_firma_emp_html = f'<img src="data:image/png;base64,{contrato_actual["firma_empleado_b64"]}" width="180" style="border:1px solid #ccc; background:#fff;"/>'
        else:
            img_firma_emp_html = "<i>[Firma no registrada]</i>"
        
        doc_con_firma_emp = f"""
        <div style="background-color: #ffffff; color: #111111; padding: 30px; border-radius: 8px; border: 1px solid #cccccc; font-family: 'Times New Roman', serif; line-height: 1.6;">
            <h3 style="text-align: center; margin-bottom: 20px;">CONTRATO INDIVIDUAL DE TRABAJO</h3>
            <p>Trabajador: <b>{contrato_actual['nombre_empleado']}</b> | C.C.: <b>{contrato_actual['cedula_empleado']}</b></p>
            <p>Cargo: <b>{contrato_actual['cargo']}</b> | Salario: <b>${contrato_actual['salario']:,.2f} COP</b></p>
            <hr>
            <table style="width:100%; border:none; margin-top:30px;">
                <tr>
                    <td style="width:50%; text-align:center;">
                        {img_firma_emp_html}<br>
                        ____________________________________<br>
                        <b>{contrato_actual['nombre_empleado']}</b><br>
                        C.C. {contrato_actual['cedula_empleado']}<br>
                        <i>Firmado el trabajador (Fase 1)</i>
                    </td>
                    <td style="width:50%; text-align:center; vertical-align:bottom;">
                        <span style="color:#888888;">[ Pendiente Firma Representante Legal ]</span>
                    </td>
                </tr>
            </table>
        </div>
        """
        st.markdown(doc_con_firma_emp, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("form_firma_empresa"):
            st.write("##### Datos de Autorización de la Empresa")
            col_gh1, col_gh2 = st.columns(2)
            with col_gh1:
                rep_nombre = st.text_input("Nombre Representante Legal", value="RAUL JAIMES", key="rep_n")
            with col_gh2:
                rep_cedula = st.text_input("Cédula Representante", value="1018400000", key="rep_c")
                
            st.caption("Traza tu firma de aprobación institucional:")
            
            canvas_rep = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=2,
                stroke_color="#000000",
                background_color="#F5F5F5",
                height=160,
                width=400,
                drawing_mode="freedraw",
                key="canvas_rep_paso2",
            )
            
            btn_finalizar = st.form_submit_button("✅ Aprobar y Cerrar Contrato", use_container_width=True)

        if btn_finalizar:
            firma_rep_b64 = ""
            if canvas_rep.image_data is not None:
                try:
                    input_array_r = canvas_rep.image_data
                    img_r = Image.fromarray(input_array_r.astype('uint8'), mode="RGBA")
                    buffered_r = io.BytesIO()
                    img_r.save(buffered_r, format="PNG")
                    firma_rep_b64 = base64.b64encode(buffered_r.getvalue()).decode()
                except Exception as e:
                    st.error(f"Error procesando la firma de la empresa: {e}")

            supabase.table("contratos_laborales").update({
                "estado": "Completado",
                "nombre_representante": rep_nombre,
                "cedula_representante": rep_cedula,
                "firma_empresa_b64": firma_rep_b64,
                "fecha_firma_empresa": "now()"
            }).eq("id", contrato_actual['id']).execute()

            st.success(f"🎉 ¡El Contrato #{contrato_actual['id']} ha completado su flujo de firmas y ha sido cerrado exitosamente!")
            st.rerun()

# ==========================================
# PESTAÑA 3: HISTORIAL Y ESTADO DEL WORKFLOW
# ==========================================
with tab_historial:
    st.subheader("Historial y Estado de Todos los Contratos")
    try:
        todos = supabase.table("contratos_laborales").select("*").order("id", desc=True).execute().data
        if todos:
            for item in todos:
                color_badge = "🟢" if item['estado'] == 'Completado' else "🟡"
                with st.expander(f"{color_badge} Contrato #{item['id']} - {item['nombre_empleado']} | Estado: {item['estado']}"):
                    st.write(f"**Cargo:** {item['cargo']} | **Salario:** ${item['salario']:,.2f}")
                    st.write(f"**Firma Empleado:** {'✅ Registrada' if item.get('firma_empleado_b64') else '❌ Pendiente'}")
                    st.write(f"**Firma Empresa:** {'✅ Registrada' if item.get('firma_empresa_b64') else '❌ Pendiente'}")
        else:
            st.info("Aún no se han generado contratos.")
    except Exception as e:
        st.error(f"Error cargando historial: {e}")
