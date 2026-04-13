"""
Centralizador de views do módulo RH.

Este arquivo importa e expõe todas as views organizadas em submódulos,
permitindo uso direto em urls.py com:

    from .views import *

Organização:
- Base (helpers)
- Dashboard
- Funcionários (core)
- Modais de funcionário
- Lembretes
- Cadastros auxiliares (cargos, lotações)
- Seções do funcionário (CRUDs por módulo)
"""

# ==========================================================
# BASE (HELPERS COMPARTILHADOS)
# ==========================================================
from .base import *


# ==========================================================
# DASHBOARD / CALENDÁRIO
# ==========================================================
from .dashboard import *
from .relatorios import *

# ==========================================================
# LOCAIS DE TRABALHO
# ==========================================================
from .locais_trabalho import *


# ==========================================================
# FUNCIONÁRIOS (CORE)
# ==========================================================
from .funcionarios import *

from .export_busca_funcionarios import *


# ==========================================================
# MODAIS DO FUNCIONÁRIO
# ==========================================================
from .modais_funcionario import *


# ==========================================================
# LEMBRETES
# ==========================================================
from .lembretes import *


# ==========================================================
# CADASTROS AUXILIARES
# ==========================================================
from .cargos import *
from .modais_cargo import *
from .lotacoes import *


# ==========================================================
# SEÇÕES DO FUNCIONÁRIO
# ==========================================================
from .ferias import *
from .afastamentos import *
from .dependentes import *
from .saude import *
from .anexos import *


# ==========================================================
# FALTAS / DESCONTOS (início: faltas)
# ==========================================================
from .faltas import *