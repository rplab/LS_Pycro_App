"""
This module contains all methods for the galvo scanning mirrors used to create the light sheet.
It uses NIDAQmx to set up tasks on the NIDAQ, which is connected to the mirrors.
NIDAQmx more or less takes the visual task creating of Labview and makes it programmatic. 
PyDAQ simple takes the C-based NIDaqMX methods and changes them into python methods. NIDAQmx
has the most awful documentation ever made , which unfortunately makes PyDAQmx just as bad. 
In all of these functions, we create a task, create channels on the NIDAQ to perform said task 
with, and then send data to those channels. I'll go through each of the methods more in-depth:

## SPIM Methods: 

#### dslm()

This is the default scanning mode and should be used in most circumstances.
Creates two analog output channels, one for each galvo mirror. The offset mirror (y-galvo) is the one
that us used to create the light sheet. A ramp sample (just a triangle wave) is sent to the DAQ, which 
it then repeatedly sends to the y-galvo mirror to create the time-averaged light sheet. 

#### dslm_not_scanning()

Same as dslm() except not scanning. Used to align the laser.

#### lsrm_not_scanning()

same as dslm_not_scanning except uses ligthsheet_readout_current_position
to set lower and upper values of scanning range.

#### lsrm()

Creates two analog channels in a retriggerable task so that laser scanning can be 
externally triggered. Currently, mirrors and camera are triggered simultaneously by the PLC. Scanning frequency 
in this mode is significantly lower than in continuous_scan() to work with the Hamamatsu Lightsheet Readout Mode.
Please read my guide on LSRM for more information on this.

#### exit()

Stops all tasks and sets galvo mirror voltages to 0.

## Future Changes
- Maybe put SPIMGalvoSettings in its own file
- scanning implementation could be reorganized and abstracted a lot. Not super important until more scanning modes
are created.
"""

import logging
import numpy as np

import nidaqmx
from nidaqmx.stream_writers import AnalogMultiChannelWriter

from LS_Pycro_App.hardware.exceptions_handle import handle_exception
from LS_Pycro_App.hardware.galvo.galvo_settings import GalvoSettings
from LS_Pycro_App.utils import constants


settings = GalvoSettings()
settings.init_from_config()
_logger = logging.getLogger(__name__)
_scan_output = nidaqmx.Task()
_cam_output = nidaqmx.Task()


@handle_exception
def set_dslm_mode():
    """
    Puts galvo mirrors into dslm (digitally scanned lightsheet microscopy) scanning mode.
    dslm scanning is just a linear ramp sweep over a voltage range. It is the standard laser 
    scanning mode.

    ### Requires the following attributes to be set in galvo settings:

    #### focus : float
        focus offset of laser (voltage offset to x-galvo mirror in mV)

    #### dslm_offset : float
        vertical offset of laser (voltage offset sent to y-galvo mirror in mV) used in cont_scan().

    #### dslm_scan_width : float
        Scanning range of laser (voltage range of scanning sample sent to y-galvo mirror)
    """
    _reset_tasks()
    # For DSLM, want the daq to generate samples continuously since we want the mirrors to scan continuously.
    sample_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS
    _scan_output.timing.cfg_samp_clk_timing(settings.DSLM_SAMPLE_RATE,
                                            sample_mode=sample_mode,
                                            samps_per_chan=settings.DSLM_NUM_SAMPLES)
    # Adds pulse output channel to _cam_output task. The pulse output is to relay the digital signals
    # from the PLC to the camera.
    _cam_output.co_channels.add_co_pulse_chan_time(settings.CAM_CHANNEL,
                                                   low_time=settings.PULSE_TIME_S,
                                                   high_time=settings.PULSE_TIME_S)
    _cam_output.timing.cfg_implicit_timing(samps_per_chan=1)
    _cam_output.triggers.start_trigger.cfg_dig_edge_start_trig(settings.PLC_INPUT_CHANNEL)
    _cam_output.triggers.start_trigger.retriggerable = True
    # Sets scan data as triangle wave. This causes the galvo to scan back
    # and forth continuously across withe scan_width range, creating the
    # time-averaged light sheet.
    scan = _get_dslm_scan_sample()
    focus = _get_focus_sample(settings.DSLM_NUM_SAMPLES)
    # Writes analog data to out_stream
    writer = AnalogMultiChannelWriter(_scan_output.out_stream)
    writer.write_many_sample(np.array([focus, scan]))
    _scan_output.start()
    _cam_output.start()
    _logger.info(f"Galvo set to dslm mode.")


@handle_exception
def set_dslm_alignment_mode():
    """
    Same as dslm() but without the ramp sample sent to the y-galvo mirror. Used to align lasers for dslm().
    """
    _reset_tasks()
    # Same as continuous_scan but without the scanning or pulse channel.
    # Used to align laser.
    sample_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS
    _scan_output.timing.cfg_samp_clk_timing(settings.DSLM_SAMPLE_RATE, 
                                            sample_mode=sample_mode,
                                            samps_per_chan=settings.DSLM_NUM_SAMPLES)
    scan = _get_alignment_scan_sample(settings.DSLM_NUM_SAMPLES, settings.dslm_offset)
    focus = _get_focus_sample(settings.DSLM_NUM_SAMPLES)
    writer = AnalogMultiChannelWriter(_scan_output.out_stream)
    writer.write_many_sample(np.array([focus, scan]))
    _scan_output.start()
    _logger.info(f"Galvo set to dslm alignment mode.")


