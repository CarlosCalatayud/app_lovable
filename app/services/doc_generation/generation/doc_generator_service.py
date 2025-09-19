import logging
import os, io, zipfile
import json
from typing import Dict, Any, List, Type
from docxtpl import DocxTemplate
from pydantic import ValidationError, BaseModel
from importlib import import_module

# --- Configuración de rutas ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_ROOT = os.path.join(BASE_DIR, '..', 'templates')
CONFIG_ROOT = os.path.join(BASE_DIR, '..', 'config')
CALCULATORS_ROOT = os.path.join(BASE_DIR, 'calculators')
DOCUMENT_SCHEMAS_ROOT = os.path.join(CONFIG_ROOT, 'document_schemas')

# --- Cargar definiciones de documentos ---
DOCUMENT_DEFINITIONS_PATH = os.path.join(CONFIG_ROOT, 'doc_definitions.json')
try:
    with open(DOCUMENT_DEFINITIONS_PATH, 'r', encoding='utf-8') as f:
        DOCUMENT_DEFINITIONS = json.load(f)
except FileNotFoundError:
    logging.error(f"Archivo de definiciones de documentos no encontrado: {DOCUMENT_DEFINITIONS_PATH}")
    DOCUMENT_DEFINITIONS = {}
except json.JSONDecodeError:
    logging.error(f"Error al parsear el archivo JSON de definiciones de documentos: {DOCUMENT_DEFINITIONS_PATH}")
    DOCUMENT_DEFINITIONS = {}

# --- Cargar módulos de cálculo dinámicamente ---
CALCULATOR_MODULES: Dict[str, Any] = {}
def load_calculators():
    # Asegúrate de que el directorio de calculators sea un paquete Python
    # Esto significa que debe tener un __init__.py
    for filename in os.listdir(CALCULATORS_ROOT):
        if filename.endswith('_calculations.py') and not filename.startswith('__'):
            module_name = filename[:-3] # Eliminar .py
            try:
                # Importar el módulo. Usamos el paquete absoluto para importlib
                # El nombre del paquete base para importlib.import_module debe coincidir con la estructura de directorios
                # Si src es el root, entonces "src.generation.calculators"
                module = import_module(f"generation.calculators.{module_name}")
                # Almacenamos el módulo bajo un nombre más corto (ej: 'common', 'structural')
                CALCULATOR_MODULES[module_name.replace('_calculations', '')] = module 
                logging.info(f"Cargado módulo de cálculo: {module_name}")
            except Exception as e:
                logging.error(f"Error al cargar el módulo de cálculo {module_name}: {e}")
load_calculators()


# --- Función auxiliar para cargar esquemas Pydantic ---
def load_document_schema(schema_name: str) -> Type[BaseModel]:
    """Carga un modelo Pydantic de esquema de documento por su nombre."""
    try:
        # Los esquemas de documentos específicos están en src/config/document_schemas/
        module_path = f"app.services.doc_generation.config.document_schemas.{schema_name}"
        # Intentar importar el módulo.
        # Por convención, el modelo dentro del archivo se llamará de una forma predecible.
        # Ej: para "andalucia_doc_informe", el modelo será "AndaluciaDocInformeContext"
        schema_module = import_module(module_path)
        # Convertir nombre snake_case a CamelCase para el nombre de la clase
        class_name = "".join(word.capitalize() for word in schema_name.split('_')) + "Context"
        
        schema_model = getattr(schema_module, class_name)
        if not issubclass(schema_model, BaseModel):
            raise TypeError(f"El objeto '{class_name}' en '{module_path}' no es un modelo Pydantic.")
        return schema_model
    except (ImportError, AttributeError) as e:
        logging.error(f"No se pudo cargar el esquema Pydantic '{schema_name}': {e}")
        raise ValueError(f"Esquema de documento '{schema_name}' no encontrado o inválido.")


def get_available_docs_for_community(community_slug: str) -> List[Dict[str, str]]:
    """
    Devuelve los documentos disponibles para una comunidad basándose en DOCUMENT_DEFINITIONS.
    """
    community_docs = DOCUMENT_DEFINITIONS.get(community_slug)
    if not community_docs:
        logging.warning(f"No se encontraron definiciones de documentos para la comunidad: {community_slug}")
        return []

    docs = []
    for doc_id, doc_info in sorted(community_docs.items()):
        docs.append({
            "id": doc_id,
            "name": doc_info.get("name", os.path.splitext(doc_id)[0].replace("_", " ").title())
        })
    return docs

def generate_document_from_template(template_full_path: str, context: Dict[str, Any]) -> bytes:
    """
    Genera un único documento .docx en memoria a partir de una plantilla y un contexto.
    Devuelve los bytes del archivo. Lanza FileNotFoundError si la plantilla no existe.
    """
    if not os.path.exists(template_full_path):
        raise FileNotFoundError(f"La plantilla no fue encontrada en la ruta: {template_full_path}")

    file_stream = io.BytesIO()
    doc = DocxTemplate(template_full_path)
    
    try:
        doc.render(context)
    except Exception as e:
        logging.error(f"Error al renderizar la plantilla {template_full_path} con el contexto proporcionado: {e}")
        raise ValueError(f"Error al generar el documento: {e}")

    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream.getvalue()

