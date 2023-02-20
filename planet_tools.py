#!/usr/bin/env python
# coding: utf-8

# In[ ]:



def get_acquired_date(item):
    return item['properties']['acquired'].split('T')[0]

def get_date_item_ids(date, all_items):
    return [i['id'] for i in all_items if get_acquired_date(i) == date]

def get_ids_by_date(items):
    acquired_dates = [get_acquired_date(item) for item in items]
    unique_acquired_dates = set(acquired_dates)
    
    ids_by_date = dict((d, get_date_item_ids(d, items))
                       for d in unique_acquired_dates)
    return ids_by_date

def build_order_request(ids, bundle, item_type, name):
    from planet.order_request import build_request, product
    item_type = item_type[0]
    products = [product(ids, bundle, item_type)]
    request = build_request(name, products=products)
    return request

def prepare_order(scenes, dataset, bundle = 'analytic_sr_udm2', name = 'default order name'):
    acquired_dates = [get_acquired_date(item) for item in scenes]
    ids_by_date = get_ids_by_date(scenes)
    list_of_order_requests = []
    unique_acquired_dates = set(acquired_dates)

    for date in list(unique_acquired_dates):
        ids = ids_by_date[date]
        list_of_order_requests.append(build_order_request(ids, bundle, dataset, name))

    print(str(len(list_of_order_requests)) + ' planet orders will be attempted')
 
    return list_of_order_requests

async def pl_search_query(login, dataset, extent, start_date, end_date, max_cloud_cover, name='default order name'):
    from planet import Auth, Session, DataClient, OrdersClient, data_filter
    from planet.order_request import build_request, product
    import asyncio, os
    
    os.environ['PL_API_KEY']=login
    PLANET_API_KEY = os.getenv('PL_API_KEY')
    
    AOI_geom = {
        "type": "Polygon",
        "coordinates": [ [extent[0], extent[1], extent[2], extent[3], extent[0]] ]
    }
    
    dataset = [dataset]
    
    geom_filter = data_filter.geometry_filter(AOI_geom)
    date_range_filter = data_filter.date_range_filter("acquired", start_date, end_date)
    cloud_cover_filter = data_filter.range_filter('cloud_cover', None, (max_cloud_cover/100))
    combined_filter = data_filter.and_filter([geom_filter, cloud_cover_filter, date_range_filter])

    from planet import Auth, Session, DataClient, OrdersClient, data_filter
    from planet.order_request import build_request, product
 
    async with Session() as sess:
        cl = DataClient(sess)
        request = await cl.create_search(name='temp_search2',search_filter=combined_filter, item_types=dataset) 

    async with Session() as sess:
        cl = DataClient(sess)
        items = cl.run_search(search_id=request['id'])
        scenes = [i async for i in items]
        
    scenes = prepare_order(scenes, dataset, name=name)

    return scenes

async def pl_place_order(login, scenes, dl_directory):
    import os
    
    output_directory = dl_directory + "planet"
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    from planet import Auth, Session, OrdersClient, reporting
    import sys
    error_list = []
    successful_orders = []

    os.environ['PL_API_KEY']=login
    PLANET_API_KEY = os.getenv('PL_API_KEY')
    
    for order_request in scenes:
        async with Session() as sess:
            cl = OrdersClient(sess)
            with reporting.StateBar(state='creating') as bar:
                # create
                print(order_request)
                try:
                    print('creating order')
                    order = await cl.create_order(order_request)
                    successful_orders.append(order_request)
                except:
                    error_list.append([sys.exc_info()[0]])
                    print("unknown error: " + str(sys.exc_info()[0]))
                    continue
                bar.update(state='created', order_id=order['id'])

                # poll
                print('polling order')
                while True:
                    try:
                        await cl.wait(order['id'], callback=bar.update_state)
                        break
                    except:
                        print("unknown error: " + str(sys.exc_info()[0]))
                        continue

            # download
            print('downloading order')
            await cl.download_order(order['id'], output_directory, progress_bar=True)

    print(str(len(successful_orders)) + ' products successfully ordered')
    return [successful_orders, error_list]


def pl_crop(scn_dirs, pg, output_directory):
    import rasterio, os
    from rasterio.mask import mask as msk
    for count, scn  in enumerate(scn_dirs):
        scn_name = scn.split('planet')[1].split("\\")[3].split("_BGRN")[0]
        print(scn)
        file_name = '{s}_clip.tif'.format(s=scn_name)
        print(file_name)
        with rasterio.open(scn) as src0:
            out_image, out_transform = msk(src0, pg, crop=True)
            out_meta = src0.meta
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