@handle_exception
def set_lsrm_mode():
    """
    Scanning mode to be used in conjunction with the Hamamatsu camera's Lightsheet Readout Mode.
    If you don't know what this is, please read the Hamamatsu documentation (can be found in HardwareCommands class)
    as well as our internal documentation.

    ### Requires the following attributes to be set in settings:

    #### lsrm_upper : float
        upper limit of galvo scanning range in lsrm() in SPIMCommands. Note that it's the upper limit 
        by value, so when lsrm_upper is set correctly, the laser will actually be at the bottom of the camera feed.

    #### lsrm_lower : float
        lower limit of galvo scanning range in lsrm() in SPIMCommands

    #### lsrm_framerate : float
        framerate of camera in lightsheet readout mode.

    #### lsrm_laser_delay : float
        laser delay in ms in lsrm()

    #### lsrm_cam_delay : float
        cam delay in ms in lsrm()
    """
    _reset_tasks()
    # Configures clock timing. Note that the AcquisitionType here is FINITE instead of CONTINUOUS in DSLM.
    sample_mode = nidaqmx.constants.AcquisitionType.FINITE
    _scan_output.timing.cfg_samp_clk_timing(settings.get_lsrm_sample_rate(), 
                                            sample_mode=sample_mode,
                                            samps_per_chan=settings.LSRM_NUM_SAMPLES)
    # Creates start trigger and makes task retriggerable so that PLC pulses retrigger it. Also adds delay which acts
    # as the laser delay.
    _scan_output.triggers.start_trigger.cfg_dig_edge_start_trig(settings.PLC_INPUT_CHANNEL)
    _scan_output.triggers.start_trigger.retriggerable = True
    _scan_output.triggers.start_trigger.delay_units = nidaqmx.constants.DigitalWidthUnits.SECONDS
    _scan_output.triggers.start_trigger.delay = settings.lsrm_laser_delay*constants.MS_TO_S

    # Adds channel pulse output to _cam_output task. The delay added here is the camera delay. This whole block
    # just sets up the camera channel to output a pulse whenever a pulse is received at the _RETRIG_CHAN.
    # God this API is awful.
    _cam_output.co_channels.add_co_pulse_chan_time(settings.CAM_CHANNEL, 
                                                   initial_delay=settings.lsrm_cam_delay*constants.MS_TO_S,
                                                   low_time=settings.PULSE_TIME_S, 
                                                   high_time=settings.PULSE_TIME_S
                                                   ).co_enable_initial_delay_on_retrigger = True
    _cam_output.timing.cfg_implicit_timing(samps_per_chan=1)
    _cam_output.triggers.start_trigger.cfg_dig_edge_start_trig(settings.PLC_INPUT_CHANNEL)
    _cam_output.triggers.start_trigger.retriggerable = True
    scan = _get_lsrm_scan_sample()
    focus = _get_focus_sample(settings.LSRM_NUM_SAMPLES)
    writer = AnalogMultiChannelWriter(_scan_output.out_stream)
    writer.write_many_sample(np.array([focus, scan]))
    _scan_output.start()
    _cam_output.start()
    _logger.info(f"Galvo set to lsrm mode.")


@handle_exception
def set_lsrm_alignment_mode():
    """
    Same as dslm_not_scanning() except uses lsrm_cur_pos attribute instead of dslm_offset. Used to
    align lasers for lsrm().
    """
    _reset_tasks()
    sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS
    _scan_output.timing.cfg_samp_clk_timing(settings.DSLM_SAMPLE_RATE, 
                                            sample_mode=sample_mode,
                                            samps_per_chan=settings.DSLM_NUM_SAMPLES)
    scan = _get_alignment_scan_sample(settings.DSLM_NUM_SAMPLES, settings.lsrm_cur_pos)
    focus = _get_focus_sample(settings.DSLM_NUM_SAMPLES)
    writer = AnalogMultiChannelWriter(_scan_output.out_stream)
    writer.write_many_sample(np.array([focus, scan]))
    _scan_output.start()
    _logger.info(f"Galvo set to lsrm alignment mode.")


def exit():
    """
    Resets all voltages to 0 and then closes tasks. Should be called after current
    galvo settings are written to config.
    """
    settings.focus = 0
    settings.dslm_offset = 0
    settings.dslm_scan_width = 0
    set_dslm_mode()
    _scan_output.close()
    _cam_output.close()


def _get_alignment_scan_sample(num_samples: int, offset: float):
    return np.zeros(num_samples) + offset


def _get_dslm_scan_sample():
    """
    Creates scan sample to be sent to the DAQ for dslm. First, creates linspace from range -scan_width/2 to
    scan_width/2 (so total scan width is scan_width). Then, appends reverse of created linspace to itself so that
    a triangle sample is made. 
    """
    scan = np.linspace(-1*settings.dslm_scan_width/2, settings.dslm_scan_width/2, int(settings.DSLM_NUM_SAMPLES/2))
    scan = np.concatenate((scan, scan[::-1]), 0) + settings.dslm_offset
    return scan


def _get_focus_sample(num_samples: int):
    """
    creates focus sample to be sent to DAQ for dslm.
    """
    return settings.focus*np.ones(num_samples)


def _get_lsrm_scan_sample():
    return np.linspace(settings.lsrm_lower, settings.lsrm_upper, settings.LSRM_NUM_SAMPLES)


def _reset_tasks():
    """
    closes DAQ tasks and creates new, empty tasks with the same variable names.
    """
    global _scan_output, _cam_output
    _scan_output.close()
    _cam_output.close()
    _scan_output = nidaqmx.Task()
    _cam_output = nidaqmx.Task()
    _scan_output.ao_channels.add_ao_voltage_chan(settings.FOCUS_CHANNEL)
    _scan_output.ao_channels.add_ao_voltage_chan(settings.OFFSET_CHANNEL)
