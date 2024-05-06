import numpy as np
import skimage
import skimage.measure
import scipy
from skimage import measure, morphology

from LS_Pycro_App.hardware import Camera, Stage
from LS_Pycro_App.utils import pycro, stitch, exceptions
from LS_Pycro_App.utils.pycro import core


CORR_TEMPLATE_PATH = "/LS_Pycro_App/utils/fish_template.png"
HOLE_AREA_UM = 4500
FEATURE_AREA_UM = 65000
SAME_FEATURE_MAX_D = 300
ECCENTRICITY_LIMIT = 0.95
NUM_FEATURES = 2
STD_FACTOR = 1.6
DX_FACTOR = 0.2
CROSS_CORRECTION = 1400


def wait_for_fish():
    core.stop_sequence_acquisition()
    core.start_continuous_sequence_acquisition(0)
    while True:
        if core.get_remaining_image_count() > 0:
            image = pycro.pop_next_image().get_raw_pixels()
            if np.mean(image) < 30:
                break
            core.clear_circular_buffer()
        else:
            core.sleep(0.5)
    core.stop_sequence_acquisition()
    core.clear_circular_buffer()
        
        
def get_stitched_image(stitched_positions):
        images = []
        for pos in stitched_positions:
            Stage.set_x_position(pos[0])
            Stage.set_y_position(pos[1])
            Stage.set_z_position(pos[2])
            Stage.wait_for_xy_stage()
            Stage.wait_for_z_stage()
            #Just to make sure bright field is being used.
            pycro.set_channel(pycro.BF_CHANNEL)
            Camera.snap_image()
            image = pycro.pop_next_image().get_raw_pixels()
            images.append(image)
        return stitch.stitch_images(images, stitched_positions, x_stage_polarity=-1)


def get_stitched_positions(start_pos, end_pos, x_step_size):
    num_steps = int(np.ceil(abs(end_pos[0]-start_pos[0])/x_step_size))
    #all increments are just linear functions using end positions and num steps
    x_incr = (end_pos[0]-start_pos[0])/num_steps
    y_incr = (end_pos[1]-start_pos[1])/num_steps
    z_incr = (end_pos[2]-start_pos[2])/num_steps
    positions = []
    for step_num in range(num_steps):
        x_pos = start_pos[0] + x_incr*step_num
        y_pos = start_pos[1] + y_incr*step_num
        z_pos = start_pos[2] + z_incr*step_num
        positions.append((x_pos, y_pos, z_pos))
    return positions

    
def get_region_1_x_offset(start_pos, end_pos, x_step_size):
    positions = get_stitched_positions(start_pos, end_pos, x_step_size)
    capillary_image = get_stitched_image(positions)
    return get_cross_cor_offset_um(capillary_image)


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
            

def get_centroids(features):
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
        #if no element was removed from centroids but len(centroids) is still
        #greater than the number of expected features, raise exception.
        else:
            raise exceptions.WeirdFishException
    #either returns list of centroids or raises exception
    return centroids


def get_x_offset_um(centroids: list[tuple[float, float]],
                    stitched_image_shape: tuple[int],
                    left_side_entry: bool = False):
    x_positions = [c[1] for c in centroids]
    x_mean = np.mean(x_positions)
    #offset position is relative to the start position, which depends on which side
    #of the image the fish entered from.
    if left_side_entry:
        #If fish enters from left side, offset is relative to left side of image,
        #so the x=0 coordinate, and so just use the mean.
        offset = x_mean
    else:
        #If fish comes in from the right of the stitched image, then the offset is
        #relative to the right side of the image, not the left, so subtract
        #mean from width of image.
        offset = stitched_image_shape[1] - x_mean
    #In both cases, using only the mean will place the centroid at the edge of the screen
    #with the eye in the field of view. Since region 1 is where the swim bladder is 
    #in the field of view, we subtract the camera image width to move to the other side.
    offset += -core.get_image_width()
    #We make one more adjustmet to the offset to correctly move the stage so that we're
    #looking at region 1 of the fish, based on the distance between the x coords of the
    #centroids.
    dx = abs(x_positions[1] - x_positions[0])
    offset += -DX_FACTOR*dx
    return offset*core.get_pixel_size_um()


def fish_detected(image, bg_image_std, bg_image_mean):
    return np.mean(image) < bg_image_mean - bg_image_std


def get_cross_cor_offset_um(capillary_image: np.ndarray):
    template = skimage.io.imread(CORR_TEMPLATE_PATH)
    capillary = skimage.exposure.rescale_intensity(capillary_image)
    image_1d = np.mean(capillary, 0)
    template_1d = np.mean(template, 0)
    #cross correlation requires functions to be centered at zero.
    zero_rms_stitched = image_1d - np.mean(image_1d)
    zero_rms_template = template_1d - np.mean(template_1d)
    cross_offset = np.argmax(scipy.signal.correlate(zero_rms_stitched, zero_rms_template, "valid"))
    #CROSS_CORRECTION is the position of region 1 relative to the template.
    #We subtract the offset from the image width because position of fish is relative to
    #where the fish entered from (the start position), which is currently from the right 
    #side of the image.
    corrected_offset = capillary_image.shape[1] - (cross_offset + CROSS_CORRECTION)
    #returns offset as um offset for stage
    return corrected_offset*core.get_pixel_size_um()


