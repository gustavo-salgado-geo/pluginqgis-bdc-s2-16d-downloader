# -*- coding: utf-8 -*-

def classFactory(iface):
    """
    Carrega o plugin no QGIS.
    
    :param iface: Uma instância da interface do QGIS (QgsInterface).
    :type iface: QgsInterface
    """
    # Importamos a classe principal aqui para evitar erros de 
    # importação circular durante a inicialização do QGIS
    from .main import BDC-S2-Downloader-QGISPlugin
    return BDC-S2-Downloader-QGISPlugin(iface)