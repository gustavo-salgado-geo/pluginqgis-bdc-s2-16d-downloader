# -*- coding: utf-8 -*-

def classFactory(iface):
    """
    Carrega o plugin no QGIS.
    
    :param iface: Uma instância da interface do QGIS (QgsInterface).
    :type iface: QgsInterface
    """
    # Importamos a classe usando o nome corrigido (sem hífens)
    # Certifique-se de que no arquivo main.py a classe tenha este exato nome.
    from .main import BDC_downloader_S216D
    return BDC_downloader_S216D(iface)
