__FILENAME__ = chromatic_adaptation
import logging

import numpy
from numpy.linalg import pinv

from colormath import color_constants

logger = logging.getLogger(__name__)


# noinspection PyPep8Naming
def _get_adaptation_matrix(orig_illum, targ_illum, observer, adaptation):
    """
    Calculate the correct transformation matrix based on origin and target
    illuminants. The observer angle must be the same between illuminants.

    See colormath.color_constants.ADAPTATION_MATRICES for a list of possible
    adaptations.

    Detailed conversion documentation is available at:
    http://brucelindbloom.com/Eqn_ChromAdapt.html
    """

    # Get the appropriate transformation matrix, [MsubA].
    transform_matrix = color_constants.ADAPTATION_MATRICES[adaptation]
    # Calculate the inverse of the transform matrix, [MsubA]^(-1)
    transform_matrix_inverse = pinv(transform_matrix)

    # Store the XYZ coordinates of the origin illuminant. Becomes XsubWS.
    illum_from = color_constants.ILLUMINANTS[observer][orig_illum]
    # Also store the XYZ coordinates of the target illuminant. Becomes XsubWD.
    illum_to = color_constants.ILLUMINANTS[observer][targ_illum]

    # Calculate cone response domains.
    pyb_source = numpy.dot(illum_from, transform_matrix)
    pyb_dest = numpy.dot(illum_to, transform_matrix)

    # Break the cone response domains out into their appropriate variables.
    P_sub_S, Y_sub_S, B_sub_S = pyb_source[0], pyb_source[1], pyb_source[2]
    P_sub_D, Y_sub_D, B_sub_D = pyb_dest[0], pyb_dest[1], pyb_dest[2]

    # Assemble the middle matrix used in the final calculation of [M].
    middle_matrix = numpy.array(((P_sub_D / P_sub_S, 0.0, 0.0),
                                 (0.0, Y_sub_D / Y_sub_S, 0.0),
                                 (0.0, 0.0, B_sub_D / B_sub_S)))

    return numpy.dot(numpy.dot(transform_matrix, middle_matrix),
                  transform_matrix_inverse)


# noinspection PyPep8Naming
def apply_chromatic_adaptation(val_x, val_y, val_z, orig_illum, targ_illum,
                               observer='2', adaptation='bradford'):
    """
    Applies a chromatic adaptation matrix to convert XYZ values between
    illuminants. It is important to recognize that color transformation results
    in color errors, determined by how far the original illuminant is from the
    target illuminant. For example, D65 to A could result in very high maximum
    deviance.

    An informative article with estimate average Delta E values for each
    illuminant conversion may be found at:

    http://brucelindbloom.com/ChromAdaptEval.html
    """

    # It's silly to have to do this, but some people may want to call this
    # function directly, so we'll protect them from messing up upper/lower case.
    orig_illum = orig_illum.lower()
    targ_illum = targ_illum.lower()
    adaptation = adaptation.lower()

    logger.debug("  \* Applying adaptation matrix: %s", adaptation)
    # Retrieve the appropriate transformation matrix from the constants.
    transform_matrix = _get_adaptation_matrix(orig_illum, targ_illum,
                                              observer, adaptation)

    # Stuff the XYZ values into a NumPy matrix for conversion.
    XYZ_matrix = numpy.array((val_x, val_y, val_z))
    # Perform the adaptation via matrix multiplication.
    result_matrix = numpy.dot(XYZ_matrix, transform_matrix)

    # Return individual X, Y, and Z coordinates.
    return result_matrix[0], result_matrix[1], result_matrix[2]


# noinspection PyPep8Naming
def apply_chromatic_adaptation_on_color(color, targ_illum, adaptation='bradford'):
    """
    Convenience function to apply an adaptation directly to a Color object.
    """

    xyz_x = color.xyz_x
    xyz_y = color.xyz_y
    xyz_z = color.xyz_z
    orig_illum = color.illuminant
    targ_illum = targ_illum.lower()
    observer = color.observer
    adaptation = adaptation.lower()

    # Return individual X, Y, and Z coordinates.
    color.xyz_x, color.xyz_y, color.xyz_z = apply_chromatic_adaptation(
        xyz_x, xyz_y, xyz_z, orig_illum, targ_illum,
        observer=observer, adaptation=adaptation)
    color.set_illuminant(targ_illum)

    return color

########NEW FILE########
__FILENAME__ = color_constants
"""
Contains lookup tables, constants, and things that are generally static
and useful throughout the library.
"""

import numpy

# Not sure what these are, they are used in Lab and Luv calculations.
CIE_E = 216.0 / 24389.0
CIE_K = 24389.0 / 27.0

# Observer Function and Illuminant Data
ILLUMINANTS = {
    # 2 Degree Functions
    '2': {
        'a': (1.09850, 1.00000, 0.35585),
        'b': (0.99072, 1.00000, 0.85223),
        'c': (0.98074, 1.00000, 1.18232),
        'd50': (0.96422, 1.00000, 0.82521),
        'd55': (0.95682, 1.00000, 0.92149),
        'd65': (0.95047, 1.00000, 1.08883),
        'd75': (0.94972, 1.00000, 1.22638),
        'e': (1.00000, 1.00000, 1.00000),
        'f2': (0.99186, 1.00000, 0.67393),
        'f7': (0.95041, 1.00000, 1.08747),
        'f11': (1.00962, 1.00000, 0.64350)
    },
    # 10 Degree Functions
    '10': {
        'd50': (0.9672, 1.000, 0.8143),
        'd55': (0.958, 1.000, 0.9093),
        'd65': (0.9481, 1.000, 1.073),
        'd75': (0.94416, 1.000, 1.2064),
    }
}

OBSERVERS = ILLUMINANTS.keys()

# Chromatic Adaptation Matrices
# http://brucelindbloom.com/Eqn_ChromAdapt.html
ADAPTATION_MATRICES = {
    'xyz_scaling': numpy.array((
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0))),
    'bradford': numpy.array((
        (0.8951, -0.7502, 0.0389),
        (0.2664, 1.7135, -0.0685),
        (-0.1614, 0.0367, 1.0296))),
    'von_kries': numpy.array((
        (0.40024, -0.22630, 0.00000),
        (0.70760, 1.16532, 0.00000),
        (-0.08081, 0.04570, 0.91822)))
}

########NEW FILE########
__FILENAME__ = color_conversions
"""
Conversion between color spaces.

.. note:: This module makes extensive use of imports within functions.
    That stinks.
"""

import math
import logging

import numpy

from colormath import color_constants
from colormath import spectral_constants
from colormath.color_objects import ColorBase, XYZColor, sRGBColor, LCHabColor, \
    LCHuvColor, LabColor, xyYColor, LuvColor, HSVColor, HSLColor, CMYColor, \
    CMYKColor, BaseRGBColor
from colormath.chromatic_adaptation import apply_chromatic_adaptation
from colormath.color_exceptions import InvalidIlluminantError, UndefinedConversionError


logger = logging.getLogger(__name__)


# noinspection PyPep8Naming
def apply_RGB_matrix(var1, var2, var3, rgb_type, convtype="xyz_to_rgb"):
    """
    Applies an RGB working matrix to convert from XYZ to RGB.
    The arguments are tersely named var1, var2, and var3 to allow for the passing
    of XYZ _or_ RGB values. var1 is X for XYZ, and R for RGB. var2 and var3
    follow suite.
    """

    convtype = convtype.lower()
    # Retrieve the appropriate transformation matrix from the constants.
    rgb_matrix = rgb_type.conversion_matrices[convtype]
   
    logger.debug("  \* Applying RGB conversion matrix: %s->%s",
                 rgb_type.__class__.__name__, convtype)
    # Stuff the RGB/XYZ values into a NumPy matrix for conversion.
    var_matrix = numpy.array((
        var1, var2, var3
    ))
    # Perform the adaptation via matrix multiplication.
    result_matrix = numpy.dot(var_matrix, rgb_matrix)
    return result_matrix[0], result_matrix[1], result_matrix[2]


# noinspection PyPep8Naming,PyUnusedLocal
def Spectral_to_XYZ(cobj, illuminant_override=None, *args, **kwargs):
    """
    Converts spectral readings to XYZ.
    """
    
    # If the user provides an illuminant_override numpy array, use it.
    if illuminant_override:
        reference_illum = illuminant_override
    else:
        # Otherwise, look up the illuminant from known standards based
        # on the value of 'illuminant' pulled from the SpectralColor object.
        try:
            reference_illum = spectral_constants.REF_ILLUM_TABLE[cobj.illuminant]
        except KeyError:
            raise InvalidIlluminantError(cobj.illuminant)
        
    # Get the spectral distribution of the selected standard observer.
    if cobj.observer == '10':
        std_obs_x = spectral_constants.STDOBSERV_X10
        std_obs_y = spectral_constants.STDOBSERV_Y10
        std_obs_z = spectral_constants.STDOBSERV_Z10
    else:
        # Assume 2 degree, since it is theoretically the only other possibility.
        std_obs_x = spectral_constants.STDOBSERV_X2
        std_obs_y = spectral_constants.STDOBSERV_Y2
        std_obs_z = spectral_constants.STDOBSERV_Z2
     
    # This is a NumPy array containing the spectral distribution of the color.
    sample = cobj.get_numpy_array()
    
    # The denominator is constant throughout the entire calculation for X,
    # Y, and Z coordinates. Calculate it once and re-use.
    denom = std_obs_y * reference_illum
    
    # This is also a common element in the calculation whereby the sample
    # NumPy array is multiplied by the reference illuminant's power distribution
    # (which is also a NumPy array).
    sample_by_ref_illum = sample * reference_illum
        
    # Calculate the numerator of the equation to find X.
    x_numerator = sample_by_ref_illum * std_obs_x
    y_numerator = sample_by_ref_illum * std_obs_y
    z_numerator = sample_by_ref_illum * std_obs_z
    
    xyz_x = x_numerator.sum() / denom.sum()
    xyz_y = y_numerator.sum() / denom.sum()
    xyz_z = z_numerator.sum() / denom.sum()
    
    return XYZColor(
        xyz_x, xyz_y, xyz_z, observer=cobj.observer, illuminant=cobj.illuminant)


# noinspection PyPep8Naming,PyUnusedLocal
def Lab_to_LCHab(cobj, *args, **kwargs):
    """
    Convert from CIE Lab to LCH(ab).
    """
   
    lch_l = cobj.lab_l
    lch_c = math.sqrt(math.pow(float(cobj.lab_a), 2) + math.pow(float(cobj.lab_b), 2))
    lch_h = math.atan2(float(cobj.lab_b), float(cobj.lab_a))
   
    if lch_h > 0:
        lch_h = (lch_h / math.pi) * 180
    else:
        lch_h = 360 - (math.fabs(lch_h) / math.pi) * 180
      
    return LCHabColor(
        lch_l, lch_c, lch_h, observer=cobj.observer, illuminant=cobj.illuminant)


# noinspection PyPep8Naming,PyUnusedLocal
def Lab_to_XYZ(cobj, *args, **kwargs):
    """
    Convert from Lab to XYZ
    """

    illum = cobj.get_illuminant_xyz()
    xyz_y = (cobj.lab_l + 16.0) / 116.0
    xyz_x = cobj.lab_a / 500.0 + xyz_y
    xyz_z = xyz_y - cobj.lab_b / 200.0
   
    if math.pow(xyz_y, 3) > color_constants.CIE_E:
        xyz_y = math.pow(xyz_y, 3)
    else:
        xyz_y = (xyz_y - 16.0 / 116.0) / 7.787

    if math.pow(xyz_x, 3) > color_constants.CIE_E:
        xyz_x = math.pow(xyz_x, 3)
    else:
        xyz_x = (xyz_x - 16.0 / 116.0) / 7.787
      
    if math.pow(xyz_z, 3) > color_constants.CIE_E:
        xyz_z = math.pow(xyz_z, 3)
    else:
        xyz_z = (xyz_z - 16.0 / 116.0) / 7.787
      
    xyz_x = (illum["X"] * xyz_x)
    xyz_y = (illum["Y"] * xyz_y)
    xyz_z = (illum["Z"] * xyz_z)
    
    return XYZColor(
        xyz_x, xyz_y, xyz_z, observer=cobj.observer, illuminant=cobj.illuminant)


# noinspection PyPep8Naming,PyUnusedLocal
def Luv_to_LCHuv(cobj, *args, **kwargs):
    """
    Convert from CIE Luv to LCH(uv).
    """
   
    lch_l = cobj.luv_l
    lch_c = math.sqrt(math.pow(cobj.luv_u, 2.0) + math.pow(cobj.luv_v, 2.0))
    lch_h = math.atan2(float(cobj.luv_v), float(cobj.luv_u))
   
    if lch_h > 0:
        lch_h = (lch_h / math.pi) * 180
    else:
        lch_h = 360 - (math.fabs(lch_h) / math.pi) * 180
    return LCHuvColor(
        lch_l, lch_c, lch_h, observer=cobj.observer, illuminant=cobj.illuminant)


# noinspection PyPep8Naming,PyUnusedLocal
def Luv_to_XYZ(cobj, *args, **kwargs):
    """
    Convert from Luv to XYZ.
    """

    illum = cobj.get_illuminant_xyz()
    # Without Light, there is no color. Short-circuit this and avoid some
    # zero division errors in the var_a_frac calculation.
    if cobj.luv_l <= 0.0:
        xyz_x = 0.0
        xyz_y = 0.0
        xyz_z = 0.0
        return XYZColor(
            xyz_x, xyz_y, xyz_z, observer=cobj.observer, illuminant=cobj.illuminant)

    # Various variables used throughout the conversion.
    cie_k_times_e = color_constants.CIE_K * color_constants.CIE_E
    u_sub_0 = (4.0 * illum["X"]) / (illum["X"] + 15.0 * illum["Y"] + 3.0 * illum["Z"])
    v_sub_0 = (9.0 * illum["Y"]) / (illum["X"] + 15.0 * illum["Y"] + 3.0 * illum["Z"])
    var_u = cobj.luv_u / (13.0 * cobj.luv_l) + u_sub_0
    var_v = cobj.luv_v / (13.0 * cobj.luv_l) + v_sub_0

    # Y-coordinate calculations.
    if cobj.luv_l > cie_k_times_e:
        xyz_y = math.pow((cobj.luv_l + 16.0) / 116.0, 3.0)
    else:
        xyz_y = cobj.luv_l / color_constants.CIE_K

    # X-coordinate calculation.
    xyz_x = xyz_y * 9.0 * var_u / (4.0 * var_v)
    # Z-coordinate calculation.
    xyz_z = xyz_y * (12.0 - 3.0 * var_u - 20.0 * var_v) / (4.0 * var_v)

    return XYZColor(
        xyz_x, xyz_y, xyz_z, illuminant=cobj.illuminant, observer=cobj.observer)


# noinspection PyPep8Naming,PyUnusedLocal
def LCHab_to_Lab(cobj, *args, **kwargs):
    """
    Convert from LCH(ab) to Lab.
    """
   
    lab_l = cobj.lch_l
    lab_a = math.cos(math.radians(cobj.lch_h)) * cobj.lch_c
    lab_b = math.sin(math.radians(cobj.lch_h)) * cobj.lch_c
    return LabColor(
        lab_l, lab_a, lab_b, illuminant=cobj.illuminant, observer=cobj.observer)


# noinspection PyPep8Naming,PyUnusedLocal
def LCHuv_to_Luv(cobj, *args, **kwargs):
    """
    Convert from LCH(uv) to Luv.
    """
   
    luv_l = cobj.lch_l
    luv_u = math.cos(math.radians(cobj.lch_h)) * cobj.lch_c
    luv_v = math.sin(math.radians(cobj.lch_h)) * cobj.lch_c
    return LuvColor(
        luv_l, luv_u, luv_v, illuminant=cobj.illuminant, observer=cobj.observer)


# noinspection PyPep8Naming,PyUnusedLocal
def xyY_to_XYZ(cobj, *args, **kwargs):
    """
    Convert from xyY to XYZ.
    """
   
    xyz_x = (cobj.xyy_x * cobj.xyy_Y) / cobj.xyy_y
    xyz_y = cobj.xyy_Y
    xyz_z = ((1.0 - cobj.xyy_x - cobj.xyy_y) * xyz_y) / cobj.xyy_y
    
    return XYZColor(
        xyz_x, xyz_y, xyz_z, illuminant=cobj.illuminant, observer=cobj.observer)


# noinspection PyPep8Naming,PyUnusedLocal
def XYZ_to_xyY(cobj, *args, **kwargs):
    """
    Convert from XYZ to xyY.
    """

    xyy_x = cobj.xyz_x / (cobj.xyz_x + cobj.xyz_y + cobj.xyz_z)
    xyy_y = cobj.xyz_y / (cobj.xyz_x + cobj.xyz_y + cobj.xyz_z)
    xyy_Y = cobj.xyz_y

    return xyYColor(
        xyy_x, xyy_y, xyy_Y, observer=cobj.observer, illuminant=cobj.illuminant)


# noinspection PyPep8Naming,PyUnusedLocal
def XYZ_to_Luv(cobj, *args, **kwargs):
    """
    Convert from XYZ to Luv
    """
   
    temp_x = cobj.xyz_x
    temp_y = cobj.xyz_y
    temp_z = cobj.xyz_z
   
    luv_u = (4.0 * temp_x) / (temp_x + (15.0 * temp_y) + (3.0 * temp_z))
    luv_v = (9.0 * temp_y) / (temp_x + (15.0 * temp_y) + (3.0 * temp_z))

    illum = cobj.get_illuminant_xyz()
    temp_y = temp_y / illum["Y"]
    if temp_y > color_constants.CIE_E:
        temp_y = math.pow(temp_y, (1.0 / 3.0))
    else:
        temp_y = (7.787 * temp_y) + (16.0 / 116.0)
   
    ref_U = (4.0 * illum["X"]) / (illum["X"] + (15.0 * illum["Y"]) + (3.0 * illum["Z"]))
    ref_V = (9.0 * illum["Y"]) / (illum["X"] + (15.0 * illum["Y"]) + (3.0 * illum["Z"]))
   
    luv_l = (116.0 * temp_y) - 16.0
    luv_u = 13.0 * luv_l * (luv_u - ref_U)
    luv_v = 13.0 * luv_l * (luv_v - ref_V)
   
    return LuvColor(
        luv_l, luv_u, luv_v, observer=cobj.observer, illuminant=cobj.illuminant)


