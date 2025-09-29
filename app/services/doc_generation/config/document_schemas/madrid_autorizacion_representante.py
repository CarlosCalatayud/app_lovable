from app.services.doc_generation.generation.models import ProjectContext, constr, Field
from typing import Literal
from datetime import date

# Hereda de ProjectContext para incluir todos los campos base
class MadridAutorizacionRepresentanteContext(ProjectContext):


    # Validadores para campos que en BD vienen como int pero el modelo base los define como str
    @field_validator('id', 'emplazamiento_tipo_via_id', mode='before')
    def _cast_to_str(cls, v):
        # Nota a mí mismo: pydantic v2 - este validador corre "before", convierte int->str
        return str(v) if v is not None else v
    
    @property
    def nombre_completo_cliente(self) -> str:
        return self.promotor.nombre_razon_social if self.promotor else "Cliente desconocido"

    @property
    def dni_o_cif_cliente(self) -> str:
        return self.promotor.cif_nif if self.promotor else "NIF desconocido"

    @property
    def nombre_tecnico_completo(self) -> str:
        return self.instalador.nombre_completo_tecnico if self.instalador else "Técnico desconocido"

    @property
    def dni_tecnico_competente(self) -> str:
        return self.instalador.numero_colegiado_o_instalador or self.instalador.cif_nif if self.instalador else "DNI desconocido"
