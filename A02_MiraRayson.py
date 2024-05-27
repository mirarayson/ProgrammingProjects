import numpy
import rasterio 
from rasterio.warp import reproject, Resampling
from rasterio.enums import ColorInterp


##Retrieving red, green, blue, and panchromatic band images.
red_input = 'LC09_L1TP_009029_20230922_20230922_02_T1_MTL/LC09_L1TP_009029_20230922_20230922_02_T1_B4-subset.tif'
green_input = 'LC09_L1TP_009029_20230922_20230922_02_T1_MTL/LC09_L1TP_009029_20230922_20230922_02_T1_B2-subset.tif'
blue_input = 'LC09_L1TP_009029_20230922_20230922_02_T1_MTL/LC09_L1TP_009029_20230922_20230922_02_T1_B3-subset.tif'
pan_input = 'LC09_L1TP_009029_20230922_20230922_02_T1_MTL/LC09_L1TP_009029_20230922_20230922_02_T1_B8-subset.tif'


##Setting scale and offset (found in metadata) for each image/band.
red_scale = 9.9152E-03
red_offset = -49.57609

green_scale = 1.2757E-02
green_offset = -63.78403

blue_scale = 1.1769E-02
blue_offset = -58.84429

pan_scale = 1.1190E-02
pan_offset = -55.94908


##Converting digital numbers to Radiance for each band image.
#Red band radiance converion & output
with rasterio.open(red_input, 'r') as red_input:
    red_profile = red_input.profile
    red_data = red_input.read()
    red_convert = red_data * red_scale + red_offset
    red_output ='red_output.tif'
    with rasterio.open(red_output, 'w', **red_profile) as red_output:
        red_output.write(red_convert)

#Green band radiance conversion & output
with rasterio.open(green_input, 'r') as green_input:
    green_profile = green_input.profile
    green_data = green_input.read()
    green_convert = green_data * green_scale + green_offset
    green_output ='green_output.tif'
    with rasterio.open(green_output, 'w', **green_profile) as green_output:
        green_output.write(green_convert)

#Blue band radiance conversion & output
with rasterio.open(blue_input, 'r') as blue_input:
    blue_profile = blue_input.profile
    blue_data = blue_input.read()
    blue_convert = blue_data * blue_scale + blue_offset
    blue_output ='blue_output.tif'
    with rasterio.open(blue_output, 'w', **blue_profile) as blue_output:
        blue_output.write(blue_convert)

#Panchromatic band radiance conversion & output
with rasterio.open(pan_input, 'r') as pan_input:
    pan_profile = pan_input.profile
    pan_data = pan_input.read()
    pan_convert = pan_data * pan_scale + pan_offset
    pan_output ='pan_output.tif'
    with rasterio.open(pan_output, 'w', **pan_profile) as pan_output:
        pan_output.write(pan_convert)


##Upscaling bands with 30m resolution to 15m.
with rasterio.open ('red_output.tif') as red, \
    rasterio.open ('green_output.tif') as green, \
    rasterio.open ('blue_output.tif') as blue, \
    rasterio.open ('pan_output.tif') as pan:

    red_band = red.read(1)
    green_band = green.read(1)
    blue_band = blue.read(1)
    pan_band = pan.read(1)

#Creating an empty numpy array with the same shape as the panchromatic band.
    red_resample = numpy.empty(pan.shape, dtype=red_band.dtype)
    green_resample = numpy.empty(pan.shape, dtype=green_band.dtype)
    blue_resample = numpy.empty(pan.shape, dtype=blue_band.dtype)

