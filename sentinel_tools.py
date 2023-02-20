#!/usr/bin/env python
# coding: utf-8

# In[ ]:

def s2_search_query(login, dataset, extent, start_date, end_date, max_cloud_cover):
    from sentinelsat import SentinelAPI
    from shapely.geometry import Polygon
    
    api = SentinelAPI(login[0], login[1], 'https://apihub.copernicus.eu/apihub')
    scenes = api.query(Polygon(extent).wkt,
                         date=(start_date, end_date),
                         platformname='Sentinel-2',
                         cloudcoverpercentage=(0, max_cloud_cover),
                         producttype=dataset
                        )
    print('Search yields: ' + str(len(scenes.items())) + ' orders')

    return [n for n in scenes.items()]

def s2_place_order(login, scenes, dl_directory):
    from sentinelsat import SentinelAPI, products
    import os, sys

    # only download the image data, throw out the metadata (unelss you want them)
    path_filter = products.make_path_filter("*GRANULE/*/IMG_DATA/*")
    
    output_directory = dl_directory + "sentinel-2"
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    api = SentinelAPI(login[0], login[1], 'https://apihub.copernicus.eu/apihub')
    
    error_list = []
    successful_orders = []
    for order in scenes:
        try:
            print(order)
            api.download(order, directory_path= output_directory, nodefilter=path_filter)
            successful_orders.append(order)
        except:
            error_list.append([sys.exc_info()[0]])
            print("unknown error: " + str(sys.exc_info()[0]))
            continue
    return [successful_orders, error_list]

def s2_stack_n_crop(scn_dirs, plygn, target_bands, output_directory):
    import rasterio, os
    from rasterio.mask import mask as msk
    for count, scn  in enumerate(scn_dirs):
        glist = []
        scn_name = scn.split('sentinel-2')[1].split("\\")[1].split(".")[0]
        file_name = '{s}_{t}_clip.tif'.format(s=scn_name, t=target_bands)
        for top, dirs, files in os.walk(scn + "//IMG_DATA//R" + target_bands + "//"):
            for file in files:
                if(file.split("_")[-2].startswith('B')):
                    glist.append(os.path.join(top, file))
        with rasterio.open(glist[0]) as src0:
            meta = src0.meta
            meta.update(count = len(glist))
            with rasterio.open('temp.tif', 'w', **meta) as dst:
                for id, layer in enumerate(glist, start=1):
                    with rasterio.open(layer) as src1:
                        print("writing layer " + str(id))
                        dst.write_band(id, src1.read(1))
                print('done writing sentinel scene {c}, proceeding'.format(c=count+1))
            with rasterio.open('temp.tif') as src1:
                out_image, out_transform = msk(src1, plygn, crop=True)
                out_meta = src1.meta
                out_meta.update({"driver": "GTiff",
                                 "height": out_image.shape[1],
                                 "width": out_image.shape[2],
                                 "transform": out_transform})
            with rasterio.open(os.path.join(output_directory, file_name), "w", **out_meta) as dest:
                dest.write(out_image)
    print("all files cropped")
    os.remove("temp.tif") 
    try:
        os.remove("temp.tif.aux.xml")
    except:
        pass