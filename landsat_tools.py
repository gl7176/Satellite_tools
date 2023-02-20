#!/usr/bin/env python
# coding: utf-8

# In[ ]:

def date_conv(date):
    y = str(date.year)
    m = str(date.month).rjust(2,'0')
    d = str(date.day).rjust(2,'0')
    return '{y}-{m}-{d}'.format(y=y, m=m, d=d)

def ls_search_query(login, dataset, extent, start_date, end_date, max_cloud_cover):
    from landsatxplore.api import API
    from utils import coords_to_bbox
    
    start_date = date_conv(start_date)
    end_date = date_conv(end_date)
    api = API(*login)
    
    scenes = api.search(
        dataset=dataset,
        bbox = coords_to_bbox(extent),
        start_date=start_date,
        end_date=end_date,
        max_cloud_cover=max_cloud_cover
    )
    
    api.logout()
    print(str(len(scenes)) + ' landsat orders wll be attempted')    
    return scenes

def ls_extract_cleanup(dl_directory):
    import tarfile, os
    for top, dirs, files in os.walk(dl_directory):
         for file in files:
                if(file.endswith(".tar")):
                    wd = os.path.join(top, file)
                    print('extracting ' + wd)
                    with tarfile.open(wd) as tar:
                        tar.extractall(path=os.path.join(top, file).split(".")[0])
                    os.remove(wd)
                
def ls_place_order(login, scenes, dl_directory):
    import sys, os
    from LandsatxploreFix.EarthExplorer import EarthExplorer
    ee = EarthExplorer(login[0], login[1])
    
    output_directory = dl_directory + "landsat"
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    error_list = []
    successful_orders = []
    for scn in scenes:
        print(scn)
        try:
            ee.download(scn, output_dir=output_directory)
            successful_orders.append(scn)
        except:
            error_list.append([sys.exc_info()[0]])
            print("unknown error: " + str(sys.exc_info()[0]))
            continue
    ee.logout()
    ls_extract_cleanup(output_directory)
    return [successful_orders, error_list]

def ls_stack_n_crop(scn_dirs, plygn, pg_crs, target_bands, output_directory):
    from rasterio.mask import mask as msk
    import rasterio, os
    from utils import transform_polygon
    
    if target_bands == '30m':
        target_band_list = ['B' + str(n) for n in range(1,8)]
    
    for count, scn  in enumerate(scn_dirs):
        glist = []
        scn_name = scn.split('landsat')[1].split("\\")[1].split(".")[0]
        file_name = '{s}_{t}_clip.tif'.format(s=scn_name, t=target_bands)
        for top, dirs, files in os.walk(scn):
            for file in files:
                file_suf = file.split("_")[-1].split('.')[0]
                if(file_suf in target_band_list):
                    glist.append(os.path.join(top, file))
        with rasterio.open(glist[0]) as src0:
            if pg_crs != src0.crs:
                plygn, pg_crs = transform_polygon(plygn, pg_crs, src0.crs)
            meta = src0.meta
            meta.update(count = len(glist))
            with rasterio.open('temp.tif', 'w', **meta) as dst:
                for id, layer in enumerate(glist, start=1):
                    with rasterio.open(layer) as src1:
                        print("writing layer " + str(id))
                        dst.write_band(id, src1.read(1))
                print('done writing scene {c}, proceeding'.format(c=count+1))
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
