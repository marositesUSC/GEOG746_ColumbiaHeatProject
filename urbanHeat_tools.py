import arcpy
import os
import shutil

## Download Raster Data
## Download CAPA Transect Data from https://osf.io/nqwyr/?view_only=

def create_file_structure(project_directory = os.getcwd()):
    '''
    Creates filestructure for data analysis
    '''
    folders = ['sentinel_rasters', 'CAPA_transects', 'CAPA_rasters', 'focal_rasters', 'resampled_rasters', 'shapefiles', 'fishnet']
    for folder in folders:
        if not os.path.exists(os.path.join(project_directory, folder)):
            os.makedirs(os.path.join(project_directory, folder))
            print(f'Created new directory: {folder}')
        else:
            print(f'{folder} already exists.')
        

def rename_rasters(input_folder):
    """
    Renames all Sentinel data so that it is easier to read.
    
    Parameters:
        input_folder (str): The folder containing the input rasters.
        
    Returns:
        None
    """
    for file in os.listdir(input_folder):
        try:
            if file.split("_")[4].startswith('Sentinel'):
                file_ext = os.path.splitext(file)[1]
                parts = file.split("_")
                new_file = f"{parts[4]}_{parts[5]}_{parts[6]}{file_ext}"
                os.rename(os.path.join(input_folder, file), os.path.join(input_folder, new_file))
                print(f"Renamed '{file}' to '{new_file}'")
            else:
                pass
        except:
            print(f"{file} not renamed.")

def apply_resampling(input_folder, output_folder, cellsize="10", resampling_type="NEAREST"):
    """
    Resamples all rasters in a folder to specified grid size.
    
    Parameters:
        input_folder (str): The folder containing the input rasters.
        output_folder (str): The folder where the output rasters will be saved.
        cellsize (): Cell size of the new raster (default is "10").
        resampling_type (str): Specifies the resampling technique to be used (default is "NEAREST").
        
    Returns:
        None
    """
    # Set up environment settings
    arcpy.env.workspace = input_folder
    arcpy.env.overwriteOutput = True
    
    # List all rasters in the input folder
    rasters = arcpy.ListRasters()
    print(rasters)
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Process each raster
    for raster in rasters:
        # Define output raster path
        output_raster = os.path.join(output_folder, f"resampled_{os.path.splitext(raster)[0]}.tif")
        
        # Resample
        arcpy.Resample_management(
            in_raster=raster,
            out_raster=output_raster,
            cell_size=cellsize,
            resampling_type='NEAREST')
                
        # Save the output raster
        print(f"Processed {raster}, resampled to {cellsize} and saved to {output_raster}")  

def apply_focal_statistics(input_folder, output_folder, radius, statistic_type="MEAN"):
    """
    Applies focal statistics with a specified radius and statistic type to all rasters in a folder.
    
    Parameters:
        input_folder (str): The folder containing the input rasters.
        output_folder (str): The folder where the output rasters will be saved.
        radius (list): The radius distance for the focal operation.
        statistic_type (str): The statistic to apply (default is "MEAN").
        
    Returns:
        None
    """
    # Set up environment settings
    arcpy.env.workspace = input_folder
    arcpy.env.overwriteOutput = True
    
    # List all rasters in the input folder
    rasters = arcpy.ListRasters()
    
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Process each raster
    for raster in rasters:
        for rad in radius:
            # Define output raster path
            output_raster = os.path.join(output_folder, f"focal_{rad}_{os.path.splitext(raster)[0]}.tif")
            
            # Apply Focal Statistics with specified radius and statistic type
            focal_raster = arcpy.sa.FocalStatistics(
                in_raster=raster,
                neighborhood=arcpy.sa.NbrCircle(rad, "CELL"),
                statistics_type=statistic_type
            )
            
            # Save the output raster
            focal_raster.save(output_raster)
            print(f"Processed {raster} with radius {rad} and saved to {output_raster}")
    
def create_fishnet(input_raster, output_folder, output_name):
    """
    Generates fishnet from existing raster (aka CAPA temperature raster). 
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/how-create-fishnet-works.htm
    
    Parameters:
        input_raster (Raster): Input raster. Raster's extent and number of columns and rows will be used to create fishnet.
        output_folder (str): The folder where the output layers will be stored.
        output_name (str): The file name of the new fishnet. 
    Returns:
        None
    """
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)    
        
    # Define existing raster extent and parameters
    raster_left = arcpy.GetRasterProperties_management(input_raster, "LEFT")
    raster_bottom = arcpy.GetRasterProperties_management(input_raster, "BOTTOM")
    raster_right = arcpy.GetRasterProperties_management(input_raster, "RIGHT")
    raster_top = arcpy.GetRasterProperties_management(input_raster, "TOP")
    raster_ncols = arcpy.GetRasterProperties_management(input_raster, "COLUMNCOUNT")
    raster_nrows = arcpy.GetRasterProperties_management(input_raster, "ROWCOUNT")
    
    # Create Fishnet
    arcpy.management.CreateFishnet(
        out_feature_class= os.path.join(output_folder, 'output_name'), 
        origin_coord= f"{raster_left.getOutput(0)} {raster_bottom.getOutput(0)}", 
        y_axis_coord= f"{raster_left.getOutput(0)} {int(raster_bottom.getOutput(0))+10}", 
        cell_width=10,
        cell_height=10,
        number_rows=raster_nrows,
        number_columns=raster_ncols,
        labels="LABELS",
        geometry_type="POLYLINE"
    )
    print(f"Processed {input_raster}. Fishnet {output_name} saved to {output_folder}")
    
