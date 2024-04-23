import numpy as np
import skimage
from skimage import measure, morphology
import skimage.measure

from LS_Pycro_App.hardware import Camera, Stage
from LS_Pycro_App.utils import pycro, stitch, exceptions
from LS_Pycro_App.utils.pycro import core


HOLE_AREA_UM = 4500
FEATURE_AREA_UM = 65000
SAME_FEATURE_MAX_D = 300
ECCENTRICITY_LIMIT = 0.95
NUM_FEATURES = 2
STD_FACTOR = 1.6
DX_FACTOR = 0.3


def wait_for_fish(bg_image: np.ndarray):
    fish_detected = False
    bg_image_mean = np.mean(bg_image)
    bg_image_std = np.std(bg_image)
    while not fish_detected:
        Camera.snap_image()
        image = pycro.pop_next_image().get_raw_pixels()
        if np.mean(image) < bg_image_mean - bg_image_std:
            return True
        
def get_capillary_image(stitched_positions):
        images = []
        for pos in stitched_positions:
            Stage.set_x_position(pos[0])
            Stage.set_y_position(pos[1])
            Stage.set_z_position(pos[2])
            Stage.wait_for_xy_stage()
            Stage.wait_for_z_stage()
            Camera.snap_image()
            image = pycro.pop_next_image().get_raw_pixels()
            images.append(image)
        return stitch.stitch_images(images, stitched_positions)

def get_stitched_positions(start_pos, end_pos, x_step_size):
    #0.90 provides 10% overlap for stitched image
    num_steps = int(np.ceil(np.abs((end_pos[0]-start_pos[0])/x_step_size)))
    y_spacing = (end_pos[1]-start_pos[1])/num_steps
    z_spacing = (end_pos[2]-start_pos[2])/num_steps
    positions = []
    for step_num in range(num_steps):
        x_pos = start_pos[0] + x_step_size*step_num
        y_pos = start_pos[1] + y_spacing*step_num
        z_pos = start_pos[2] + z_spacing*step_num
        positions.append((x_pos, y_pos, z_pos))
    return positions
    
def get_region_1_x_offset(start_pos, end_pos, x_step_size):
    positions = get_stitched_positions(start_pos, end_pos, x_step_size)
    capillary_image = get_capillary_image(positions)
    features = get_features(capillary_image)
    #If no features are found, assume system was triggered by a bubble or some other dark object
    #that isn't a fish.
    if not features:
        raise exceptions.BubbleException("Bubble detected. Skipping.")
    centroids = get_centroids(features)
    return get_x_offset_um(centroids)

def get_features(capillary_image):
    std = np.std(capillary_image)
    median = np.median(capillary_image)
    #threshold value. Uses median and std for consistency with different exposure
    threshold = median - STD_FACTOR*std
    #thresholded image
    threshed = capillary_image < threshold
    #Removes holes in objects (such as from bright pixels in swim bladder). Area argument here
    #is somewhat arbitrary, but should be large enough for holes in swim bladder to be filled.
    filled = morphology.remove_small_holes(threshed, core.get_pixel_size_um()*HOLE_AREA_UM)
    #label image so we can extract properties using skimage regionprops
    labeled = measure.label(filled)
    #creates list of region properties that meet criteria for fish features. Eccentricity to
    #ensure objects are round and area to ensure they're the correct size.
    return [f for f in measure.regionprops(labeled) if f.eccentricity < ECCENTRICITY_LIMIT and f.area > core.get_pixel_size_um()*FEATURE_AREA_UM]
            
def get_centroids(features: list[measure._regionprops._RegionProperties]):
    centroids = [f.centroid for f in features]
    while len(centroids) > NUM_FEATURES:
        for centroid in centroids:
            #checks if any other centroid x-coords are less than distance away. If so,
            #removes centroid from centroids. This is to remove features that are redundant,
            #such as if the fish is on its side and te eyes are segmented as separate objects.
            if any([abs(c[1] - centroid[1]) <= SAME_FEATURE_MAX_D and c!= centroid for c in centroids]):
                centroids.remove(centroid)
                #break to force check number of elements in centroids and continue 
                #removal if necessary
                break
    #raises exception if distance is too large to be features in same position
    else:
        raise exceptions.WeirdFishException("Detection has found three or more features. Skipping.")


def get_x_offset_um(centroids: list[tuple[float, float]]):
    x_positions = [c[1] for c in centroids]
    pixel_size = core.get_pixel_size_um()
    #distance between centroids in um
    dx_um = abs(x_positions[1] - x_positions[0])*pixel_size
    #mean of centroids in um relative to stage position at x=0 in
    #capillary image.
    x_mean_um = np.mean(x_positions)*pixel_size
    #offset to make position centered instead of on the left side of the camera
    #field.
    center_offset = -0.5*core.get_image_width()*pixel_size
    #offset of region 1 position from mean position.
    region_1_offset = -dx_um*DX_FACTOR
    #offset being x_mean_um would move stage so that left side of camera field
    #goes to x_mean_um position since offset is based on number of pixels in
    #image, and left side of image is x=0. Therefore, to center, add 1/2 image
    #width. Then, add region_1_offset to center stage at correct region 1 position.
    return x_mean_um + center_offset + region_1_offset


def fish_detected(image, bg_image_std, bg_image_mean):
    return np.mean(image) < bg_image_mean - bg_image_std
