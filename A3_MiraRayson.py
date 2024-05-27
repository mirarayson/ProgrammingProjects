import numpy
import pystac_client
import planetary_computer
import shapely
import shapely.ops
import fiona
import sqlite3
import rasterio
from rasterio.plot import reshape_as_image
from rasterio.enums import ColorInterp 
from rasterio.windows import Window
from rasterio import features
from rasterio.crs import CRS
from rasterio.windows import Window
from rasterio.windows import from_bounds
from rasterio.windows import  round_window_to_full_blocks
from time import time
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report, accuracy_score
from matplotlib import pyplot
from datetime import datetime


### Making connection to planetary computer and importing chosen data
client = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)
landsat_id = 'LC08_L2SP_008029_20201016_02_T1'
search = client.search(
    collections=['landsat-c2-l2'],
    ids=[landsat_id]
)
item = search.item_collection()[0]
bands = ['blue', 'green', 'red', 'nir08', 'swir16', 'swir22']
features = len(bands)

right = 472460
left = 422400
top = 4966160
bottom = 4917440

bbox = (left, bottom, right, top)


### Defining the area of interest and creating a window
with rasterio.open(item.assets['blue'].href, 'r') as input:
    window=rasterio.windows.from_bounds(*bbox, input.transform)
    window=rasterio.windows.round_window_to_full_blocks(
                window,
                [(input.profile['blockysize'], input.profile['blockxsize'])])
  
    data=input.read(1, window=window)
    
    profile=input.profile
    ulx, uly=input.xy(int(window.row_off), int(window.col_off), offset='ul')
    profile['transform']=rasterio.Affine(
        input.transform.a,
        input.transform.b,
        ulx,
        input.transform.d,
        input.transform.e,
        uly
    )
    profile['compress']='deflate'
    profile['width']=int(window.width)
    profile['height']=int(window.height)
    profile['driver']='COG'
    profile['count']=1
    profile['dtype']=rasterio.uint8
    

### Sampling the Data
with fiona.open('training.gpkg', layer='training-2020') as training:
    y_labels=numpy.fromiter([l['properties']['code'] for l in training], numpy.uint8)
    coordinates=[c['geometry']['coordinates'] for c in training]
    X_samples=numpy.empty((len(coordinates), features), dtype=numpy.uint16)
 
    for b in bands:
        with rasterio.open(item.assets[b].href) as image:
            samples=image.sample(coordinates)
            samples=numpy.fromiter([s[0] for s in samples],
                                     numpy.uint16).reshape(len(y_labels), 1)
            numpy.put_along_axis(X_samples,
                                 numpy.full_like(samples, bands.index(b)),
                                 samples, axis=1)


### Printing accuracy assessments and completing classification
X_train, X_test, y_train, y_test = train_test_split(X_samples, y_labels, test_size=0.7, stratify=y_labels)

classification = SVC()
classification.fit(X_train, y_train)

classification_test = classification.predict(X_test)

print('Accuracy Score:')
print(f'{accuracy_score(y_test, classification_test)}')
print('Classification Report:')
print(classification_report(y_test, classification_test, zero_division=1))
print('Confusion Matrix:')
print(confusion_matrix(y_test, classification_test))

with (rasterio.open(f'{landsat_id}_classified_svc_nrcan.tif',
                   mode='w',
                   **profile) as classified):
    data = numpy.empty((window.width * window.height, features), dtype=numpy.uint16)
    for b in bands:
        with rasterio.open(item.assets[b].href) as band:
            data_band = reshape_as_image(
                            band.read(window=window)).reshape(-1, 1)
            numpy.put_along_axis(data, 
                                numpy.full_like(data_band, bands.index(b)), 
                                data_band, axis=1)
    prediction = classification.predict(data).reshape(int(window.height), 
                                                      int(window.width))
    
    classified.write(prediction, indexes=1)


### Applying Pseudo Colour
with sqlite3.connect('training.gpkg') as db:
    colours={}
    cursor=db.cursor()
    cursor.execute(
        """SELECT code, red, green, blue FROM landcover_class"""
    )
    for r in cursor.fetchall():
        colours[r[0]] = [r[1], r[2], r[3]]

prediction = classification.predict(data).reshape(int(window.height), int(window.width))

with rasterio.open(f'{landsat_id}_classified.tif', mode='w', **profile) as classified:
    classified.write(prediction, indexes=1)
    classified.write_colormap(1, colours)


### Counting number of pixels in each class for both classifications
landcover2020_subset = 'landcover-2020-classification-subset.tif'
with rasterio.open(landcover2020_subset) as src:
    classification_data=src.read(1)
    unique_classes, class_counts=numpy.unique(classification_data, return_counts=True)
for class_value, count in zip(unique_classes, class_counts):
    print(f"Class {class_value}: {count} pixels")

landsat_subset = 'LC08_L2SP_008029_20201016_02_T1_classified.tif'
with rasterio.open(landsat_subset) as src2:
    classification_data2=src2.read(1)
    unique_classes2, class_counts2=numpy.unique(classification_data2, return_counts=True)
for class_value2, count2 in zip(unique_classes2, class_counts2):
    print(f"Class {class_value2}: {count2} pixels")
    