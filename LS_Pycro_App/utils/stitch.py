import numpy as np
import skimage

from LS_Pycro_App.utils.pycro import core


def stitch_images(images: list[np.ndarray],
                  positions: list[tuple[float, float, float]],
                  x_stage_polarity: int = 1,
                  y_stage_polarity: int = 1
                  ) -> np.ndarray:
    """
    Stitches images with micro-manager metadata. 
    """
    for image_num, image in enumerate(images):
        if image_num == 0:
            start_position = positions[image_num]
            pixel_size = core.get_pixel_size_um()
            stitched_x_range, stitched_y_range = _init_ranges(image.shape)
            stitched_image = image
        else:
            x_offset, y_offset = _get_xy_offsets(
                start_position, positions[image_num], pixel_size, x_stage_polarity, y_stage_polarity)
            stitched_image = _stitch_new_image(
                image, stitched_image, x_offset, y_offset, 
                stitched_x_range, stitched_y_range)
    return stitched_image


def _init_ranges(shape: tuple[int, int]) -> tuple[list]:
    """
    Initializes x and y ranges to be used in dynamic resizing of stitched
    image.
    """
    stitched_x_range = [0, shape[1]]
    stitched_y_range = [0, shape[0]]
    return stitched_x_range, stitched_y_range


def _get_xy_offsets(start_position: list[int], 
                    position: list[int], 
                    pixel_size: float,
                    x_stage_polarity: int = 1,
                    y_stage_polarity: int = 1
                    ) -> tuple[int]:
    """
    Returns x and y pixel offets relative to the position of the first image
    added to the stitched image. 
    """
    x_offset = x_stage_polarity*_get_pixel_offset(start_position[0], position[0], pixel_size)
    y_offset = y_stage_polarity*_get_pixel_offset(start_position[1], position[1], pixel_size)
    return x_offset, y_offset


def _get_pixel_offset(start_um: float, 
                      end_um: float, 
                      pixel_size: float
                      ) -> int:
    """
    Calculates pixel offset between images based on difference in 
    stage positions and returns it.
    """
    return round((end_um - start_um)/pixel_size)


def _stitch_new_image(new_image: np.ndarray, 
                      stitched_image: np.ndarray, 
                      x_offset: int, 
                      y_offset: int, 
                      stitched_x_range: list[int], 
                      stitched_y_range: list[int]
                      ) -> np.ndarray:
    """
    Stitches new_image with stitched_image based on stage positions in
    Micro-Manager metadata.
    """
    new_x_range, new_y_range = _get_new_image_range(
        x_offset, y_offset, new_image.shape)
    x_extensions, y_extensions = _get_stitched_extensions(
        stitched_x_range, stitched_y_range, new_x_range, new_y_range)
    stitched_x_range, stitched_y_range = _update_stitched_range(
        stitched_x_range, stitched_y_range, new_x_range, new_y_range)
    
    stitched_image = _add_stitched_extensions(
        stitched_image, x_extensions, y_extensions)
    slices = _get_new_image_position_slices(
        x_extensions, y_extensions, new_image.shape)
    #If two images are added with the same stage position (ie, if z-stack 
    # is split into two files because it's too large for one), second region
    #would just overwrite the first. This takes a max projection of the
    #newly added region and the previously added one so this doesn't 
    #happen.
    stitched_region = stitched_image[slices[1], slices[0]]
    region_array = np.array((stitched_region, new_image))
    new_region = np.max(region_array, 0)
    stitched_image[slices[1], slices[0]] = new_region
    return stitched_image


def _get_new_image_range(x_stage_offset: int, 
                         y_stage_offset: int, 
                         image_dims: list[int, int]
                         ) -> tuple[list[int], list[int]]:
    """
    Gets min and max pixel positions of new_image based on x_stage_offset,
    y_stage_offset, and width and height of new_image.
    """
    new_x_range = [x_stage_offset, x_stage_offset + image_dims[1]]
    new_y_range = [y_stage_offset, y_stage_offset + image_dims[0]]
    return new_x_range, new_y_range


def _get_stitched_extensions(stitched_x_range: list[int], 
                             stitched_y_range: list[int], 
                             new_image_x_range: list[int], 
                             new_image_y_range: list[int]
                             ) -> tuple[list[int]]:
    """
    Gets stitched extensions--number of rows and columns to be concatenated
    to stitched_image--to make room for new_image to be added.
    """
    x_min_extension = stitched_x_range[0] - new_image_x_range[0]
    x_max_extension = new_image_x_range[1] - stitched_x_range[1]
    y_min_extension = stitched_y_range[0] - new_image_y_range[0]
    y_max_extension = new_image_y_range[1] - stitched_y_range[1]
    x_extensions = [x_min_extension, x_max_extension]
    y_extensions = [y_min_extension, y_max_extension]
    return x_extensions, y_extensions


def _update_stitched_range(stitched_x_range: list[int], 
                           stitched_y_range: list[int], 
                           new_x_range: list[int], 
                           new_y_range: list[int]
                           ) -> tuple[list[int]]:
    """
    Determines new stitched image range by comparing min and max values of
    old stitched image range and new image range.
    """
    
    stitched_x_range[0] = min(stitched_x_range[0], new_x_range[0])
    stitched_y_range[0] = min(stitched_y_range[0], new_y_range[0])
    stitched_x_range[1] = max(stitched_x_range[1], new_x_range[1])
    stitched_y_range[1] = max(stitched_y_range[1], new_y_range[1])
    return stitched_x_range, stitched_y_range


def _add_stitched_extensions(stitched_image: np.ndarray,
                             x_extensions: list[int], 
                             y_extensions: list[int]
                             ) -> np.ndarray:
    """
    Concatenates image extensions and stitched image. Image extensions
    are arrays of zeros that are added to the left, right, top, and bottom
    of stitched_image to make space for newly added new_image.
    """
    dtype = stitched_image.dtype
    if x_extensions[0] > 0:
        extension = np.zeros([stitched_image.shape[0], x_extensions[0]])
        stitched_image = np.c_[extension, stitched_image]
    if x_extensions[1] > 0:
        extension = np.zeros([stitched_image.shape[0], x_extensions[1]])
        stitched_image = np.c_[stitched_image, extension]
    if y_extensions[0] > 0:
        extension = np.zeros([y_extensions[0], stitched_image.shape[1]])
        stitched_image = np.concatenate([extension, stitched_image])
    if y_extensions[1] > 0:
        extension = np.zeros([y_extensions[1], stitched_image.shape[1]])
        stitched_image = np.concatenate([stitched_image, extension])

    #numpy concatenation doesn't seem to conserve datatype, so ensure
    #datatype is same as original stitched image.
    return stitched_image.astype(dtype)


def _get_new_image_position_slices(x_extensions: list[int], 
                                   y_extensions: list[int], 
                                   shape: list[int]
                                   ) -> tuple[slice, slice]:
    """
    Gets image position slices where new_image will be inserted
    into stitched_image array.
    """
    if x_extensions[0] > 0:
        x_slice = slice(0, shape[1])
    else:
        x_slice = slice(-x_extensions[0], shape[1] - x_extensions[0])

    if y_extensions[0] > 0:
        y_slice = slice(0, shape[0])
    else:
        y_slice = slice(-y_extensions[0], shape[0] - y_extensions[0])
    return x_slice, y_slice