# noinspection PyPep8Naming,PyUnusedLocal
def XYZ_to_Lab(cobj, *args, **kwargs):
    """
    Converts XYZ to Lab.
    """

    illum = cobj.get_illuminant_xyz()
    temp_x = cobj.xyz_x / illum["X"]
    temp_y = cobj.xyz_y / illum["Y"]
    temp_z = cobj.xyz_z / illum["Z"]
   
    if temp_x > color_constants.CIE_E:
        temp_x = math.pow(temp_x, (1.0 / 3.0))
    else:
        temp_x = (7.787 * temp_x) + (16.0 / 116.0)     

    if temp_y > color_constants.CIE_E:
        temp_y = math.pow(temp_y, (1.0 / 3.0))
    else:
        temp_y = (7.787 * temp_y) + (16.0 / 116.0)
   
    if temp_z > color_constants.CIE_E:
        temp_z = math.pow(temp_z, (1.0 / 3.0))
    else:
        temp_z = (7.787 * temp_z) + (16.0 / 116.0)
      
    lab_l = (116.0 * temp_y) - 16.0
    lab_a = 500.0 * (temp_x - temp_y)
    lab_b = 200.0 * (temp_y - temp_z)
    return LabColor(
        lab_l, lab_a, lab_b, observer=cobj.observer, illuminant=cobj.illuminant)


# noinspection PyPep8Naming,PyUnusedLocal
def XYZ_to_RGB(cobj, target_rgb, *args, **kwargs):
    """
    XYZ to RGB conversion.
    """

    temp_X = cobj.xyz_x
    temp_Y = cobj.xyz_y
    temp_Z = cobj.xyz_z

    logger.debug("  \- Target RGB space: %s", target_rgb)
    target_illum = target_rgb.native_illuminant
    logger.debug("  \- Target native illuminant: %s", target_illum)
    logger.debug("  \- XYZ color's illuminant: %s", cobj.illuminant)
   
    # If the XYZ values were taken with a different reference white than the
    # native reference white of the target RGB space, a transformation matrix
    # must be applied.
    if cobj.illuminant != target_illum:
        logger.debug("  \* Applying transformation from %s to %s ",
                     cobj.illuminant, target_illum)
        # Get the adjusted XYZ values, adapted for the target illuminant.
        temp_X, temp_Y, temp_Z = apply_chromatic_adaptation(
            temp_X, temp_Y, temp_Z,
            orig_illum=cobj.illuminant, targ_illum=target_illum)
        logger.debug("  \*   New values: %.3f, %.3f, %.3f",
                     temp_X, temp_Y, temp_Z)
   
    # Apply an RGB working space matrix to the XYZ values (matrix mul).
    rgb_r, rgb_g, rgb_b = apply_RGB_matrix(
        temp_X, temp_Y, temp_Z,
        rgb_type=target_rgb, convtype="xyz_to_rgb")

    # v
    linear_channels = dict(r=rgb_r, g=rgb_g, b=rgb_b)
    # V
    nonlinear_channels = {}
    if target_rgb == sRGBColor:
        for channel in ['r', 'g', 'b']:
            v = linear_channels[channel]
            if v <= 0.0031308:
                nonlinear_channels[channel] = v * 12.92
            else:
                nonlinear_channels[channel] = 1.055 * math.pow(v, 1 / 2.4) - 0.055
    else:
        # If it's not sRGB...
        for channel in ['r', 'g', 'b']:
            v = linear_channels[channel]
            nonlinear_channels[channel] = math.pow(v, 1 / target_rgb.rgb_gamma)

    return target_rgb(
        nonlinear_channels['r'], nonlinear_channels['g'], nonlinear_channels['b'])


# noinspection PyPep8Naming,PyUnusedLocal
def RGB_to_XYZ(cobj, target_illuminant=None, *args, **kwargs):
    """
    RGB to XYZ conversion. Expects 0-255 RGB values.

    Based off of: http://www.brucelindbloom.com/index.html?Eqn_RGB_to_XYZ.html
    """

    # Will contain linearized RGB channels (removed the gamma func).
    linear_channels = {}

    if isinstance(cobj, sRGBColor):
        for channel in ['r', 'g', 'b']:
            V = getattr(cobj, 'rgb_' + channel)
            if V <= 0.04045:
                linear_channels[channel] = V / 12.92
            else:
                linear_channels[channel] = math.pow((V + 0.055) / 1.055, 2.4)
    else:
        # If it's not sRGB...
        gamma = cobj.rgb_gamma

        for channel in ['r', 'g', 'b']:
            V = getattr(cobj, 'rgb_' + channel)
            linear_channels[channel] = math.pow(V, gamma)
        
    # Apply an RGB working space matrix to the XYZ values (matrix mul).
    xyz_x, xyz_y, xyz_z = apply_RGB_matrix(
        linear_channels['r'], linear_channels['g'], linear_channels['b'],
        rgb_type=cobj, convtype="rgb_to_xyz")

    if target_illuminant is None:
        target_illuminant = cobj.native_illuminant
    
    # The illuminant of the original RGB object. This will always match
    # the RGB colorspace's native illuminant.
    illuminant = cobj.native_illuminant
    xyzcolor = XYZColor(xyz_x, xyz_y, xyz_z, illuminant=illuminant)
    # This will take care of any illuminant changes for us (if source
    # illuminant != target illuminant).
    xyzcolor.apply_adaptation(target_illuminant)

    return xyzcolor


# noinspection PyPep8Naming,PyUnusedLocal
def __RGB_to_Hue(var_R, var_G, var_B, var_min, var_max):
    """
    For RGB_to_HSL and RGB_to_HSV, the Hue (H) component is calculated in
    the same way.
    """

    if var_max == var_min:
        return 0.0
    elif var_max == var_R:
        return (60.0 * ((var_G - var_B) / (var_max - var_min)) + 360) % 360.0
    elif var_max == var_G:
        return 60.0 * ((var_B - var_R) / (var_max - var_min)) + 120
    elif var_max == var_B:
        return 60.0 * ((var_R - var_G) / (var_max - var_min)) + 240.0


# noinspection PyPep8Naming,PyUnusedLocal
def RGB_to_HSV(cobj, *args, **kwargs):
    """
    Converts from RGB to HSV.
    
    H values are in degrees and are 0 to 360.
    S values are a percentage, 0.0 to 1.0.
    V values are a percentage, 0.0 to 1.0.
    """

    var_R = cobj.rgb_r
    var_G = cobj.rgb_g
    var_B = cobj.rgb_b
    
    var_max = max(var_R, var_G, var_B)
    var_min = min(var_R, var_G, var_B)
    
    var_H = __RGB_to_Hue(var_R, var_G, var_B, var_min, var_max)
    
    if var_max == 0:
        var_S = 0
    else:
        var_S = 1.0 - (var_min / var_max)
        
    var_V = var_max

    hsv_h = var_H
    hsv_s = var_S
    hsv_v = var_V

    return HSVColor(
        var_H, var_S, var_V)


# noinspection PyPep8Naming,PyUnusedLocal
def RGB_to_HSL(cobj, *args, **kwargs):
    """
    Converts from RGB to HSL.
    
    H values are in degrees and are 0 to 360.
    S values are a percentage, 0.0 to 1.0.
    L values are a percentage, 0.0 to 1.0.
    """
    
    var_R = cobj.rgb_r
    var_G = cobj.rgb_g
    var_B = cobj.rgb_b
    
    var_max = max(var_R, var_G, var_B)
    var_min = min(var_R, var_G, var_B)
    
    var_H = __RGB_to_Hue(var_R, var_G, var_B, var_min, var_max)
    var_L = 0.5 * (var_max + var_min)
    
    if var_max == var_min:
        var_S = 0
    elif var_L <= 0.5:
        var_S = (var_max - var_min) / (2.0 * var_L)
    else:
        var_S = (var_max - var_min) / (2.0 - (2.0 * var_L))
    
    return HSLColor(
        var_H, var_S, var_L)


# noinspection PyPep8Naming,PyUnusedLocal
def __Calc_HSL_to_RGB_Components(var_q, var_p, C):
    """
    This is used in HSL_to_RGB conversions on R, G, and B.
    """

    if C < 0:
        C += 1.0
    if C > 1:
        C -= 1.0

    # Computing C of vector (Color R, Color G, Color B)
    if C < (1.0 / 6.0):
        return var_p + ((var_q - var_p) * 6.0 * C)
    elif (1.0 / 6.0) <= C < 0.5:
        return var_q
    elif 0.5 <= C < (2.0 / 3.0):
        return var_p + ((var_q - var_p) * 6.0 * ((2.0 / 3.0) - C))
    else:
        return var_p


