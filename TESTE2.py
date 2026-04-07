# Importa os módulos necessários
import requests
import os
from osgeo import gdal, ogr, osr
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject
from scipy import ndimage
import numpy as np

# Dados de entrada
tiles = ['031007']
date = '26/06/2025'

# Diretório de destino
directory = r"C:\Users\Usuario\Documents\Gustavo\SITS\nf" 

def generate_urls(tiles, date):
    # No Python, split retorna uma lista diretamente
    parts = date.split('/')
    day = parts[0]
    month = parts[1]
    year = parts[2]
    
    # Criando a data compacta AAAAMMDD
    date_compact = f"{year}{month}{day}"
    
    urls = []
    for tile in tiles:
        # Slicing no Python: tile[inicio:fim_exclusivo]
        # '015002'[0:3] extrai '015' (índices 0, 1, 2)
        # '015002'[3:6] extrai '002' (índices 3, 4, 5)
        h = tile[0:3]
        v = tile[3:6]
        
        # Usamos f-strings para montar a URL de forma limpa
        url = (
            f"https://data.inpe.br/bdc/data/s2-16d/v2/"
            f"{h}/{v}/{year}/{month}/{day}/"
            f"S2-16D_V2_{tile}_{date_compact}"
        )
        urls.append(url)
        
    return urls

# Execução
urls = generate_urls(tiles, date)

# Print do resultado (formatado para leitura)
for u in urls:
    print(u)

# Função para baixar um arquivo de uma URL e salvá-lo localmente
def download_file(url, local_filename):
    try:
        # Faz uma requisição GET para a URL
        with requests.get(url, stream=True) as r:
            r.raise_for_status()  # Levanta uma exceção se a requisição falhar
            # Salva o conteúdo do arquivo em partes (chunks)
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename  # Retorna o caminho do arquivo salvo
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar o arquivo: {e}")  # Imprime o erro se a requisição falhar
        return None  # Retorna None se houver um erro

# Função para normalizar um array para 8 bits
def normalize_to_8bit(array):
    array_min = np.min(array)  # Obtém o valor mínimo do array
    array_max = np.max(array)  # Obtém o valor máximo do array
    normalized = ((array - array_min) / (array_max - array_min)) * 255  # Normaliza o array para a faixa 0-255
    return normalized.astype(np.uint8)  # Converte o array normalizado para tipo uint8

# Função para criar uma composição RGB a partir de três bandas
def create_rgb_composition(band4_path, band8_path, band11_path, output_path):
    try:
        # Abre os arquivos das bandas usando GDAL
        band4 = gdal.Open(band4_path)
        band8 = gdal.Open(band8_path)
        band11 = gdal.Open(band11_path)
        
        # Cria um novo arquivo GeoTIFF para a composição RGB
        driver = gdal.GetDriverByName('GTiff')
        out_ds = driver.Create(output_path, band4.RasterXSize, band4.RasterYSize, 3, gdal.GDT_Byte)
        
        # Define a projeção e a transformação geoespacial do novo arquivo
        out_ds.SetProjection(band4.GetProjection())
        out_ds.SetGeoTransform(band4.GetGeoTransform())
        
        # Lê os dados das bandas como arrays
        band4_data = band4.GetRasterBand(1).ReadAsArray()
        band8_data = band8.GetRasterBand(1).ReadAsArray()
        band11_data = band11.GetRasterBand(1).ReadAsArray()
        
        # Escreve os arrays normalizados para o novo arquivo
        out_ds.GetRasterBand(1).WriteArray(normalize_to_8bit(band11_data))
        out_ds.GetRasterBand(2).WriteArray(normalize_to_8bit(band8_data))
        out_ds.GetRasterBand(3).WriteArray(normalize_to_8bit(band4_data))        
        
        out_ds.FlushCache()  # Garante que todos os dados sejam escritos no disco
        
        # LIBERAÇÃO DE MEMÓRIA (Crucial para permitir a exclusão dos arquivos depois)
        out_ds = None  
        band4 = None
        band8 = None
        band11 = None
        
        return output_path  # Retorna o caminho do arquivo de saída
    except Exception as e:
        print(f"Erro ao criar a composição RGB: {e}")  # Imprime o erro se a criação falhar
        return None  # Retorna None se houver um erro

# ──────────────────────────────────────────────────────────────────────────────
# vetoriza pixels de nuvem (valores 3, 8, 9 e 10) da banda CLOUD
# ──────────────────────────────────────────────────────────────────────────────

def fill_holes_in_mask(mask):
    # Preenche buracos internos na máscara binária
    return ndimage.binary_fill_holes(mask).astype(np.uint8)

