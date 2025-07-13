# src/generation/doc_generator.py
from docxtpl import DocxTemplate
import os
import datetime # Puede que no sea necesario si la fecha ya está en el context_dict

def fill_template_docxtpl(template_path, output_path, context_dict):
    """
    Rellena una plantilla de Word (.docx) usando docxtpl (motor Jinja2).
    
    Args:
        template_path (str): Ruta al archivo de plantilla .docx.
        output_path (str): Ruta donde se guardará el documento generado.
        context_dict (dict): Diccionario con los datos a renderizar en la plantilla.
                             Las claves deben coincidir con las variables usadas en 
                             la plantilla Jinja2 (lo que va dentro de {{ }}).
    """
    try:
        if not os.path.exists(template_path):
            print(f"Error: Plantilla no encontrada en {template_path}")
            return False

        doc = DocxTemplate(template_path)
        
        # El context_dict ya debería tener todos los datos necesarios.
        # Los valores None se renderizarán como strings vacíos por defecto en Jinja2,
        # lo cual suele ser el comportamiento deseado.
        # Si necesitas un valor específico para None, puedes manejarlo al crear context_dict
        # o usar filtros Jinja2 en la plantilla: {{ mi_variable | default('') }}

        doc.render(context_dict)
        
        output_dir = os.path.dirname(output_path)
        # Asegurarse de que el directorio de salida exista
        if output_dir and not os.path.exists(output_dir): # Solo crear si output_dir no es vacío (ruta relativa al dir actual)
            os.makedirs(output_dir)
        
        doc.save(output_path)
        print(f"Documento (docxtpl) generado con éxito: {output_path}")
        return True
    except Exception as e:
        print(f"Error al generar documento con docxtpl ({type(e).__name__}): {e}")
        import traceback
        traceback.print_exc() # Imprime el traceback completo para depuración
        return False

