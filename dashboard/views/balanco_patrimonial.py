# views/balanco_patrimonial.py
# ------------------------------------------------------------------------------
# Compatibilidade: a página de Balanço Patrimonial agora usa o renderizador
# genérico de demonstrativos (views/demonstrativos.py).
# ------------------------------------------------------------------------------
from views.demonstrativos import render_demonstrativo


def render_bp_page(cnpj, nome, anos):
    render_demonstrativo(cnpj, nome, "BP", anos)