def vectorize_cloud_mask(cloud_path, output_gpkg):
    try:
        cloud_ds = gdal.Open(cloud_path)
        if not cloud_ds:
            return None
        
        band = cloud_ds.GetRasterBand(1)
        cloud_data = band.ReadAsArray()
        projection = cloud_ds.GetProjection()
        geotransform = cloud_ds.GetGeoTransform()
        
        srs = osr.SpatialReference()
        srs.ImportFromWkt(projection)

        drv_gpkg = ogr.GetDriverByName('GPKG')
        if os.path.exists(output_gpkg):
            drv_gpkg.DeleteDataSource(output_gpkg)
        
        out_ds = drv_gpkg.CreateDataSource(output_gpkg)
        out_layer = out_ds.CreateLayer('cloud_mask', srs=srs, geom_type=ogr.wkbPolygon)
        
        # Como estamos dissolvendo tudo, o valor será único (ex: 1)
        out_layer.CreateField(ogr.FieldDefn('is_cloud', ogr.OFTInteger))
        layer_defn = out_layer.GetLayerDefn()

        cloud_values = [3, 8, 9, 10]
        
        # Coleção global que vai armazenar TODAS as geometrias de todas as classes
        geom_collection = ogr.Geometry(ogr.wkbMultiPolygon)

        for val in cloud_values:
            mask = (cloud_data == val).astype(np.uint8)
            if not np.any(mask):
                continue
            
            filled_mask = fill_holes_in_mask(mask)

            # Raster temporário em memória
            mem_drv = gdal.GetDriverByName('MEM')
            tmp_ds = mem_drv.Create('', cloud_ds.RasterXSize, cloud_ds.RasterYSize, 1, gdal.GDT_Byte)
            tmp_ds.SetProjection(projection)
            tmp_ds.SetGeoTransform(geotransform)
            tmp_band = tmp_ds.GetRasterBand(1)
            tmp_band.WriteArray(filled_mask)
            tmp_band.SetNoDataValue(0)

            # Vetor temporário em memória
            mem_ogr_drv = ogr.GetDriverByName('Memory')
            temp_mem_ds = mem_ogr_drv.CreateDataSource('mem_ds')
            temp_mem_layer = temp_mem_ds.CreateLayer('temp', srs=srs, geom_type=ogr.wkbPolygon)
            
            gdal.Polygonize(tmp_band, tmp_band, temp_mem_layer, -1, [], callback=None)

            # Acumula as geometrias validadas na coleção global (sem salvar no disco ainda)
            for feature in temp_mem_layer:
                geom = feature.GetGeometryRef()
                if geom is None or geom.IsEmpty():
                    continue

                if not geom.IsValid():
                    geom = geom.Buffer(0)
                    if geom is None or geom.IsEmpty():
                        continue
                
                # Extrai partes do MultiPolygon ou adiciona o Polygon direto
                if geom.GetGeometryType() == ogr.wkbMultiPolygon:
                    for i in range(geom.GetGeometryCount()):
                        geom_collection.AddGeometry(geom.GetGeometryRef(i))
                else:
                    geom_collection.AddGeometry(geom)
            
            temp_mem_ds = None
            tmp_ds = None

        # ─── ETAPA DE DISSOLVE E EXPLODE ──────────────────────────────────────────
        
        if not geom_collection.IsEmpty():
            # UnionCascaded dissolve todas as geometrias que se tocam ou sobrepõem
            dissolved_geom = geom_collection.UnionCascaded()
            
            # Garantia: Correção de geometria no resultado do dissolve
            if not dissolved_geom.IsValid():
                dissolved_geom = dissolved_geom.Buffer(0)
            
            # Explode (transforma o resultado dissolvido em partes simples) e grava
            out_layer.StartTransaction()
            
            # área mínima de 1 hectare = 10.000 m² (assumindo que imagem está em um sistema projetado, como UTM ou SIRGAS 2000)
            min_area_sqm = 10000
            
            if dissolved_geom.GetGeometryType() == ogr.wkbMultiPolygon:
                for i in range(dissolved_geom.GetGeometryCount()):
                    sub_geom = dissolved_geom.GetGeometryRef(i)
                    
                    if sub_geom is None or sub_geom.IsEmpty():
                        continue
                    
                    # FILTRO DE ÁREA : Ignora o polígono se for menor que 1 ha
                    if sub_geom.GetArea() < min_area_sqm:
                        continue
                    
                    new_feat = ogr.Feature(layer_defn)
                    new_feat.SetField('is_cloud', 1)
                    new_feat.SetGeometry(sub_geom)
                    out_layer.CreateFeature(new_feat)
                    
            else: # Caso raro de sobrar apenas um único polígono na cena toda
                if dissolved_geom.GetArea() >= min_area_sqm:
                    new_feat = ogr.Feature(layer_defn)
                    new_feat.SetField('is_cloud', 1)
                    new_feat.SetGeometry(dissolved_geom)
                    out_layer.CreateFeature(new_feat)
                
            out_layer.CommitTransaction()
        # ──────────────────────────────────────────────────────────────────────────

        out_ds.FlushCache()
        out_ds = None
        cloud_ds = None
        
        print(f"  GeoPackage processado, dissolvido e vetorizado: {output_gpkg}")
        return output_gpkg

    except Exception as e:
        print(f"Erro ao processar máscara de nuvens: {e}")
        return None
