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
import nidaqmx
import numpy as np
from nidaqmx.stream_writers import AnalogMultiChannelWriter
from hardware.exceptions_handle import handle_exception
from models import galvo_settings
from utils import constants


class Galvo(object):
    _logger = logging.getLogger(__name__)

    _scan_output = nidaqmx.Task()
    _cam_output = nidaqmx.Task()

    @classmethod
    @handle_exception
    def set_dslm_mode(cls):
        """
        Puts galvo mirrors into dslm (digitally scanned lightsheet microscopy) scanning mode.
        dslm scanning is just a linear ramp sweep over a voltage range. It is the standard laser 
        scanning mode.

        ### Requires the following attributes to be set in settings:

        #### focus : float
            focus offset of laser (voltage offset to x-galvo mirror in mV)

        #### dslm_offset : float
            vertical offset of laser (voltage offset sent to y-galvo mirror in mV) used in cont_scan().

        #### dslm_scan_width : float
            Scanning range of laser (voltage range of scanning sample sent to y-galvo mirror)
        """
        cls._reset_tasks()
        # For DSLM, want the daq to generate samples continuously since we want the mirrors to scan continuously.
        cls._scan_output.timing.cfg_samp_clk_timing(galvo_settings.DSLM_SAMPLE_RATE,
                                                    sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
                                                    samps_per_chan=galvo_settings.DSLM_NUM_SAMPLES)

        # Adds pulse output channel to _cam_output task. The pulse output is to relay the digital signals
        # from the PLC to the camera.
        cls._cam_output.co_channels.add_co_pulse_chan_time(galvo_settings.CAM_CHANNEL,
                                                           low_time=galvo_settings.PULSE_TIME_S,
                                                           high_time=galvo_settings.PULSE_TIME_S)
        cls._cam_output.timing.cfg_implicit_timing(samps_per_chan=1)
        cls._cam_output.triggers.start_trigger.cfg_dig_edge_start_trig(galvo_settings.PLC_INPUT_CHANNEL)
        cls._cam_output.triggers.start_trigger.retriggerable = True

        # Sets scan data as triangle wave. This causes the galvo to scan back
        # and forth continuously across withe scan_width range, creating the
        # time-averaged light sheet.
        scan = cls.create_scan_sample()
        focus = galvo_settings.focus*np.ones(galvo_settings.DSLM_NUM_SAMPLES)
        # Writes analog data to out_stream
        writer = AnalogMultiChannelWriter(cls._scan_output.out_stream)
        writer.write_many_sample(np.array([focus, scan]))

        cls._scan_output.start()
        cls._cam_output.start()

    @classmethod
    def create_scan_sample(cls):
        """
        Creates scan sample to be set to the DAQ for dslm scan. First, creates linspace from range -scan_width/2 to
        scan_width/2 (so total scan width is scan_width). Then, appends reverse of created linspace to itself so that
        a triangle sample is made. 
        """
        scan = np.linspace(-1*galvo_settings.dslm_scan_width/2, galvo_settings.dslm_scan_width /
                           2, int(galvo_settings.DSLM_NUM_SAMPLES/2))
        scan = np.concatenate((scan, scan[::-1]), 0) + galvo_settings.dslm_offset
        return scan

    @classmethod
    @handle_exception
    def set_dslm_alignment_mode(cls):
        """
        Same as dslm() but without the ramp sample sent to the y-galvo mirror. Used to align lasers for dslm().
        """
        cls._reset_tasks()

        # Same as continuous_scan but without the scanning or pulse channel.
        # Used to align laser.
        cls._scan_output.timing.cfg_samp_clk_timing(galvo_settings.DSLM_SAMPLE_RATE, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
                                                    samps_per_chan=galvo_settings.DSLM_NUM_SAMPLES)

        scan = np.zeros(galvo_settings.DSLM_NUM_SAMPLES) + galvo_settings.dslm_offset
        focus = galvo_settings.focus*np.ones(galvo_settings.DSLM_NUM_SAMPLES)
        writer = AnalogMultiChannelWriter(cls._scan_output.out_stream)
        writer.write_many_sample(np.array([focus, scan]))

        cls._scan_output.start()

    @classmethod
    @handle_exception
    def set_lsrm_mode(cls):
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
        cls._reset_tasks()

        # Configures clock timing. Note that the AcquisitionType here is FINITE instead of CONTINUOUS in DSLM.
        cls._scan_output.timing.cfg_samp_clk_timing(galvo_settings.get_lsrm_sample_rate(), sample_mode=nidaqmx.constants.AcquisitionType.FINITE,
                                                    samps_per_chan=galvo_settings.LSRM_NUM_SAMPLES)

        # Creates start trigger and makes task retriggerable so that PLC pulses retrigger it. Also adds delay which acts
        # as the laser delay.
        cls._scan_output.triggers.start_trigger.cfg_dig_edge_start_trig(galvo_settings.PLC_INPUT_CHANNEL)
        cls._scan_output.triggers.start_trigger.retriggerable = True
        cls._scan_output.triggers.start_trigger.delay_units = nidaqmx.constants.DigitalWidthUnits.SECONDS
        cls._scan_output.triggers.start_trigger.delay = galvo_settings.lsrm_laser_delay*constants.MS_TO_S

        # Adds channel pulse output to _cam_output task. The delay added here is the camera delay. This whole block
        # just sets up the camera channel to output a pulse whenever a pulse is received at the _RETRIG_CHAN.
        # God this API is awful.
        cls._cam_output.co_channels.add_co_pulse_chan_time(galvo_settings.CAM_CHANNEL, initial_delay=galvo_settings.lsrm_cam_delay*constants.MS_TO_S,
                                                           low_time=galvo_settings.PULSE_TIME_S, high_time=galvo_settings.PULSE_TIME_S).co_enable_initial_delay_on_retrigger = True
        cls._cam_output.timing.cfg_implicit_timing(samps_per_chan=1)
        cls._cam_output.triggers.start_trigger.cfg_dig_edge_start_trig(galvo_settings.PLC_INPUT_CHANNEL)
        cls._cam_output.triggers.start_trigger.retriggerable = True

        scan = np.linspace(galvo_settings.lsrm_lower, galvo_settings.lsrm_upper, galvo_settings.LSRM_NUM_SAMPLES)
        focus = galvo_settings.focus * np.ones(galvo_settings.LSRM_NUM_SAMPLES)
        writer = AnalogMultiChannelWriter(cls._scan_output.out_stream)
        writer.write_many_sample(np.array([focus, scan]))

        cls._scan_output.start()
        cls._cam_output.start()

    @classmethod
    @handle_exception
    def set_lsrm_alignment_mode(cls):
        """
        Same as dslm_not_scanning() except uses lsrm_cur_pos attribute instead of dslm_offset. Used to
        align lasers for lsrm().
        """
        cls._reset_tasks()

        cls._scan_output.timing.cfg_samp_clk_timing(galvo_settings.DSLM_SAMPLE_RATE, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
                                                    samps_per_chan=galvo_settings.DSLM_NUM_SAMPLES)

        scan = np.zeros(galvo_settings.DSLM_NUM_SAMPLES) + galvo_settings.lsrm_cur_pos
        focus = galvo_settings.focus*np.ones(galvo_settings.DSLM_NUM_SAMPLES)

        writer = AnalogMultiChannelWriter(cls._scan_output.out_stream)
        writer.write_many_sample(np.array([focus, scan]))

        cls._scan_output.start()

    @classmethod
    def _reset_tasks(cls):
        """
        closes DAQ tasks and creates new, empty tasks with the same variable names.
        """
        cls._scan_output.close()
        cls._cam_output.close()
        cls._scan_output = nidaqmx.Task()
        cls._cam_output = nidaqmx.Task()
        cls._scan_output.ao_channels.add_ao_voltage_chan(galvo_settings.FOCUS_CHANNEL)
        cls._scan_output.ao_channels.add_ao_voltage_chan(galvo_settings.OFFSET_CHANNEL)

    @classmethod
    def exit(cls):
        """
        Resets all voltages to 0 and then closes tasks. Should be called after current
        galvo settings are written to config.
        """
        galvo_settings.focus = 0
        galvo_settings.dslm_offset = 0
        galvo_settings.dslm_scan_width = 0
        cls.set_dslm_mode()
        cls._scan_output.close
        cls._cam_output.close()