def prepare_document_context(
    raw_context: Dict[str, Any], 
    community_slug: str, 
    document_id: str
) -> Dict[str, Any]:
    """
    Valida el contexto de entrada y ejecuta los cálculos necesarios
    para un documento específico de una comunidad.
    """
    # 1. Obtener la definición del documento
    community_docs = DOCUMENT_DEFINITIONS.get(community_slug)
    if not community_docs:
        raise ValueError(f"Comunidad '{community_slug}' no tiene documentos definidos.")
    
    doc_info = community_docs.get(document_id)
    if not doc_info:
        raise ValueError(f"Documento '{document_id}' no definido para la comunidad '{community_slug}'.")

    context_schema_name = doc_info.get('context_schema')
    required_calcs_groups = doc_info.get('required_calcs', [])

    if not context_schema_name:
        logging.warning(f"Documento '{document_id}' no tiene un esquema de contexto definido. Se usará el modelo base si existe.")
        SpecificDocContext = import_module("generation.models").ProjectContext # Fallback a ProjectContext
    else:
        try:
            SpecificDocContext = load_document_schema(context_schema_name)
        except ValueError as e:
            logging.error(f"No se pudo cargar el esquema para el documento {document_id}: {e}")
            raise e

    # 2. Validar y normalizar el contexto de entrada usando Pydantic
    try:
        # Creamos una instancia del modelo Pydantic
        validated_context = SpecificDocContext(**raw_context)
        # Convertimos el modelo Pydantic de nuevo a un diccionario para que docxtpl pueda usarlo
        ctx_dict = validated_context.model_dump() # Usar .dict() en Pydantic v1
        logging.info(
            f"Contexto validado para {document_id}: "
            f"{json.dumps(ctx_dict, indent=2, default=str)}"
        )
    except ValidationError as e:
        logging.error(
            f"Errores de validación para {document_id}: "
            f"{json.dumps(e.errors(), indent=2, default=str)}"
        )

        logging.error(f"Errores de validación para {document_id}: {json.dumps(e.errors(), indent=2)}")
        raise ValueError(f"Datos de entrada incompletos o incorrectos para el documento '{document_id}': {e.errors()}")
    except Exception as e:
        logging.error(
            f"Errores de validación para {document_id}: "
            f"{json.dumps(e.errors(), indent=2, default=str)}"
        )
        raise

    # 3. Ejecutar los cálculos requeridos
    calculated_data = {}
    for calc_group_name in required_calcs_groups:
        calculator_module = CALCULATOR_MODULES.get(calc_group_name)
        if not calculator_module:
            logging.warning(f"Grupo de cálculo '{calc_group_name}' no encontrado para el documento '{document_id}'.")
            continue

        # Asumimos que cada módulo de cálculo tiene una función con el patrón `calculate_<group_name>_data`
        # o que simplemente iteramos sobre todas las funciones que empiezan con 'calculate_'
        for attr_name in dir(calculator_module):
            if attr_name.startswith('calculate_') and callable(getattr(calculator_module, attr_name)):
                calc_func = getattr(calculator_module, attr_name)
                try:
                    # Pasamos el contexto actual (ya con los datos calculados previamente)
                    # y fusionamos los nuevos cálculos
                    new_calcs = calc_func(ctx_dict) # Pasa el diccionario actual
                    calculated_data.update(new_calcs)
                    logging.debug(f"Ejecutado cálculo '{attr_name}' del grupo '{calc_group_name}'.")
                except Exception as e:
                    logging.error(f"Error al ejecutar la función de cálculo '{attr_name}' para '{document_id}': {e}")
                    raise RuntimeError(f"Error en los cálculos para el documento: {e}")

    # 4. Fusionar datos originales (validados) con los datos calculados
    # Los datos calculados tienen prioridad si hay solapamiento
    ctx_dict.update(calculated_data)
    return ctx_dict

def generate_documents_for_project(
    project_data: Dict[str, Any], 
    community_slug: str, 
    requested_doc_ids: List[str]
) -> Dict[str, bytes]:
    """
    Genera múltiples documentos para un proyecto dado.
    Devuelve un diccionario con el nombre del archivo como clave y los bytes del documento como valor.
    """
    generated_files = {}
    
    # Obtener las definiciones de documentos para la comunidad
    community_docs_definitions = DOCUMENT_DEFINITIONS.get(community_slug)
    if not community_docs_definitions:
        raise ValueError(f"No hay documentos definidos para la comunidad: {community_slug}")

    for doc_id in requested_doc_ids:
        doc_info = community_docs_definitions.get(doc_id)
        if not doc_info:
            logging.warning(f"Documento '{doc_id}' no encontrado en las definiciones para '{community_slug}'. Saltando.")
            continue
        
        template_relative_path = doc_info['template']
        template_full_path = os.path.join(TEMPLATES_ROOT, template_relative_path)
        
        try:
            # Prepara y valida el contexto con los cálculos
            final_context = prepare_document_context(project_data, community_slug, doc_id)
            
            # Genera el documento
            doc_bytes = generate_document_from_template(template_full_path, final_context)
            
            # El nombre del archivo para la descarga
            output_filename = doc_info.get("name", os.path.splitext(doc_id)[0].replace("_", " ").title()) + ".docx"
            generated_files[output_filename] = doc_bytes
            logging.info(f"Documento '{output_filename}' generado exitosamente.")
            
        except (ValueError, FileNotFoundError, RuntimeError) as e:
            logging.error(f"Fallo al generar el documento '{doc_id}' para el proyecto '{project_data.get('id', 'N/A')}': {e}")
            # Decidir si se levanta el error o se registra y se continúa con otros documentos
            # Por ahora, levantaremos el error para que la API responda adecuadamente.
            raise 
        except Exception as e:
            logging.error(f"Error inesperado al generar el documento '{doc_id}': {e}", exc_info=True)
            raise

    return generated_files

def create_zip_archive(files: Dict[str, bytes]) -> bytes:
    """
    Crea un archivo ZIP en memoria a partir de un diccionario de nombres de archivo y sus bytes.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()