# ──────────────────────────────────────────────────────────────────────────────

# Função principal para baixar as bandas e criar a composição RGB
def download_and_create_rgb(urls, directory):
    if not os.path.exists(directory):
        os.makedirs(directory)  # Cria o diretório se ele não existir

    for url_base in urls:
        base_name = url_base.split('/')[-1]  # Obtém o nome base da URL
        # Define os nomes dos arquivos das bandas usando o nome base
        bands = {
            "B04":       f"{base_name}_B04.tif",
            "B08":       f"{base_name}_B08.tif",
            "B11":       f"{base_name}_B11.tif",
            "PROVENANCE": f"{base_name}_PROVENANCE.tif",
            "SCL":     f"{base_name}_SCL.tif",   
        }
        
        file_paths = {}
        
        # Baixa cada banda e salva no diretório especificado
        for band, filename in bands.items():
            url = f"{url_base}_{band}.tif"  # Constrói a URL completa para a banda
            local_filename = os.path.join(directory, filename)  # Define o caminho local para salvar o arquivo
            file_paths[band] = download_file(url, local_filename)  # Baixa o arquivo e salva o caminho
        
        # Verifica se todas as bandas foram baixadas com sucesso
        if all(file_paths.values()):
            print(f"Todas as bandas para a URL {url_base} foram baixadas com sucesso!")

            # ── Composição RGB ────────────────────────────────────────────────
            rgb_output = os.path.join(directory, f"{base_name}_B11B08B04.tif")
            rgb_composition = create_rgb_composition(
                file_paths["B04"], file_paths["B08"],
                file_paths["B11"], rgb_output
            )

            if rgb_composition:
                print(f"Composição RGB criada: {url_base}")
                raster_layer = QgsRasterLayer(rgb_composition,
                                              f"{base_name}")
                if not raster_layer.isValid():
                    print(f"Erro ao carregar a composição RGB: {url_base}")
                else:
                    QgsProject.instance().addMapLayer(raster_layer)
                    print(f"Composição RGB carregada: {url_base}")
            else:
                print(f"Erro ao criar a composição RGB para a URL {url_base}!")  # Imprime um erro se a composição falhar
                
            # ── Vetorização de nuvens ─────────────────────────────────────────
            cloud_gpkg = os.path.join(directory, f"{base_name}_CLOUD_mask.gpkg")
            cloud_vector = vectorize_cloud_mask(file_paths["SCL"], cloud_gpkg)

            if cloud_vector:
                vector_layer = QgsVectorLayer(cloud_vector,
                                              f"Nuvens {base_name}", "ogr")
                if not vector_layer.isValid():
                    print(f"Erro ao carregar o vetor de nuvens: {url_base}")
                else:
                    QgsProject.instance().addMapLayer(vector_layer)
                    print(f"Vetor de nuvens carregado: {url_base}")
            
            # ── Limpeza dos arquivos das bandas individuais (EXCETO PROVENANCE) ──
            print("\nIniciando limpeza dos arquivos originais temporários...")
            for band_name, filepath in file_paths.items():
                
                # Regra para não excluir a banda PROVENANCE
                if band_name == "PROVENANCE":
                    print(f"  Mantido: {os.path.basename(filepath)} (PROVENANCE)")
                    continue  # Pula para o próximo item do loop sem rodar os comandos abaixo

                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        print(f"  Excluído: {os.path.basename(filepath)}")
                except Exception as e:
                    print(f"  Aviso: Não foi possível excluir a banda {band_name}. Erro: {e}")
            print("-" * 50)
            
        else:
            print(f"Erro ao baixar as bandas para a URL {url_base}!")


# Executa a função para baixar as bandas e criar a composição RGB para cada URL
download_and_create_rgb(urls, directory)