# noinspection PyPep8Naming,PyUnusedLocal
def HSV_to_RGB(cobj, target_rgb, *args, **kwargs):
    """
    HSV to RGB conversion.
    
    H values are in degrees and are 0 to 360.
    S values are a percentage, 0.0 to 1.0.
    V values are a percentage, 0.0 to 1.0.
    """
    
    H = cobj.hsv_h
    S = cobj.hsv_s
    V = cobj.hsv_v
    
    h_floored = int(math.floor(H))
    h_sub_i = int(h_floored / 60) % 6
    var_f = (H / 60.0) - (h_floored // 60)
    var_p = V * (1.0 - S)
    var_q = V * (1.0 - var_f * S)
    var_t = V * (1.0 - (1.0 - var_f) * S)
       
    if h_sub_i == 0:
        rgb_r = V
        rgb_g = var_t
        rgb_b = var_p
    elif h_sub_i == 1:
        rgb_r = var_q
        rgb_g = V
        rgb_b = var_p
    elif h_sub_i == 2:
        rgb_r = var_p
        rgb_g = V
        rgb_b = var_t
    elif h_sub_i == 3:
        rgb_r = var_p
        rgb_g = var_q
        rgb_b = V
    elif h_sub_i == 4:
        rgb_r = var_t
        rgb_g = var_p
        rgb_b = V
    elif h_sub_i == 5:
        rgb_r = V
        rgb_g = var_p
        rgb_b = var_q
    else:
        raise ValueError("Unable to convert HSL->RGB due to value error.")

    # In the event that they define an HSV color and want to convert it to 
    # a particular RGB space, let them override it here.
    if target_rgb is not None:
        rgb_type = target_rgb
    else:
        rgb_type = cobj.rgb_type
        
    return target_rgb(rgb_r, rgb_g, rgb_b)


# noinspection PyPep8Naming,PyUnusedLocal
def HSL_to_RGB(cobj, target_rgb, *args, **kwargs):
    """
    HSL to RGB conversion.
    """
    
    H = cobj.hsl_h
    S = cobj.hsl_s
    L = cobj.hsl_l
    
    if L < 0.5:
        var_q = L * (1.0 + S)
    else:
        var_q = L + S - (L * S)
        
    var_p = 2.0 * L - var_q
    
    # H normalized to range [0,1]
    h_sub_k = (H / 360.0)
    
    t_sub_R = h_sub_k + (1.0 / 3.0)
    t_sub_G = h_sub_k
    t_sub_B = h_sub_k - (1.0 / 3.0)
    
    rgb_r = __Calc_HSL_to_RGB_Components(var_q, var_p, t_sub_R)
    rgb_g = __Calc_HSL_to_RGB_Components(var_q, var_p, t_sub_G)
    rgb_b = __Calc_HSL_to_RGB_Components(var_q, var_p, t_sub_B)

    # In the event that they define an HSV color and want to convert it to 
    # a particular RGB space, let them override it here.
    if target_rgb is not None:
        rgb_type = target_rgb
    else:
        rgb_type = cobj.rgb_type
    
    return target_rgb(rgb_r, rgb_g, rgb_b)


# noinspection PyPep8Naming,PyUnusedLocal
def RGB_to_CMY(cobj, *args, **kwargs):
    """
    RGB to CMY conversion.
    
    NOTE: CMYK and CMY values range from 0.0 to 1.0
    """
   
    cmy_c = 1.0 - cobj.rgb_r
    cmy_m = 1.0 - cobj.rgb_g
    cmy_y = 1.0 - cobj.rgb_b
    
    return CMYColor(cmy_c, cmy_m, cmy_y)


# noinspection PyPep8Naming,PyUnusedLocal
def CMY_to_RGB(cobj, target_rgb, *args, **kwargs):
    """
    Converts CMY to RGB via simple subtraction.
    
    NOTE: Returned values are in the range of 0-255.
    """
    
    rgb_r = 1.0 - cobj.cmy_c
    rgb_g = 1.0 - cobj.cmy_m
    rgb_b = 1.0 - cobj.cmy_y
    
    return target_rgb(rgb_r, rgb_g, rgb_b)


# noinspection PyPep8Naming,PyUnusedLocal
def CMY_to_CMYK(cobj, *args, **kwargs):
    """
    Converts from CMY to CMYK.
    
    NOTE: CMYK and CMY values range from 0.0 to 1.0
    """

    var_k = 1.0
    if cobj.cmy_c < var_k:
        var_k = cobj.cmy_c
    if cobj.cmy_m < var_k:
        var_k = cobj.cmy_m
    if cobj.cmy_y < var_k:
        var_k = cobj.cmy_y
      
    if var_k == 1:
        cmyk_c = 0.0
        cmyk_m = 0.0
        cmyk_y = 0.0
    else:
        cmyk_c = (cobj.cmy_c - var_k) / (1.0 - var_k)
        cmyk_m = (cobj.cmy_m - var_k) / (1.0 - var_k)
        cmyk_y = (cobj.cmy_y - var_k) / (1.0 - var_k)
    cmyk_k = var_k

    return CMYKColor(cmyk_c, cmyk_m, cmyk_y, cmyk_k)


# noinspection PyPep8Naming,PyUnusedLocal
def CMYK_to_CMY(cobj, *args, **kwargs):
    """
    Converts CMYK to CMY.
    
    NOTE: CMYK and CMY values range from 0.0 to 1.0
    """

    cmy_c = cobj.cmyk_c * (1.0 - cobj.cmyk_k) + cobj.cmyk_k
    cmy_m = cobj.cmyk_m * (1.0 - cobj.cmyk_k) + cobj.cmyk_k
    cmy_y = cobj.cmyk_y * (1.0 - cobj.cmyk_k) + cobj.cmyk_k
    
    return CMYColor(cmy_c, cmy_m, cmy_y)


CONVERSION_TABLE = {
    "SpectralColor": {
   "SpectralColor": [None],
        "XYZColor": [Spectral_to_XYZ],
        "xyYColor": [Spectral_to_XYZ, XYZ_to_xyY],
        "LabColor": [Spectral_to_XYZ, XYZ_to_Lab],
      "LCHabColor": [Spectral_to_XYZ, XYZ_to_Lab, Lab_to_LCHab],
      "LCHuvColor": [Spectral_to_XYZ, XYZ_to_Luv, Luv_to_LCHuv],
        "LuvColor": [Spectral_to_XYZ, Lab_to_XYZ, XYZ_to_Luv],
       "sRGBColor": [Spectral_to_XYZ, XYZ_to_RGB],
        "HSLColor": [Spectral_to_XYZ, XYZ_to_RGB, RGB_to_HSL],
        "HSVColor": [Spectral_to_XYZ, XYZ_to_RGB, RGB_to_HSV],
        "CMYColor": [Spectral_to_XYZ, XYZ_to_RGB, RGB_to_CMY],
       "CMYKColor": [Spectral_to_XYZ, XYZ_to_RGB, RGB_to_CMY, CMY_to_CMYK],
    },
    "LabColor": {
        "LabColor": [None],
        "XYZColor": [Lab_to_XYZ],
        "xyYColor": [Lab_to_XYZ, XYZ_to_xyY],
      "LCHabColor": [Lab_to_LCHab],
      "LCHuvColor": [Lab_to_XYZ, XYZ_to_Luv, Luv_to_LCHuv],
        "LuvColor": [Lab_to_XYZ, XYZ_to_Luv],
       "sRGBColor": [Lab_to_XYZ, XYZ_to_RGB],
        "HSLColor": [Lab_to_XYZ, XYZ_to_RGB, RGB_to_HSL],
        "HSVColor": [Lab_to_XYZ, XYZ_to_RGB, RGB_to_HSV],
        "CMYColor": [Lab_to_XYZ, XYZ_to_RGB, RGB_to_CMY],
       "CMYKColor": [Lab_to_XYZ, XYZ_to_RGB, RGB_to_CMY, CMY_to_CMYK],
    },
    "LCHabColor": {
      "LCHabColor": [None],
        "XYZColor": [LCHab_to_Lab, Lab_to_XYZ],
        "xyYColor": [LCHab_to_Lab, Lab_to_XYZ, XYZ_to_xyY],
        "LabColor": [LCHab_to_Lab],
      "LCHuvColor": [LCHab_to_Lab, Lab_to_XYZ, XYZ_to_Luv, Luv_to_LCHuv],
        "LuvColor": [LCHab_to_Lab, Lab_to_XYZ, XYZ_to_Luv],
       "sRGBColor": [LCHab_to_Lab, Lab_to_XYZ, XYZ_to_RGB],
        "HSLColor": [LCHab_to_Lab, Lab_to_XYZ, XYZ_to_RGB, RGB_to_HSL],
        "HSVColor": [LCHab_to_Lab, Lab_to_XYZ, XYZ_to_RGB, RGB_to_HSV],
        "CMYColor": [LCHab_to_Lab, Lab_to_XYZ, XYZ_to_RGB, RGB_to_CMY],
       "CMYKColor": [LCHab_to_Lab, Lab_to_XYZ, XYZ_to_RGB, RGB_to_CMY, CMY_to_CMYK],
    },
    "LCHuvColor": {
      "LCHuvColor": [None],
        "XYZColor": [LCHuv_to_Luv, Luv_to_XYZ],
        "xyYColor": [LCHuv_to_Luv, Luv_to_XYZ, XYZ_to_xyY],
        "LabColor": [LCHuv_to_Luv, Luv_to_XYZ, XYZ_to_Lab],
        "LuvColor": [LCHuv_to_Luv],
      "LCHabColor": [LCHuv_to_Luv, Luv_to_XYZ, XYZ_to_Lab, Lab_to_LCHab],
       "sRGBColor": [LCHuv_to_Luv, Luv_to_XYZ, XYZ_to_RGB],
        "HSLColor": [LCHuv_to_Luv, Luv_to_XYZ, XYZ_to_RGB, RGB_to_HSL],
        "HSVColor": [LCHuv_to_Luv, Luv_to_XYZ, XYZ_to_RGB, RGB_to_HSV],
        "CMYColor": [LCHuv_to_Luv, Luv_to_XYZ, XYZ_to_RGB, RGB_to_CMY],
       "CMYKColor": [LCHuv_to_Luv, Luv_to_XYZ, XYZ_to_RGB, RGB_to_CMY, CMY_to_CMYK],
    },
    "LuvColor": {
        "LuvColor": [None],
        "XYZColor": [Luv_to_XYZ],
        "xyYColor": [Luv_to_XYZ, XYZ_to_xyY],
        "LabColor": [Luv_to_XYZ, XYZ_to_Lab],
      "LCHabColor": [Luv_to_XYZ, XYZ_to_Lab, Lab_to_LCHab],
      "LCHuvColor": [Luv_to_LCHuv],
       "sRGBColor": [Luv_to_XYZ, XYZ_to_RGB],
        "HSLColor": [Luv_to_XYZ, XYZ_to_RGB, RGB_to_HSL],
        "HSVColor": [Luv_to_XYZ, XYZ_to_RGB, RGB_to_HSV],
        "CMYColor": [Luv_to_XYZ, XYZ_to_RGB, RGB_to_CMY],
       "CMYKColor": [Luv_to_XYZ, XYZ_to_RGB, RGB_to_CMY, CMY_to_CMYK],
    },
    "XYZColor": {
        "XYZColor": [None],
        "xyYColor": [XYZ_to_xyY],
        "LabColor": [XYZ_to_Lab],
      "LCHabColor": [XYZ_to_Lab, Lab_to_LCHab],
      "LCHuvColor": [XYZ_to_Lab, Luv_to_LCHuv],
        "LuvColor": [XYZ_to_Luv],
       "sRGBColor": [XYZ_to_RGB],
        "HSLColor": [XYZ_to_RGB, RGB_to_HSL],
        "HSVColor": [XYZ_to_RGB, RGB_to_HSV],
        "CMYColor": [XYZ_to_RGB, RGB_to_CMY],
       "CMYKColor": [XYZ_to_RGB, RGB_to_CMY, CMY_to_CMYK],
    },
    "xyYColor": {
        "xyYColor": [None],
        "XYZColor": [xyY_to_XYZ],
        "LabColor": [xyY_to_XYZ, XYZ_to_Lab],
      "LCHabColor": [xyY_to_XYZ, XYZ_to_Lab, Lab_to_LCHab],
      "LCHuvColor": [xyY_to_XYZ, XYZ_to_Luv, Luv_to_LCHuv],
        "LuvColor": [xyY_to_XYZ, XYZ_to_Luv],
       "sRGBColor": [xyY_to_XYZ, XYZ_to_RGB],
        "HSLColor": [xyY_to_XYZ, XYZ_to_RGB, RGB_to_HSL],
        "HSVColor": [xyY_to_XYZ, XYZ_to_RGB, RGB_to_HSV],
        "CMYColor": [xyY_to_XYZ, XYZ_to_RGB, RGB_to_CMY],
       "CMYKColor": [xyY_to_XYZ, XYZ_to_RGB, RGB_to_CMY, CMY_to_CMYK],
    },
    "HSLColor": {
        "HSLColor": [None],
        "HSVColor": [HSL_to_RGB, RGB_to_HSV],
       "sRGBColor": [HSL_to_RGB],
        "CMYColor": [HSL_to_RGB, RGB_to_CMY],
       "CMYKColor": [HSL_to_RGB, RGB_to_CMY, CMY_to_CMYK],
        "XYZColor": [HSL_to_RGB, RGB_to_XYZ],
        "xyYColor": [HSL_to_RGB, RGB_to_XYZ, XYZ_to_xyY],
        "LabColor": [HSL_to_RGB, RGB_to_XYZ, XYZ_to_Lab],
      "LCHabColor": [HSL_to_RGB, RGB_to_XYZ, XYZ_to_Lab, Lab_to_LCHab],
      "LCHuvColor": [HSL_to_RGB, RGB_to_XYZ, XYZ_to_Luv, Luv_to_LCHuv],
        "LuvColor": [HSL_to_RGB, RGB_to_XYZ, XYZ_to_RGB],
    },
    "HSVColor": {
        "HSVColor": [None],
        "HSLColor": [HSV_to_RGB, RGB_to_HSL],
       "sRGBColor": [HSV_to_RGB],
        "CMYColor": [HSV_to_RGB, RGB_to_CMY],
       "CMYKColor": [HSV_to_RGB, RGB_to_CMY, CMY_to_CMYK],
        "XYZColor": [HSV_to_RGB, RGB_to_XYZ],
        "xyYColor": [HSV_to_RGB, RGB_to_XYZ, XYZ_to_xyY],
        "LabColor": [HSV_to_RGB, RGB_to_XYZ, XYZ_to_Lab],
      "LCHabColor": [HSV_to_RGB, RGB_to_XYZ, XYZ_to_Lab, Lab_to_LCHab],
      "LCHuvColor": [HSV_to_RGB, RGB_to_XYZ, XYZ_to_Luv, Luv_to_LCHuv],
        "LuvColor": [HSV_to_RGB, RGB_to_XYZ, XYZ_to_RGB],
    },
    "CMYColor": {
        "CMYColor": [None],
       "CMYKColor": [CMY_to_CMYK],
        "HSLColor": [CMY_to_RGB, RGB_to_HSL],
        "HSVColor": [CMY_to_RGB, RGB_to_HSV],
       "sRGBColor": [CMY_to_RGB],
        "XYZColor": [CMY_to_RGB, RGB_to_XYZ],
        "xyYColor": [CMY_to_RGB, RGB_to_XYZ, XYZ_to_xyY],
        "LabColor": [CMY_to_RGB, RGB_to_XYZ, XYZ_to_Lab],
      "LCHabColor": [CMY_to_RGB, RGB_to_XYZ, XYZ_to_Lab, Lab_to_LCHab],
      "LCHuvColor": [CMY_to_RGB, RGB_to_XYZ, XYZ_to_Luv, Luv_to_LCHuv],
        "LuvColor": [CMY_to_RGB, RGB_to_XYZ, XYZ_to_RGB],
    },
    "CMYKColor": {
       "CMYKColor": [None],
        "CMYColor": [CMYK_to_CMY],
        "HSLColor": [CMYK_to_CMY, CMY_to_RGB, RGB_to_HSL],
        "HSVColor": [CMYK_to_CMY, CMY_to_RGB, RGB_to_HSV],
       "sRGBColor": [CMYK_to_CMY, CMY_to_RGB],
        "XYZColor": [CMYK_to_CMY, CMY_to_RGB, RGB_to_XYZ],
        "xyYColor": [CMYK_to_CMY, CMY_to_RGB, RGB_to_XYZ, XYZ_to_xyY],
        "LabColor": [CMYK_to_CMY, CMY_to_RGB, RGB_to_XYZ, XYZ_to_Lab],
      "LCHabColor": [CMYK_to_CMY, CMY_to_RGB, RGB_to_XYZ, XYZ_to_Lab, Lab_to_LCHab],
      "LCHuvColor": [CMYK_to_CMY, CMY_to_RGB, RGB_to_XYZ, XYZ_to_Luv, Luv_to_LCHuv],
        "LuvColor": [CMYK_to_CMY, CMY_to_RGB, RGB_to_XYZ, XYZ_to_RGB],
    },
}

# We use this as a template conversion dict for each RGB color space. They
# are all identical.
_RGB_CONVERSION_DICT_TEMPLATE = {
        "HSLColor": [RGB_to_HSL],
        "HSVColor": [RGB_to_HSV],
        "CMYColor": [RGB_to_CMY],
       "CMYKColor": [RGB_to_CMY, CMY_to_CMYK],
        "XYZColor": [RGB_to_XYZ],
        "xyYColor": [RGB_to_XYZ, XYZ_to_xyY],
        "LabColor": [RGB_to_XYZ, XYZ_to_Lab],
      "LCHabColor": [RGB_to_XYZ, XYZ_to_Lab, Lab_to_LCHab],
      "LCHuvColor": [RGB_to_XYZ, XYZ_to_Luv, Luv_to_LCHuv],
        "LuvColor": [RGB_to_XYZ, XYZ_to_Luv],
}

# Avoid the repetition, since the conversion tables for the various RGB
# spaces are the same.
_RGB_SPACES = ["sRGBColor", "AdobeRGBColor"]
for rgb_space in _RGB_SPACES:
    if rgb_space != "sRGBColor":
        # This is a bit strange, but wherever we see sRGBColor in a conversion
        # dict, duplicate it for each additional color space. Keeps us from
        # having to manually type/update this for every single RGB space.
        for key in CONVERSION_TABLE:
            CONVERSION_TABLE[key][rgb_space] = CONVERSION_TABLE[key]["sRGBColor"]
    # Avoid modifying the original template dict.
    conv_dict = _RGB_CONVERSION_DICT_TEMPLATE.copy()
    # No-ops conversions to self.
    conv_dict[rgb_space] = [None]
    # The new RGB color space is now a part of the conversion table.
    CONVERSION_TABLE[rgb_space] = conv_dict


def convert_color(color, target_cs, through_rgb_type=sRGBColor,
                  target_illuminant=None, *args, **kwargs):
    """
    Converts the color to the designated color space.

    :param color: A Color instance to convert.
    :param target_cs: The Color class to convert to. Note that this is not
        an instance, but a class.
    :keyword BaseRGBColor through_rgb_type: If during your conversion between
        your original and target color spaces you have to pass through RGB,
        this determines which kind of RGB to use. For example, XYZ->HSL.
        You probably don't need to specify this unless you have a special
        usage case.
    :type target_illuminant: None or str
    :keyword target_illuminant: If during conversion from RGB to a reflective
        color space you want to explicitly end up with a certain illuminant,
        pass this here. Otherwise the RGB space's native illuminant will be used.
    :returns: An instance of the type passed in as ``target_cs``.
    :raises: :py:exc:`colormath.color_exceptions.UndefinedConversionError`
        if conversion between the two color spaces isn't possible.
    """

    if isinstance(target_cs, str):
        raise ValueError("target_cs parameter must be a Color object.")
    if not issubclass(target_cs, ColorBase):
        raise ValueError("target_cs parameter must be a Color object.")

    # Find the origin color space's conversion table.
    cs_table = CONVERSION_TABLE[color.__class__.__name__]
    try:
        # Look up the conversion path for the specified color space.
        conversions = cs_table[target_cs.__name__]
    except KeyError:
        raise UndefinedConversionError(
            color.__class__.__name__,
            target_cs.__name__,
        )

    logger.debug('Converting %s to %s', color, target_cs)
    logger.debug(' @ Conversion path: %s', conversions)

    # Start with original color in case we convert to the same color space.
    new_color = color

    if issubclass(target_cs, BaseRGBColor):
        # If the target_cs is an RGB color space of some sort, then we
        # have to set our through_rgb_type to make sure the conversion returns
        # the expected RGB colorspace (instead of defaulting to sRGBColor).
        through_rgb_type = target_cs

    # We have to be careful to use the same RGB color space that created
    # an object (if it was created by a conversion) in order to get correct
    # results. For example, XYZ->HSL via Adobe RGB should default to Adobe
    # RGB when taking that generated HSL object back to XYZ.
    # noinspection PyProtectedMember
    if through_rgb_type != sRGBColor:
        # User overrides take priority over everything.
        # noinspection PyProtectedMember
        target_rgb = through_rgb_type
    elif color._through_rgb_type:
        # Otherwise, a value on the color object is the next best thing,
        # when available.
        # noinspection PyProtectedMember
        target_rgb = color._through_rgb_type
    else:
        # We could collapse this into a single if statement above,
        # but I think this reads better.
        target_rgb = through_rgb_type

    # Iterate through the list of functions for the conversion path, storing
    # the results in a dictionary via update(). This way the user has access
    # to all of the variables involved in the conversion.
    for func in conversions:
        # Execute the function in this conversion step and store the resulting
        # Color object.
        logger.debug(' * Conversion: %s passed to %s()',
                     new_color.__class__.__name__, func)
        logger.debug(' |->  in %s', new_color)

        if func:
            # This can be None if you try to convert a color to the color
            # space that is already in. IE: XYZ->XYZ.
            new_color = func(
                new_color,
                target_rgb=target_rgb,
                target_illuminant=target_illuminant,
                *args, **kwargs)

        logger.debug(' |-< out %s', new_color)

    # If this conversion had something other than the default sRGB color space
    # requested,
    if through_rgb_type != sRGBColor:
        new_color._through_rgb_type = through_rgb_type

    return new_color

########NEW FILE########
__FILENAME__ = color_diff
"""
The functions in this module are used for comparing two LabColor objects
using various Delta E formulas.
"""

import numpy

from colormath import color_diff_matrix


def _get_lab_color1_vector(color):
    """
    Converts an LabColor into a NumPy vector.

    :param LabColor color:
    :rtype: numpy.ndarray
    """

    if not color.__class__.__name__ == 'LabColor':
        raise ValueError(
            "Delta E functions can only be used with two LabColor objects.")
    return numpy.array([color.lab_l, color.lab_a, color.lab_b])


def _get_lab_color2_matrix(color):
    """
    Converts an LabColor into a NumPy matrix.

    :param LabColor color:
    :rtype: numpy.ndarray
    """
    if not color.__class__.__name__ == 'LabColor':
        raise ValueError(
            "Delta E functions can only be used with two LabColor objects.")
    return numpy.array([(color.lab_l, color.lab_a, color.lab_b)])


# noinspection PyPep8Naming
def delta_e_cie1976(color1, color2):
    """
    Calculates the Delta E (CIE1976) of two colors.
    """

    color1_vector = _get_lab_color1_vector(color1)
    color2_matrix = _get_lab_color2_matrix(color2)
    delta_e = color_diff_matrix.delta_e_cie1976(color1_vector, color2_matrix)[0]
    return numpy.asscalar(delta_e)


# noinspection PyPep8Naming
def delta_e_cie1994(color1, color2, K_L=1, K_C=1, K_H=1, K_1=0.045, K_2=0.015):
    """
    Calculates the Delta E (CIE1994) of two colors.
    
    K_l:
      0.045 graphic arts
      0.048 textiles
    K_2:
      0.015 graphic arts
      0.014 textiles
    K_L:
      1 default
      2 textiles
    """

    color1_vector = _get_lab_color1_vector(color1)
    color2_matrix = _get_lab_color2_matrix(color2)
    delta_e = color_diff_matrix.delta_e_cie1994(
        color1_vector, color2_matrix, K_L=K_L, K_C=K_C, K_H=K_H, K_1=K_1, K_2=K_2)[0]
    return numpy.asscalar(delta_e)


# noinspection PyPep8Naming
def delta_e_cie2000(color1, color2, Kl=1, Kc=1, Kh=1):
    """
    Calculates the Delta E (CIE2000) of two colors.
    """

    color1_vector = _get_lab_color1_vector(color1)
    color2_matrix = _get_lab_color2_matrix(color2)
    delta_e = color_diff_matrix.delta_e_cie2000(
        color1_vector, color2_matrix, Kl=Kl, Kc=Kc, Kh=Kh)[0]
    return numpy.asscalar(delta_e)


# noinspection PyPep8Naming
def delta_e_cmc(color1, color2, pl=2, pc=1):
    """
    Calculates the Delta E (CMC) of two colors.
    
    CMC values
      Acceptability: pl=2, pc=1
      Perceptability: pl=1, pc=1
    """

    color1_vector = _get_lab_color1_vector(color1)
    color2_matrix = _get_lab_color2_matrix(color2)
    delta_e = color_diff_matrix.delta_e_cmc(
        color1_vector, color2_matrix, pl=pl, pc=pc)[0]
    return numpy.asscalar(delta_e)

########NEW FILE########
__FILENAME__ = color_diff_matrix
"""
This module contains the formulas for comparing Lab values with matrices
and vectors. The benefit of using NumPy's matrix capabilities is speed. These
calls can be used to efficiently compare large volumes of Lab colors.
"""

import numpy


def delta_e_cie1976(lab_color_vector, lab_color_matrix):
    """
    Calculates the Delta E (CIE1976) between `lab_color_vector` and all
    colors in `lab_color_matrix`.
    """

    return numpy.sqrt(numpy.sum(numpy.power(lab_color_vector - lab_color_matrix, 2), axis=1))


# noinspection PyPep8Naming
def delta_e_cie1994(lab_color_vector, lab_color_matrix,
                    K_L=1, K_C=1, K_H=1, K_1=0.045, K_2=0.015):
    """
    Calculates the Delta E (CIE1994) of two colors.

    K_l:
      0.045 graphic arts
      0.048 textiles
    K_2:
      0.015 graphic arts
      0.014 textiles
    K_L:
      1 default
      2 textiles
    """

    C_1 = numpy.sqrt(numpy.sum(numpy.power(lab_color_vector[1:], 2)))
    C_2 = numpy.sqrt(numpy.sum(numpy.power(lab_color_matrix[:, 1:], 2), axis=1))

    delta_lab = lab_color_vector - lab_color_matrix

    delta_L = delta_lab[:, 0].copy()
    delta_C = C_1 - C_2
    delta_lab[:, 0] = delta_C

    delta_H_sq = numpy.sum(numpy.power(delta_lab, 2) * numpy.array([-1, 1, 1]), axis=1)
    # noinspection PyArgumentList
    delta_H = numpy.sqrt(delta_H_sq.clip(min=0))

    S_L = 1
    S_C = 1 + K_1 * C_1
    S_H = 1 + K_2 * C_1

    LCH = numpy.vstack([delta_L, delta_C, delta_H])
    params = numpy.array([[K_L * S_L], [K_C * S_C], [K_H * S_H]])

    return numpy.sqrt(numpy.sum(numpy.power(LCH / params, 2), axis=0))


# noinspection PyPep8Naming
def delta_e_cmc(lab_color_vector, lab_color_matrix, pl=2, pc=1):
    """
    Calculates the Delta E (CIE1994) of two colors.

    CMC values
      Acceptability: pl=2, pc=1
      Perceptability: pl=1, pc=1
    """

    L, a, b = lab_color_vector

    C_1 = numpy.sqrt(numpy.sum(numpy.power(lab_color_vector[1:], 2)))
    C_2 = numpy.sqrt(numpy.sum(numpy.power(lab_color_matrix[:, 1:], 2), axis=1))

    delta_lab = lab_color_vector - lab_color_matrix

    delta_L = delta_lab[:, 0].copy()
    delta_C = C_1 - C_2
    delta_lab[:, 0] = delta_C

    H_1 = numpy.degrees(numpy.arctan2(b, a))

    if H_1 < 0:
        H_1 += 360

    F = numpy.sqrt(numpy.power(C_1, 4) / (numpy.power(C_1, 4) + 1900.0))

    # noinspection PyChainedComparisons
    if 164 <= H_1 and H_1 <= 345:
        T = 0.56 + abs(0.2 * numpy.cos(numpy.radians(H_1 + 168)))
    else:
        T = 0.36 + abs(0.4 * numpy.cos(numpy.radians(H_1 + 35)))

    if L < 16:
        S_L = 0.511
    else:
        S_L = (0.040975 * L) / (1 + 0.01765 * L)

    S_C = ((0.0638 * C_1) / (1 + 0.0131 * C_1)) + 0.638
    S_H = S_C * (F * T + 1 - F)

    delta_C = C_1 - C_2

    delta_H_sq = numpy.sum(numpy.power(delta_lab, 2) * numpy.array([-1, 1, 1]), axis=1)
    # noinspection PyArgumentList
    delta_H = numpy.sqrt(delta_H_sq.clip(min=0))

    LCH = numpy.vstack([delta_L, delta_C, delta_H])
    params = numpy.array([[pl * S_L], [pc * S_C], [S_H]])

    return numpy.sqrt(numpy.sum(numpy.power(LCH / params, 2), axis=0))


# noinspection PyPep8Naming
def delta_e_cie2000(lab_color_vector, lab_color_matrix, Kl=1, Kc=1, Kh=1):
    """
    Calculates the Delta E (CIE2000) of two colors.
    """

    L, a, b = lab_color_vector

    avg_Lp = (L + lab_color_matrix[:, 0]) / 2.0

    C1 = numpy.sqrt(numpy.sum(numpy.power(lab_color_vector[1:], 2)))
    C2 = numpy.sqrt(numpy.sum(numpy.power(lab_color_matrix[:, 1:], 2), axis=1))

    avg_C1_C2 = (C1 + C2) / 2.0

    G = 0.5 * (1 - numpy.sqrt(numpy.power(avg_C1_C2, 7.0) / (numpy.power(avg_C1_C2, 7.0) + numpy.power(25.0, 7.0))))

    a1p = (1.0 + G) * a
    a2p = (1.0 + G) * lab_color_matrix[:, 1]

    C1p = numpy.sqrt(numpy.power(a1p, 2) + numpy.power(b, 2))
    C2p = numpy.sqrt(numpy.power(a2p, 2) + numpy.power(lab_color_matrix[:, 2], 2))

    avg_C1p_C2p = (C1p + C2p) / 2.0

    h1p = numpy.degrees(numpy.arctan2(b, a1p))
    h1p += (h1p < 0) * 360

    h2p = numpy.degrees(numpy.arctan2(lab_color_matrix[:, 2], a2p))
    h2p += (h2p < 0) * 360

    avg_Hp = (((numpy.fabs(h1p - h2p) > 180) * 360) + h1p + h2p) / 2.0

    T = 1 - 0.17 * numpy.cos(numpy.radians(avg_Hp - 30)) + \
        0.24 * numpy.cos(numpy.radians(2 * avg_Hp)) + \
        0.32 * numpy.cos(numpy.radians(3 * avg_Hp + 6)) - \
        0.2 * numpy.cos(numpy.radians(4 * avg_Hp - 63))

    diff_h2p_h1p = h2p - h1p
    delta_hp = diff_h2p_h1p + (numpy.fabs(diff_h2p_h1p) > 180) * 360
    delta_hp -= (h2p > h1p) * 720

    delta_Lp = lab_color_matrix[:, 0] - L
    delta_Cp = C2p - C1p
    delta_Hp = 2 * numpy.sqrt(C2p * C1p) * numpy.sin(numpy.radians(delta_hp) / 2.0)

    S_L = 1 + ((0.015 * numpy.power(avg_Lp - 50, 2)) / numpy.sqrt(20 + numpy.power(avg_Lp - 50, 2.0)))
    S_C = 1 + 0.045 * avg_C1p_C2p
    S_H = 1 + 0.015 * avg_C1p_C2p * T

    delta_ro = 30 * numpy.exp(-(numpy.power(((avg_Hp - 275) / 25), 2.0)))
    R_C = numpy.sqrt((numpy.power(avg_C1p_C2p, 7.0)) / (numpy.power(avg_C1p_C2p, 7.0) + numpy.power(25.0, 7.0)))
    R_T = -2 * R_C * numpy.sin(2 * numpy.radians(delta_ro))

    return numpy.sqrt(
        numpy.power(delta_Lp / (S_L * Kl), 2) +
        numpy.power(delta_Cp / (S_C * Kc), 2) +
        numpy.power(delta_Hp / (S_H * Kh), 2) +
        R_T * (delta_Cp / (S_C * Kc)) * (delta_Hp / (S_H * Kh)))

########NEW FILE########
__FILENAME__ = color_exceptions
"""
This module contains exceptions for use throughout the L11 Colorlib.
"""


class ColorMathException(Exception):
    """
    Base exception for all colormath exceptions.
    """

    pass


class UndefinedConversionError(ColorMathException):
    """
    Raised when the user asks for a color space conversion that does not exist.
    """

    def __init__(self, cobj, cs_to):
        super(UndefinedConversionError, self).__init__(cobj, cs_to)
        self.message = "Conversion from %s to %s is not defined." % (cobj, cs_to)


class InvalidIlluminantError(ColorMathException):
    """
    Raised when an invalid illuminant is set on a ColorObj.
    """

    def __init__(self, illuminant):
        super(InvalidIlluminantError, self).__init__(illuminant)
        self.message = "Invalid illuminant specified: %s" % illuminant


class InvalidObserverError(ColorMathException):
    """
    Raised when an invalid observer is set on a ColorObj.
    """

    def __init__(self, cobj):
        super(InvalidObserverError, self).__init__(cobj)
        self.message = "Invalid observer angle specified: %s" % cobj.observer

########NEW FILE########
__FILENAME__ = color_objects
"""
This module contains classes to represent various color spaces.
"""

import logging
import math

import numpy

from colormath import color_constants
from colormath import density
from colormath.chromatic_adaptation import apply_chromatic_adaptation_on_color
from colormath.color_exceptions import InvalidObserverError, InvalidIlluminantError

logger = logging.getLogger(__name__)


class ColorBase(object):
    """
    A base class holding some common methods and values.
    """

    # Attribute names containing color data on the sub-class. For example,
    # sRGBColor would be ['rgb_r', 'rgb_g', 'rgb_b']
    VALUES = []
    # If this object as converted such that its values passed through an
    # RGB colorspace, this is set to the class for said RGB color space.
    # Allows reversing conversions automatically and accurately.
    _through_rgb_type = None

    def get_value_tuple(self):
        """
        Returns a tuple of the color's values (in order). For example,
        an LabColor object will return (lab_l, lab_a, lab_b), where each
        member of the tuple is the float value for said variable.
        """

        retval = tuple()
        for val in self.VALUES:
            retval += (getattr(self, val),)
        return retval

    def __str__(self):
        """
        String representation of the color.
        """

        retval = self.__class__.__name__ + ' ('
        for val in self.VALUES:
            value = getattr(self, val, None)
            if value is not None:
                retval += '%s:%.4f ' % (val, getattr(self, val))
        return retval.strip() + ')'

    def __repr__(self):
        """
        String representation of the object.
        """

        retval = self.__class__.__name__ + '('
        attributes = [(attr, getattr(self, attr)) for attr in self.VALUES]
        values = [x + "=" + repr(y) for x, y in attributes]
        retval += ','.join(values)
        return retval + ')'


class IlluminantMixin(object):
    """
    Color spaces that have a notion of an illuminant should inherit this.
    """

    # noinspection PyAttributeOutsideInit
    def set_observer(self, observer):
        """
        Validates and sets the color's observer angle.

        .. note:: This only changes the observer angle value. It does no conversion
            of the color's coordinates.

        :param str observer: One of '2' or '10'.
        """

        observer = str(observer)
        if observer not in color_constants.OBSERVERS:
            raise InvalidObserverError(self)
        self.observer = observer

    # noinspection PyAttributeOutsideInit
    def set_illuminant(self, illuminant):
        """
        Validates and sets the color's illuminant.

        .. note:: This only changes the illuminant. It does no conversion
            of the color's coordinates. For this, you'll want to refer to
            :py:meth:`XYZColor.apply_adaptation <colormath.color_objects.XYZColor.apply_adaptation>`.

        .. tip:: Call this after setting your observer.

        :param str illuminant: One of the various illuminants.
        """

        illuminant = illuminant.lower()
        if illuminant not in color_constants.ILLUMINANTS[self.observer]:
            raise InvalidIlluminantError(illuminant)
        self.illuminant = illuminant

    def get_illuminant_xyz(self, observer=None, illuminant=None):
        """
        :param str observer: Get the XYZ values for another observer angle. Must
            be either '2' or '10'.
        :param str illuminant: Get the XYZ values for another illuminant.
        :returns: the color's illuminant's XYZ values.
        """

        try:
            if observer is None:
                observer = self.observer

            illums_observer = color_constants.ILLUMINANTS[observer]
        except KeyError:
            raise InvalidObserverError(self)

        try:
            if illuminant is None:
                illuminant = self.illuminant

            illum_xyz = illums_observer[illuminant]
        except (KeyError, AttributeError):
            raise InvalidIlluminantError(illuminant)

        return {'X': illum_xyz[0], 'Y': illum_xyz[1], 'Z': illum_xyz[2]}


class SpectralColor(IlluminantMixin, ColorBase):
    """
    A SpectralColor represents a spectral power distribution, as read by
    a spectrophotometer. Our current implementation has wavelength intervals
    of 10nm, starting at 340nm and ending at 830nm.

    Spectral colors are the lowest level, most "raw" measurement of color.
    You may convert spectral colors to any other color space, but you can't
    convert any other color space back to spectral.

    See `Spectral power distribution <http://en.wikipedia.org/wiki/Spectral_power_distribution>`_
    on Wikipedia for some higher level details on how these work.
    """

    VALUES = [
        'spec_340nm', 'spec_350nm', 'spec_360nm', 'spec_370nm',
        'spec_380nm', 'spec_390nm', 'spec_400nm', 'spec_410nm',
        'spec_420nm', 'spec_430nm', 'spec_440nm', 'spec_450nm',
        'spec_460nm', 'spec_470nm', 'spec_480nm', 'spec_490nm',
        'spec_500nm', 'spec_510nm', 'spec_520nm', 'spec_530nm',
        'spec_540nm', 'spec_550nm', 'spec_560nm', 'spec_570nm',
        'spec_580nm', 'spec_590nm', 'spec_600nm', 'spec_610nm',
        'spec_620nm', 'spec_630nm', 'spec_640nm', 'spec_650nm',
        'spec_660nm', 'spec_670nm', 'spec_680nm', 'spec_690nm',
        'spec_700nm', 'spec_710nm', 'spec_720nm', 'spec_730nm',
        'spec_740nm', 'spec_750nm', 'spec_760nm', 'spec_770nm',
        'spec_780nm', 'spec_790nm', 'spec_800nm', 'spec_810nm',
        'spec_820nm', 'spec_830nm'
    ]

    def __init__(self,
        spec_340nm=0.0, spec_350nm=0.0, spec_360nm=0.0, spec_370nm=0.0,
        spec_380nm=0.0, spec_390nm=0.0, spec_400nm=0.0, spec_410nm=0.0,
        spec_420nm=0.0, spec_430nm=0.0, spec_440nm=0.0, spec_450nm=0.0,
        spec_460nm=0.0, spec_470nm=0.0, spec_480nm=0.0, spec_490nm=0.0,
        spec_500nm=0.0, spec_510nm=0.0, spec_520nm=0.0, spec_530nm=0.0,
        spec_540nm=0.0, spec_550nm=0.0, spec_560nm=0.0, spec_570nm=0.0,
        spec_580nm=0.0, spec_590nm=0.0, spec_600nm=0.0, spec_610nm=0.0,
        spec_620nm=0.0, spec_630nm=0.0, spec_640nm=0.0, spec_650nm=0.0,
        spec_660nm=0.0, spec_670nm=0.0, spec_680nm=0.0, spec_690nm=0.0,
        spec_700nm=0.0, spec_710nm=0.0, spec_720nm=0.0, spec_730nm=0.0,
        spec_740nm=0.0, spec_750nm=0.0, spec_760nm=0.0, spec_770nm=0.0,
        spec_780nm=0.0, spec_790nm=0.0, spec_800nm=0.0, spec_810nm=0.0,
        spec_820nm=0.0, spec_830nm=0.0, observer='2', illuminant='d50'):
        """
        :keyword str observer: Observer angle. Either ``'2'`` or ``'10'`` degrees.
        :keyword str illuminant: See :doc:`illuminants` for valid values.
        """

        super(SpectralColor, self).__init__()
        # Spectral fields
        self.spec_340nm = float(spec_340nm)
        self.spec_350nm = float(spec_350nm)
        self.spec_360nm = float(spec_360nm)
        self.spec_370nm = float(spec_370nm)
        # begin Blue wavelengths
        self.spec_380nm = float(spec_380nm)
        self.spec_390nm = float(spec_390nm)
        self.spec_400nm = float(spec_400nm)
        self.spec_410nm = float(spec_410nm)
        self.spec_420nm = float(spec_420nm)
        self.spec_430nm = float(spec_430nm)
        self.spec_440nm = float(spec_440nm)
        self.spec_450nm = float(spec_450nm)
        self.spec_460nm = float(spec_460nm)
        self.spec_470nm = float(spec_470nm)
        self.spec_480nm = float(spec_480nm)
        self.spec_490nm = float(spec_490nm)
        # end Blue wavelengths
        # start Green wavelengths
        self.spec_500nm = float(spec_500nm)
        self.spec_510nm = float(spec_510nm)
        self.spec_520nm = float(spec_520nm)
        self.spec_530nm = float(spec_530nm)
        self.spec_540nm = float(spec_540nm)
        self.spec_550nm = float(spec_550nm)
        self.spec_560nm = float(spec_560nm)
        self.spec_570nm = float(spec_570nm)
        self.spec_580nm = float(spec_580nm)
        self.spec_590nm = float(spec_590nm)
        self.spec_600nm = float(spec_600nm)
        self.spec_610nm = float(spec_610nm)
        # end Green wavelengths
        # start Red wavelengths
        self.spec_620nm = float(spec_620nm)
        self.spec_630nm = float(spec_630nm)
        self.spec_640nm = float(spec_640nm)
        self.spec_650nm = float(spec_650nm)
        self.spec_660nm = float(spec_660nm)
        self.spec_670nm = float(spec_670nm)
        self.spec_680nm = float(spec_680nm)
        self.spec_690nm = float(spec_690nm)
        self.spec_700nm = float(spec_700nm)
        self.spec_710nm = float(spec_710nm)
        self.spec_720nm = float(spec_720nm)
        # end Red wavelengths
        self.spec_730nm = float(spec_730nm)
        self.spec_740nm = float(spec_740nm)
        self.spec_750nm = float(spec_750nm)
        self.spec_760nm = float(spec_760nm)
        self.spec_770nm = float(spec_770nm)
        self.spec_780nm = float(spec_780nm)
        self.spec_790nm = float(spec_790nm)
        self.spec_800nm = float(spec_800nm)
        self.spec_810nm = float(spec_810nm)
        self.spec_820nm = float(spec_820nm)
        self.spec_830nm = float(spec_830nm)

        #: The color's observer angle. Set with :py:meth:`set_observer`.
        self.observer = None
        #: The color's illuminant. Set with :py:meth:`set_illuminant`.
        self.illuminant = None

        self.set_observer(observer)
        self.set_illuminant(illuminant)

    def get_numpy_array(self):
        """
        Dump this color into NumPy array.
        """

        # This holds the obect's spectral data, and will be passed to
        # numpy.array() to create a numpy array (matrix) for the matrix math
        # that will be done during the conversion to XYZ.
        values = []

        # Use the required value list to build this dynamically. Default to
        # 0.0, since that ultimately won't affect the outcome due to the math
        # involved.
        for val in self.VALUES:
            values.append(getattr(self, val, 0.0))

        # Create and the actual numpy array/matrix from the spectral list.
        color_array = numpy.array([values])
        return color_array

    def calc_density(self, density_standard=None):
        """
        Calculates the density of the SpectralColor. By default, Status T
        density is used, and the correct density distribution (Red, Green,
        or Blue) is chosen by comparing the Red, Green, and Blue components of
        the spectral sample (the values being red in via "filters").
        """

        if density_standard is not None:
            return density.ansi_density(self, density_standard)
        else:
            return density.auto_density(self)


class LabColor(IlluminantMixin, ColorBase):
    """
    Represents a CIE Lab color. For more information on CIE Lab,
    see `Lab color space <http://en.wikipedia.org/wiki/Lab_color_space>`_ on
    Wikipedia.
    """

    VALUES = ['lab_l', 'lab_a', 'lab_b']

    def __init__(self, lab_l, lab_a, lab_b, observer='2', illuminant='d50'):
        """
        :param float lab_l: L coordinate.
        :param float lab_a: a coordinate.
        :param float lab_b: b coordinate.
        :keyword str observer: Observer angle. Either ``'2'`` or ``'10'`` degrees.
        :keyword str illuminant: See :doc:`illuminants` for valid values.
        """

        super(LabColor, self).__init__()
        #: L coordinate
        self.lab_l = float(lab_l)
        #: a coordinate
        self.lab_a = float(lab_a)
        #: b coordinate
        self.lab_b = float(lab_b)

        #: The color's observer angle. Set with :py:meth:`set_observer`.
        self.observer = None
        #: The color's illuminant. Set with :py:meth:`set_illuminant`.
        self.illuminant = None

        self.set_observer(observer)
        self.set_illuminant(illuminant)


class LCHabColor(IlluminantMixin, ColorBase):
    """
    Represents an CIE LCH color that was converted to LCH by passing through
    CIE Lab.  This differs from :py:class:`LCHuvColor`, which was converted to
    LCH through CIE Luv.

    See `Introduction to Colour Spaces <http://www.colourphil.co.uk/lab_lch_colour_space.shtml>`_
    by Phil Cruse for an illustration of how CIE LCH differs from CIE Lab.
    """

    VALUES = ['lch_l', 'lch_c', 'lch_h']

    def __init__(self, lch_l, lch_c, lch_h, observer='2', illuminant='d50'):
        """
        :param float lch_l: L coordinate.
        :param float lch_c: C coordinate.
        :param float lch_h: H coordinate.
        :keyword str observer: Observer angle. Either ``'2'`` or ``'10'`` degrees.
        :keyword str illuminant: See :doc:`illuminants` for valid values.
        """

        super(LCHabColor, self).__init__()
        #: L coordinate
        self.lch_l = float(lch_l)
        #: C coordinate
        self.lch_c = float(lch_c)
        #: H coordinate
        self.lch_h = float(lch_h)

        #: The color's observer angle. Set with :py:meth:`set_observer`.
        self.observer = None
        #: The color's illuminant. Set with :py:meth:`set_illuminant`.
        self.illuminant = None

        self.set_observer(observer)
        self.set_illuminant(illuminant)


class LCHuvColor(IlluminantMixin, ColorBase):
    """
    Represents an CIE LCH color that was converted to LCH by passing through
    CIE Luv.  This differs from :py:class:`LCHabColor`, which was converted to
    LCH through CIE Lab.

    See `Introduction to Colour Spaces <http://www.colourphil.co.uk/lab_lch_colour_space.shtml>`_
    by Phil Cruse for an illustration of how CIE LCH differs from CIE Lab.
    """

    VALUES = ['lch_l', 'lch_c', 'lch_h']

    def __init__(self, lch_l, lch_c, lch_h, observer='2', illuminant='d50'):
        """
        :param float lch_l: L coordinate.
        :param float lch_c: C coordinate.
        :param float lch_h: H coordinate.
        :keyword str observer: Observer angle. Either ``'2'`` or ``'10'`` degrees.
        :keyword str illuminant: See :doc:`illuminants` for valid values.
        """

        super(LCHuvColor, self).__init__()
        #: L coordinate
        self.lch_l = float(lch_l)
        #: C coordinate
        self.lch_c = float(lch_c)
        #: H coordinate
        self.lch_h = float(lch_h)

        #: The color's observer angle. Set with :py:meth:`set_observer`.
        self.observer = None
        #: The color's illuminant. Set with :py:meth:`set_illuminant`.
        self.illuminant = None

        self.set_observer(observer)
        self.set_illuminant(illuminant)


class LuvColor(IlluminantMixin, ColorBase):
    """
    Represents an Luv color.
    """

    VALUES = ['luv_l', 'luv_u', 'luv_v']

    def __init__(self, luv_l, luv_u, luv_v, observer='2', illuminant='d50'):
        """
        :param float luv_l: L coordinate.
        :param float luv_u: u coordinate.
        :param float luv_v: v coordinate.
        :keyword str observer: Observer angle. Either ``'2'`` or ``'10'`` degrees.
        :keyword str illuminant: See :doc:`illuminants` for valid values.
        """

        super(LuvColor, self).__init__()
        #: L coordinate
        self.luv_l = float(luv_l)
        #: u coordinate
        self.luv_u = float(luv_u)
        #: v coordinate
        self.luv_v = float(luv_v)

        #: The color's observer angle. Set with :py:meth:`set_observer`.
        self.observer = None
        #: The color's illuminant. Set with :py:meth:`set_illuminant`.
        self.illuminant = None

        self.set_observer(observer)
        self.set_illuminant(illuminant)


class XYZColor(IlluminantMixin, ColorBase):
    """
    Represents an XYZ color.
    """

    VALUES = ['xyz_x', 'xyz_y', 'xyz_z']

    def __init__(self, xyz_x, xyz_y, xyz_z, observer='2', illuminant='d50'):
        """
        :param float xyz_x: X coordinate.
        :param float xyz_y: Y coordinate.
        :param float xyz_z: Z coordinate.
        :keyword str observer: Observer angle. Either ``'2'`` or ``'10'`` degrees.
        :keyword str illuminant: See :doc:`illuminants` for valid values.
        """

        super(XYZColor, self).__init__()
        #: X coordinate
        self.xyz_x = float(xyz_x)
        #: Y coordinate
        self.xyz_y = float(xyz_y)
        #: Z coordinate
        self.xyz_z = float(xyz_z)

        #: The color's observer angle. Set with :py:meth:`set_observer`.
        self.observer = None
        #: The color's illuminant. Set with :py:meth:`set_illuminant`.
        self.illuminant = None

        self.set_observer(observer)
        self.set_illuminant(illuminant)

    def apply_adaptation(self, target_illuminant, adaptation='bradford'):
        """
        This applies an adaptation matrix to change the XYZ color's illuminant.
        You'll most likely only need this during RGB conversions.
        """

        logger.debug("  \- Original illuminant: %s", self.illuminant)
        logger.debug("  \- Target illuminant: %s", target_illuminant)

        # If the XYZ values were taken with a different reference white than the
        # native reference white of the target RGB space, a transformation matrix
        # must be applied.
        if self.illuminant != target_illuminant:
            logger.debug("  \* Applying transformation from %s to %s ",
                         self.illuminant, target_illuminant)
            # Sets the adjusted XYZ values, and the new illuminant.
            apply_chromatic_adaptation_on_color(
                color=self,
                targ_illum=target_illuminant,
                adaptation=adaptation)


# noinspection PyPep8Naming
class xyYColor(IlluminantMixin, ColorBase):
    """
    Represents an xYy color.
    """

    VALUES = ['xyy_x', 'xyy_y', 'xyy_Y']

    def __init__(self, xyy_x, xyy_y, xyy_Y, observer='2', illuminant='d50'):
        """
        :param float xyy_x: x coordinate.
        :param float xyy_y: y coordinate.
        :param float xyy_Y: Y coordinate.
        :keyword str observer: Observer angle. Either ``'2'`` or ``'10'`` degrees.
        :keyword str illuminant: See :doc:`illuminants` for valid values.
        """

        super(xyYColor, self).__init__()
        #: x coordinate
        self.xyy_x = float(xyy_x)
        #: y coordinate
        self.xyy_y = float(xyy_y)
        #: Y coordinate
        self.xyy_Y = float(xyy_Y)

        #: The color's observer angle. Set with :py:meth:`set_observer`.
        self.observer = None
        #: The color's illuminant. Set with :py:meth:`set_illuminant`.
        self.illuminant = None

        self.set_observer(observer)
        self.set_illuminant(illuminant)


class BaseRGBColor(ColorBase):
    """
    Base class for all RGB color spaces.

    .. warning:: Do not use this class directly!
    """

    VALUES = ['rgb_r', 'rgb_g', 'rgb_b']

    def __init__(self, rgb_r, rgb_g, rgb_b, is_upscaled=False):
        """
        :param float rgb_r: R coordinate. 0...1. 1-255 if is_upscaled=True.
        :param float rgb_g: G coordinate. 0...1. 1-255 if is_upscaled=True.
        :param float rgb_b: B coordinate. 0...1. 1-255 if is_upscaled=True.
        :keyword bool is_upscaled: If False, RGB coordinate values are
            beteween 0.0 and 1.0. If True, RGB values are between 1 and 255.
        """

        super(BaseRGBColor, self).__init__()
        if is_upscaled:
            self.rgb_r = rgb_r / 255.0
            self.rgb_g = rgb_g / 255.0
            self.rgb_b = rgb_b / 255.0
        else:
            self.rgb_r = float(rgb_r)
            self.rgb_g = float(rgb_g)
            self.rgb_b = float(rgb_b)
        self.is_upscaled = is_upscaled

    def _clamp_rgb_coordinate(self, coord):
        """
        Clamps an RGB coordinate, taking into account whether or not the
        color is upscaled or not.

        :param float coord: The coordinate value.
        :rtype: float
        :returns: The clamped value.
        """

        if not self.is_upscaled:
            return min(max(coord, 0.0), 1.0)
        else:
            return min(max(coord, 1), 255)

    @property
    def clamped_rgb_r(self):
        """
        The clamped (0.0-1.0) R value.
        """

        return self._clamp_rgb_coordinate(self.rgb_r)

    @property
    def clamped_rgb_g(self):
        """
        The clamped (0.0-1.0) G value.
        """

        return self._clamp_rgb_coordinate(self.rgb_g)

    @property
    def clamped_rgb_b(self):
        """
        The clamped (0.0-1.0) B value.
        """

        return self._clamp_rgb_coordinate(self.rgb_b)

    def get_upscaled_value_tuple(self):
        """
        Scales an RGB color object from decimal 0.0-1.0 to int 0-255.
        """

        # Scale up to 0-255 values.
        rgb_r = int(math.floor(0.5 + self.rgb_r * 255))
        rgb_g = int(math.floor(0.5 + self.rgb_g * 255))
        rgb_b = int(math.floor(0.5 + self.rgb_b * 255))

        return rgb_r, rgb_g, rgb_b

    def get_rgb_hex(self):
        """
        Converts the RGB value to a hex value in the form of: #RRGGBB

        :rtype: str
        """

        rgb_r, rgb_g, rgb_b = self.get_upscaled_value_tuple()
        return '#%02x%02x%02x' % (rgb_r, rgb_g, rgb_b)

    @classmethod
    def new_from_rgb_hex(cls, hex_str):
        """
        Converts an RGB hex string like #RRGGBB and assigns the values to
        this sRGBColor object.

        :rtype: sRGBColor
        """

        colorstring = hex_str.strip()
        if colorstring[0] == '#':
            colorstring = colorstring[1:]
        if len(colorstring) != 6:
            raise ValueError("input #%s is not in #RRGGBB format" % colorstring)
        r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
        r, g, b = [int(n, 16) / 255.0 for n in (r, g, b)]
        return cls(r, g, b)


# noinspection PyPep8Naming
class sRGBColor(BaseRGBColor):
    """
    Represents an sRGB color.

    .. note:: If you pass in upscaled values, we automatically scale them
        down to 0.0-1.0. If you need the old upscaled values, you can
        retrieve them with :py:meth:`get_upscaled_value_tuple`.

    :ivar float rgb_r: R coordinate
    :ivar float rgb_g: G coordinate
    :ivar float rgb_b: B coordinate
    :ivar bool is_upscaled: If True, RGB values are between 1-255. If False,
        0.0-1.0.
    """

    #: RGB space's gamma constant.
    rgb_gamma = 2.2
    #: The RGB space's native illuminant. Important when converting to XYZ.
    native_illuminant = "d65"
    conversion_matrices = {
        "xyz_to_rgb":
            numpy.array((
                ( 3.24071, -0.969258, 0.0556352),
                (-1.53726, 1.87599, -0.203996),
                (-0.498571, 0.0415557, 1.05707))),
        "rgb_to_xyz":
            numpy.array((
                ( 0.412424, 0.212656, 0.0193324),
                ( 0.357579, 0.715158, 0.119193),
                ( 0.180464, 0.0721856, 0.950444))),
    }


class AdobeRGBColor(BaseRGBColor):
    """
    Represents an Adobe RGB color.

    .. note:: If you pass in upscaled values, we automatically scale them
        down to 0.0-1.0. If you need the old upscaled values, you can
        retrieve them with :py:meth:`get_upscaled_value_tuple`.

    :ivar float rgb_r: R coordinate
    :ivar float rgb_g: G coordinate
    :ivar float rgb_b: B coordinate
    :ivar bool is_upscaled: If True, RGB values are between 1-255. If False,
        0.0-1.0.
    """

    #: RGB space's gamma constant.
    rgb_gamma = 2.2
    #: The RGB space's native illuminant. Important when converting to XYZ.
    native_illuminant = "d65"
    conversion_matrices = {
        "xyz_to_rgb":
            numpy.array((
                ( 2.04148, -0.969258, 0.0134455),
                (-0.564977, 1.87599, -0.118373),
                (-0.344713, 0.0415557, 1.01527))),
        "rgb_to_xyz":
            numpy.array((
                ( 0.576700, 0.297361, 0.0270328),
                ( 0.185556, 0.627355, 0.0706879),
                ( 0.188212, 0.0752847, 0.991248))),
    }


class HSLColor(ColorBase):
    """
    Represents an HSL color.
    """

    VALUES = ['hsl_h', 'hsl_s', 'hsl_l']

    def __init__(self, hsl_h, hsl_s, hsl_l):
        """
        :param float hsl_h: H coordinate.
        :param float hsl_s: S coordinate.
        :param float hsl_l: L coordinate.
        """

        super(HSLColor, self).__init__()
        #: H coordinate
        self.hsl_h = float(hsl_h)
        #: S coordinate
        self.hsl_s = float(hsl_s)
        #: L coordinate
        self.hsl_l = float(hsl_l)


class HSVColor(ColorBase):
    """
    Represents an HSV color.
    """

    VALUES = ['hsv_h', 'hsv_s', 'hsv_v']

    def __init__(self, hsv_h, hsv_s, hsv_v):
        """
        :param float hsv_h: H coordinate.
        :param float hsv_s: S coordinate.
        :param float hsv_v: V coordinate.
        """

        super(HSVColor, self).__init__()
        #: H coordinate
        self.hsv_h = float(hsv_h)
        #: S coordinate
        self.hsv_s = float(hsv_s)
        #: V coordinate
        self.hsv_v = float(hsv_v)


class CMYColor(ColorBase):
    """
    Represents a CMY color.
    """

    VALUES = ['cmy_c', 'cmy_m', 'cmy_y']

    def __init__(self, cmy_c, cmy_m, cmy_y):
        """
        :param float cmy_c: C coordinate.
        :param float cmy_m: M coordinate.
        :param float cmy_y: Y coordinate.
        """

        super(CMYColor, self).__init__()
        #: C coordinate
        self.cmy_c = float(cmy_c)
        #: M coordinate
        self.cmy_m = float(cmy_m)
        #: Y coordinate
        self.cmy_y = float(cmy_y)


class CMYKColor(ColorBase):
    """
    Represents a CMYK color.
    """

    VALUES = ['cmyk_c', 'cmyk_m', 'cmyk_y', 'cmyk_k']

    def __init__(self, cmyk_c, cmyk_m, cmyk_y, cmyk_k):
        """
        :param float cmyk_c: C coordinate.
        :param float cmyk_m: M coordinate.
        :param float cmyk_y: Y coordinate.
        :param float cmyk_k: K coordinate.
        """

        super(CMYKColor, self).__init__()
        #: C coordinate
        self.cmyk_c = float(cmyk_c)
        #: M coordinate
        self.cmyk_m = float(cmyk_m)
        #: Y coordinate
        self.cmyk_y = float(cmyk_y)
        #: K coordinate
        self.cmyk_k = float(cmyk_k)

########NEW FILE########
__FILENAME__ = density
"""
Formulas for density calculation.
"""

from math import log10
from colormath.density_standards import ANSI_STATUS_T_BLUE, ANSI_STATUS_T_GREEN, \
    ANSI_STATUS_T_RED, VISUAL_DENSITY_THRESH, ISO_VISUAL


def ansi_density(color, density_standard):
    """
    Calculates density for the given SpectralColor using the spectral weighting
    function provided. For example, ANSI_STATUS_T_RED. These may be found in
    :py:mod:`colormath.density_standards`.
    
    :param SpectralColor color: The SpectralColor object to calculate density for.
    :param numpy.ndarray std_array: NumPy array of filter of choice
        from :py:mod:`colormath.density_standards`.
    :rtype: float
    :returns: The density value for the given color and density standard.
    """

    # Load the spec_XXXnm attributes into a Numpy array.
    sample = color.get_numpy_array()
    # Matrix multiplication
    intermediate = sample * density_standard
    
    # Sum the products.
    numerator = intermediate.sum()
    # This is the denominator in the density equation.
    sum_of_standard_wavelengths = density_standard.sum()
    
    # This is the top level of the density formula.
    return -1.0 * log10(numerator / sum_of_standard_wavelengths)


def auto_density(color):
    """
    Given a SpectralColor, automatically choose the correct ANSI T filter. Returns
    a tuple with a string representation of the filter the calculated density.

    :param SpectralColor color: The SpectralColor object to calculate density for.
    :rtype: float
    :returns: The density value, with the filter selected automatically.
    """

    blue_density = ansi_density(color, ANSI_STATUS_T_BLUE)
    green_density = ansi_density(color, ANSI_STATUS_T_GREEN)
    red_density = ansi_density(color, ANSI_STATUS_T_RED)
    
    densities = [blue_density, green_density, red_density]
    min_density = min(densities)
    max_density = max(densities)
    density_range = max_density - min_density
    
    # See comments in density_standards.py for VISUAL_DENSITY_THRESH to
    # understand what this is doing.
    if density_range <= VISUAL_DENSITY_THRESH:
        return ansi_density(color, ISO_VISUAL)
    elif blue_density > green_density and blue_density > red_density:
        return blue_density
    elif green_density > blue_density and green_density > red_density:
        return green_density
    else:
        return red_density

########NEW FILE########
__FILENAME__ = density_standards
"""
Various density standards.
"""

from numpy import array

# Visual density is typically used on grey patches. Take a reading and get
# the density values of the Red, Green, and Blue filters. If the difference
# between the highest and lowest value is less than or equal to the value
# below, return the density reading calculated against the ISO Visual spectral
# weighting curve. The X-Rite 500 uses a thresh of 0.05, the X-Rite i1 appears
# to use 0.08.
VISUAL_DENSITY_THRESH = 0.08

ANSI_STATUS_A_RED = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.37,
    43.45,
    100.00,
    74.30,
    40.18,
    19.32,
    7.94,
    3.56,
    1.46,
    0.60,
    0.24,
    0.09,
    0.04,
    0.01,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_A_GREEN = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.04,
    6.64,
    60.53,
    100.00,
    80.54,
    44.06,
    16.63,
    4.06,
    0.58,
    0.04,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_A_BLUE = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    4.00,
    65.92,
    100.00,
    81.66,
    41.69,
    10.96,
    0.79,
    0.04,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_E_RED = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.01,
    0.06,
    0.45,
    29.99,
    100.00,
    84.92,
    54.95,
    25.00,
    10.00,
    5.00,
    1.50,
    0.50,
    0.30,
    0.15,
    0.05,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_E_GREEN = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.01,
    1.00,
    5.00,
    27.99,
    68.08,
    92.04,
    100.00,
    87.90,
    66.07,
    41.98,
    21.98,
    8.99,
    2.50,
    0.70,
    0.09,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_E_BLUE = array((
    0.00,
    0.00,
    0.00,
    0.01,
    0.27,
    2.70,
    13.00,
    29.99,
    59.98,
    82.04,
    100.00,
    90.99,
    76.03,
    46.99,
    17.99,
    6.00,
    0.80,
    0.05,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_M_RED = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.13,
    30.13,
    100.00,
    79.25,
    37.84,
    17.86,
    7.50,
    3.10,
    1.26,
    0.49,
    0.19,
    0.07,
    0.03,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_M_GREEN = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.01,
    0.16,
    1.43,
    6.37,
    18.71,
    42.27,
    74.47,
    100.00,
    98.86,
    65.77,
    28.71,
    8.22,
    1.49,
    0.17,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_M_BLUE = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.13,
    12.91,
    42.85,
    74.30,
    100.00,
    90.16,
    55.34,
    22.03,
    5.53,
    0.98,
    0.07,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_T_RED = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.06,
    0.45,
    29.99,
    100.00,
    84.92,
    54.95,
    25.00,
    10.00,
    5.00,
    1.50,
    0.50,
    0.30,
    0.15,
    0.05,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_T_GREEN = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    1.00,
    5.00,
    27.99,
    68.08,
    92.04,
    100.00,
    87.90,
    66.07,
    41.98,
    21.98,
    8.99,
    2.50,
    0.70,
    0.09,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ANSI_STATUS_T_BLUE = array((
    0.00,
    0.01,
    0.02,
    0.10,
    0.30,
    1.50,
    6.00,
    16.98,
    39.99,
    59.98,
    82.04,
    93.97,
    100.00,
    97.05,
    84.92,
    65.01,
    39.99,
    17.99,
    5.00,
    0.20,
    0.04,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

TYPE1 = array((
    0.00,
    0.00,
    0.01,
    0.04,
    0.72,
    28.84,
    100.00,
    28.84,
    0.72,
    0.04,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

TYPE2 = array((
    0.01,
    0.51,
    19.05,
    38.28,
    57.54,
    70.96,
    82.41,
    90.36,
    97.27,
    100.00,
    97.72,
    89.33,
    73.11,
    55.34,
    38.19,
    22.44,
    9.84,
    2.52,
    0.64,
    0.16,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

ISO_VISUAL = array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.01,
    0.02,
    0.08,
    0.28,
    0.65,
    1.23,
    2.22,
    3.82,
    6.58,
    10.99,
    18.88,
    32.58,
    50.35,
    66.83,
    80.35,
    90.57,
    97.50,
    100.00,
    97.50,
    90.36,
    79.80,
    67.14,
    53.83,
    39.17,
    27.10,
    17.30,
    10.30,
    5.61,
    3.09,
    1.54,
    0.80,
    0.42,
    0.22,
    0.11,
    0.05,
    0.03,
    0.01,
    0.01,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

########NEW FILE########
__FILENAME__ = spectral_constants
"""
Contains lookup tables, constants, and things that are generally static
and useful throughout the library.
"""
import numpy

STDOBSERV_X2 = numpy.array((
    0.000000000000,
    0.000000000000,
    0.000129900000,
    0.000414900000,
    0.001368000000,
    0.004243000000,
    0.014310000000,
    0.043510000000,
    0.134380000000,
    0.283900000000,
    0.348280000000,
    0.336200000000,
    0.290800000000,
    0.195360000000,
    0.095640000000,
    0.032010000000,
    0.004900000000,
    0.009300000000,
    0.063270000000,
    0.165500000000,
    0.290400000000,
    0.433449900000,
    0.594500000000,
    0.762100000000,
    0.916300000000,
    1.026300000000,
    1.062200000000,
    1.002600000000,
    0.854449900000,
    0.642400000000,
    0.447900000000,
    0.283500000000,
    0.164900000000,
    0.087400000000,
    0.046770000000,
    0.022700000000,
    0.011359160000,
    0.005790346000,
    0.002899327000,
    0.001439971000,
    0.000690078600,
    0.000332301100,
    0.000166150500,
    0.000083075270,
    0.000041509940,
    0.000020673830,
    0.000010253980,
    0.000005085868,
    0.000002522525,
    0.000001251141
))

STDOBSERV_Y2 = numpy.array((
    0.000000000000,
    0.000000000000,
    0.000003917000,
    0.000012390000,
    0.000039000000,
    0.000120000000,
    0.000396000000,
    0.001210000000,
    0.004000000000,
    0.011600000000,
    0.023000000000,
    0.038000000000,
    0.060000000000,
    0.090980000000,
    0.139020000000,
    0.208020000000,
    0.323000000000,
    0.503000000000,
    0.710000000000,
    0.862000000000,
    0.954000000000,
    0.994950100000,
    0.995000000000,
    0.952000000000,
    0.870000000000,
    0.757000000000,
    0.631000000000,
    0.503000000000,
    0.381000000000,
    0.265000000000,
    0.175000000000,
    0.107000000000,
    0.061000000000,
    0.032000000000,
    0.017000000000,
    0.008210000000,
    0.004102000000,
    0.002091000000,
    0.001047000000,
    0.000520000000,
    0.000249200000,
    0.000120000000,
    0.000060000000,
    0.000030000000,
    0.000014990000,
    0.000007465700,
    0.000003702900,
    0.000001836600,
    0.000000910930,
    0.000000451810
))

STDOBSERV_Z2 = numpy.array((
    0.000000000000,
    0.000000000000,
    0.000606100000,
    0.001946000000,
    0.006450001000,
    0.020050010000,
    0.067850010000,
    0.207400000000,
    0.645600000000,
    1.385600000000,
    1.747060000000,
    1.772110000000,
    1.669200000000,
    1.287640000000,
    0.812950100000,
    0.465180000000,
    0.272000000000,
    0.158200000000,
    0.078249990000,
    0.042160000000,
    0.020300000000,
    0.008749999000,
    0.003900000000,
    0.002100000000,
    0.001650001000,
    0.001100000000,
    0.000800000000,
    0.000340000000,
    0.000190000000,
    0.000049999990,
    0.000020000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000
))

STDOBSERV_X10 = numpy.array((
    0.000000000000,
    0.000000000000,
    0.000000122200,
    0.000005958600,
    0.000159952000,
    0.002361600000,
    0.019109700000,
    0.084736000000,
    0.204492000000,
    0.314679000000,
    0.383734000000,
    0.370702000000,
    0.302273000000,
    0.195618000000,
    0.080507000000,
    0.016172000000,
    0.003816000000,
    0.037465000000,
    0.117749000000,
    0.236491000000,
    0.376772000000,
    0.529826000000,
    0.705224000000,
    0.878655000000,
    1.014160000000,
    1.118520000000,
    1.123990000000,
    1.030480000000,
    0.856297000000,
    0.647467000000,
    0.431567000000,
    0.268329000000,
    0.152568000000,
    0.081260600000,
    0.040850800000,
    0.019941300000,
    0.009576880000,
    0.004552630000,
    0.002174960000,
    0.001044760000,
    0.000508258000,
    0.000250969000,
    0.000126390000,
    0.000064525800,
    0.000033411700,
    0.000017611500,
    0.000009413630,
    0.000005093470,
    0.000002795310,
    0.000001553140
))

STDOBSERV_Y10 = numpy.array((
    0.000000000000,
    0.000000000000,
    0.000000013398,
    0.000000651100,
    0.000017364000,
    0.000253400000,
    0.002004400000,
    0.008756000000,
    0.021391000000,
    0.038676000000,
    0.062077000000,
    0.089456000000,
    0.128201000000,
    0.185190000000,
    0.253589000000,
    0.339133000000,
    0.460777000000,
    0.606741000000,
    0.761757000000,
    0.875211000000,
    0.961988000000,
    0.991761000000,
    0.997340000000,
    0.955552000000,
    0.868934000000,
    0.777405000000,
    0.658341000000,
    0.527963000000,
    0.398057000000,
    0.283493000000,
    0.179828000000,
    0.107633000000,
    0.060281000000,
    0.031800400000,
    0.015905100000,
    0.007748800000,
    0.003717740000,
    0.001768470000,
    0.000846190000,
    0.000407410000,
    0.000198730000,
    0.000098428000,
    0.000049737000,
    0.000025486000,
    0.000013249000,
    0.000007012800,
    0.000003764730,
    0.000002046130,
    0.000001128090,
    0.000000629700
))

STDOBSERV_Z10 = numpy.array((
    0.000000000000,
    0.000000000000,
    0.000000535027,
    0.000026143700,
    0.000704776000,
    0.010482200000,
    0.086010900000,
    0.389366000000,
    0.972542000000,
    1.553480000000,
    1.967280000000,
    1.994800000000,
    1.745370000000,
    1.317560000000,
    0.772125000000,
    0.415254000000,
    0.218502000000,
    0.112044000000,
    0.060709000000,
    0.030451000000,
    0.013676000000,
    0.003988000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000,
    0.000000000000
))

REFERENCE_ILLUM_A = numpy.array((
    3.59,
    4.75,
    6.15,
    7.83,
    9.80,
    12.09,
    14.72,
    17.69,
    21.01,
    24.68,
    28.71,
    33.10,
    37.82,
    42.88,
    48.25,
    53.92,
    59.87,
    66.07,
    72.50,
    79.14,
    85.95,
    92.91,
    100.00,
    107.18,
    114.43,
    121.72,
    129.03,
    136.33,
    143.60,
    150.81,
    157.95,
    164.99,
    171.92,
    178.72,
    185.38,
    191.88,
    198.20,
    204.34,
    210.29,
    216.04,
    221.58,
    226.91,
    232.02,
    236.91,
    241.57,
    246.01,
    250.21,
    254.19,
    257.95,
    261.47
))

REFERENCE_ILLUM_B = numpy.array((
    2.40,
    5.60,
    9.60,
    15.20,
    22.40,
    31.30,
    41.30,
    52.10,
    63.20,
    73.10,
    80.80,
    85.40,
    88.30,
    92.00,
    95.20,
    96.50,
    94.20,
    90.70,
    89.50,
    92.20,
    96.90,
    101.00,
    102.80,
    102.60,
    101.00,
    99.20,
    98.00,
    98.50,
    99.70,
    101.00,
    102.20,
    103.90,
    105.00,
    104.90,
    103.90,
    101.60,
    99.10,
    96.20,
    92.90,
    89.40,
    86.90,
    85.20,
    84.70,
    85.40,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

REFERENCE_ILLUM_C = numpy.array((
    2.70,
    7.00,
    12.90,
    21.40,
    33.00,
    47.40,
    63.30,
    80.60,
    98.10,
    112.40,
    121.50,
    124.00,
    123.10,
    123.80,
    123.90,
    120.70,
    112.10,
    102.30,
    96.90,
    98.00,
    102.10,
    105.20,
    105.30,
    102.30,
    97.80,
    93.20,
    89.70,
    88.40,
    88.10,
    88.00,
    87.80,
    88.20,
    87.90,
    86.30,
    84.00,
    80.20,
    76.30,
    72.40,
    68.30,
    64.40,
    61.50,
    59.20,
    58.10,
    58.20,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

REFERENCE_ILLUM_D50 = numpy.array((
    17.92,
    20.98,
    23.91,
    25.89,
    24.45,
    29.83,
    49.25,
    56.45,
    59.97,
    57.76,
    74.77,
    87.19,
    90.56,
    91.32,
    95.07,
    91.93,
    95.70,
    96.59,
    97.11,
    102.09,
    100.75,
    102.31,
    100.00,
    97.74,
    98.92,
    93.51,
    97.71,
    99.29,
    99.07,
    95.75,
    98.90,
    95.71,
    98.24,
    103.06,
    99.19,
    87.43,
    91.66,
    92.94,
    76.89,
    86.56,
    92.63,
    78.27,
    57.72,
    82.97,
    78.31,
    79.59,
    73.44,
    63.95,
    70.81,
    74.48
))

REFERENCE_ILLUM_D65 = numpy.array((
    39.90,
    44.86,
    46.59,
    51.74,
    49.92,
    54.60,
    82.69,
    91.42,
    93.37,
    86.63,
    104.81,
    116.96,
    117.76,
    114.82,
    115.89,
    108.78,
    109.33,
    107.78,
    104.78,
    107.68,
    104.40,
    104.04,
    100.00,
    96.34,
    95.79,
    88.69,
    90.02,
    89.61,
    87.71,
    83.30,
    83.72,
    80.05,
    80.24,
    82.30,
    78.31,
    69.74,
    71.63,
    74.37,
    61.62,
    69.91,
    75.11,
    63.61,
    46.43,
    66.83,
    63.40,
    64.32,
    59.47,
    51.97,
    57.46,
    60.33
))

REFERENCE_ILLUM_E = numpy.array((
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
    100.00,
))

REFERENCE_ILLUM_F2 = numpy.array((
    0.00,
    0.00,
    0.00,
    0.00,
    1.18,
    1.84,
    3.44,
    3.85,
    4.19,
    5.06,
    11.81,
    6.63,
    7.19,
    7.54,
    7.65,
    7.62,
    7.28,
    7.05,
    7.16,
    8.04,
    10.01,
    16.64,
    16.16,
    18.62,
    22.79,
    18.66,
    16.54,
    13.80,
    10.95,
    8.40,
    6.31,
    4.68,
    3.45,
    2.55,
    1.89,
    1.53,
    1.10,
    0.88,
    0.68,
    0.56,
    0.51,
    0.47,
    0.46,
    0.40,
    0.27,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

REFERENCE_ILLUM_F7 = numpy.array((
    0.00,
    0.00,
    0.00,
    0.00,
    2.56,
    3.84,
    6.15,
    7.37,
    7.71,
    9.15,
    17.52,
    12.00,
    13.08,
    13.71,
    13.95,
    13.82,
    13.43,
    13.08,
    12.78,
    12.44,
    12.26,
    17.05,
    12.58,
    12.83,
    16.75,
    12.67,
    12.19,
    11.60,
    11.12,
    10.76,
    10.11,
    10.02,
    9.87,
    7.27,
    5.83,
    5.04,
    4.12,
    3.46,
    2.73,
    2.25,
    1.90,
    1.62,
    1.45,
    1.17,
    0.81,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

REFERENCE_ILLUM_F11 = numpy.array((
    0.00,
    0.00,
    0.00,
    0.00,
    0.91,
    0.46,
    1.29,
    1.59,
    2.46,
    4.49,
    12.13,
    7.19,
    6.72,
    5.46,
    5.66,
    14.96,
    4.72,
    1.47,
    0.89,
    1.18,
    39.59,
    32.61,
    2.83,
    1.67,
    11.28,
    12.73,
    7.33,
    55.27,
    13.18,
    12.26,
    2.07,
    3.58,
    2.48,
    1.54,
    1.46,
    2.00,
    1.35,
    5.58,
    0.57,
    0.23,
    0.24,
    0.20,
    0.32,
    0.16,
    0.09,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00
))

REFERENCE_ILLUM_BLACKBODY = numpy.array((
    43.36,
    47.77,
    52.15,
    56.44,
    60.62,
    64.65,
    68.51,
    72.18,
    75.63,
    78.87,
    81.87,
    84.63,
    87.16,
    89.44,
    91.48,
    93.29,
    94.87,
    96.23,
    97.37,
    98.31,
    99.05,
    99.61,
    100.00,
    100.22,
    100.29,
    100.21,
    100.00,
    99.67,
    99.22,
    98.67,
    98.02,
    97.28,
    96.47,
    95.58,
    94.63,
    93.62,
    92.56,
    91.45,
    90.30,
    89.12,
    87.91,
    86.67,
    85.42,
    84.15,
    82.86,
    81.56,
    80.26,
    78.95,
    77.64,
    76.33
))

# This table is used to match up illuminants to spectral distributions above.
# It should correspond to a ColorObject.illuminant attribute.
REF_ILLUM_TABLE = {
    'a': REFERENCE_ILLUM_A,
    'b': REFERENCE_ILLUM_B,
    'c': REFERENCE_ILLUM_C,
    'd50': REFERENCE_ILLUM_D50,
    'd65': REFERENCE_ILLUM_D65,
    'e': REFERENCE_ILLUM_E,
    'f2': REFERENCE_ILLUM_F2,
    'f7': REFERENCE_ILLUM_F7,
    'f11': REFERENCE_ILLUM_F11,
    'blackbody': REFERENCE_ILLUM_BLACKBODY,
}
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# python-colormath documentation build configuration file, created by
# sphinx-quickstart on Thu Mar 20 00:32:55 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
project_root = os.path.dirname(os.path.abspath('.'))
sys.path.insert(0, project_root)

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'python-colormath'
copyright = u'2014, Greg Taylor'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.0'
# The full version, including alpha/beta/rc tags.
release = '2.0.2'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'python-colormathdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'python-colormath.tex', u'python-colormath Documentation',
   u'Greg Taylor', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'python-colormath', u'python-colormath Documentation',
     [u'Greg Taylor'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'python-colormath', u'python-colormath Documentation',
   u'Greg Taylor', 'python-colormath', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

autoclass_content = "both"
autodoc_default_flags = ["members", "inherited-members", "show-inheritance"]
autodoc_member_order = "groupwise"

########NEW FILE########
__FILENAME__ = conversions
"""
This module shows you how to perform color space conversions. Please see the
chart on www.brucelindbloom.com/Math.html for an illustration of the conversions
you may perform.
"""

# Does some sys.path manipulation so we can run examples in-place.
# noinspection PyUnresolvedReferences
import example_config

from colormath.color_conversions import convert_color
from colormath.color_objects import LabColor, LCHabColor, SpectralColor, sRGBColor, \
    XYZColor, LCHuvColor


def example_lab_to_xyz():
    """
    This function shows a simple conversion of an Lab color to an XYZ color.
    """

    print("=== Simple Example: Lab->XYZ ===")
    # Instantiate an Lab color object with the given values.
    lab = LabColor(0.903, 16.296, -2.22)
    # Show a string representation.
    print(lab)
    # Convert to XYZ.
    xyz = convert_color(lab, XYZColor)
    print(xyz)
    print("=== End Example ===\n")


def example_lchab_to_lchuv():
    """
    This function shows very complex chain of conversions in action.
    
    LCHab to LCHuv involves four different calculations, making this the
    conversion requiring the most steps.
    """

    print("=== Complex Example: LCHab->LCHuv ===")
    # Instantiate an LCHab color object with the given values.
    lchab = LCHabColor(0.903, 16.447, 352.252)
    # Show a string representation.
    print(lchab)
    # Convert to LCHuv.
    lchuv = convert_color(lchab, LCHuvColor)
    print(lchuv)
    print("=== End Example ===\n")


def example_lab_to_rgb():
    """
    Conversions to RGB are a little more complex mathematically. There are also
    several kinds of RGB color spaces. When converting from a device-independent
    color space to RGB, sRGB is assumed unless otherwise specified with the
    target_rgb keyword arg.
    """

    print("=== RGB Example: Lab->RGB ===")
    # Instantiate an Lab color object with the given values.
    lab = LabColor(0.903, 16.296, -2.217)
    # Show a string representation.
    print(lab)
    # Convert to XYZ.
    rgb = convert_color(lab, sRGBColor)
    print(rgb)
    print("=== End Example ===\n")


def example_rgb_to_xyz():
    """
    The reverse is similar.
    """

    print("=== RGB Example: RGB->XYZ ===")
    # Instantiate an Lab color object with the given values.
    rgb = sRGBColor(120, 130, 140)
    # Show a string representation.
    print(rgb)
    # Convert RGB to XYZ using a D50 illuminant.
    xyz = convert_color(rgb, XYZColor, target_illuminant='D50')
    print(xyz)
    print("=== End Example ===\n")


def example_spectral_to_xyz():
    """
    Instantiate an Lab color object with the given values. Note that the
    spectral range can run from 340nm to 830nm. Any omitted values assume a
    value of 0.0, which is more or less ignored. For the distribution below,
    we are providing an example reading from an X-Rite i1 Pro, which only
    measures between 380nm and 730nm.
    """

    print("=== Example: Spectral->XYZ ===")
    spc = SpectralColor(
        observer='2', illuminant='d50',
        spec_380nm=0.0600, spec_390nm=0.0600, spec_400nm=0.0641,
        spec_410nm=0.0654, spec_420nm=0.0645, spec_430nm=0.0605,
        spec_440nm=0.0562, spec_450nm=0.0543, spec_460nm=0.0537,
        spec_470nm=0.0541, spec_480nm=0.0559, spec_490nm=0.0603,
        spec_500nm=0.0651, spec_510nm=0.0680, spec_520nm=0.0705,
        spec_530nm=0.0736, spec_540nm=0.0772, spec_550nm=0.0809,
        spec_560nm=0.0870, spec_570nm=0.0990, spec_580nm=0.1128,
        spec_590nm=0.1251, spec_600nm=0.1360, spec_610nm=0.1439,
        spec_620nm=0.1511, spec_630nm=0.1590, spec_640nm=0.1688,
        spec_650nm=0.1828, spec_660nm=0.1996, spec_670nm=0.2187,
        spec_680nm=0.2397, spec_690nm=0.2618, spec_700nm=0.2852,
        spec_710nm=0.2500, spec_720nm=0.2400, spec_730nm=0.2300)
    xyz = convert_color(spc, XYZColor)
    print(xyz)
    print("=== End Example ===\n")
    
# Feel free to comment/un-comment examples as you please.
example_lab_to_xyz()
example_lchab_to_lchuv()
example_lab_to_rgb()
example_spectral_to_xyz()
example_rgb_to_xyz()

########NEW FILE########
__FILENAME__ = delta_e
"""
This module shows some examples of Delta E calculations of varying types.
"""

# Does some sys.path manipulation so we can run examples in-place.
# noinspection PyUnresolvedReferences
import example_config

from colormath.color_objects import LabColor
from colormath.color_diff import delta_e_cie1976, delta_e_cie1994, \
    delta_e_cie2000, delta_e_cmc

# Reference color.
color1 = LabColor(lab_l=0.9, lab_a=16.3, lab_b=-2.22)
# Color to be compared to the reference.
color2 = LabColor(lab_l=0.7, lab_a=14.2, lab_b=-1.80)

print("== Delta E Colors ==")
print(" COLOR1: %s" % color1)
print(" COLOR2: %s" % color2)
print("== Results ==")
print(" CIE1976: %.3f" % delta_e_cie1976(color1, color2))
print(" CIE1994: %.3f (Graphic Arts)" % delta_e_cie1994(color1, color2))
# Different values for textiles.
print(" CIE1994: %.3f (Textiles)" % delta_e_cie1994(color1,
    color2, K_1=0.048, K_2=0.014, K_L=2))
print(" CIE2000: %.3f" % delta_e_cie2000(color1, color2))
# Typically used for acceptability.
print("     CMC: %.3f (2:1)" % delta_e_cmc(color1, color2, pl=2, pc=1))
# Typically used to more closely model human perception.
print("     CMC: %.3f (1:1)" % delta_e_cmc(color1, color2, pl=1, pc=1))

########NEW FILE########
__FILENAME__ = delta_e_matrix
"""
For a massive matrix of colors and color labels you can download
the follow two files

# http://lyst-classifiers.s3.amazonaws.com/color/lab-colors.pk
# http://lyst-classifiers.s3.amazonaws.com/color/lab-matrix.pk

lab-colors is a cPickled list of color names and lab-matrix is a
cPickled (n,3) numpy array LAB values such that row q maps to
index q in the lab color list
"""

import sys
import csv
import bz2

import numpy as np

# Does some sys.path manipulation so we can run examples in-place.
# noinspection PyUnresolvedReferences
import example_config

from colormath.color_diff_matrix import delta_e_cie2000
from colormath.color_objects import LabColor


# load list of 1000 random colors from the XKCD color chart
if sys.version_info >= (3, 0):
    reader = csv.DictReader(bz2.open('lab_matrix.csv.bz2', mode='rt'))
    lab_matrix = np.array([list(map(float, row.values())) for row in reader])
else:
    reader = csv.DictReader(bz2.BZ2File('lab_matrix.csv.bz2'))
    lab_matrix = np.array([map(float, row.values()) for row in reader])

color = LabColor(lab_l=69.34, lab_a=-0.88, lab_b=-52.57)
lab_color_vector = np.array([color.lab_l, color.lab_a, color.lab_b])
delta = delta_e_cie2000(lab_color_vector, lab_matrix)

print('%s is closest to %s' % (color, lab_matrix[np.argmin(delta)]))

########NEW FILE########
__FILENAME__ = density
"""
This module shows you how to perform various kinds of density calculations.
"""

# Does some sys.path manipulation so we can run examples in-place.
# noinspection PyUnresolvedReferences
import example_config

from colormath.color_objects import SpectralColor
from colormath.density_standards import ANSI_STATUS_T_RED, ISO_VISUAL

EXAMPLE_COLOR = SpectralColor(
    observer=2, illuminant='d50',
    spec_380nm=0.0600, spec_390nm=0.0600, spec_400nm=0.0641,
    spec_410nm=0.0654, spec_420nm=0.0645, spec_430nm=0.0605,
    spec_440nm=0.0562, spec_450nm=0.0543, spec_460nm=0.0537,
    spec_470nm=0.0541, spec_480nm=0.0559, spec_490nm=0.0603,
    spec_500nm=0.0651, spec_510nm=0.0680, spec_520nm=0.0705,
    spec_530nm=0.0736, spec_540nm=0.0772, spec_550nm=0.0809,
    spec_560nm=0.0870, spec_570nm=0.0990, spec_580nm=0.1128,
    spec_590nm=0.1251, spec_600nm=0.1360, spec_610nm=0.1439,
    spec_620nm=0.1511, spec_630nm=0.1590, spec_640nm=0.1688,
    spec_650nm=0.1828, spec_660nm=0.1996, spec_670nm=0.2187,
    spec_680nm=0.2397, spec_690nm=0.2618, spec_700nm=0.2852,
    spec_710nm=0.2500, spec_720nm=0.2400, spec_730nm=0.2300)


def example_auto_status_t_density():
    print("=== Example: Automatic Status T Density ===")
    # If no arguments are provided to calc_density(), ANSI Status T density is
    # assumed. The correct RGB "filter" is automatically selected for you.
    print("Density: %f" % EXAMPLE_COLOR.calc_density())
    print("=== End Example ===\n")


def example_manual_status_t_density():
    print("=== Example: Manual Status T Density ===")
    # Here we are specifically requesting the value of the red band via the
    # ANSI Status T spec.
    print("Density: %f (Red)" % EXAMPLE_COLOR.calc_density(
        density_standard=ANSI_STATUS_T_RED))
    print("=== End Example ===\n")


def example_visual_density():
    print("=== Example: Visual Density ===")
    # Here we pass the ISO Visual spectral standard.
    print("Density: %f" % EXAMPLE_COLOR.calc_density(
        density_standard=ISO_VISUAL))
    print("=== End Example ===\n")
    
# Feel free to comment/un-comment examples as you please.
example_auto_status_t_density()
example_manual_status_t_density()
example_visual_density()

########NEW FILE########
__FILENAME__ = example_config
"""
This file holds various configuration options used for all of the examples.
"""
import os
import sys
# Use the colormath directory included in the downloaded package instead of
# any globally installed versions.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
########NEW FILE########
__FILENAME__ = test_chromatic_adaptation
"""
Tests for color difference (Delta E) equations.
"""

import unittest

from colormath.color_objects import XYZColor


# noinspection PyPep8Naming
class chromaticAdaptationTestCase(unittest.TestCase):
    def setUp(self):
        self.color = XYZColor(0.5, 0.4, 0.1, illuminant='C')
        
    def test_adaptation_c_to_d65(self):
        self.color.apply_adaptation(target_illuminant='D65')
        self.assertAlmostEqual(
            self.color.xyz_x, 0.491, 3,
            "C to D65 adaptation failed: X coord")
        self.assertAlmostEqual(
            self.color.xyz_y, 0.400, 3,
            "C to D65 adaptation failed: Y coord")
        self.assertAlmostEqual(
            self.color.xyz_z, 0.093, 3,
            "C to D65 adaptation failed: Z coord")
        self.assertEqual(
            self.color.illuminant, 'd65',
            "C to D65 adaptation failed: Illuminant transfer")

########NEW FILE########
__FILENAME__ = test_color_diff
"""
Tests for color difference (Delta E) equations.
"""

import unittest

from colormath.color_diff import delta_e_cie1976, delta_e_cie1994, \
    delta_e_cie2000, delta_e_cmc
from colormath.color_objects import LabColor, sRGBColor


class DeltaETestCase(unittest.TestCase):
    def setUp(self):
        self.color1 = LabColor(lab_l=0.9, lab_a=16.3, lab_b=-2.22)
        self.color2 = LabColor(lab_l=0.7, lab_a=14.2, lab_b=-1.80)
        
    def test_cie2000_accuracy(self):
        result = delta_e_cie2000(self.color1, self.color2)
        expected = 1.523
        self.assertAlmostEqual(result, expected, 3, 
            "DeltaE CIE2000 formula error. Got %.3f, expected %.3f (diff: %.3f)." % (
                result, expected, result - expected))
        
    def test_cie2000_accuracy_2(self):
        """
        Follow a different execution path based on variable values.
        """

        # These values are from ticket 8 in regards to a CIE2000 bug.
        c1 = LabColor(lab_l=32.8911, lab_a=-53.0107, lab_b=-43.3182)
        c2 = LabColor(lab_l=77.1797, lab_a=25.5928, lab_b=17.9412)
        result = delta_e_cie2000(c1, c2)
        expected = 78.772
        self.assertAlmostEqual(result, expected, 3, 
            "DeltaE CIE2000 formula error. Got %.3f, expected %.3f (diff: %.3f)." % (
                result, expected, result - expected))
        
    def test_cie2000_accuracy_3(self):
        """
        Reference:
        "The CIEDE2000 Color-Difference Formula: Implementation Notes, 
        Supplementary Test Data, and Mathematical Observations,", G. Sharma, 
        W. Wu, E. N. Dalal, submitted to Color Research and Application,
        January 2004. http://www.ece.rochester.edu/~gsharma/ciede2000/
        """

        color1 = (
            LabColor(lab_l=50.0000, lab_a=2.6772, lab_b=-79.7751),
            LabColor(lab_l=50.0000, lab_a=3.1571, lab_b=-77.2803),
            LabColor(lab_l=50.0000, lab_a=2.8361, lab_b=-74.0200),
            LabColor(lab_l=50.0000, lab_a=-1.3802, lab_b=-84.2814),
            LabColor(lab_l=50.0000, lab_a=-1.1848, lab_b=-84.8006),
            LabColor(lab_l=50.0000, lab_a=-0.9009, lab_b=-85.5211),
            LabColor(lab_l=50.0000, lab_a=0.0000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=-1.0000, lab_b=2.0000),
            LabColor(lab_l=50.0000, lab_a=2.4900, lab_b=-0.0010),
            LabColor(lab_l=50.0000, lab_a=2.4900, lab_b=-0.0010),
            LabColor(lab_l=50.0000, lab_a=2.4900, lab_b=-0.0010),
            LabColor(lab_l=50.0000, lab_a=2.4900, lab_b=-0.0010),
            LabColor(lab_l=50.0000, lab_a=-0.0010, lab_b=2.4900),
            LabColor(lab_l=50.0000, lab_a=-0.0010, lab_b=2.4900),
            LabColor(lab_l=50.0000, lab_a=-0.0010, lab_b=2.4900),
            LabColor(lab_l=50.0000, lab_a=2.5000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=2.5000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=2.5000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=2.5000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=2.5000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=2.5000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=2.5000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=2.5000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=2.5000, lab_b=0.0000),
            LabColor(lab_l=60.2574, lab_a=-34.0099, lab_b=36.2677),
            LabColor(lab_l=63.0109, lab_a=-31.0961, lab_b=-5.8663),
            LabColor(lab_l=61.2901, lab_a=3.7196, lab_b=-5.3901),
            LabColor(lab_l=35.0831, lab_a=-44.1164, lab_b=3.7933),
            LabColor(lab_l=22.7233, lab_a=20.0904, lab_b=-46.6940),
            LabColor(lab_l=36.4612, lab_a=47.8580, lab_b=18.3852),
            LabColor(lab_l=90.8027, lab_a=-2.0831, lab_b=1.4410),
            LabColor(lab_l=90.9257, lab_a=-0.5406, lab_b=-0.9208),
            LabColor(lab_l=6.7747, lab_a=-0.2908, lab_b=-2.4247),
            LabColor(lab_l=2.0776, lab_a=0.0795, lab_b=-1.1350)
        )
        color2 = (
            LabColor(lab_l=50.0000, lab_a=0.0000, lab_b=-82.7485),
            LabColor(lab_l=50.0000, lab_a=0.0000, lab_b=-82.7485),
            LabColor(lab_l=50.0000, lab_a=0.0000, lab_b=-82.7485),
            LabColor(lab_l=50.0000, lab_a=0.0000, lab_b=-82.7485),
            LabColor(lab_l=50.0000, lab_a=0.0000, lab_b=-82.7485),
            LabColor(lab_l=50.0000, lab_a=0.0000, lab_b=-82.7485),
            LabColor(lab_l=50.0000, lab_a=-1.0000, lab_b=2.0000),
            LabColor(lab_l=50.0000, lab_a=0.0000, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=-2.4900, lab_b=0.0009),
            LabColor(lab_l=50.0000, lab_a=-2.4900, lab_b=0.0010),
            LabColor(lab_l=50.0000, lab_a=-2.4900, lab_b=0.0011),
            LabColor(lab_l=50.0000, lab_a=-2.4900, lab_b=0.0012),
            LabColor(lab_l=50.0000, lab_a=0.0009, lab_b=-2.4900),
            LabColor(lab_l=50.0000, lab_a=0.0010, lab_b=-2.4900),
            LabColor(lab_l=50.0000, lab_a=0.0011, lab_b=-2.4900),
            LabColor(lab_l=50.0000, lab_a=0.0000, lab_b=-2.5000),
            LabColor(lab_l=73.0000, lab_a=25.0000, lab_b=-18.0000),
            LabColor(lab_l=61.0000, lab_a=-5.0000, lab_b=29.0000),
            LabColor(lab_l=56.0000, lab_a=-27.0000, lab_b=-3.0000),
            LabColor(lab_l=58.0000, lab_a=24.0000, lab_b=15.0000),
            LabColor(lab_l=50.0000, lab_a=3.1736, lab_b=0.5854),
            LabColor(lab_l=50.0000, lab_a=3.2972, lab_b=0.0000),
            LabColor(lab_l=50.0000, lab_a=1.8634, lab_b=0.5757),
            LabColor(lab_l=50.0000, lab_a=3.2592, lab_b=0.3350),
            LabColor(lab_l=60.4626, lab_a=-34.1751, lab_b=39.4387),
            LabColor(lab_l=62.8187, lab_a=-29.7946, lab_b=-4.0864),
            LabColor(lab_l=61.4292, lab_a=2.2480, lab_b=-4.9620),
            LabColor(lab_l=35.0232, lab_a=-40.0716, lab_b=1.5901),
            LabColor(lab_l=23.0331, lab_a=14.9730, lab_b=-42.5619),
            LabColor(lab_l=36.2715, lab_a=50.5065, lab_b=21.2231),
            LabColor(lab_l=91.1528, lab_a=-1.6435, lab_b=0.0447),
            LabColor(lab_l=88.6381, lab_a=-0.8985, lab_b=-0.7239),
            LabColor(lab_l=5.8714, lab_a=-0.0985, lab_b=-2.2286),
            LabColor(lab_l=0.9033, lab_a=-0.0636, lab_b=-0.5514)
        )
        diff = (
            2.0425, 2.8615, 3.4412, 1.0000, 1.0000, 
            1.0000, 2.3669, 2.3669, 7.1792, 7.1792, 
            7.2195, 7.2195, 4.8045, 4.8045, 4.7461, 
            4.3065, 27.1492, 22.8977, 31.9030, 19.4535, 
            1.0000, 1.0000, 1.0000, 1.0000, 1.2644, 
            1.2630, 1.8731, 1.8645, 2.0373, 1.4146, 
            1.4441, 1.5381, 0.6377, 0.9082
        )
        for l_set in zip(color1, color2, diff):
            result = delta_e_cie2000(l_set[0], l_set[1])
            expected = l_set[2]
            self.assertAlmostEqual(result, expected, 4,
                "DeltaE CIE2000 formula error. Got %.4f, expected %.4f (diff: %.4f)." % (
                    result, expected, result - expected))
        
    def test_cie1994_negative_square_root(self):
        """
        Tests against a case where a negative square root in the delta_H
        calculation could happen.
        """

        standard = LabColor(lab_l=0.9, lab_a=1, lab_b=1)
        sample = LabColor(lab_l=0.7, lab_a=0, lab_b=0)
        delta_e_cie1994(standard, sample)

    def test_cmc_negative_square_root(self):
        """
        Tests against a case where a negative square root in the delta_H
        calculation could happen.
        """

        standard = LabColor(lab_l=0.9, lab_a=1, lab_b=1)
        sample = LabColor(lab_l=0.7, lab_a=0, lab_b=0)
        delta_e_cmc(standard, sample)

    # noinspection PyArgumentEqualDefault
    def test_cmc_accuracy(self):
        # Test 2:1
        result = delta_e_cmc(self.color1, self.color2, pl=2, pc=1)
        expected = 1.443
        self.assertAlmostEqual(result, expected, 3, 
            "DeltaE CMC (2:1) formula error. Got %.3f, expected %.3f (diff: %.3f)." % (
                result, expected, result - expected))
        
        # Test against 1:1 as well
        result = delta_e_cmc(self.color1, self.color2, pl=1, pc=1)
        expected = 1.482
        self.assertAlmostEqual(result, expected, 3, 
            "DeltaE CMC (1:1) formula error. Got %.3f, expected %.3f (diff: %.3f)." % (
                result, expected, result - expected))
        
        # Testing atan H behavior.
        atan_color1 = LabColor(lab_l=69.417, lab_a=-12.612, lab_b=-11.271)
        atan_color2 = LabColor(lab_l=83.386, lab_a=39.426, lab_b=-17.525)
        result = delta_e_cmc(atan_color1, atan_color2)
        expected = 44.346
        self.assertAlmostEqual(result, expected, 3, 
            "DeltaE CMC Atan test formula error. Got %.3f, expected %.3f (diff: %.3f)." % (
                result, expected, result - expected))
        
    def test_cie1976_accuracy(self):
        result = delta_e_cie1976(self.color1, self.color2)
        expected = 2.151
        self.assertAlmostEqual(result, expected, 3, 
            "DeltaE CIE1976 formula error. Got %.3f, expected %.3f (diff: %.3f)." % (
                result, expected, result - expected))
        
    def test_cie1994_accuracy_graphic_arts(self):
        result = delta_e_cie1994(self.color1, self.color2)
        expected = 1.249
        self.assertAlmostEqual(result, expected, 3, 
            "DeltaE CIE1994 (graphic arts) formula error. Got %.3f, expected %.3f (diff: %.3f)." % (
                result, expected, result - expected))
        
    def test_cie1994_accuracy_textiles(self):
        result = delta_e_cie1994(
            self.color1, self.color2, K_1=0.048, K_2=0.014, K_L=2)
        expected = 1.204
        self.assertAlmostEqual(result, expected, 3, 
            "DeltaE CIE1994 (textiles) formula error. Got %.3f, expected %.3f (diff: %.3f)." % (
                result, expected, result - expected))

    def test_cie1994_domain_error(self):
        # These values are from ticket 98 in regards to a CIE1995
        # domain error exception being raised.
        c1 = LabColor(lab_l=50, lab_a=0, lab_b=0)
        c2 = LabColor(lab_l=50, lab_a=-1, lab_b=2)
        try:
            delta_e_cie1994(c1, c2)
        except ValueError:
            self.fail("DeltaE CIE1994 domain error.")

    def test_non_lab_color(self):
        other_color = sRGBColor(1.0, 0.5, 0.3)
        self.assertRaises(
            ValueError, delta_e_cie2000, self.color1, other_color)

########NEW FILE########
__FILENAME__ = test_color_objects
"""
Various tests for color objects.
"""

import unittest

from colormath.color_conversions import convert_color
from colormath.color_objects import SpectralColor, XYZColor, xyYColor, \
    LabColor, LuvColor, LCHabColor, LCHuvColor, sRGBColor, HSLColor, HSVColor, \
    CMYColor, CMYKColor, AdobeRGBColor


class BaseColorConversionTest(unittest.TestCase):
    """
    All color conversion tests should inherit from this class. Has some
    convenience methods for re-use.
    """

    # noinspection PyPep8Naming
    def assertColorMatch(self, conv, std):
        """
        Checks a converted color against an expected standard.

        :param conv: The converted color object.
        :param std: The object to use as a standard for comparison.
        """

        self.assertEqual(conv.__class__, std.__class__)
        attribs = std.VALUES
        for attrib in attribs:
            conv_value = getattr(conv, attrib)
            std_value = getattr(std, attrib)
            self.assertAlmostEqual(
                conv_value, std_value, 3,
                "%s is %s, expected %s" % (attrib, conv_value, std_value))


class SpectralConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        """
        While it is possible to specify the entire spectral color using
        positional arguments, set this thing up with keywords for the ease of
        manipulation.
        """

        color = SpectralColor(
            spec_380nm=0.0600, spec_390nm=0.0600, spec_400nm=0.0641,
            spec_410nm=0.0654, spec_420nm=0.0645, spec_430nm=0.0605,
            spec_440nm=0.0562, spec_450nm=0.0543, spec_460nm=0.0537,
            spec_470nm=0.0541, spec_480nm=0.0559, spec_490nm=0.0603,
            spec_500nm=0.0651, spec_510nm=0.0680, spec_520nm=0.0705,
            spec_530nm=0.0736, spec_540nm=0.0772, spec_550nm=0.0809,
            spec_560nm=0.0870, spec_570nm=0.0990, spec_580nm=0.1128,
            spec_590nm=0.1251, spec_600nm=0.1360, spec_610nm=0.1439,
            spec_620nm=0.1511, spec_630nm=0.1590, spec_640nm=0.1688,
            spec_650nm=0.1828, spec_660nm=0.1996, spec_670nm=0.2187,
            spec_680nm=0.2397, spec_690nm=0.2618, spec_700nm=0.2852,
            spec_710nm=0.2500, spec_720nm=0.2400, spec_730nm=0.2300)
        self.color = color
                
    def test_conversion_to_xyz(self):
        xyz = convert_color(self.color, XYZColor)
        self.assertColorMatch(xyz, XYZColor(0.115, 0.099, 0.047))

    def test_conversion_to_xyz_with_negatives(self):
        """
        This has negative spectral values, which should never happen. Just
        clamp these to 0.0 instead of running into the domain errors. A badly
        or uncalibrated spectro can sometimes report negative values.
        """

        self.color.spec_530nm = -0.0736
        # TODO: Convert here.

    def test_convert_to_self(self):
        same_color = convert_color(self.color, SpectralColor)
        self.assertEqual(self.color, same_color)


class XYZConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = XYZColor(0.1, 0.2, 0.3)

    def test_conversion_to_xyy(self):
        xyy = convert_color(self.color, xyYColor)
        self.assertColorMatch(xyy, xyYColor(0.167, 0.333, 0.200))

    def test_conversion_to_lab(self):
        lab = convert_color(self.color, LabColor)
        self.assertColorMatch(lab, LabColor(51.837, -57.486, -25.780))

    def test_conversion_to_rgb(self):
        # Picked a set of XYZ coordinates that would return a good RGB value.
        self.color = XYZColor(0.300, 0.200, 0.300)
        rgb = convert_color(self.color, sRGBColor)
        self.assertColorMatch(rgb, sRGBColor(0.715, 0.349, 0.663))

    def test_conversion_to_luv(self):
        luv = convert_color(self.color, LuvColor)
        self.assertColorMatch(luv, LuvColor(51.837, -73.561, -25.657))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, XYZColor)
        self.assertEqual(self.color, same_color)


# noinspection PyPep8Naming
class xyYConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = xyYColor(0.167, 0.333, 0.200)

    def test_conversion_to_xyz(self):
        xyz = convert_color(self.color, XYZColor)
        self.assertColorMatch(xyz, XYZColor(0.100, 0.200, 0.300))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, xyYColor)
        self.assertEqual(self.color, same_color)


class LabConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = LabColor(1.807, -3.749, -2.547)

    def test_conversion_to_xyz(self):
        xyz = convert_color(self.color, XYZColor)
        self.assertColorMatch(xyz, XYZColor(0.001, 0.002, 0.003))

    def test_conversion_to_lchab(self):
        lch = convert_color(self.color, LCHabColor)
        self.assertColorMatch(lch, LCHabColor(1.807, 4.532, 214.191))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, LabColor)
        self.assertEqual(self.color, same_color)


class LuvConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = LuvColor(1.807, -2.564, -0.894)

    def test_conversion_to_xyz(self):
        xyz = convert_color(self.color, XYZColor)
        self.assertColorMatch(xyz, XYZColor(0.001, 0.002, 0.003))

    def test_conversion_to_lchuv(self):
        lch = convert_color(self.color, LCHuvColor)
        self.assertColorMatch(lch, LCHuvColor(1.807, 2.715, 199.222))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, LuvColor)
        self.assertEqual(self.color, same_color)


class LCHabConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = LCHabColor(1.807, 4.532, 214.191)

    def test_conversion_to_lab(self):
        lab = convert_color(self.color, LabColor)
        self.assertColorMatch(lab, LabColor(1.807, -3.749, -2.547))

    def test_conversion_to_rgb_zero_div(self):
        """
        The formula I grabbed for LCHuv to XYZ had a zero division error in it
        if the L coord was 0. Also check against LCHab in case.

        Issue #13 in the Google Code tracker.
        """

        lchab = LCHabColor(0.0, 0.0, 0.0)
        rgb = convert_color(lchab, sRGBColor)
        self.assertColorMatch(rgb, sRGBColor(0.0, 0.0, 0.0))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, LCHabColor)
        self.assertEqual(self.color, same_color)


class LCHuvConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = LCHuvColor(1.807, 2.715, 199.228)

    def test_conversion_to_luv(self):
        luv = convert_color(self.color, LuvColor)
        self.assertColorMatch(luv, LuvColor(1.807, -2.564, -0.894))

    def test_conversion_to_rgb_zero_div(self):
        """
        The formula I grabbed for LCHuv to XYZ had a zero division error in it
        if the L coord was 0. Check against that here.

        Issue #13 in the Google Code tracker.
        """

        lchuv = LCHuvColor(0.0, 0.0, 0.0)
        rgb = convert_color(lchuv, sRGBColor)
        self.assertColorMatch(rgb, sRGBColor(0.0, 0.0, 0.0))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, LCHuvColor)
        self.assertEqual(self.color, same_color)


class RGBConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = sRGBColor(0.482, 0.784, 0.196)

    def test_channel_clamping(self):
        high_r = sRGBColor(1.482, 0.2, 0.3)
        self.assertEqual(high_r.clamped_rgb_r, 1.0)
        self.assertEqual(high_r.clamped_rgb_g, high_r.rgb_g)
        self.assertEqual(high_r.clamped_rgb_b, high_r.rgb_b)

        low_r = sRGBColor(-0.1, 0.2, 0.3)
        self.assertEqual(low_r.clamped_rgb_r, 0.0)
        self.assertEqual(low_r.clamped_rgb_g, low_r.rgb_g)
        self.assertEqual(low_r.clamped_rgb_b, low_r.rgb_b)

        high_g = sRGBColor(0.2, 1.482, 0.3)
        self.assertEqual(high_g.clamped_rgb_r, high_g.rgb_r)
        self.assertEqual(high_g.clamped_rgb_g, 1.0)
        self.assertEqual(high_g.clamped_rgb_b, high_g.rgb_b)

        low_g = sRGBColor(0.2, -0.1, 0.3)
        self.assertEqual(low_g.clamped_rgb_r, low_g.rgb_r)
        self.assertEqual(low_g.clamped_rgb_g, 0.0)
        self.assertEqual(low_g.clamped_rgb_b, low_g.rgb_b)

        high_b = sRGBColor(0.1, 0.2, 1.482)
        self.assertEqual(high_b.clamped_rgb_r, high_b.rgb_r)
        self.assertEqual(high_b.clamped_rgb_g, high_b.rgb_g)
        self.assertEqual(high_b.clamped_rgb_b, 1.0)

        low_b = sRGBColor(0.1, 0.2, -0.1)
        self.assertEqual(low_b.clamped_rgb_r, low_b.rgb_r)
        self.assertEqual(low_b.clamped_rgb_g, low_b.rgb_g)
        self.assertEqual(low_b.clamped_rgb_b, 0.0)

    def test_to_xyz_and_back(self):
        xyz = convert_color(self.color, XYZColor)
        rgb = convert_color(xyz, sRGBColor)
        self.assertColorMatch(rgb, self.color)

    def test_conversion_to_hsl_max_r(self):
        color = sRGBColor(255, 123, 50, is_upscaled=True)
        hsl = convert_color(color, HSLColor)
        self.assertColorMatch(hsl, HSLColor(21.366, 1.000, 0.598))

    def test_conversion_to_hsl_max_g(self):
        color = sRGBColor(123, 255, 50, is_upscaled=True)
        hsl = convert_color(color, HSLColor)
        self.assertColorMatch(hsl, HSLColor(98.634, 1.000, 0.598))

    def test_conversion_to_hsl_max_b(self):
        color = sRGBColor(0.482, 0.482, 1.0)
        hsl = convert_color(color, HSLColor)
        self.assertColorMatch(hsl, HSLColor(240.000, 1.000, 0.741))

    def test_conversion_to_hsl_gray(self):
        color = sRGBColor(0.482, 0.482, 0.482)
        hsl = convert_color(color, HSLColor)
        self.assertColorMatch(hsl, HSLColor(0.000, 0.000, 0.482))

    def test_conversion_to_hsv(self):
        hsv = convert_color(self.color, HSVColor)
        self.assertColorMatch(hsv, HSVColor(90.816, 0.750, 0.784))

    def test_conversion_to_cmy(self):
        cmy = convert_color(self.color, CMYColor)
        self.assertColorMatch(cmy, CMYColor(0.518, 0.216, 0.804))

    def test_srgb_conversion_to_xyz_d50(self):
        """
        sRGB's native illuminant is D65. Test the XYZ adaptations by setting
        a target illuminant to something other than D65.
        """

        xyz = convert_color(self.color, XYZColor, target_illuminant='D50')
        self.assertColorMatch(xyz, XYZColor(0.313, 0.460, 0.082))

    def test_srgb_conversion_to_xyz_d65(self):
        """
        sRGB's native illuminant is D65. This is a straightforward conversion.
        """

        xyz = convert_color(self.color, XYZColor)
        self.assertColorMatch(xyz, XYZColor(0.294, 0.457, 0.103))

    def test_adobe_conversion_to_xyz_d65(self):
        """
        Adobe RGB's native illuminant is D65, like sRGB's. However, sRGB uses
        different conversion math that uses gamma, so test the alternate logic
        route for non-sRGB RGB colors.
        """

        adobe = AdobeRGBColor(0.482, 0.784, 0.196)
        xyz = convert_color(adobe, XYZColor)
        self.assertColorMatch(xyz, XYZColor(0.230, 0.429, 0.074))

    def test_conversion_through_rgb(self):
        """
        Make sure our convenience RGB tracking feature is working. For example,
        going from XYZ->HSL via Adobe RGB, then taking that HSL object and
        converting back to XYZ should also use Adobe RGB (instead of the
        default of sRGB).
        """

        xyz = convert_color(self.color, XYZColor)
        hsl = convert_color(xyz, HSLColor, through_rgb_type=AdobeRGBColor)
        # Notice how we don't have to pass through_rgb_type explicitly.
        xyz2 = convert_color(hsl, XYZColor)
        self.assertColorMatch(xyz, xyz2)

    def test_adobe_conversion_to_xyz_d50(self):
        """
        Adobe RGB's native illuminant is D65, so an adaptation matrix is
        involved here. However, the math for sRGB and all other RGB types is
        different, so test all of the other types with an adaptation matrix
        here.
        """

        adobe = AdobeRGBColor(0.482, 0.784, 0.196)
        xyz = convert_color(adobe, XYZColor, target_illuminant='D50')
        self.assertColorMatch(xyz, XYZColor(0.247, 0.431, 0.060))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, sRGBColor)
        self.assertEqual(self.color, same_color)

    def test_get_rgb_hex(self):
        hex_str = self.color.get_rgb_hex()
        self.assertEqual(hex_str, "#7bc832", "sRGB to hex conversion failed")

    def test_set_from_rgb_hex(self):
        rgb = sRGBColor.new_from_rgb_hex('#7bc832')
        self.assertColorMatch(rgb, sRGBColor(0.482, 0.784, 0.196))


class HSLConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = HSLColor(200.0, 0.400, 0.500)

    def test_conversion_to_rgb(self):
        rgb = convert_color(self.color, sRGBColor)
        self.assertColorMatch(rgb, sRGBColor(0.300, 0.567, 0.700))
        # Make sure this converts to AdobeRGBColor instead of sRGBColor.
        adobe_rgb = convert_color(self.color, AdobeRGBColor)
        self.assertIsInstance(adobe_rgb, AdobeRGBColor)

    def test_convert_to_self(self):
        same_color = convert_color(self.color, HSLColor)
        self.assertEqual(self.color, same_color)


class HSVConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = HSVColor(91.0, 0.750, 0.784)

    def test_conversion_to_rgb(self):
        rgb = convert_color(self.color, sRGBColor)
        self.assertColorMatch(rgb, sRGBColor(0.480, 0.784, 0.196))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, HSVColor)
        self.assertEqual(self.color, same_color)


class CMYConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = CMYColor(0.518, 0.216, 0.804)

    def test_conversion_to_cmyk(self):
        cmyk = convert_color(self.color, CMYKColor)
        self.assertColorMatch(cmyk, CMYKColor(0.385, 0.000, 0.750, 0.216))

    def test_conversion_to_rgb(self):
        rgb = convert_color(self.color, sRGBColor)
        self.assertColorMatch(rgb, sRGBColor(0.482, 0.784, 0.196))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, CMYColor)
        self.assertEqual(self.color, same_color)


class CMYKConversionTestCase(BaseColorConversionTest):
    def setUp(self):
        self.color = CMYKColor(0.385, 0.000, 0.750, 0.216)

    def test_conversion_to_cmy(self):
        cmy = convert_color(self.color, CMYColor)
        self.assertColorMatch(cmy, CMYColor(0.518, 0.216, 0.804))

    def test_convert_to_self(self):
        same_color = convert_color(self.color, CMYKColor)
        self.assertEqual(self.color, same_color)

########NEW FILE########
