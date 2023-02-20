#!/usr/bin/env python
# coding: utf-8

# In[ ]:

def get_spatial_extent(dataset, latlon=False):
    natv_positions = dataset.transform * (0, 0), dataset.transform * (dataset.width, 0), dataset.transform * (dataset.width, dataset.height), dataset.transform * (0, dataset.height),
    if not latlon:
        return list(natv_positions)
    else:
        from pyproj import Transformer
        import numpy as np
        transformer = Transformer.from_crs(dataset.crs, "EPSG:4326")
        ll_positions = transformer.transform(np.array(natv_positions)[:,0],np.array(natv_positions)[:,1])
        ll_positions = list(zip(ll_positions[1], ll_positions[0]))
        return ll_positions

def coords_to_bbox(coords):
    x_coordinates, y_coordinates = zip(*coords)
    bbox = [min(x_coordinates), min(y_coordinates), max(x_coordinates), max(y_coordinates)]
    return bbox

def polygon_to_bbox(polygon_path):
    import geopandas as gpd
    
    suffix = polygon_path.split(".")[-1]
    if suffix.lower() == "kml":
        import fiona
        gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
        df = gpd.read_file(polygon_path, driver='KML')
    if suffix.lower() == "geojson" or suffix.lower() == "shp":
        df = gpd.read_file(polygon_path)
    output = list([float(df.bounds.minx), float(df.bounds.miny), float(df.bounds.maxx), float(df.bounds.maxy)])
    return output

def spatialfile_to_poly(input_file, output):
    # input can be
    # raster file: tif, jp2
    # polygon file
    
    # output can be
    # coords in native format
    # coords in latlon format
    # coords in bounding box
    # coords in min max
    
    x_coordinates, y_coordinates = zip(*coords)
    bbox = [min(x_coordinates), min(y_coordinates), max(x_coordinates), max(y_coordinates)]
    return bbox

def ls_directory_scns(dl_directory):
    from os import walk, path
    scene_locations = []
    for top, dirs, files in walk(dl_directory):
        for dir in dirs:
            wd = path.join(top, dir)
            scene_locations.append(wd)
    return scene_locations

def s2_directory_scns(dl_directory):
    from os import walk
    scene_locations = []
    for top, dirs, files in walk(dl_directory):
        for dir in dirs:
            if(dir.endswith('IMG_DATA')):
                wd = top
                scene_locations.append(wd)
    return scene_locations

def pl_directory_scns(dl_directory):
    from os import walk, path
    scene_locations = []
    for top, dirs, files in walk(dl_directory):
          for file in files:
                if(file.endswith("SR.tif")):
                    wd = path.join(top, file)
                    scene_locations.append(wd)
    return scene_locations

def limit_order(order_list, order_limit):
    order_list = order_list[:order_limit]
    return order_list

def extract_dir_IDs(inhand_files):
    for key, val in inhand_files.items():
        if key == 'landsat':
            inhand_files['landsat'] = [n.split("\\")[-1] for n in val]
        if key == 'sentinel-2':
            inhand_files['sentinel-2'] = [n.split(".SAFE")[0].split("\\")[1] for n in val]
        if key == 'planet':
            inhand_files['planet'] = [n.split("\\")[-1].split("_BGRN_")[0] for n in val]
    return inhand_files
                
def directory_scns(dl_directory, landsat=False, sentinel=False, planet=False):
    returns = {}
    if landsat:
        ls_scn_dirs = ls_directory_scns(dl_directory + 'landsat')
        returns['landsat'] = ls_scn_dirs
    if sentinel:
        s2_scn_dirs = s2_directory_scns(dl_directory + 'sentinel-2')
        returns['sentinel-2'] = s2_scn_dirs
    if planet:
        pl_scn_dirs = pl_directory_scns(dl_directory + 'planet')
        returns['planet'] = pl_scn_dirs
    
    returns = extract_dir_IDs(returns)
    
    return returns

def extract_order_keys(landsat=False, sentinel=False, planet=False):
    returns = {}
    if landsat:
        ls_keys = [n['display_id'] for n in landsat]
        returns['landsat'] = ls_keys
    if sentinel:
        s2_keys = [n[1]['title'] for n in sentinel]
        returns['sentinel-2'] = s2_keys
    if planet:
        pl_keys = [n['products'][0]['item_ids'] for n in planet]