#Using reproject function to transform each band and it's respective profile.
    red_resampled, red_transform = reproject(
        red_band,
        red_resample,
        src_transform=red.transform,
        src_crs=red.crs,
        dst_transform=pan.transform,
        dst_crs=pan.crs,
        red_resampling = Resampling.nearest
    )
    red_profile = red.profile
    red_profile['transform'] = red_transform
    red_profile['width'] = pan.width
    red_profile['height'] = pan.height
    with rasterio.open('red_upscaled.tif', mode='w', **red_profile) as output:
        output.write(red_resampled, indexes=1)

    green_resampled, green_transform = reproject(
        green_band,
        green_resample,
        src_transform=green.transform,
        src_crs=red.crs,
        dst_transform=pan.transform,
        dst_crs=pan.crs,
        green_resampling = Resampling.nearest
    )
    green_profile = green.profile
    green_profile['transform'] = green_transform
    green_profile['width'] = pan.width
    green_profile['height'] = pan.height
    with rasterio.open('green_upscaled.tif', mode='w', **green_profile) as output:
        output.write(green_resampled, indexes=1)

    blue_resampled, blue_transform = reproject(
        blue_band,
        blue_resample,
        src_transform=blue.transform,
        src_crs=blue.crs,
        dst_transform=pan.transform,
        dst_crs=pan.crs,
        blue_resampling = Resampling.nearest
    )
    blue_profile = blue.profile
    blue_profile['transform'] = blue_transform
    blue_profile['width'] = pan.width
    blue_profile['height'] = pan.height
    with rasterio.open('blue_upscaled.tif', mode='w', **blue_profile) as output:
        output.write(blue_resampled, indexes=1)


##Using the Brovey Transformation to apply pan sharpening to the upscaled bands
#Reading upscaled bands
with rasterio.open('red_upscaled.tif') as red, \
    rasterio.open('green_upscaled.tif') as green,\
    rasterio.open('blue_upscaled.tif') as blue:

    red_up = red.read(1)
    green_up = green.read(1)
    blue_up = blue.read(1)

with rasterio.open('pan_output.tif') as pan:
    pan = pan.read(1)

#Applying Brovey Transformation to sharpen bands
red_brovey = red_up * (pan / (red_up + green_up + blue_up))
green_brovey = green_up * (pan / (red_up + green_up + blue_up))
blue_brovey = blue_up * (pan / (red_up + green_up + blue_up))

#Writing the pan-sharpened images
red_sharp = 'red_pan_sharpened.tif'
green_sharp = 'green_pan_sharpened.tif'
blue_sharp = 'blue_pan_sharpened.tif'

with rasterio.open(red_sharp, 'w', **red_profile) as red_sharp_output:
    red_sharp_output.write(red_brovey, indexes = 1)

with rasterio.open(green_sharp, 'w', **green_profile) as green_sharp_output:
    green_sharp_output.write(green_brovey, indexes = 1)

with rasterio.open(blue_sharp, 'w', **blue_profile) as blue_sharp_output:
    blue_sharp_output.write(blue_brovey, indexes = 1)


##Radiometric conversion to scale values back to 16-bit unsigned intergers using converted radiance, scale and offset values
#I am not totally sure that I wrote these calculations correctly!
red_dn = (red_brovey - red_offset) / red_scale
green_dn = (green_brovey - green_offset) / green_scale
blue_dn = (blue_brovey - blue_offset) / blue_scale

#Stacking outputted bands
red_filename = 'red_pan_sharpened.tif'
green_filename = 'green_pan_sharpened.tif'
blue_filename = 'blue_pan_sharpened.tif'

filenames = [
    red_filename,
    green_filename,
    blue_filename
]

#Creating image profile for the output - only necessary to use one file as the basis.
with rasterio.open(red_filename) as red:
    profile = red.profile

#ensuring the output dataset has 3 bands and are 16-bit unsigned interger datatypes.
profile['count'] = 3
profile['dtype'] = 'uint16'

#Opening the file that data will be written, iterating over file names and indicating the index.
with rasterio.open ('stacked_bands.tif', mode='w', **profile) as output:
    for f in filenames:
        with rasterio.open(f) as input:
            output.write(input.read(1), indexes=filenames.index(f)+1)
 #Setting colour interpretation   
    output.colorinterp = [ColorInterp.red, ColorInterp.green, ColorInterp.blue] 
