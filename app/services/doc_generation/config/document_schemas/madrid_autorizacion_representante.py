from app.services.doc_generation.generation.models import ProjectContext, constr, Field
from typing import Literal
from datetime import date

# Hereda de ProjectContext para incluir todos los campos base
class MadridAutorizacionRepresentanteContext(ProjectContext):
    """
    Esquema de datos específico para el 'AUTORIZACION_REPRESENTANTE.docx' de Madrid.
    Podemos hacer campos opcionales en ProjectContext obligatorios aquí.
    """
    # Campos que se mapean o ya existen en ProjectContext
    # Nombre_completo_cliente: Se puede obtener de promotor.nombre_razon_social
    # DNI_o_CIF: Se puede obtener de promotor.cif_nif
    # Dirección_completa: Se puede obtener de promotor_direccion_completa (calculado) o emplazamiento.
    
    # Nombre_técnico_competente_que_suscribe: Se puede obtener de instalador.nombre_completo_tecnico
    # Apellido_1_técnico_competente_que_suscribe: Derivado de nombre_completo_tecnico, o añadir un campo si es necesario
    # Apellido_2_técnico_competente_que_suscribe: Derivado de nombre_completo_tecnico, o añadir un campo si es necesario
    # DNI_técnico_competente_que_suscribe: Se puede obtener de instalador.cif_nif o numero_colegiado_o_instalador

    # Día, Mes, Año: Se pueden obtener de 'dia_actual', 'mes_actual', 'anio_actual' (calculados)

    # --- Campos adicionales o re-validaciones para este documento ---
    # Aquí podríamos hacer que algunos campos opcionales en ProjectContext sean obligatorios
    # o añadir campos específicos que solo este documento necesita.

    # Ejemplo: Si para este certificado la fecha de finalización debe ser OBLIGATORIA
    # y no solo opcional como en el ProjectContext base si no hay valor.
    # Ya ProjectContext la tiene como 'date', así que su presencia es validada.
    fecha_finalizacion: date = Field(..., description="Fecha de finalización del proyecto, obligatoria para el certificado.")

    # Si necesitas una separación explícita de nombre y apellidos del técnico,
    # podrías añadir estos campos y tu frontend debería proporcionarlos.
    # O bien, podrías modificar el CommonCalculations para parsearlos si siempre vienen en un solo campo.
    # Para este ejemplo, asumiremos que los campos de instalador.nombre_completo_tecnico ya son suficientes
    # y se pueden manipular en la plantilla o en un cálculo específico.
    
    # Ejemplo de un campo específico que no está en ProjectContext
    # numero_registro_instalacion: constr(min_length=1, max_length=50) = Field(..., description="Número de registro de la instalación en el organismo competente.")

    # Sobreescribimos la validación para asegurarnos de que ciertos campos estén presentes
    # o tengan un formato específico, si es necesario, más allá de ProjectContext.
    # Por ejemplo, podríamos asegurar que el CIF del promotor es un CIF válido si ProjectContext solo verifica min_length.

    class Config:
        # Pydantic Configuration
        # Esto es útil si tienes campos con nombres diferentes en la base de datos
        # o necesitas un mapeo específico para la plantilla.
        # Por ahora, nos basamos en los nombres del ProjectContext.
        pass

    # Puedes añadir métodos o propiedades aquí si el documento necesita datos derivados
    # de una forma muy específica que no encaje en los módulos de cálculo generales.
    @property
    def nombre_completo_cliente(self) -> str:
        return self.cliente.nombre_razon_socialcliente_nombre + self.cliente.nombre_razon_socialcliente_apellidos

    @property
    def dni_o_cif_cliente(self) -> str:
        return self.cliente.cliente_dni
    
    # La dirección completa del cliente ya se calcula en common_calculations como 'promotor_direccion_completa'
    # La dirección completa del emplazamiento como 'direccion_emplazamiento_completa'
    
    @property
    def nombre_tecnico_completo(self) -> str:
        return self.instalador.nombre_completo_instalador

    @property
    def dni_tecnico_competente(self) -> str:
        # Podría ser cif_nif de la empresa o el numero_colegiado_o_instalador si aplica al técnico.
        # Ajusta esto a la lógica de tu negocio.
        return self.instalador.instalador_tecnico_dni # O instalador.numero_colegiado_o_instalador

    # Día, mes, año se calcularán y añadirán al contexto por common_calculations
    # con las claves 'dia_actual', 'mes_actual', 'anio_actual'
