"""
Povoamentos Sb Az Plugin
Um plugin QGIS para delimitar áreas de povoamento de sobreiro e azinheira
"""

def classFactory(iface):
    from .povoamentos_sb_az import PovoamentosSbAzPlugin
    return PovoamentosSbAzPlugin(iface)