#        pl_keys = [val2 for sublist in pl_keys for val2 in sublist]
        returns['planet'] = pl_keys
    
    return returns

def extract_order_dates(landsat=False, sentinel=False, planet=False):
    import datetime
    returns = {}
    if landsat:
        ls_dates = [n.split("\\")[-1].split("/")[-1].split("_")[-3] for n in landsat]
        ls_dates = [datetime.datetime(month=int(n[4:6]), day=int(n[6:8]), year=int(n[0:4])) for n in ls_dates]
        returns['landsat'] = ls_dates
    if sentinel:
        s2_dates = [n.split("\\")[-1].split("/")[-1].split("_")[-1][0:8] for n in sentinel]
        s2_dates = [datetime.datetime(month=int(n[4:6]), day=int(n[6:8]), year=int(n[0:4])) for n in s2_dates]
        returns['sentinel-2'] = s2_dates
    if planet:
        pl_dates = [n.split("\\")[-1].split("/")[-1].split("_")[-4] for n in planet]
        pl_dates = [datetime.datetime(month=int(n.split("-")[1]), day=int(n.split("-")[2]), year=int(n.split("-")[0])) for n in pl_dates]
        returns['planet'] = dates

    return returns

def check_dls(dl_directory, landsat=False, sentinel=False, planet=False):
    inhand_files = directory_scns(dl_directory, landsat=landsat, sentinel=sentinel, planet=planet)
    dl_keys = extract_order_keys(landsat=landsat, sentinel=sentinel, planet=planet)
    for key, val in dl_keys.items():
        for n in inhand_files[key]:
            try:
                dl_keys[key].remove(n)
                print(n + " is already downloaded")
            except:
                pass
    return dl_keys

def s2_key_to_hash(dl_key, scene_list):
    for c, m in enumerate(dl_key):
        for n in scene_list:
            if m == n[1]['title']:
                dl_key[c] = n[0]
    return dl_key

def pl_key_to_hash(dl_key, scene_list):
    for c, m in enumerate(dl_key):
        for n in scene_list:
            if m == n['products'][0]['item_ids']:
                dl_key[c] = n
    return dl_key

def transform_polygon(pg, pg_crs, new_crs):
    from shapely.geometry import Polygon, MultiPolygon
    import numpy as np
    from pyproj import Transformer
    ntransformer = Transformer.from_crs(pg_crs, new_crs)
    temp = list(pg.geoms[0].exterior.coords)
    new_positions = ntransformer.transform(np.array(temp)[:,0],np.array(temp)[:,1])
    new_positions = list(zip(new_positions[0], new_positions[1]))
    npg = Polygon(new_positions)
    npg = MultiPolygon([npg])
    return npg, new_crs

def polygon_from_rasterbounds(dataset, output_type='shapefile', output_directory=False, output_name=False):
    # imports
    from shapely.geometry import box, mapping
    import fiona
    import rasterio
    import os
    if output_directory==False:
        output_directory=os.getcwd()
    if output_name==False:
        output_name='bbox'
    # create a Polygon from the raster bounds
    bbox = box(*dataset.bounds)

    # create a schema with no properties
    schema = {'geometry': 'Polygon', 'properties': {}}
    
    if output_type=='shapefile':
        driver='ESRI Shapefile'
        suffix='.shp'
    elif output_type=='kml':
        import geopandas as gd
        gd.io.file.fiona.drvsupport.supported_drivers['kml'] = 'rw'
        gd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
        gd.io.file.fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'
        fiona.drvsupport.supported_drivers['kml'] = 'rw'  # enable KML support which is disabled by default
        fiona.drvsupport.supported_drivers['KML'] = 'rw'  # enable KML support which is disabled by default
        fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'  # enable KML support which is disabled by default
        driver='kml'
        suffix='.kml'
    # create output file
    with fiona.open(output_directory + "/" + output_name + suffix, 'w', driver=driver,
                    crs=dataset.crs.to_dict(), schema=schema) as c:
        c.write({'geometry': mapping(bbox), 'properties': {}})