def extract_values(in_points_file, rasters_folder, output_folder, output_file):
    """
    Extracts cell values at point features.
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/extract-multi-values-to-points.htm 
    
    Parameters:
        in_points_file (FeatureLayer): Input point features to which data will be added. Original is copied.
        input_folder (str): The folder containing the input rasters.
        output_folder (str): The folder where the output layer will be stored.
        
    Returns:
        None
    """
    # Ensure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
 
    output = os.path.join(output_folder, output_file)
    arcpy.management.CopyFeatures(in_points_file, output) 
        
    # Set up environment settings
    arcpy.env.workspace = rasters_folder
    arcpy.env.overwriteOutput = True
    
    # List all rasters in the input folder
    rasters = arcpy.ListRasters()
    
    # Create list of lists for each raster...
    inRasterList = []
    for raster in rasters:
        # Define Raster name and new field for point shapefile
        name = raster.split('.')[0]
        nameparts = name.split('_')
        new_fieldname = nameparts[-1] + '_' + nameparts[1] + '0m' #nameparts[0] + nameparts[1] + '_' + nameparts[-1]
        inRasterList.append([raster, new_fieldname])
    print(inRasterList)    
    arcpy.sa.ExtractMultiValuesToPoints(output, inRasterList, "NONE")           
    print(f"Processed {len(inRasterList)} rasters. And saved to {output}") 
    
def create_boundingBox(feature_classes):
    """
    Description of function
    
    Parameters:
        example (type): explaination of param
        
    Returns:
        None
    """
    pass

def grid_to_points(input_raster):
    """
    Description of function
    
    Parameters:
        example (type): explaination of param
        
    Returns:
        None
    """
    pass

# CREATE PROJECT
project_dir = r'C:\Users\bm233557\Documents\GradSchool\Climate\Project'
#create_file_structure(project_dir)

# DEFINE FILE DIRECTORIES
raw_raster_folder = os.path.join(project_dir, 'sentinel_rasters') # r"C:\Users\bm233557\Downloads\Browser_images (2)"
#output_folder = # r"C:\Users\bm233557\Downloads\TEST"
resample_folder = os.path.join(project_dir, "resampled_rasters")
focal_stats_folder = os.path.join(project_dir, "focal_rasters")
transverse_folder = os.path.join(project_dir, 'CAPA_transects') #r"C:\Users\bm233557\Downloads\traverses_chw_columbia_092222 (1)"
CAPA_raster_folder = os.path.join(project_dir, 'CAPA_rasters') #r'C:\Users\bm233557\Downloads\rasters_chw_columbia_101722'


# PROCESS RASTERS
#rename_rasters(raw_raster_folder)
#apply_resampling(raw_raster_folder, resample_folder, "10 10")
# Measured in Cells we use 10m cells, so multiply by 10. Literature uses 0 m, 100 m, 150 m, 200 m, 250 m, 300 m, 350 m, 400 m, 450  m,  500  m,  600  m,  700  m,  800  m,  900  m,  and  1000  m
radius = [10,15,20,25,30,35,40,45,50,60,70,80,90,100] 
#apply_focal_statistics(resample_folder, focal_stats_folder, radius)

utm_spatial_ref = arcpy.SpatialReference(32617)

# Define location of CAPA transverse data

am_shp = os.path.join(transverse_folder, 'am_trav.shp')
af_shp = os.path.join(transverse_folder, 'af_trav.shp')
pm_shp = os.path.join(transverse_folder, 'pm_trav.shp')

trans_data = [am_shp, af_shp, pm_shp]

# Define location of CAPA Rasters   
capa_am_t_raster = os.path.join(CAPA_raster_folder, 'am_t_f.tif')
capa_am_hi_raster = os.path.join(CAPA_raster_folder, 'am_hi_f.tif')
capa_af_t_raster = os.path.join(CAPA_raster_folder, 'af_t_f.tif')
capa_af_hi_raster = os.path.join(CAPA_raster_folder, 'af_hi_f.tif')
capa_pm_t_raster = os.path.join(CAPA_raster_folder, 'pm_t_f.tif')
capa_pm_hi_raster = os.path.join(CAPA_raster_folder, 'pm_hi_f.tif')

# CREATE FISHNET *** THIS TAKES A LONG TIME TO RUN ***
# fishnet_folder = os.path.join(output_folder, "Fishnet")
# create_fishnet(capa_am_t_raster, fishnet_folder, 'Fishnet')


# # EXTRACT RASTER VALUE FOR POINT
processed_transects_folder = os.path.join(project_dir, 'shapefiles') #r'C:\Users\bm233557\Downloads\TEST\Points'
am_shp_w_rasterdata = r'am_output.shp'
af_shp_w_rasterdata = r'af_output.shp'
pm_shp_w_rasterdata = r'pm_output.shp'

extract_values(am_shp, focal_stats_folder, processed_transects_folder, am_shp_w_rasterdata)
extract_values(af_shp, focal_stats_folder, processed_transects_folder, af_shp_w_rasterdata)
extract_values(pm_shp, focal_stats_folder, processed_transects_folder, pm_shp_w_rasterdata)



