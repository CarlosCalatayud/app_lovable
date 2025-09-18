from src.generation.models import ProjectContext, constr, Field
from typing import Literal

# Hereda de ProjectContext para incluir todos los campos base
class AndaluciaDocInformeContext(ProjectContext):
    """
    Esquema de datos específico para el 'informe_tecnico.docx' de Andalucía.
    Podemos hacer campos opcionales en ProjectContext obligatorios aquí.
    """
    # Hacer referencia_catastral obligatoria para este documento
    referencia_catastral: constr(min_length=1, max_length=50) = Field(..., description="Referencia catastral del emplazamiento, obligatoria para este informe.")
    
    # Añadir un campo específico que solo este documento necesite
    tipo_cubierta: Literal["Plana", "Inclinada", "Mixta"] = Field(..., description="Tipo de cubierta de la instalación.")
    
    # Podríamos sobrescribir validaciones o añadir alias si fuera necesario
    # Por ejemplo, si en la plantilla se espera 'nombre_instalador' en lugar de 'instalador.nombre_empresa'
    # class Config:
    #     fields = {'instalador_nombre_empresa': 'nombre_instalador'}