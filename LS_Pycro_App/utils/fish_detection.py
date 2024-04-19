import numpy as np
import skimage
from skimage import measure, morphology
import skimage.measure

from hardware import Camera, Stage
from utils import pycro, stitch, exceptions
from utils.pycro import core


HOLE_AREA_UM = 4500
FEATURE_AREA_UM = 65000
SAME_FEATURE_MAX_D = 300
ECCENTRICITY_LIMIT = 0.95
NUM_FEATURES = 2
STD_FACTOR = 1.6


def wait_for_fish(bg_image: np.ndarray):
    fish_detected = False
    bg_image_mean = np.mean(bg_image)
    bg_image_std = np.std(bg_image)
    while not fish_detected:
        Camera.snap_image()
        image = pycro.pop_next_image().get_raw_pixels()
        if np.mean(image) < bg_image_mean - bg_image_std:
            return True
        
def get_capillary_image(start_pos: tuple[float, float, float], 
                        end_pos: tuple[float, float, float]):

        x_0 = start_pos[0]
        y_0 = start_pos[1]
        z_0 = start_pos[2]
        x_1 = end_pos[0]
        y_1 = end_pos[1]
        z_1 = end_pos[2]

        pixel_size = core.get_pixel_size_um()
        image_width_um = pixel_size*core.get_image_width()
        #0.90 provides 10% overlap for stitched image
        x_spacing = 0.9*image_width_um
        num_steps = int(np.ceil(np.abs((x_1-x_0)/x_spacing)))
        y_spacing = (y_1-y_0)/num_steps

        images = []
        positions = []
        for step_num in range(num_steps):
            x_pos = x_0 + x_spacing*step_num
            y_pos = y_0 + y_spacing*step_num
            positions.append((x_pos, y_pos))

            Stage.set_x_position(x_pos)
            Stage.set_y_position(y_0)
            Stage.set_z_position(z_0)
            Stage.wait_for_xy_stage()
            Stage.wait_for_z_stage()
            Camera.snap_image()
            image = pycro.pop_next_image().get_raw_pixels()
            images.append(image)
        
        return stitch.stitch_images(images, positions)
        
    
def get_region_1_x_pos(capillary_image):
    image = skimage.exposure.rescale_intensity(capillary_image)
    std = np.std(image)
    median = np.median(image)
    threshold = median - STD_FACTOR*std
    threshed = capillary_image < threshold
    #Removes holes in objects (such a-s from bright pixels in swim bladder). Area argument here
    #is somewat
    filled = morphology.remove_small_holes(threshed, core.get_pixel_size_um()*HOLE_AREA_UM)
    labeled = measure.label(filled)
    features = [f for f in measure.regionprops(labeled) if f.eccentricity < ECCENTRICITY_LIMIT and f.area > core.get_pixel_size_um()*FEATURE_AREA_UM]
    #If more than just the eye and swim bladder are detected (ie, if fish is on its 
    #side and there are two eyes)
    if not features:
        raise exceptions.BubbleException
    centroids = get_centroids(features)
    x_pos = get_x_pos_from_centroids(centroids)
            
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


def get_x_pos_from_centroids(centroids: list[tuple[float, float]]):
    x_positions = [c[1] for c in centroids]
    dx = abs(x_positions[1] - x_positions[0])
    x_mean = np.mean(x_positions)


def fish_detected(bg_image_mean, bg_image_std):
    Camera.snap_image()
    image = pycro.pop_next_image().get_raw_pixels()
    return np.mean(image) < bg_image_mean - bg_image_std
