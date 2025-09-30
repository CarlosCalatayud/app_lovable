from app.services.doc_generation.generation.models import ProjectContext, constr, Field
from typing import Literal, Optional
from datetime import date

# Hereda de ProjectContext para incluir todos los campos base
class MadridAutorizacionRepresentanteContext(ProjectContext):

    fecha_finalizacion: Optional[date] = Field(default_factory=date.today, description="Fecha de finalización del proyecto (opcional)")


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
