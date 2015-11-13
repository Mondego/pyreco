__FILENAME__ = APC
# --== Decompile ==--

import Live
from _Framework.ControlSurface import ControlSurface
MANUFACTURER_ID = 71
ABLETON_MODE = 65 #65 = 0x41 = Ableton Live Mode 1; 66 = 0x42 = Ableton Mode 2; 67 = 0x43 = Ableton Mode 3 (APC20 only)
#PRODUCT_MODEL_ID = 115 # 0x73 Product Model ID (APC40)

class APC(ControlSurface):
    __doc__ = " Script for Akai's line of APC Controllers "
    _active_instances = []
    def _combine_active_instances():
        if not len(APC._active_instances) > 0:
            raise AssertionError
        if len(APC._active_instances) > 1:
            support_devices = False
            for instance in APC._active_instances:
                support_devices |= instance._device_component != None
            track_offset = 0
            for instance in APC._active_instances:
                instance._activate_combination_mode(track_offset, support_devices)
                track_offset += instance._session.width()
        return None

    _combine_active_instances = staticmethod(_combine_active_instances)
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self.set_suppress_rebuild_requests(True)
        self._suppress_session_highlight = True
        self._suppress_send_midi = True
        self._suggested_input_port = 'Akai ' + self.__class__.__name__
        self._suggested_output_port = 'Akai ' + self.__class__.__name__
        self._shift_button = None
        self._matrix = None
        self._session = None
        self._session_zoom = None
        self._mixer = None
        self._setup_session_control()
        self._setup_mixer_control()
        self._session.set_mixer(self._mixer)
        self._shift_button.name = 'Shift_Button'
        self._setup_custom_components()
        for component in self.components:
            component.set_enabled(False)
        self.set_suppress_rebuild_requests(False)
        self._device_id = 0
        self._common_channel = 0
        self._dongle_challenge = (Live.Application.get_random_int(0, 2000000), Live.Application.get_random_int(2000001, 4000000))
        return None

    def disconnect(self):
        self._shift_button = None
        self._matrix = None
        self._session = None
        self._session_zoom = None
        self._mixer = None
        ControlSurface.disconnect(self)
        return None

    def connect_script_instances(self, instanciated_scripts):
        if len(APC._active_instances) > 0 and self == APC._active_instances[0]:
            APC._combine_active_instances()

    def refresh_state(self):
        ControlSurface.refresh_state(self)
        self.schedule_message(5, self._update_hardware)    
        
    def handle_sysex(self, midi_bytes):
        self._suppress_send_midi = False
        if ((midi_bytes[3] == 6) and (midi_bytes[4] == 2)):
            assert (midi_bytes[5] == MANUFACTURER_ID)
            assert (midi_bytes[6] == self._product_model_id_byte()) # PRODUCT_MODEL_ID
            version_bytes = midi_bytes[9:13]
            self._device_id = midi_bytes[13]
            self._send_introduction_message() # instead of _send_midi, below:
            #self._send_midi((240,
                             #MANUFACTURER_ID,
                             #self._device_id,
                             #PRODUCT_MODEL_ID,
                             #96,
                             #0,
                             #4,
                             #APPLICTION_ID,
                             #self.application().get_major_version(),
                             #self.application().get_minor_version(),
                             #self.application().get_bugfix_version(),
                             #247))
            challenge1 = [0,
                          0,
                          0,
                          0,
                          0,
                          0,
                          0,
                          0]
            challenge2 = [0,
                          0,
                          0,
                          0,
                          0,
                          0,
                          0,
                          0]
            for index in range(8):
                challenge1[index] = ((self._dongle_challenge[0] >> (4 * (7 - index))) & 15)
                challenge2[index] = ((self._dongle_challenge[1] >> (4 * (7 - index))) & 15)

            dongle_message = ((((240,
                                 MANUFACTURER_ID,
                                 self._device_id,
                                 self._product_model_id_byte(),
                                 80,
                                 0,
                                 16) + tuple(challenge1)) + tuple(challenge2)) + (247,))
            self._send_midi(dongle_message)
            message = (((self.__class__.__name__ + ': Got response from controller, version ' + str(((version_bytes[0] << 4) + version_bytes[1]))) + '.') + str(((version_bytes[2] << 4) + version_bytes[3])))
            self.log_message(message)
        elif (midi_bytes[4] == 81):
            assert (midi_bytes[1] == MANUFACTURER_ID)
            assert (midi_bytes[2] == self._device_id)
            assert (midi_bytes[3] == self._product_model_id_byte()) # PRODUCT_MODEL_ID)
            assert (midi_bytes[5] == 0)
            assert (midi_bytes[6] == 16)
            response = [long(0),
                        long(0)]
            for index in range(8):
                response[0] += (long((midi_bytes[(7 + index)] & 15)) << (4 * (7 - index)))
                response[1] += (long((midi_bytes[(15 + index)] & 15)) << (4 * (7 - index)))

            expected_response = Live.Application.encrypt_challenge(self._dongle_challenge[0], self._dongle_challenge[1])
            if ((long(expected_response[0]) == response[0]) and (long(expected_response[1]) == response[1])):
                self._suppress_session_highlight = False
                for component in self.components:
                    component.set_enabled(True)

                self._on_selected_track_changed()

    def _update_hardware(self):
        self._suppress_send_midi = True
        self._suppress_session_highlight = True
        self.set_suppress_rebuild_requests(True)
        for component in self.components:
            component.set_enabled(False)
        self.set_suppress_rebuild_requests(False)
        self._suppress_send_midi = False
        self._send_midi((240, 126, 0, 6, 1, 247)) #(0xF0, 0x7E, 0x00, 0x06, 0x01, 0xF7) = Standard MMC Device Enquiry

    def _set_session_highlight(self, track_offset, scene_offset, width, height, include_return_tracks):
        if not self._suppress_session_highlight:
            self._suppress_session_highlight
            ControlSurface._set_session_highlight(self, track_offset, scene_offset, width, height, include_return_tracks)
        else:
            self._suppress_session_highlight

    def _send_midi(self, midi_bytes):
        if not self._suppress_send_midi:
            self._suppress_send_midi
            ControlSurface._send_midi(self, midi_bytes)
        else:
            self._suppress_send_midi

    def _send_introduction_message(self, mode_byte=ABLETON_MODE):
        self._send_midi((240, MANUFACTURER_ID, self._device_id, self._product_model_id_byte(), 96, 0, 4, mode_byte, self.application().get_major_version(), self.application().get_minor_version(), self.application().get_bugfix_version(), 247))

    def _activate_combination_mode(self, track_offset, support_devices):
        self._session.link_with_track_offset(track_offset)

    def _setup_session_control(self):
        raise AssertionError, 'Function _setup_session_control must be overridden by subclass'

    def _setup_mixer_control(self):
        raise AssertionError, 'Function _setup_mixer_control must be overridden by subclass'

    def _setup_custom_components(self):
        raise AssertionError, 'Function _setup_custom_components must be overridden by subclass'

    def _product_model_id_byte(self):
        raise AssertionError, 'Function _product_model_id_byte must be overridden by subclass'




########NEW FILE########
__FILENAME__ = APC40plus22
# http://remotescripts.blogspot.com

import Live
from APC import APC
from _Framework.ControlSurface import ControlSurface
from _Framework.InputControlElement import *
from _Framework.SliderElement import SliderElement
from _Framework.ButtonElement import ButtonElement
from _Framework.EncoderElement import EncoderElement
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.MixerComponent import MixerComponent
from _Framework.ClipSlotComponent import ClipSlotComponent
from _Framework.ChannelStripComponent import ChannelStripComponent
from _Framework.SceneComponent import SceneComponent
from _Framework.SessionZoomingComponent import SessionZoomingComponent
from _Framework.ChannelTranslationSelector import ChannelTranslationSelector
from EncoderMixerModeSelectorComponent import EncoderMixerModeSelectorComponent
from RingedEncoderElement import RingedEncoderElement
from DetailViewControllerComponent import DetailViewControllerComponent
from ShiftableDeviceComponent import ShiftableDeviceComponent
from ShiftableTransportComponent import ShiftableTransportComponent
from ShiftableTranslatorComponent import ShiftableTranslatorComponent
from PedaledSessionComponent import PedaledSessionComponent
from SpecialMixerComponent import SpecialMixerComponent

# Additional imports from APC20.py:
from ShiftableSelectorComponent import ShiftableSelectorComponent
from SliderModesComponent import SliderModesComponent

# Import added from Launchpad scripts - needed for Note Mode:
from ConfigurableButtonElement import ConfigurableButtonElement 

# New components
from MatrixModesComponent import MatrixModesComponent
from EncoderUserModesComponent import EncoderUserModesComponent
from ShiftableEncoderSelectorComponent import ShiftableEncoderSelectorComponent
from EncoderEQComponent import EncoderEQComponent
from EncoderDeviceComponent import EncoderDeviceComponent

#from ShiftableLooperComponent import ShiftableLooperComponent
from LooperComponent import LooperComponent
from RepeatComponent import RepeatComponent
from VUMeters import VUMeters


class APC40plus22(APC):
    __doc__ = " Script for Akai's APC40 Controller with extra features added "
    def __init__(self, c_instance):
        self._c_instance = c_instance
        self._shift_modes = None #added from APC20 script
        self._encoder_modes = None #added
        self._slider_modes = None #added
        APC.__init__(self, c_instance)
        self.show_message("APC40_22 script loaded")
        
        # Disabling the scene launch buttons and assigning them to the first 5 repeats on Master
        self._device_buttons = []
        self.setup_device_buttons()

    def disconnect(self): #this is from the APC20 script
        for button in self._device_buttons:
            button.remove_value_listener(self._device_toggle)
        self._device_buttons = None
        self._shift_modes = None
        self._encoder_modes = None
        self._slider_modes = None
        APC.disconnect(self)        

    def setup_device_buttons(self):
      repeat = RepeatComponent(self)
      repeat.set_shift_button(self._shift_button)

    def _setup_session_control(self):
        is_momentary = True
        self._shift_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 98)        
        right_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 96)
        left_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 97)
        up_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 94)
        down_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 95)
        right_button.name = 'Bank_Select_Right_Button'
        left_button.name = 'Bank_Select_Left_Button'
        up_button.name = 'Bank_Select_Up_Button'
        down_button.name = 'Bank_Select_Down_Button'
        self._session = PedaledSessionComponent(8, 5)
        self._session.name = 'Session_Control'
        self._session.set_track_bank_buttons(right_button, left_button)
        self._session.set_scene_bank_buttons(down_button, up_button)
        self._matrix = ButtonMatrixElement() #was: matrix = ButtonMatrixElement()
        self._matrix.name = 'Button_Matrix' #was: matrix.name = 'Button_Matrix'
        scene_launch_buttons = [ ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, (index + 82)) for index in range(5) ]
        #self._track_stop_buttons = [ ButtonElement(is_momentary, MIDI_NOTE_TYPE, index, 52) for index in range(8) ]
        self._track_stop_buttons = [ ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, index, 52) for index in range(8) ]
        for index in range(len(scene_launch_buttons)):
            scene_launch_buttons[index].name = 'Scene_'+ str(index) + '_Launch_Button'
        for index in range(len(self._track_stop_buttons)):
            self._track_stop_buttons[index].name = 'Track_' + str(index) + '_Stop_Button'
        stop_all_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 81)
        stop_all_button.name = 'Stop_All_Clips_Button'
        self._session.set_stop_all_clips_button(stop_all_button)
        self._session.set_stop_track_clip_buttons(tuple(self._track_stop_buttons))
        self._session.set_stop_track_clip_value(2)

        self._button_rows = []
        for scene_index in range(5):
            scene = self._session.scene(scene_index)
            scene.name = 'Scene_' + str(scene_index)
            button_row = []
            scene.set_launch_button(scene_launch_buttons[scene_index])
            scene.set_triggered_value(2)
            for track_index in range(8):
                #button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, track_index, (scene_index + 53)) 
                button = ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, track_index, (scene_index + 53)) #use Launchpad configurable button instead
                button.name = str(track_index) + '_Clip_' + str(scene_index) + '_Button'
                button_row.append(button)
                clip_slot = scene.clip_slot(track_index)
                clip_slot.name = str(track_index) + '_Clip_Slot_' + str(scene_index)
                clip_slot.set_triggered_to_play_value(2)
                clip_slot.set_triggered_to_record_value(4)
                clip_slot.set_stopped_value(3)
                clip_slot.set_started_value(1)
                clip_slot.set_recording_value(5)
                clip_slot.set_launch_button(button)
            self._matrix.add_row(tuple(button_row)) #matrix.add_row(tuple(button_row))
            self._button_rows.append(button_row)

        # Removing the launch selected clip footpedal option
        #self._session.set_slot_launch_button(ButtonElement(is_momentary, MIDI_CC_TYPE, 0, 67))


        self._session.selected_scene().name = 'Selected_Scene'
        self._session.selected_scene().set_launch_button(ButtonElement(is_momentary, MIDI_CC_TYPE, 0, 64))
        self._session_zoom = SessionZoomingComponent(self._session) #use APC20 Zooming instead      
        self._session_zoom.name = 'Session_Overview'
        self._session_zoom.set_button_matrix(self._matrix) #was: self._session_zoom.set_button_matrix(matrix)
        self._session_zoom.set_zoom_button(self._shift_button) #set in MatrixModesComponent instead
        self._session_zoom.set_nav_buttons(up_button, down_button, left_button, right_button)
        self._session_zoom.set_scene_bank_buttons(tuple(scene_launch_buttons))
        self._session_zoom.set_stopped_value(3)
        self._session_zoom.set_selected_value(5)
        return None

    def _setup_mixer_control(self):
        is_momentary = True
        self._mixer = SpecialMixerComponent(self, 8) #added self for parent
        self._mixer.name = 'Mixer'
        self._mixer.master_strip().name = 'Master_Channel_Strip'
        master_select_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 80)
        master_select_button.name = 'Master_Select_Button'
        self._mixer.master_strip().set_select_button(master_select_button) #set in ShiftableSelectorComponent instead if used for Note Mode
        self._mixer.selected_strip().name = 'Selected_Channel_Strip'
        select_buttons = [] #added
        arm_buttons = [] #added
        sliders = [] #added     
        for track in range(8):
            strip = self._mixer.channel_strip(track)
            strip.name = 'Channel_Strip_' + str(track)
            #volume_control = SliderElement(MIDI_CC_TYPE, track, 7) #set in ShiftableSelectorComponent instead
            #arm_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, track, 48) #see below
            solo_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, track, 49)
            solo_button.name = str(track) + '_Solo_Button'
            strip.set_solo_button(solo_button)

            if track < 4:
              mute_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, track, 50)
              mute_button.name = str(track) + '_Mute_Button'
              strip.set_mute_button(mute_button)
              strip.set_invert_mute_feedback(True)

            strip.set_shift_button(self._shift_button)
            select_buttons.append(ButtonElement(is_momentary, MIDI_NOTE_TYPE, track, 51)) #added
            select_buttons[-1].name = str(track) + '_Select_Button' #added            
            #strip.set_select_button(select_buttons[-1]) #added 
            arm_buttons.append(ButtonElement(is_momentary, MIDI_NOTE_TYPE, track, 48)) #added
            arm_buttons[-1].name = str(track) + '_Arm_Button' #added
            sliders.append(SliderElement(MIDI_CC_TYPE, track, 7)) #added
            sliders[-1].name = str(track) + '_Volume_Control' #added

        self._crossfader = SliderElement(MIDI_CC_TYPE, 0, 15)
        master_volume_control = SliderElement(MIDI_CC_TYPE, 0, 14)
        self._prehear_control = EncoderElement(MIDI_CC_TYPE, 0, 47, Live.MidiMap.MapMode.relative_two_compliment)
        self._crossfader.name = 'Crossfader' #not used in APC20
        master_volume_control.name = 'Master_Volume_Control'
        self._prehear_control.name = 'Prehear_Volume_Control'
        self._mixer.set_shift_button(self._shift_button) #added for shifting prehear
        self._mixer.set_crossfader_control(self._crossfader) #not used in APC20
        self._mixer.set_prehear_volume_control(self._prehear_control) #functionality overridden in SpecialMixerComponent
        self._mixer.master_strip().set_volume_control(master_volume_control)
        self._slider_modes = SliderModesComponent(self._mixer, tuple(sliders)) #added from APC20 script
        self._slider_modes.name = 'Slider_Modes' #added from APC20 script
        matrix_modes = MatrixModesComponent(self._matrix, self._session, self._session_zoom, tuple(self._track_stop_buttons), self) #added new
        matrix_modes.name = 'Matrix_Modes' #added new
        # Original method args for ShiftableSelectorComponent: (self, select_buttons, master_button, arm_buttons, matrix, session, zooming, mixer, transport, slider_modes, mode_callback)
        #self._shift_modes = ShiftableSelectorComponent(tuple(select_buttons), master_select_button, tuple(arm_buttons), self._matrix, self._session, self._session_zoom, self._mixer, transport, slider_modes, self._send_introduction_message)
        self._shift_modes = ShiftableSelectorComponent(self, tuple(select_buttons), master_select_button, tuple(arm_buttons), self._matrix, self._session, self._session_zoom, self._mixer, self._slider_modes, matrix_modes) #, self._send_introduction_message) #also added self for _parent
        self._shift_modes.name = 'Shift_Modes'
        self._shift_modes.set_mode_toggle(self._shift_button)

    def _setup_custom_components(self):
        self._setup_looper_control()
        self._setup_device_and_transport_control()
        self._setup_global_control()    

    def _setup_looper_control(self):
        is_momentary = True
        #pedal = ButtonElement(is_momentary, MIDI_CC_TYPE, 0, 67)
        loop_on = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 4, 50)
        loop_start = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 5, 50)
        halve = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 6, 50)
        double = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 7, 50)
        looper = LooperComponent(self)
        looper.set_shift_button(self._shift_button)
        looper.set_loop_toggle_button(loop_on)
        looper.set_loop_start_button(loop_start)
        looper.set_loop_double_button(double) 
        looper.set_loop_halve_button(halve) 

    def _setup_device_and_transport_control(self):
        is_momentary = True
        device_bank_buttons = []
        device_param_controls = []
        bank_button_labels = ('Clip_Track_Button', 'Device_On_Off_Button', 'Previous_Device_Button', 'Next_Device_Button', 'Detail_View_Button', 'Rec_Quantization_Button', 'Midi_Overdub_Button', 'Device_Lock_Button', 'Metronome_Button')
        for index in range(8):
            device_bank_buttons.append(ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 58 + index))
            device_bank_buttons[-1].name = bank_button_labels[index]
            ring_mode_button = ButtonElement(not is_momentary, MIDI_CC_TYPE, 0, 24 + index)
            ringed_encoder = RingedEncoderElement(MIDI_CC_TYPE, 0, 16 + index, Live.MidiMap.MapMode.absolute)
            ringed_encoder.set_ring_mode_button(ring_mode_button)
            ringed_encoder.set_feedback_delay(-1) #added from Axiom DirectLink example
            ringed_encoder.name = 'Device_Control_' + str(index)
            ring_mode_button.name = ringed_encoder.name + '_Ring_Mode_Button'
            device_param_controls.append(ringed_encoder)
        self._device = ShiftableDeviceComponent()
        self._device.name = 'Device_Component'
        self._device.set_bank_buttons(tuple(device_bank_buttons))
        self._device.set_shift_button(self._shift_button)
        self._device.set_parameter_controls(tuple(device_param_controls))
        self._device.set_on_off_button(device_bank_buttons[1])
        self.set_device_component(self._device)
        detail_view_toggler = DetailViewControllerComponent()
        detail_view_toggler.name = 'Detail_View_Control'
        detail_view_toggler.set_shift_button(self._shift_button)
        detail_view_toggler.set_device_clip_toggle_button(device_bank_buttons[0])
        detail_view_toggler.set_detail_toggle_button(device_bank_buttons[4])
        detail_view_toggler.set_device_nav_buttons(device_bank_buttons[2], device_bank_buttons[3])


        # VU Meters
        vu = VUMeters(self)

        transport = ShiftableTransportComponent()
        transport.name = 'Transport'
        play_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 91)
        stop_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 92)
        record_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 93)
        nudge_up_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 100)
        nudge_down_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 101)
        tap_tempo_button = ButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 99)
        play_button.name = 'Play_Button'
        stop_button.name = 'Stop_Button'
        record_button.name = 'Record_Button'
        nudge_up_button.name = 'Nudge_Up_Button'
        nudge_down_button.name = 'Nudge_Down_Button'
        tap_tempo_button.name = 'Tap_Tempo_Button'
        transport.set_shift_button(self._shift_button)
        transport.set_play_button(play_button)
        transport.set_stop_button(stop_button)
        transport.set_record_button(record_button)
        transport.set_nudge_buttons(nudge_up_button, nudge_down_button)
        transport.set_undo_button(nudge_down_button) #shifted nudge
        transport.set_redo_button(nudge_up_button) #shifted nudge
        transport.set_tap_tempo_button(tap_tempo_button)
        self._device.set_lock_button(tap_tempo_button) #shifted tap tempo
        transport.set_quant_toggle_button(device_bank_buttons[5])
        transport.set_overdub_button(device_bank_buttons[6])
        transport.set_metronome_button(device_bank_buttons[7])
        transport.set_tempo_encoder(self._prehear_control) #shifted prehear
        bank_button_translator = ShiftableTranslatorComponent()
        bank_button_translator.set_controls_to_translate(tuple(device_bank_buttons))
        bank_button_translator.set_shift_button(self._shift_button)


    def _setup_global_control(self):
        is_momentary = True
        self._global_bank_buttons = []
        self._global_param_controls = []
        for index in range(8):
            ring_button = ButtonElement(not is_momentary, MIDI_CC_TYPE, 0, 56 + index)
            ringed_encoder = RingedEncoderElement(MIDI_CC_TYPE, 0, 48 + index, Live.MidiMap.MapMode.absolute)
            ringed_encoder.name = 'Track_Control_' + str(index)
            ringed_encoder.set_feedback_delay(-1)
            ring_button.name = ringed_encoder.name + '_Ring_Mode_Button'
            ringed_encoder.set_ring_mode_button(ring_button)
            self._global_param_controls.append(ringed_encoder)
        self._global_bank_buttons = []
        global_bank_labels = ('Pan_Button', 'Send_A_Button', 'Send_B_Button', 'Send_C_Button')
        for index in range(4):
            self._global_bank_buttons.append(ConfigurableButtonElement(is_momentary, MIDI_NOTE_TYPE, 0, 87 + index))#(not is_momentary, MIDI_NOTE_TYPE, 0, 87 + index))
            self._global_bank_buttons[-1].name = global_bank_labels[index]
        self._encoder_modes = EncoderMixerModeSelectorComponent(self._mixer)
        self._encoder_modes.name = 'Track_Control_Modes'
        #self._encoder_modes.set_modes_buttons(self._global_bank_buttons) # set in ShiftableEncoderSelectorComponent
        self._encoder_modes.set_controls(tuple(self._global_param_controls))
        #self._encoder_device_modes = EncoderDeviceModeSelectorComponent(self._mixer, self._device) #new
        self._encoder_device_modes = EncoderDeviceComponent(self._mixer, self._device, self)
        self._encoder_device_modes.name = 'Alt_Device_Control_Modes' #new
        self._encoder_eq_modes = EncoderEQComponent(self._mixer, self)#EncoderEQModeSelectorComponent(self._mixer) #new
        self._encoder_eq_modes.name = 'EQ_Control_Modes' #new
        global_translation_selector = ChannelTranslationSelector() #translate track encoders to channels 1 through 4, based on button selection (pan = 1, send A = 2, send B = 3, send C = 4)
        global_translation_selector.name = 'Global_Translations'
        global_translation_selector.set_controls_to_translate(tuple(self._global_param_controls))
        global_translation_selector.set_mode_buttons(tuple(self._global_bank_buttons))
        encoder_user_modes = EncoderUserModesComponent(self, self._encoder_modes, tuple(self._global_param_controls), tuple(self._global_bank_buttons), self._mixer, self._device, self._encoder_device_modes, self._encoder_eq_modes) #self._mixer, tuple(sliders)) #added
        encoder_user_modes.name = 'Encoder_User_Modes' #added   
        self._encoder_shift_modes = ShiftableEncoderSelectorComponent(self, tuple(self._global_bank_buttons), encoder_user_modes, self._encoder_modes, self._encoder_eq_modes, self._encoder_device_modes) #tuple(select_buttons), master_select_button, tuple(arm_buttons), self._matrix, self._session, self._session_zoom, self._mixer, slider_modes, matrix_modes) #, self._send_introduction_message) #also added self for _parent
        self._encoder_shift_modes.name = 'Encoder_Shift_Modes'
        self._encoder_shift_modes.set_mode_toggle(self._shift_button)     


    def _on_selected_track_changed(self):
        ControlSurface._on_selected_track_changed(self)
        #self._slider_modes.update() #added to update alternate slider assignments
        track = self.song().view.selected_track
        device_to_select = track.view.selected_device
        if device_to_select == None and len(track.devices) > 0:
            device_to_select = track.devices[0]
        if device_to_select != None:
            self.song().view.select_device(device_to_select)
        self._device_component.set_device(device_to_select)
        return None

    def _product_model_id_byte(self):
        return 115

########NEW FILE########
__FILENAME__ = APCSessionComponent
# emacs-mode: -*- python-*-
# -*- coding: utf-8 -*-

import Live 
from _Framework.SessionComponent import SessionComponent 
from _Framework.CompoundComponent import CompoundComponent #added
#from SpecialClipSlotComponent import SpecialClipSlotComponent #added
from _Framework.SceneComponent import SceneComponent #added
from _Framework.ClipSlotComponent import ClipSlotComponent #added

class APCSessionComponent(SessionComponent):
    " Special SessionComponent for the APC controllers' combination mode "
    __module__ = __name__

    def __init__(self, num_tracks, num_scenes):
        SessionComponent.__init__(self, num_tracks, num_scenes)
    #def __init__(self, num_tracks, num_scenes):
        #if not SessionComponent._session_highlighting_callback != None:
            #raise AssertionError
        #if not isinstance(num_tracks, int):
            #isinstance(num_tracks, int)
            #raise AssertionError
        #isinstance(num_tracks, int)
        #if not num_tracks >= 0:
            #raise AssertionError
        #if not isinstance(num_scenes, int):
            #isinstance(num_scenes, int)
            #raise AssertionError
        #isinstance(num_scenes, int)
        #if not num_scenes >= 0:
            #raise AssertionError
        #CompoundComponent.__init__(self)
        #self._track_offset = -1
        #self._scene_offset = -1
        #self._num_tracks = num_tracks
        #self._bank_up_button = None
        #self._bank_down_button = None
        #self._bank_right_button = None
        #self._bank_left_button = None
        #self._stop_all_button = None
        #self._next_scene_button = None
        #self._prev_scene_button = None
        #self._stop_track_clip_buttons = None
        #self._scroll_up_ticks_delay = -1
        #self._scroll_down_ticks_delay = -1
        #self._scroll_right_ticks_delay = -1
        #self._scroll_left_ticks_delay = -1
        #self._stop_track_clip_value = 127
        #self._offset_callback = None
        #self._highlighting_callback = SessionComponent._session_highlighting_callback
        #if num_tracks > 0:
            #pass
        #self._show_highlight = num_tracks > 0
        #self._mixer = None
        #self._selected_scene = SpecialSceneComponent(self._num_tracks, self.tracks_to_use)
        #self.on_selected_scene_changed()
        #self.register_components(self._selected_scene)
        #self._scenes = []
        #self._tracks_and_listeners = []
        #for index in range(num_scenes):
            #self._scenes.append(self._create_scene(self._num_tracks))
            #self.register_components(self._scenes[index])
        #self.set_offsets(0, 0)
        #self._register_timer_callback(self._on_timer)
        #return None

    #def _create_scene(self, num_tracks):
        #return SpecialSceneComponent(self.tracks_to_use)    
    
    def link_with_track_offset(self, track_offset):
        assert (track_offset >= 0)
        if self._is_linked():
            self._unlink()
        self._change_offsets(track_offset, 0)
        self._link()


# local variables:
# tab-width: 4

#class SpecialSceneComponent(SceneComponent):

    #def __init__(self, num_slots, tracks_to_use_callback):
        #SceneComponent.__init__(self, num_slots, tracks_to_use_callback)

    #def _create_clip_slot(self):
        #return ClipSlotComponent()


#class SpecialClipSlotComponent(ClipSlotComponent):

    #def __init__(self):
        #ClipSlotComponent.__init__(self)


    #def update(self):
        #self._has_fired_slot = False
        #if (self.is_enabled() and (self._launch_button != None)):
            #self._launch_button.turn_off()
            #value_to_send = -1
            #if (self._clip_slot != None):
                #if self.has_clip():
                    #value_to_send = self._stopped_value
                    #if self._clip_slot.clip.is_triggered:
                        #if self._clip_slot.clip.will_record_on_start:
                            #value_to_send = self._triggered_to_record_value
                        #else:
                            #value_to_send = self._triggered_to_play_value
                    #elif self._clip_slot.clip.is_playing:
                        #if self._clip_slot.clip.is_recording:
                            #value_to_send = self._recording_value
                        #else:
                            #value_to_send = self._started_value
                #elif self._clip_slot.is_triggered:
                    #if self._clip_slot.will_record_on_start:
                        #value_to_send = self._triggered_to_record_value
                    #else:
                        #value_to_send = self._triggered_to_play_value
                #if (value_to_send in range(128)):
                    #self._launch_button.send_value(value_to_send, True)
########NEW FILE########
__FILENAME__ = ConfigurableButtonElement
# emacs-mode: -*- python-*-
#From Launchpad scripts

import Live
from _Framework.ButtonElement import *
class ConfigurableButtonElement(ButtonElement):
    __module__ = __name__
    __doc__ = ' Special button class that can be configured with custom on- and off-values '

    def __init__(self, is_momentary, msg_type, channel, identifier):
        ButtonElement.__init__(self, is_momentary, msg_type, channel, identifier)
        self._on_value = 1 #127 for Launchpad #0=off, 1=green, 2=green blink, 3=red, 4=red blink, 5=yellow, 6=yellow blink, 7-127=green
        self._off_value = 0 #4 for Launchpad, 0 for APC40/20
        self._is_enabled = True
        self._is_notifying = False
        self._force_next_value = False
        self._pending_listeners = []



    def set_on_off_values(self, on_value, off_value):
        assert (on_value in range(128))
        assert (off_value in range(128))
        self._last_sent_value = -1
        self._on_value = on_value
        self._off_value = off_value



    def set_force_next_value(self):
        self._force_next_value = True



    def set_enabled(self, enabled):
        self._is_enabled = enabled



    def turn_on(self):
        self.send_value(self._on_value)



    def turn_off(self):
        self.send_value(self._off_value)



    def reset(self):
        self.send_value(0) #4 for Launchpad, 0 for APC40/20



    def add_value_listener(self, callback, identify_sender = False):
        if (not self._is_notifying):
            ButtonElement.add_value_listener(self, callback, identify_sender)
        else:
            self._pending_listeners.append((callback,
             identify_sender))



    def receive_value(self, value):
        self._is_notifying = True
        ButtonElement.receive_value(self, value)
        self._is_notifying = False
        for listener in self._pending_listeners:
            self.add_value_listener(listener[0], listener[1])

        self._pending_listeners = []



    def send_value(self, value, force = False):
        ButtonElement.send_value(self, value, (force or self._force_next_value))
        self._force_next_value = False



    def install_connections(self):
        if self._is_enabled:
            ButtonElement.install_connections(self)
        elif ((self._msg_channel != self._original_channel) or (self._msg_identifier != self._original_identifier)):
            self._install_translation(self._msg_type, self._original_identifier, self._original_channel, self._msg_identifier, self._msg_channel)




# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = DetailViewControllerComponent
# Partial --== Decompile ==-- with fixes
import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.ButtonElement import ButtonElement
SHOW_PLAYING_CLIP_DELAY = 5
class DetailViewControllerComponent(ControlSurfaceComponent):
    __module__ = __name__
    __doc__ = ' Component that can toggle the device chain- and clip view of the selected track '

    def __init__(self):
        ControlSurfaceComponent.__init__(self)
        self._device_clip_toggle_button = None
        self._detail_toggle_button = None
        self._left_button = None
        self._right_button = None
        self._shift_button = None
        self._shift_pressed = False
        self._show_playing_clip_ticks_delay = -1
        self.application().view.add_is_view_visible_listener('Detail', self._detail_view_visibility_changed)
        self._register_timer_callback(self._on_timer)
        return None

    def disconnect(self):
        self._unregister_timer_callback(self._on_timer)
        self.application().view.remove_is_view_visible_listener('Detail', self._detail_view_visibility_changed)
        if self._device_clip_toggle_button != None:
            self._device_clip_toggle_button.remove_value_listener(self._device_clip_toggle_value)
            self._device_clip_toggle_button = None
        if self._detail_toggle_button != None:
            self._detail_toggle_button.remove_value_listener(self._detail_toggle_value)
            self._detail_toggle_button = None
        if self._left_button != None:
            self._left_button.remove_value_listener(self._nav_value)
            self._left_button = None
        if self._right_button != None:
            self._right_button.remove_value_listener(self._nav_value)
            self._right_button = None
        if self._shift_button != None:
            self._shift_button.remove_value_listener(self._shift_value)
            self._shift_button = None
        return None

    def set_device_clip_toggle_button(self, button):
        if not(button == None or isinstance(button, ButtonElement)):
            isinstance(button, ButtonElement)
            raise AssertionError
        if self._device_clip_toggle_button != button:
            if self._device_clip_toggle_button != None:
                self._device_clip_toggle_button.remove_value_listener(self._device_clip_toggle_value)
            self._device_clip_toggle_button = button
            if self._device_clip_toggle_button != None:
                self._device_clip_toggle_button.add_value_listener(self._device_clip_toggle_value)
            #self._rebuild_callback()
            self.update()
        return None

    def set_detail_toggle_button(self, button):
        if not(button == None or isinstance(button, ButtonElement)):
            isinstance(button, ButtonElement)
            raise AssertionError
        if self._detail_toggle_button != button:
            if self._detail_toggle_button != None:
                self._detail_toggle_button.remove_value_listener(self._detail_toggle_value)
            self._detail_toggle_button = button
            if self._detail_toggle_button != None:
                self._detail_toggle_button.add_value_listener(self._detail_toggle_value)
            #self._rebuild_callback()
            self.update()
        return None

    def set_device_nav_buttons(self, left_button, right_button):
        if not(left_button == None or isinstance(left_button, ButtonElement)):
            isinstance(left_button, ButtonElement)
            raise AssertionError
        if not(right_button == None or isinstance(right_button, ButtonElement)):
            isinstance(right_button, ButtonElement)
            raise AssertionError
        identify_sender = True
        if self._left_button != None:
            self._left_button.remove_value_listener(self._nav_value)
        self._left_button = left_button
        if self._left_button != None:
            self._left_button.add_value_listener(self._nav_value, identify_sender)
        if self._right_button != None:
            self._right_button.remove_value_listener(self._nav_value)
        self._right_button = right_button
        if self._right_button != None:
            self._right_button.add_value_listener(self._nav_value, identify_sender)
        #self._rebuild_callback()
        self.update()
        return None

    def set_shift_button(self, button):
        if not(button == None or isinstance(button, ButtonElement) and button.is_momentary()):
            isinstance(button, ButtonElement)
            raise AssertionError
        if self._shift_button != button:
            if self._shift_button != None:
                self._shift_button.remove_value_listener(self._shift_value)
            self._shift_button = button
            if self._shift_button != None:
                self._shift_button.add_value_listener(self._shift_value)
            #self._rebuild_callback()
            self.update()
        return None

    def on_enabled_changed(self):
        self.update()

    def update(self):
        if self.is_enabled():
            self.is_enabled()
            if not self._shift_pressed:
                self._shift_pressed
                if self._left_button != None:
                    self._left_button.turn_off()
                if self._right_button != None:
                    self._right_button.turn_off()
                if self._device_clip_toggle_button != None:
                    self._device_clip_toggle_button.turn_off()
                self._detail_view_visibility_changed()
            else:
                self._shift_pressed
        else:
            self.is_enabled()
        return None

    def _detail_view_visibility_changed(self):
        if self.is_enabled() and not self._shift_pressed and self._detail_toggle_button != None:
            if self.application().view.is_view_visible('Detail'):
                self.application().view.is_view_visible('Detail')
                self._detail_toggle_button.turn_on()
            else:
                self.application().view.is_view_visible('Detail')
                self._detail_toggle_button.turn_off()
        else:
            self.is_enabled()
        return None

    def _device_clip_toggle_value(self, value):
        if not self._device_clip_toggle_button != None:
            raise AssertionError
        if not value in range(128):
            raise AssertionError
        if self.is_enabled() and not self._shift_pressed:
            not self._shift_pressed
            button_is_momentary = self._device_clip_toggle_button.is_momentary()
            if not button_is_momentary or value != 0:
                not button_is_momentary
                if not self.application().view.is_view_visible('Detail'):
                    self.application().view.is_view_visible('Detail')
                    self.application().view.show_view('Detail')
                else:
                    self.application().view.is_view_visible('Detail')
                if not self.application().view.is_view_visible('Detail/DeviceChain'):
                    self.application().view.is_view_visible('Detail/DeviceChain')
                    self.application().view.show_view('Detail/DeviceChain')
                else:
                    self.application().view.is_view_visible('Detail/DeviceChain')
                    self.application().view.show_view('Detail/Clip')
            if button_is_momentary and value != 0:
                self._show_playing_clip_ticks_delay = SHOW_PLAYING_CLIP_DELAY
            else:
                button_is_momentary
                self._show_playing_clip_ticks_delay = -1
        else:
            self.is_enabled()
        return None


    def _detail_toggle_value(self, value):
        assert (self._detail_toggle_button != None)
        assert (value in range(128))
        if (self.is_enabled() and (not self._shift_pressed)):
            if ((not self._detail_toggle_button.is_momentary()) or (value != 0)):
                if (not self.application().view.is_view_visible('Detail')):
                    self.application().view.show_view('Detail')
                else:
                    self.application().view.hide_view('Detail')	    

	    
    def _shift_value(self, value):
        if not self._shift_button != None:
            raise AssertionError
        if not value in range(128):
            raise AssertionError
        self._shift_pressed = value != 0
        self.update()
        return None

    def _nav_value(self, value, sender):
        assert ((sender != None) and (sender in (self._left_button,
                                                 self._right_button)))
        if (self.is_enabled() and (not self._shift_pressed)):
            if ((not sender.is_momentary()) or (value != 0)):
                modifier_pressed = True
                if ((not self.application().view.is_view_visible('Detail')) or (not self.application().view.is_view_visible('Detail/DeviceChain'))):
                    self.application().view.show_view('Detail')
                    self.application().view.show_view('Detail/DeviceChain')
                else:
                    direction = Live.Application.Application.View.NavDirection.left
                    if (sender == self._right_button):
                        direction = Live.Application.Application.View.NavDirection.right
                    self.application().view.scroll_view(direction, 'Detail/DeviceChain', (not modifier_pressed))

    def _on_timer(self):
        if (self.is_enabled() and (not self._shift_pressed)):
            if (self._show_playing_clip_ticks_delay > -1):
                if (self._show_playing_clip_ticks_delay == 0):
                    song = self.song()
                    playing_slot_index = song.view.selected_track.playing_slot_index
                    if (playing_slot_index > -1):
                        song.view.selected_scene = song.scenes[playing_slot_index]
                        if song.view.highlighted_clip_slot.has_clip:
                            self.application().view.show_view('Detail/Clip')
                self._show_playing_clip_ticks_delay -= 1
########NEW FILE########
__FILENAME__ = EncoderDeviceComponent
# emacs-mode: -*- python-*-
# http://remotescripts.blogspot.com

import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.EncoderElement import EncoderElement
from _Framework.MixerComponent import MixerComponent 
from _Framework.DeviceComponent import DeviceComponent

class EncoderDeviceComponent(ControlSurfaceComponent):
    __module__ = __name__
    __doc__ = " Class representing encoder Device component "

    def __init__(self, mixer, device, parent):
        ControlSurfaceComponent.__init__(self)
        assert isinstance(mixer, MixerComponent)
        self._param_controls = None
        self._mixer = mixer
        self._buttons = []
        self._lock_button = None
        self._last_mode = 0
        self._is_locked = False
        self._ignore_buttons = False
        self._track = None
        self._strip = None
        self._parent = parent
        self._device = device
        self._alt_device = DeviceComponent()
        self._alt_device.name = 'Alt_Device_Component'
        self.song().add_appointed_device_listener(self._on_device_changed)

    def disconnect(self):
        self.song().remove_appointed_device_listener(self._on_device_changed)
        self._param_controls = None
        self._mixer = None
        self._buttons = None
        self._lock_button = None
        self._track = None
        self._strip = None
        self._parent = None
        self._device = None
        self._alt_device = None

    def update(self):
        pass
        #self._show_msg_callback("EncoderDeviceComponent update called")


    def set_controls_and_buttons(self, controls, buttons):
        assert ((controls == None) or (isinstance(controls, tuple) and (len(controls) == 8)))
        self._param_controls = controls
        assert ((buttons == None) or (isinstance(buttons, tuple)) or (len(buttons) == 4))
        self._buttons = buttons
        self.set_lock_button(self._buttons[0])

        if self._is_locked == True:
            self._alt_device.set_parameter_controls(self._param_controls)  
            self._alt_device.set_bank_nav_buttons(self._buttons[2], self._buttons[3])
            self._alt_device.set_on_off_button(self._buttons[1])
        else:
            self.on_selected_track_changed()


    def _on_device_changed(self):
        if self.is_enabled():
            if self._is_locked != True:
                selected_device= self.song().appointed_device
                self._alt_device.set_device(selected_device)
                self._setup_controls_and_buttons()


    def on_selected_track_changed(self):
        if self.is_enabled():
            if self._is_locked != True:
                track = self.song().view.selected_track
                selected_device = track.view.selected_device
                self._alt_device.set_device(selected_device)
                self._setup_controls_and_buttons()


    def _setup_controls_and_buttons(self):
        if self._buttons != None and self._param_controls != None:
            if self._alt_device != None:
                self._alt_device.set_parameter_controls(self._param_controls)  
                self._alt_device.set_bank_nav_buttons(self._buttons[2], self._buttons[3])
                self._alt_device.set_on_off_button(self._buttons[1])
            self._alt_device._on_on_off_changed()

            #self._rebuild_callback()


    def on_enabled_changed(self):
        self.update()  


    def set_lock_button(self, button):
        assert ((button == None) or isinstance(button, ButtonElement))
        if (self._lock_button != None):
            self._lock_button.remove_value_listener(self._lock_value)
            self._lock_button = None
        self._lock_button = button
        if (self._lock_button != None):
            self._lock_button.add_value_listener(self._lock_value)
            if self._is_locked:
                self._lock_button.turn_on()
            else:
                self._lock_button.turn_off()            


    def _lock_value(self, value):
        assert (self._lock_button != None)
        assert (value != None)
        assert isinstance(value, int)
        if ((not self._lock_button.is_momentary()) or (value is not 0)):
            if self._ignore_buttons == False:
                if self._is_locked:
                    self._is_locked = False
                    self._lock_button.turn_off()
                    self.on_selected_track_changed()
                else:
                    self._is_locked = True
                    self._lock_button.turn_on()



# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = EncoderEQComponent
# emacs-mode: -*- python-*-
# http://remotescripts.blogspot.com

import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.EncoderElement import EncoderElement
from _Framework.MixerComponent import MixerComponent 
from _Framework.TrackEQComponent import TrackEQComponent
from _Framework.TrackFilterComponent import TrackFilterComponent

from _Generic.Devices import *
EQ_DEVICES = {'Eq8': {'Gains': [ ('%i Gain A' % (index + 1)) for index in range(8) ]},
              'FilterEQ3': {'Gains': ['GainLo',
                                      'GainMid',
                                      'GainHi'],
                            'Cuts': ['LowOn',
                                     'MidOn',
                                     'HighOn']}}
class SpecialTrackEQComponent(TrackEQComponent): #added to override _cut_value

    def __init__(self):
        TrackEQComponent.__init__(self)
        self._ignore_cut_buttons = False

    def _cut_value(self, value, sender):
        assert (sender in self._cut_buttons)
        assert (value in range(128))
        if self._ignore_cut_buttons == False: #added
            if (self.is_enabled() and (self._device != None)):
                if ((not sender.is_momentary()) or (value is not 0)):
                    device_dict = EQ_DEVICES[self._device.class_name]
                    if ('Cuts' in device_dict.keys()):
                        cut_names = device_dict['Cuts']
                        index = list(self._cut_buttons).index(sender)
                        if (index in range(len(cut_names))):
                            parameter = get_parameter_by_name(self._device, cut_names[index])
                            if (parameter != None):
                                parameter.value = float((int((parameter.value + 1)) % 2))


class EncoderEQComponent(ControlSurfaceComponent):
    __module__ = __name__
    __doc__ = " Class representing encoder EQ component "

    def __init__(self, mixer, parent):
        ControlSurfaceComponent.__init__(self)
        assert isinstance(mixer, MixerComponent)
        self._param_controls = None
        self._mixer = mixer
        self._buttons = []
        self._param_controls = None
        self._lock_button = None
        self._last_mode = 0
        self._is_locked = False
        self._ignore_buttons = False
        self._track = None
        self._strip = None
        self._parent = parent
        self._track_eq = SpecialTrackEQComponent()
        self._track_filter = TrackFilterComponent()

    def disconnect(self):
        self._param_controls = None
        self._mixer = None
        self._buttons = None
        self._param_controls = None
        self._lock_button = None
        self._track = None
        self._strip = None
        self._parent = None
        self._track_eq = None
        self._track_filter = None

    def update(self):
        pass


    def set_controls_and_buttons(self, controls, buttons):
        assert ((controls == None) or (isinstance(controls, tuple) and (len(controls) == 8)))
        self._param_controls = controls
        assert ((buttons == None) or (isinstance(buttons, tuple)) or (len(buttons) == 4))
        self._buttons = buttons
        self.set_lock_button(self._buttons[0])
        self._update_controls_and_buttons()


    def _update_controls_and_buttons(self):
        #if self.is_enabled():
        if self._param_controls != None and self._buttons != None:
            if self._is_locked != True:
                self._track = self.song().view.selected_track
                self._track_eq.set_track(self._track)
                cut_buttons = [self._buttons[1], self._buttons[2], self._buttons[3]]
                self._track_eq.set_cut_buttons(tuple(cut_buttons))
                self._track_eq.set_gain_controls(tuple([self._param_controls[5], self._param_controls[6], self._param_controls[7]]))
                self._track_filter.set_track(self._track)
                self._track_filter.set_filter_controls(self._param_controls[0], self._param_controls[4])
                self._strip = self._mixer._selected_strip
                self._strip.set_send_controls(tuple([self._param_controls[1], self._param_controls[2], self._param_controls[3]]))         

            else:
                self._track_eq.set_track(self._track)
                cut_buttons = [self._buttons[1], self._buttons[2], self._buttons[3]]
                self._track_eq.set_cut_buttons(tuple(cut_buttons))
                self._track_eq.set_gain_controls(tuple([self._param_controls[5], self._param_controls[6], self._param_controls[7]]))
                self._track_filter.set_track(self._track)
                self._track_filter.set_filter_controls(self._param_controls[0], self._param_controls[4])
                ##self._strip = self._mixer._selected_strip
                self._strip.set_send_controls(tuple([self._param_controls[1], self._param_controls[2], self._param_controls[3]])) 
                ##pass               

        #self._rebuild_callback()


    def on_track_list_changed(self):
        self.on_selected_track_changed()


    def on_selected_track_changed(self):
        if self.is_enabled():
            if self._is_locked != True:
                self._update_controls_and_buttons()


    def on_enabled_changed(self):
        self.update()  

    def set_lock_button(self, button):
        assert ((button == None) or isinstance(button, ButtonElement))
        if (self._lock_button != None):
            self._lock_button.remove_value_listener(self._lock_value)
            self._lock_button = None
        self._lock_button = button
        if (self._lock_button != None):
            self._lock_button.add_value_listener(self._lock_value)
            if self._is_locked:
                self._lock_button.turn_on()
            else:
                self._lock_button.turn_off()            


    def _lock_value(self, value):
        assert (self._lock_button != None)
        assert (value != None)
        assert isinstance(value, int)
        if ((not self._lock_button.is_momentary()) or (value is not 0)):
        #if (value is not 0):
            if self._ignore_buttons == False:
                if self._is_locked:
                    self._is_locked = False
                    self._mixer._is_locked = False
                    self._lock_button.turn_off()
                    self._mixer.on_selected_track_changed()
                    self.on_selected_track_changed()
                else:
                    self._is_locked = True
                    self._mixer._is_locked = True
                    self._lock_button.turn_on()



# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = EncoderMixerModeSelectorComponent
# emacs-mode: -*- python-*-
# -*- coding: utf-8 -*-

from _Framework.ModeSelectorComponent import ModeSelectorComponent 
from _Framework.ButtonElement import ButtonElement 
from _Framework.MixerComponent import MixerComponent 
PAN_TO_VOL_DELAY = 5 #added delay value for _on_timer Pan/Vol Mode selection

class EncoderMixerModeSelectorComponent(ModeSelectorComponent):
    ' Class that reassigns encoders on the AxiomPro to different mixer functions '
    __module__ = __name__

    def __init__(self, mixer):
        assert isinstance(mixer, MixerComponent)
        ModeSelectorComponent.__init__(self)
        self._controls = None
        self._mixer = mixer
        self.set_mode(0) #moved here
        self._pan_to_vol_ticks_delay = -1 #added
        self._mode_is_pan = True #new
        self._register_timer_callback(self._on_timer) #added


    def disconnect(self):
        for button in self._modes_buttons:
            button.remove_value_listener(self._mode_value)

        self._controls = None
        self._mixer = None
        self._unregister_timer_callback(self._on_timer) #added
        ModeSelectorComponent.disconnect(self)


    def set_modes_buttons(self, buttons):
        assert ((buttons == None) or (isinstance(buttons, tuple) or (len(buttons) == self.number_of_modes())))
        identify_sender = True
        for button in self._modes_buttons:
            button.remove_value_listener(self._mode_value)

        self._modes_buttons = []
        if (buttons != None):
            for button in buttons:
                assert isinstance(button, ButtonElement)
                self._modes_buttons.append(button)
                button.add_value_listener(self._mode_value, identify_sender)
        self.update()


    def set_controls(self, controls):
        assert ((controls == None) or (isinstance(controls, tuple) and (len(controls) == 8)))
        self._controls = controls
        self.update()


    def number_of_modes(self):
        return 4


    def _mode_value(self, value, sender):
        if self.is_enabled(): #added to ignore mode buttons when not enabled
            assert (len(self._modes_buttons) > 0)
            assert isinstance(value, int)
            assert isinstance(sender, ButtonElement)
            assert (self._modes_buttons.count(sender) == 1)
            if ((value is not 0) or (not sender.is_momentary())):
                self.set_mode(self._modes_buttons.index(sender))
            if self._modes_buttons.index(sender) == 0 and sender.is_momentary() and (value != 0): #added check for Pan button
                self._pan_to_vol_ticks_delay = PAN_TO_VOL_DELAY
            else:
                self._pan_to_vol_ticks_delay = -1

    def update(self):
        assert (self._modes_buttons != None)
        if self.is_enabled():
            if (self._modes_buttons != None):
                for button in self._modes_buttons:
                    if (self._modes_buttons.index(button) == self._mode_index):
                        button.turn_on()
                    else:
                        button.turn_off()

            if (self._controls != None):
                for index in range(len(self._controls)):
                    if (self._mode_index == 0):
                        if self._mode_is_pan == True: #added
                            self._mixer.channel_strip(index).set_volume_control(None)
                            self._mixer.channel_strip(index).set_pan_control(self._controls[index])
                        else:
                            self._mixer.channel_strip(index).set_pan_control(None)
                            self._mixer.channel_strip(index).set_volume_control(self._controls[index])
                        self._mixer.channel_strip(index).set_send_controls((None, None, None))
                    elif (self._mode_index == 1):
                        self._mixer.channel_strip(index).set_volume_control(None) #added
                        self._mixer.channel_strip(index).set_pan_control(None)
                        self._mixer.channel_strip(index).set_send_controls((self._controls[index],
                                                                            None,
                                                                            None))
                    elif (self._mode_index == 2):
                        self._mixer.channel_strip(index).set_volume_control(None) #added
                        self._mixer.channel_strip(index).set_pan_control(None)
                        self._mixer.channel_strip(index).set_send_controls((None,
                                                                            self._controls[index],
                                                                            None))
                    elif (self._mode_index == 3):
                        self._mixer.channel_strip(index).set_volume_control(None) #added
                        self._mixer.channel_strip(index).set_pan_control(None)
                        self._mixer.channel_strip(index).set_send_controls((None,
                                                                            None,
                                                                            self._controls[index]))
                    else:
                        pass
                        #print 'Invalid mode index'
                        #assert False
        else:
            for index in range(8):
                self._mixer.channel_strip(index).set_pan_control(None)
                self._mixer.channel_strip(index).set_send_controls((None, None, None))            
        #self._rebuild_callback()

        
    def _on_timer(self): #added to allow press & hold for Pan/Vol Mode selection
        if (self.is_enabled()):
            if (self._pan_to_vol_ticks_delay > -1):
                if (self._pan_to_vol_ticks_delay == 0):
                    self._mode_is_pan = not self._mode_is_pan
                    if self._mode_is_pan == True:
                        self._show_msg_callback("Set to Pan Mode")
                    else:
                        self._show_msg_callback("Set to Volume Mode")
                    self.update()
                self._pan_to_vol_ticks_delay -= 1

# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = EncoderUserModesComponent

import Live 
from _Framework.ModeSelectorComponent import ModeSelectorComponent 
from _Framework.ButtonElement import ButtonElement
from _Framework.DeviceComponent import DeviceComponent

class EncoderUserModesComponent(ModeSelectorComponent):
    ' SelectorComponent that assigns encoders to different user functions '
    __module__ = __name__

    def __init__(self, parent, encoder_modes, param_controls, bank_buttons, mixer, device, encoder_device_modes, encoder_eq_modes): #, mixer, sliders):
        assert (len(bank_buttons) == 4)
        ModeSelectorComponent.__init__(self)
        self._parent = parent
        self._encoder_modes = encoder_modes  
        self._param_controls = param_controls
        self._bank_buttons = bank_buttons
        self._mixer = mixer
        self._device = device
        self._encoder_device_modes = encoder_device_modes
        self._encoder_eq_modes = encoder_eq_modes
        self._mode_index = 0
        self._modes_buttons = []
        self._user_buttons = []
        self._last_mode = 0


    def disconnect(self):
        ModeSelectorComponent.disconnect(self)
        self._parent = None
        self._encoder_modes = None
        self._param_controls = None
        self._bank_buttons = None
        self._mixer = None
        self._device = None
        self._encoder_device_modes = None
        self._encoder_eq_modes = None
        self._modes_buttons = None
        self._user_buttons = None

    def on_enabled_changed(self):
        pass

    def set_mode(self, mode):
        assert isinstance(mode, int)
        assert (mode in range(self.number_of_modes()))
        if (self._mode_index != mode):
            self._last_mode = self._mode_index # keep track of previous mode, to allow conditional actions
            self._mode_index = mode
            self._set_modes()


    def set_mode_buttons(self, buttons):
        assert isinstance(buttons, (tuple,
                                    type(None)))
        for button in self._modes_buttons:
            button.remove_value_listener(self._mode_value)  

        self._modes_buttons = []
        if (buttons != None):
            for button in buttons:
                assert isinstance(button, ButtonElement)
                identify_sender = True
                button.add_value_listener(self._mode_value, identify_sender)
                self._modes_buttons.append(button)
            assert (self._mode_index in range(self.number_of_modes()))


    def number_of_modes(self):
        return 4


    def update(self):
        pass


    def _mode_value(self, value, sender):
        assert (len(self._modes_buttons) > 0)
        assert isinstance(value, int)
        assert isinstance(sender, ButtonElement)
        assert (self._modes_buttons.count(sender) == 1)
        if ((value is not 0) or (not sender.is_momentary())):
            self.set_mode(self._modes_buttons.index(sender))    


    def _set_modes(self):
        if self.is_enabled():
            assert (self._mode_index in range(self.number_of_modes()))
            for index in range(len(self._modes_buttons)):
                if (index <= self._mode_index):
                    self._modes_buttons[index].turn_on()
                else:
                    self._modes_buttons[index].turn_off()
            for button in self._modes_buttons:
                button.release_parameter()
                button.use_default_message()
            for control in self._param_controls:
                control.release_parameter()
                control.use_default_message()
                #control.set_needs_takeover(False)
            self._encoder_modes.set_enabled(False)
            
            self._encoder_device_modes.set_lock_button(None)
            self._encoder_device_modes._alt_device.set_bank_nav_buttons(None, None)
            self._encoder_device_modes._alt_device.set_on_off_button(None)
            if self._encoder_device_modes._alt_device._parameter_controls != None:
                for control in self._encoder_device_modes._alt_device._parameter_controls:
                    control.release_parameter()
            self._encoder_device_modes.set_enabled(False)
            
            self._encoder_eq_modes.set_enabled(False)
            self._encoder_eq_modes.set_lock_button(None)
            if self._encoder_eq_modes._track_eq != None:
                self._encoder_eq_modes._track_eq.set_cut_buttons(None)
                if self._encoder_eq_modes._track_eq._gain_controls != None:
                    for control in self._encoder_eq_modes._track_eq._gain_controls:
                        control.release_parameter()  
            if self._encoder_eq_modes._strip != None:
                self._encoder_eq_modes._strip.set_send_controls(None)              
            
            self._user_buttons = []

            if (self._mode_index == 0):               
                self._encoder_modes.set_enabled(True)

            elif (self._mode_index == 1):
                self._encoder_device_modes.set_enabled(True)
                self._encoder_device_modes.set_controls_and_buttons(self._param_controls, self._modes_buttons)

            elif (self._mode_index == 2):
                self._encoder_eq_modes.set_enabled(True)
                self._encoder_eq_modes.set_controls_and_buttons(self._param_controls, self._modes_buttons)


            elif (self._mode_index == 3):
                self._encoder_eq_modes._ignore_buttons = True
                if self._encoder_eq_modes._track_eq != None:
                    self._encoder_eq_modes._track_eq._ignore_cut_buttons = True
                self._encoder_device_modes._ignore_buttons = True
                for button in self._modes_buttons:
                    self._user_buttons.append(button)
                for control in self._param_controls:
                    control.set_identifier((control.message_identifier() - 9))
                    control._ring_mode_button.send_value(0)
            else:
                pass
            #self._rebuild_callback()



# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = LooperComponent
from _Framework.ButtonElement import ButtonElement #added
from _Framework.EncoderElement import EncoderElement #added    

class LooperComponent():
  'Handles looping controls'
  __module__ = __name__


  def __init__(self, parent):
    self._parent = parent
    self._loop_toggle_button = None
    self._loop_start_button = None
    self._loop_double_button = None
    self._loop_halve_button = None
    self._loop_length = 64
    self._loop_start = 0
    self._clip_length = 0
    self._shift_button = None
    self._current_clip = None
    self._shift_pressed = False

  def set_loop_toggle_button(self, button):
    assert ((button == None) or (isinstance(button, ButtonElement) and button.is_momentary()))
    if self._loop_toggle_button != button:
      if self._loop_toggle_button != None:
        self._loop_toggle_button.remove_value_listener(self.toggle_loop)
      self._loop_toggle_button = button
      if (self._loop_toggle_button != None):
        self._loop_toggle_button.add_value_listener(self.toggle_loop)


  def toggle_loop(self, value):
    if value == 1: 
      self.get_current_clip()
      if self._current_clip != None:
        current_clip = self._current_clip
        if not self._shift_pressed:
          if current_clip.looping == 1:
            current_clip.looping = 0
          else:
            self._clip_length = current_clip.length
            current_clip.looping = 1
        else:
          was_playing = current_clip.looping
          current_clip.looping = 1
          if current_clip.loop_start >= 32.0:
            current_clip.loop_end = current_clip.loop_end - 32.0
            current_clip.loop_start = current_clip.loop_start - 32.0 
          else:
            current_clip.loop_end = 0.0 + self._loop_length
            current_clip.loop_start = 0.0
          if was_playing == 0:
            current_clip.looping = 0


  def set_loop_start_button(self, button):
    assert ((button == None) or (isinstance(button, ButtonElement) and button.is_momentary()))
    if self._loop_start_button != button:
      if self._loop_start_button != None:
        self._loop_start_button.remove_value_listener(self.move_loop_start)
      self._loop_start_button = button
      if (self._loop_start_button != None):
        self._loop_start_button.add_value_listener(self.move_loop_start)

  def move_loop_start(self, value):
    if value == 1: 
      self.get_current_clip()
      if self._current_clip != None:
        current_clip = self._current_clip
        if not self._shift_pressed:
          self._loop_start = round(current_clip.playing_position / 4.0) * 4
          was_playing = current_clip.looping
          current_clip.looping = 1
          current_clip.loop_end = self._loop_start + self._loop_length
          current_clip.loop_start = self._loop_start
          # Twice to fix a weird bug
          current_clip.loop_end = self._loop_start + self._loop_length
          if was_playing == 0:
            current_clip.looping = 0
        else:
          was_playing = current_clip.looping
          current_clip.looping = 1
          current_clip.loop_end = current_clip.loop_end + 32.0
          current_clip.loop_start = current_clip.loop_start + 32.0
          if was_playing == 0:
            current_clip.looping = 0

  def set_loop_double_button(self, button):
    assert ((button == None) or (isinstance(button, ButtonElement) and button.is_momentary()))
    if self._loop_double_button != button:
      if self._loop_double_button != None:
        self._loop_double_button.remove_value_listener(self.increase_loop)
      self._loop_double_button = button
      if (self._loop_double_button != None):
        self._loop_double_button.add_value_listener(self.increase_loop)

  # Doubles loop without shift
  # Moves loop one bar right with shift
  def increase_loop(self, value):
    if value == 1: 
      self.get_current_clip()
      if self._current_clip != None:
        current_clip = self._current_clip
        was_playing = current_clip.looping
        current_clip.looping = 1
        if not self._shift_pressed:
          if self._loop_length <= 128:
            self._loop_length = self._loop_length * 2.0
          else:
            self._loop_length = self._loop_length + 16 
          current_clip.loop_end = current_clip.loop_start + self._loop_length
        else:
          current_clip.loop_end = current_clip.loop_end + 4.0
          current_clip.loop_start = current_clip.loop_start + 4.0
        if was_playing == 0:
          current_clip.looping = 0


  def set_loop_halve_button(self, button):
    assert ((button == None) or (isinstance(button, ButtonElement) and button.is_momentary()))
    if self._loop_halve_button != button:
      if self._loop_halve_button != None:
        self._loop_halve_button.remove_value_listener(self.decrease_loop)
      self._loop_halve_button = button
      if (self._loop_halve_button != None):
        self._loop_halve_button.add_value_listener(self.decrease_loop)

  # halves loop without shift
  # left loop one bar right with shift
  def decrease_loop(self, value):
    if value == 1: 
      self.get_current_clip()
      if self._current_clip != None:
        current_clip = self._current_clip
        was_playing = current_clip.looping
        current_clip.looping = 1
        if not self._shift_pressed:
          if self._loop_length <= 128:
            self._loop_length = self._loop_length / 2.0
          else:
            self._loop_length = self._loop_length - 16 
          current_clip.loop_end = current_clip.loop_start + self._loop_length
        else:
          if current_clip.loop_start >= 4.0:
            current_clip.loop_end = current_clip.loop_end - 4.0
            current_clip.loop_start = current_clip.loop_start - 4.0
          else:
            current_clip.loop_end = 0.0 + self._loop_length 
            current_clip.loop_start = 0.0 
        if was_playing == 0:
          current_clip.looping = 0


  def get_current_clip(self):
    if (self._parent.song().view.highlighted_clip_slot != None):
      clip_slot = self._parent.song().view.highlighted_clip_slot
      if clip_slot.has_clip:
        self._current_clip = clip_slot.clip
      else:
        self._current_clip = None
    else:
      self._current_clip = None


  def set_shift_button(self, button): #added
      assert ((button == None) or (isinstance(button, ButtonElement) and button.is_momentary()))
      if (self._shift_button != button):
          if (self._shift_button != None):
              self._shift_button.remove_value_listener(self._shift_value)
          self._shift_button = button
          if (self._shift_button != None):
              self._shift_button.add_value_listener(self._shift_value)

  def _shift_value(self, value): #added
      assert (self._shift_button != None)
      assert (value in range(128))
      self._shift_pressed = (value != 0)

########NEW FILE########
__FILENAME__ = MatrixModesComponent
# emacs-mode: -*- python-*-
# -*- coding: utf-8 -*-

from _Framework.ModeSelectorComponent import ModeSelectorComponent 
from _Framework.ButtonElement import ButtonElement 
from _Framework.MixerComponent import MixerComponent 
from _Framework.ButtonMatrixElement import ButtonMatrixElement
from _Framework.ControlSurface import ControlSurface
from Matrix_Maps import *

class MatrixModesComponent(ModeSelectorComponent):
    ' SelectorComponent that assigns matrix to different functions '
    __module__ = __name__

    def __init__(self, matrix, session, zooming, stop_buttons, parent):
        assert isinstance(matrix, ButtonMatrixElement)
        ModeSelectorComponent.__init__(self)
        self._controls = None
        self._session = session
        self._session_zoom = zooming
        self._matrix = matrix
        self._track_stop_buttons = stop_buttons
        self._stop_button_matrix = ButtonMatrixElement() #new dummy matrix for stop buttons, to allow note mode/user mode switching
        button_row = []
        for track_index in range(8):
            button = self._track_stop_buttons[track_index]
            button_row.append(button)
        self._stop_button_matrix.add_row(tuple(button_row))
        self._mode_index = 0
        self._last_mode = 0
        self._parent = parent
        self._parent.set_pad_translations(PAD_TRANSLATIONS) #comment out to remove Drum Rack mapping

        
    def disconnect(self):
        for button in self._modes_buttons:
            button.remove_value_listener(self._mode_value)
        self._controls = None
        self._session = None
        self._session_zoom = None
        self._matrix = None
        self._track_stop_buttons = None
        self._stop_button_matrix = None
        ModeSelectorComponent.disconnect(self)

        
    def set_mode(self, mode): #override ModeSelectorComponent set_mode, to avoid flickers
        assert isinstance(mode, int)
        assert (mode in range(self.number_of_modes()))
        if (self._mode_index != mode):
            self._last_mode = self._mode_index # keep track of previous mode, to allow refresh after Note Mode only
            self._mode_index = mode
            self._set_modes()
            
            
    def set_mode_buttons(self, buttons):
        assert isinstance(buttons, (tuple,
                                    type(None)))
        for button in self._modes_buttons:
            button.remove_value_listener(self._mode_value)

        self._modes_buttons = []
        if (buttons != None):
            for button in buttons:
                assert isinstance(button, ButtonElement)
                identify_sender = True
                button.add_value_listener(self._mode_value, identify_sender)
                self._modes_buttons.append(button)
            for index in range(len(self._modes_buttons)):
                if (index == self._mode_index):
                    self._modes_buttons[index].turn_on()
                else:
                    self._modes_buttons[index].turn_off()


    def number_of_modes(self):
        return 8

    
    def update(self):
        pass

    
    def _set_modes(self):
        if self.is_enabled():
            self._session.set_allow_update(False)
            self._session_zoom.set_allow_update(False)
            assert (self._mode_index in range(self.number_of_modes()))
            for index in range(len(self._modes_buttons)):
                if (index == self._mode_index):
                    self._modes_buttons[index].turn_on()
                else:
                    self._modes_buttons[index].turn_off()
            self._session.set_stop_track_clip_buttons(tuple(self._track_stop_buttons))            
            for track_index in range(8):
                button = self._track_stop_buttons[track_index]
                button.use_default_message()
                button.set_enabled(True)
                button.set_force_next_value()
                button.send_value(0)
            self._session_zoom.set_enabled(True)
            self._session.set_enabled(True)
            self._session.set_show_highlight(True)
            self._session_zoom.set_zoom_button(self._parent._shift_button)
            for scene_index in range(5):
                scene = self._session.scene(scene_index) 
                for track_index in range(8):                
                    button = self._matrix.get_button(track_index, scene_index)
                    button.use_default_message()
                    clip_slot = scene.clip_slot(track_index)
                    clip_slot.set_launch_button(button)
                    button.set_enabled(True)
                
            if (self._mode_index == 0): #Clip Launch
                self._session_zoom._zoom_value(1) #zoom out
                pass
                        
            elif (self._mode_index == 1): #Session Overview
                self._session_zoom.set_enabled(True)
                self._session_zoom._is_zoomed_out = True
                self._session_zoom._scene_bank_index = int(((self._session_zoom._session.scene_offset() / self._session_zoom._session.height()) / self._session_zoom._buttons.height()))               
                self._session.set_enabled(False)
                self._session_zoom.update()
                self._session_zoom.set_zoom_button(None)
    
            elif (self._mode_index == 2):
                self._set_note_mode(PATTERN_1, CHANNEL_1, NOTEMAP_1, USE_STOP_ROW_1, IS_NOTE_MODE_1)
            elif (self._mode_index == 3):
                self._set_note_mode(PATTERN_2, CHANNEL_2, NOTEMAP_2, USE_STOP_ROW_2, IS_NOTE_MODE_2)
            elif (self._mode_index == 4):
                self._set_note_mode(PATTERN_3, CHANNEL_3, NOTEMAP_3, USE_STOP_ROW_3, IS_NOTE_MODE_3)
            elif (self._mode_index == 5):
                self._set_note_mode(PATTERN_4, CHANNEL_4, NOTEMAP_4, USE_STOP_ROW_4, IS_NOTE_MODE_4)
            elif (self._mode_index == 6):
                self._set_note_mode(PATTERN_5, CHANNEL_5, NOTEMAP_5, USE_STOP_ROW_5, IS_NOTE_MODE_5)
            elif (self._mode_index == 7):
                self._set_note_mode(PATTERN_6, CHANNEL_6, NOTEMAP_6, USE_STOP_ROW_6, IS_NOTE_MODE_6)
            else:
                pass #assert False
            self._session.set_allow_update(True)
            self._session_zoom.set_allow_update(True)
            #self._rebuild_callback()


    def _set_note_mode(self, pattern, channel, notemap, use_stop_row = False, is_note_mode = True):
        self._session_zoom.set_zoom_button(None)
        self._session_zoom.set_enabled(False)
        for scene_index in range(5):
            scene = self._session.scene(scene_index) 
            for track_index in range(8):
                clip_slot = scene.clip_slot(track_index)
                button = self._matrix.get_button(track_index, scene_index)
                clip_slot.set_launch_button(None)
                button.set_channel(channel) #remap all Note Mode notes to new channel
                button.set_identifier(notemap[scene_index][track_index])
                #button.send_value(pattern[scene_index][track_index], True)
                button.set_on_off_values(pattern[scene_index][track_index], 0)
                button.set_force_next_value()
                button.turn_on()
                #button.turn_off()
                if is_note_mode == True:
                    button.set_enabled(False)
        if use_stop_row == True:
            self._session.set_stop_track_clip_buttons(None)
            for track_index in range(8):
                button = self._stop_button_matrix.get_button(track_index, 0)
                button.set_channel(channel) #remap all Note Mode notes to new channel
                button.set_identifier(notemap[5][track_index])
                button.set_force_next_value()
                button.send_value(pattern[5][track_index])
                #button.receive_value(pattern[5][track_index]) #TODO - feedback?
                if is_note_mode == True:
                    button.set_enabled(False)
        else:
            #self._session.set_enabled(True)
            for track_index in range(8):
                button = self._stop_button_matrix.get_button(track_index, 0)
                button.send_value(0, True)
        self._session.set_enabled(True)
        self._session.set_show_highlight(True)

# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = Matrix_Maps
# http://remotescripts.blogspot.com
# Mappings for APC40_21 USER MODE/NOTE MODE are defined in this file
# Values may be edited with any text editor, but avoid using tabs for indentation

#---------- Page 1 is Clip Launch

#---------- Page 2 is Session Overview

#---------- Page 3 is User Mode 1

#set USE_STOP_MODE to True in order to use Track Stop buttons as part of Note Mode/User Mode grid, otherwise set to False.
USE_STOP_ROW_1 = True 

#set IS_NOTE_MODE to True for Note Mode (sends MIDI notes), or set to False for User Mode (does not send MIDI notes)
IS_NOTE_MODE_1 = True

# The PATTERN array represents the colour values for each button in the grid; there are 6 rows and 8 columns
# The LED colour values are: 0=off, 1=green, 2=green blink, 3=red, 4=red blink, 5=yellow, 6=yellow blink, 7-127=green
# The last row represents the Track Stop buttons; these values will be ignored unless USE_STOP_ROW is set to True
# The Track Stop buttons can be set to 0=off or 1-127=green
PATTERN_1 = ((3, 3, 3, 3, 5, 5, 5, 5), #Row 1
             (3, 3, 3, 3, 5, 5, 5, 5), #Row 2
             (1, 1, 1, 1, 1, 1, 1, 1), #Row 3
             (1, 1, 1, 1, 3, 3, 3, 3), #Row 4
             (1, 1, 1, 1, 3, 3, 3, 3), #Row 5
             (1, 1, 1, 1, 1, 1, 1, 1), #Clip Stop Row
             ) #0=off, 1=green, 2=green blink, 3=red, 4=red blink, 5=yellow, 6=yellow blink, 7-127=green

# The CHANNEL value sets the MIDI Channel for the entire grid. 
# Values 0 through 15 correspond to MIDI channels 1 through 16. 
# Channels 0 through 8 should be avoided, to prevent conflict with the APC40's native mappings
CHANNEL_1 = 9

# The NOTEMAP array represents the MIDI note values for each button in the grid; there are 6 rows and 8 columns
# Valid note values are 0 through 127
# The last row represents the Track Stop buttons; these values will be ignored unless USE_STOP_ROW is set to True
NOTEMAP_1 = ((56, 57, 58, 59, 80, 81, 82, 83), #Row 1
             (52, 53, 54, 55, 76, 77, 78, 79), #Row 2
             (48, 49, 50, 51, 72, 73, 74, 75), #Row 3
             (44, 45, 46, 47, 68, 69, 70, 71), #Row 4
             (40, 41, 42, 43, 64, 65, 66, 67), #Row 5
             (36, 37, 38, 39, 60, 61, 62, 63), #Clip Stop Row
             )

#---------- Page 4 is User Mode 2

USE_STOP_ROW_2 = True
IS_NOTE_MODE_2 = True

PATTERN_2 = ((5, 5, 5, 5, 5, 5, 5, 5), #Row 1
             (1, 1, 1, 1, 5, 5, 5, 5), #Row 2
             (1, 1, 1, 1, 1, 1, 1, 1), #Row 3
             (3, 3, 3, 3, 3, 3, 3, 3), #Row 4
             (1, 1, 1, 1, 3, 3, 3, 3), #Row 5
             (1, 1, 1, 1, 1, 1, 1, 1), #Clip Stop Row
             ) #0=off, 1=green, 2=green blink, 3=red, 4=red blink, 5=yellow, 6=yellow blink, 7-127=green

CHANNEL_2 = 10

NOTEMAP_2 = ((76, 77, 78, 79, 80, 81, 82, 83), #Row 1
             (68, 69, 70, 71, 72, 73, 74, 75), #Row 2
             (60, 61, 62, 63, 64, 65, 66, 67), #Row 3
             (52, 53, 54, 55, 56, 57, 58, 59), #Row 4
             (44, 45, 46, 47, 48, 49, 50, 51), #Row 5
             (36, 37, 38, 39, 40, 41, 42, 43), #Clip Stop Row
             )

#---------- Page 5 is User Mode 3

USE_STOP_ROW_3 = True
IS_NOTE_MODE_3 = True

PATTERN_3 = ((5, 5, 0, 5, 0, 5, 0, 5), #Row 1
             (0, 1, 0, 1, 5, 0, 5, 0), #Row 2
             (1, 0, 1, 0, 1, 1, 0, 1), #Row 3
             (3, 3, 0, 3, 0, 3, 0, 3), #Row 4
             (0, 1, 0, 1, 3, 0, 3, 0), #Row 5
             (1, 0, 1, 0, 1, 1, 0, 1), #Clip Stop Row
             ) #0=off, 1=green, 2=green blink, 3=red, 4=red blink, 5=yellow, 6=yellow blink, 7-127=green

CHANNEL_3 = 11

NOTEMAP_3 = ((76, 77, 78, 79, 80, 81, 82, 83), #Row 1
             (68, 69, 70, 71, 72, 73, 74, 75), #Row 2
             (60, 61, 62, 63, 64, 65, 66, 67), #Row 3
             (52, 53, 54, 55, 56, 57, 58, 59), #Row 4
             (44, 45, 46, 47, 48, 49, 50, 51), #Row 5
             (36, 37, 38, 39, 40, 41, 42, 43), #Clip Stop Row
             )

#---------- Page 6 is User Mode 4

USE_STOP_ROW_4 = False
IS_NOTE_MODE_4 = True

PATTERN_4 = ((5, 1, 5, 1, 3, 1, 3, 1), #Row 1
             (1, 5, 1, 5, 1, 3, 1, 3), #Row 2
             (5, 1, 5, 1, 3, 1, 3, 1), #Row 3
             (1, 5, 1, 5, 1, 3, 1, 3), #Row 4
             (5, 1, 5, 1, 3, 1, 3, 1), #Row 5
             (1, 1, 1, 1, 1, 1, 1, 1), #Clip Stop Row
             ) #0=off, 1=green, 2=green blink, 3=red, 4=red blink, 5=yellow, 6=yellow blink, 7-127=green

CHANNEL_4 = 12

NOTEMAP_4 = ((56, 57, 58, 59, 80, 81, 82, 83), #Row 1
             (52, 53, 54, 55, 76, 77, 78, 79), #Row 2
             (48, 49, 50, 51, 72, 73, 74, 75), #Row 3
             (44, 45, 46, 47, 68, 69, 70, 71), #Row 4
             (40, 41, 42, 43, 64, 65, 66, 67), #Row 5
             (36, 37, 38, 39, 60, 61, 62, 63), #Clip Stop Row
             )

#---------- Page 7 is User Mode 5

USE_STOP_ROW_5 = True
IS_NOTE_MODE_5 = True

PATTERN_5 = ((1, 5, 3, 1, 5, 3, 1, 5), #Row 1
             (1, 5, 3, 1, 5, 3, 1, 5), #Row 2
             (1, 5, 3, 1, 5, 3, 1, 5), #Row 3
             (1, 5, 3, 1, 5, 3, 1, 5), #Row 4
             (1, 5, 3, 1, 5, 3, 1, 5), #Row 5
             (1, 1, 1, 1, 1, 1, 1, 5), #Clip Stop Row
             ) #0=off, 1=green, 2=green blink, 3=red, 4=red blink, 5=yellow, 6=yellow blink, 7-127=green

CHANNEL_5 = 13

NOTEMAP_5 = ((41, 47, 53, 59, 65, 71, 77, 83), #Row 1
             (40, 46, 52, 58, 64, 70, 76, 82), #Row 2
             (39, 45, 51, 57, 63, 69, 75, 81), #Row 3
             (38, 44, 50, 56, 62, 68, 74, 80), #Row 4
             (37, 43, 49, 55, 61, 67, 73, 79), #Row 5
             (36, 42, 48, 54, 60, 66, 72, 78), #Clip Stop Row
             )

#---------- Page 8 is User Mode 6

USE_STOP_ROW_6 = True
IS_NOTE_MODE_6 = False

PATTERN_6 = ((3, 3, 3, 3, 3, 3, 3, 3), #Row 1
             (5, 5, 5, 5, 5, 5, 5, 5), #Row 2
             (1, 1, 1, 1, 1, 1, 1, 1), #Row 3
             (3, 3, 3, 3, 3, 3, 3, 3), #Row 4
             (5, 5, 5, 5, 5, 5, 5, 5), #Row 5
             (1, 1, 1, 1, 1, 1, 1, 1), #Clip Stop Row
             ) #0=off, 1=green, 2=green blink, 3=red, 4=red blink, 5=yellow, 6=yellow blink, 7-127=green

CHANNEL_6 = 14

NOTEMAP_6 = ((56, 57, 58, 59, 80, 81, 82, 83), #Row 1
             (52, 53, 54, 55, 76, 77, 78, 79), #Row 2
             (48, 49, 50, 51, 72, 73, 74, 75), #Row 3
             (44, 45, 46, 47, 68, 69, 70, 71), #Row 4
             (40, 41, 42, 43, 64, 65, 66, 67), #Row 5
             (36, 37, 38, 39, 60, 61, 62, 63), #Clip Stop Row
             )

#---------- Pad Translations for Drum Rack

# The PAD_TRANSLATIONS array represents a 4 x 4 Drum Rack
# Each slot in the rack is identified using X,Y coordinates, and mapped to a MIDI note and MIDI channel:
# (pad_x, pad_y, note, channel)
# Only one drum rack can be used at a time; maximum grid size is 4 x 4 (LiveAPI limitation)
PAD_TRANSLATIONS = ((0, 0, 48, 9), (1, 0, 49, 9), (2, 0, 50, 9), (3, 0, 51, 9), 
                    (0, 1, 44, 9), (1, 1, 45, 9), (2, 1, 46, 9), (3, 1, 47, 9),
                    (0, 2, 40, 9), (1, 2, 41, 9), (2, 2, 42, 9), (3, 2, 43, 9),
                    (0, 3, 36, 9), (1, 3, 37, 9), (2, 3, 38, 9), (3, 3, 39, 9),
                    ) #(pad_x, pad_y, note, channel)
########NEW FILE########
__FILENAME__ = PedaledSessionComponent
# emacs-mode: -*- python-*-
# -*- coding: utf-8 -*-

import Live 
from APCSessionComponent import APCSessionComponent 
from _Framework.ButtonElement import ButtonElement 
from ConfigurableButtonElement import ConfigurableButtonElement #added
class PedaledSessionComponent(APCSessionComponent):
    ' Special SessionComponent with a button (pedal) to fire the selected clip slot '
    __module__ = __name__

    def __init__(self, num_tracks, num_scenes):
        APCSessionComponent.__init__(self, num_tracks, num_scenes)
        self._slot_launch_button = None



    def disconnect(self):
        #for index in range(len(self._tracks_and_listeners)): #added from launchpad
            #track = self._tracks_and_listeners[index][0]
            #listener = self._tracks_and_listeners[index][2]
            #if ((track != None) and track.playing_slot_index_has_listener(listener)):
                #track.remove_playing_slot_index_listener(listener)
        APCSessionComponent.disconnect(self)
        if (self._slot_launch_button != None):
            self._slot_launch_button.remove_value_listener(self._slot_launch_value)
            self._slot_launch_button = None



    def set_slot_launch_button(self, button):
        assert ((button == None) or isinstance(button, ButtonElement))
        if (self._slot_launch_button != button):
            if (self._slot_launch_button != None):
                self._slot_launch_button.remove_value_listener(self._slot_launch_value)
            self._slot_launch_button = button
            if (self._slot_launch_button != None):
                self._slot_launch_button.add_value_listener(self._slot_launch_value)
            #self._rebuild_callback()
            self.update()



    def _slot_launch_value(self, value):
        assert (value in range(128))
        assert (self._slot_launch_button != None)
        if self.is_enabled():
            if ((value != 0) or (not self._slot_launch_button.is_momentary())):
                if (self.song().view.highlighted_clip_slot != None):
                    self.song().view.highlighted_clip_slot.fire()



# local variables:
# tab-width: 4

    #def _reassign_tracks(self):
        #for index in range(len(self._tracks_and_listeners)):
            #track = self._tracks_and_listeners[index][0]
            #fire_listener = self._tracks_and_listeners[index][1]
            #playing_listener = self._tracks_and_listeners[index][2]
            #if (track != None):
                #if track.fired_slot_index_has_listener(fire_listener):
                    #track.remove_fired_slot_index_listener(fire_listener)
                #if track.playing_slot_index_has_listener(playing_listener):
                    #track.remove_playing_slot_index_listener(playing_listener)

        #self._tracks_and_listeners = []
        #tracks_to_use = self.tracks_to_use()
        #for index in range(self._num_tracks):
            #fire_listener = lambda index = index:self._on_fired_slot_index_changed(index)

            #playing_listener = lambda index = index:self._on_playing_slot_index_changed(index)

            #track = None
            #if ((self._track_offset + index) < len(tracks_to_use)):
                #track = tracks_to_use[(self._track_offset + index)]
            #if (track != None):
                #self._tracks_and_listeners.append((track,
                 #fire_listener,
                 #playing_listener))
                #track.add_fired_slot_index_listener(fire_listener)
                #track.add_playing_slot_index_listener(playing_listener)
            #self._update_stop_clips_led(index)




    #def _on_fired_slot_index_changed(self, index):
        #self._update_stop_clips_led(index)



    #def _on_playing_slot_index_changed(self, index):
        #self._update_stop_clips_led(index)



    #def _update_stop_clips_led(self, index):
        #if (self.is_enabled() and (self._stop_track_clip_buttons != None)):
            #button = self._stop_track_clip_buttons[index]
            #if (index in range(len(self._tracks_and_listeners))):
                #track = self._tracks_and_listeners[index][0]
                #if (track.fired_slot_index == -2):
                    #button.send_value(self._stop_track_clip_value)
                #elif (track.playing_slot_index >= 0):
                    #button.send_value(1)
                #else:
                    #button.turn_off()
            #else:
                #button.send_value(0)


########NEW FILE########
__FILENAME__ = RepeatComponent
from _Framework.ButtonElement import ButtonElement #added
from _Framework.EncoderElement import EncoderElement #added    


class RepeatComponent():
  'Handles beat repeat controls'
  __module__ = __name__


  def __init__(self, parent):
    self._shift_button = None
    self._shift_pressed = False
    self._rack = None

    for device in parent.song().master_track.devices:
        if device.name == "Repeats":
            self._rack = device
            break
            
    if self._rack:
        for scene_index in range(5):
            scene = parent._session.scene(scene_index)
            button = scene._launch_button
            scene.set_launch_button(None)

            parent._device_buttons.append(button)
            button.add_value_listener(self._device_toggle, True)

  def _device_toggle(self, value, sender):
    if not self._shift_pressed:
      id = sender.message_identifier() - 82
      self._rack.parameters[id + 1].value = (value * 127)





  def set_shift_button(self, button): #added
      assert ((button == None) or (isinstance(button, ButtonElement) and button.is_momentary()))
      if (self._shift_button != button):
          if (self._shift_button != None):
              self._shift_button.remove_value_listener(self._shift_value)
          self._shift_button = button
          if (self._shift_button != None):
              self._shift_button.add_value_listener(self._shift_value)

  def _shift_value(self, value): #added
      assert (self._shift_button != None)
      assert (value in range(128))
      self._shift_pressed = (value != 0)

########NEW FILE########
__FILENAME__ = RingedEncoderElement
# emacs-mode: -*- python-*-
# -*- coding: utf-8 -*-

from _Framework.EncoderElement import EncoderElement 
from _Framework.ButtonElement import ButtonElement 
RING_OFF_VALUE = 0
RING_SIN_VALUE = 1
RING_VOL_VALUE = 2
RING_PAN_VALUE = 3
class RingedEncoderElement(EncoderElement):
    ' Class representing a continuous control on the controller enclosed with an LED ring '
    __module__ = __name__

    def __init__(self, msg_type, channel, identifier, map_mode):
        EncoderElement.__init__(self, msg_type, channel, identifier, map_mode)
        self._ring_mode_button = None
        self.set_needs_takeover(False)



    def set_ring_mode_button(self, button):
        assert ((button == None) or isinstance(button, ButtonElement))
        if (self._ring_mode_button != None):
            force_send = True
            self._ring_mode_button.send_value(RING_OFF_VALUE, force_send)
        self._ring_mode_button = button
        self._update_ring_mode()



    def connect_to(self, parameter):
        if ((parameter != self._parameter_to_map_to) and (not self.is_mapped_manually())):
            force_send = True
            self._ring_mode_button.send_value(RING_OFF_VALUE, force_send)
        EncoderElement.connect_to(self, parameter)



    def release_parameter(self):
        EncoderElement.release_parameter(self)
        self._update_ring_mode()



    def install_connections(self):
        EncoderElement.install_connections(self)
        if ((not self._is_mapped) and (len(self._value_notifications) == 0)):
            self._is_being_forwarded = self._install_forwarding(self)
        self._update_ring_mode()



    def is_mapped_manually(self):
        return ((not self._is_mapped) and (not self._is_being_forwarded))



    def _update_ring_mode(self):
        if (self._ring_mode_button != None):
            force_send = True
            if self.is_mapped_manually():
                self._ring_mode_button.send_value(RING_SIN_VALUE, force_send)
            elif (self._parameter_to_map_to != None):
                param = self._parameter_to_map_to
                p_range = (param.max - param.min)
                value = (((param.value - param.min) / p_range) * 127)
                self.send_value(int(value), force_send)
                if (self._parameter_to_map_to.min == (-1 * self._parameter_to_map_to.max)):
                    self._ring_mode_button.send_value(RING_PAN_VALUE, force_send)
                elif self._parameter_to_map_to.is_quantized:
                    self._ring_mode_button.send_value(RING_SIN_VALUE, force_send)
                else:
                    self._ring_mode_button.send_value(RING_VOL_VALUE, force_send)
            else:
                self._ring_mode_button.send_value(RING_OFF_VALUE, force_send)



# local variables:
# tab-width: 4
########NEW FILE########
__FILENAME__ = ShiftableDeviceComponent
# emacs-mode: -*- python-*-
# -*- coding: utf-8 -*-

import Live 
from _Generic.Devices import * 
from _Framework.DeviceComponent import DeviceComponent 
from _Framework.ChannelTranslationSelector import ChannelTranslationSelector 
from _Framework.ButtonElement import ButtonElement 
class ShiftableDeviceComponent(DeviceComponent):
    ' DeviceComponent that only uses bank buttons if a shift button is pressed '
    __module__ = __name__

    def __init__(self):
        DeviceComponent.__init__(self)
        self._shift_button = None
        self._shift_pressed = False
        self._control_translation_selector = ChannelTranslationSelector(8)


    def disconnect(self):
        DeviceComponent.disconnect(self)
        self._control_translation_selector.disconnect()
        if (self._shift_button != None):
            self._shift_button.remove_value_listener(self._shift_value)
            self._shift_button = None


    def set_parameter_controls(self, controls):
        DeviceComponent.set_parameter_controls(self, controls)
        self._control_translation_selector.set_controls_to_translate(controls)
        self._control_translation_selector.set_mode(self._bank_index)



    def set_device(self, device):
        DeviceComponent.set_device(self, device)
        self._control_translation_selector.set_mode(self._bank_index)



    def set_shift_button(self, button):
        assert ((button == None) or (isinstance(button, ButtonElement) and button.is_momentary()))
        if (self._shift_button != button):
            if (self._shift_button != None):
                self._shift_button.remove_value_listener(self._shift_value)
            self._shift_button = button
            if (self._shift_button != None):
                self._shift_button.add_value_listener(self._shift_value)
            self.update()



    def update(self):
        if (self._parameter_controls != None):
            for control in self._parameter_controls:
                control.release_parameter()

        if (self.is_enabled() and (self._device != None)):
            self._device_bank_registry[self._device] = self._bank_index
            if ((self._parameter_controls != None) and (self._bank_index < number_of_parameter_banks(self._device))):
                old_bank_name = self._bank_name
                self._assign_parameters()
                if (self._bank_name != old_bank_name):
                    self._show_msg_callback(((self._device.name + ' Bank: ') + self._bank_name))

        if (not self._shift_pressed):
            self._on_on_off_changed()

        elif (self._bank_buttons != None):
            for index in range(len(self._bank_buttons)):
                if (index == self._bank_index):
                    self._bank_buttons[index].turn_on()
                else:
                    self._bank_buttons[index].turn_off()

        #self._rebuild_callback()



    def _shift_value(self, value):
        assert (self._shift_button != None)
        assert (value in range(128))
        self._shift_pressed = (value != 0)
        self.update()



    def _bank_value(self, value, sender):
        assert ((sender != None) and (sender in self._bank_buttons))
        if (self._shift_pressed and self.is_enabled()):
            if ((value != 0) or (not sender.is_momentary())):
                self._bank_name = ''
                self._bank_index = list(self._bank_buttons).index(sender)
                self._control_translation_selector.set_mode(self._bank_index)
                self.update()



    def _on_off_value(self, value):
        if not self._shift_pressed:
            DeviceComponent._on_off_value(self, value)



    def _on_on_off_changed(self):
        if not self._shift_pressed:
            DeviceComponent._on_on_off_changed(self)



    def _lock_value(self, value): #added
        if self._shift_pressed:
            DeviceComponent._lock_value(self, value)


# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = ShiftableEncoderSelectorComponent

import Live
from _Framework.ModeSelectorComponent import ModeSelectorComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.DeviceComponent import DeviceComponent 

class ShiftableEncoderSelectorComponent(ModeSelectorComponent):
    __doc__ = ' SelectorComponent that assigns encoders to functions based on the shift button '

    def __init__(self, parent, bank_buttons, encoder_user_modes, encoder_modes, encoder_eq_modes, encoder_device_modes):#, select_buttons, master_button, arm_buttons, matrix, session, zooming, mixer, slider_modes, matrix_modes): #, mode_callback):
        if not len(bank_buttons) == 4:
            raise AssertionError
        ModeSelectorComponent.__init__(self)
        self._toggle_pressed = False
        self._invert_assignment = False
        self._parent = parent
        self._bank_buttons = bank_buttons        
        self._encoder_user_modes = encoder_user_modes
        self._encoder_modes = encoder_modes
        self._encoder_eq_modes = encoder_eq_modes
        self._encoder_device_modes = encoder_device_modes

    def disconnect(self):
        ModeSelectorComponent.disconnect(self)
        self._parent = None #added
        self._bank_buttons = None #added
        self._encoder_modes = None
        self._encoder_user_modes = None
        self._encoder_eq_modes = None
        self._encoder_device_modes = None
        return None

    def set_mode_toggle(self, button):
        ModeSelectorComponent.set_mode_toggle(self, button) #called from parent: self._shift_modes.set_mode_toggle(self._shift_button)
        self.set_mode(0)

    def invert_assignment(self):
        self._invert_assignment = True
        self._recalculate_mode()

    def number_of_modes(self):
        return 2

    def update(self):
        if self.is_enabled():
            if self._mode_index == int(self._invert_assignment):
                self._encoder_user_modes.set_mode_buttons(None)
                self._encoder_modes.set_modes_buttons(self._bank_buttons)                                 
            else:
                self._encoder_modes.set_modes_buttons(None)
                self._encoder_user_modes.set_mode_buttons(self._bank_buttons)             
        return None
      
    
    def _toggle_value(self, value): #"toggle" is shift button
        if not self._mode_toggle != None:
            raise AssertionError
        if not value in range(128):
            raise AssertionError
        self._toggle_pressed = value > 0
        self._recalculate_mode()
        if value > 0:
            self._encoder_eq_modes._ignore_buttons = True
            if self._encoder_eq_modes._track_eq != None:
                self._encoder_eq_modes._track_eq._ignore_cut_buttons = True
            self._encoder_device_modes._ignore_buttons = True
            for button in self._encoder_user_modes._modes_buttons:
                button.use_default_message()
        else:
            self._encoder_eq_modes._ignore_buttons = False
            if self._encoder_eq_modes._track_eq != None:
                self._encoder_eq_modes._track_eq._ignore_cut_buttons = False
            self._encoder_device_modes._ignore_buttons = False
            if self._encoder_user_modes._mode_index == 3:
                for control in self._encoder_user_modes._param_controls:
                    control.set_channel(9 + self._encoder_user_modes._mode_index)
                if self._encoder_user_modes._user_buttons != None:
                    for button in self._encoder_user_modes._user_buttons:
                        button.turn_off()
                    for button in self._encoder_user_modes._user_buttons:
                        button.set_channel(9 + self._encoder_user_modes._mode_index) 

        return None

    
    def _recalculate_mode(self): #called if toggle (i.e. shift) is pressed
        self.set_mode((int(self._toggle_pressed) + int(self._invert_assignment)) % self.number_of_modes())



        
########NEW FILE########
__FILENAME__ = ShiftableSelectorComponent

import Live
from _Framework.ModeSelectorComponent import ModeSelectorComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.DeviceComponent import DeviceComponent 
from EncoderUserModesComponent import EncoderUserModesComponent #added
from PedaledSessionComponent import PedaledSessionComponent #added
from _Framework.SessionZoomingComponent import SessionZoomingComponent #added
#from consts import * #see below (not used)
#MANUFACTURER_ID = 71
#ABLETON_MODE = 65
#NOTE_MODE = 65 #67 = APC20 Note Mode; 65 = APC40 Ableton Mode 1

class ShiftableSelectorComponent(ModeSelectorComponent):
    __doc__ = ' SelectorComponent that assigns buttons to functions based on the shift button '
    #def __init__(self, select_buttons, master_button, arm_buttons, matrix, session, zooming, mixer, transport, slider_modes, mode_callback):
    def __init__(self, parent, select_buttons, master_button, arm_buttons, matrix, session, zooming, mixer, slider_modes, matrix_modes):
        if not len(select_buttons) == 8:
            raise AssertionError
        if not len(arm_buttons) == 8:
            raise AssertionError
        ModeSelectorComponent.__init__(self)
        self._toggle_pressed = False
        self._note_mode_active = False
        self._invert_assignment = False
        self._select_buttons = select_buttons
        self._master_button = master_button
        self._slider_modes = slider_modes
        self._matrix_modes = matrix_modes #added new        
        self._arm_buttons = arm_buttons
        #self._transport = transport
        self._session = session
        self._zooming = zooming
        self._matrix = matrix
        self._mixer = mixer
        #self._master_button.add_value_listener(self._master_value)
        self._parent = parent #use this to call methods of parent class (APC40plus21)


    def disconnect(self):
        ModeSelectorComponent.disconnect(self)
        #self._master_button.remove_value_listener(self._master_value)
        self._select_buttons = None
        self._master_button = None
        self._slider_modes = None
        self._matrix_modes = None #added
        self._arm_buttons = None
        #self._transport = None
        self._session = None
        self._zooming = None
        self._matrix = None
        self._mixer = None
        self._parent = None #added
        return None

    def set_mode_toggle(self, button):
        ModeSelectorComponent.set_mode_toggle(self, button) #called from APC40_22: self._shift_modes.set_mode_toggle(self._shift_button)
        self.set_mode(0)

    def invert_assignment(self):
        self._invert_assignment = True
        self._recalculate_mode()

    def number_of_modes(self):
        return 2

    def update(self):
        if self.is_enabled():
            if self._mode_index == int(self._invert_assignment):
                self._slider_modes.set_mode_buttons(None)
                self._matrix_modes.set_mode_buttons(None)
                for index in range(len(self._arm_buttons)): #was: for index in range(len(self._select_buttons)):
                    self._mixer.channel_strip(index).set_arm_button(self._arm_buttons[index])
                    self._mixer.channel_strip(index).set_select_button(self._select_buttons[index])
            else:
                for index in range(len(self._arm_buttons)): #was: for index in range(len(self._select_buttons)):
                    self._mixer.channel_strip(index).set_arm_button(None)
                    self._mixer.channel_strip(index).set_select_button(None)
                self._slider_modes.set_mode_buttons(self._arm_buttons)
                self._matrix_modes.set_mode_buttons(self._select_buttons)
        return None

    def _partial_refresh(self, value):
        #for control in self._parent.controls:
            #control.clear_send_cache()   
        for component in self._parent.components:
            if isinstance(component, PedaledSessionComponent) or isinstance(component, SessionZoomingComponent):
                component.update()


    def _toggle_value(self, value): #"toggle" is shift button
        if not self._mode_toggle != None:
            raise AssertionError
        if not value in range(128):
            raise AssertionError
        self._toggle_pressed = value > 0
        self._recalculate_mode()
        if value < 1 and self._matrix_modes._last_mode > 1: #refresh on Shift button release, and if previous mode was Note Mode
            self._parent.schedule_message(2, self._partial_refresh, value)
        return None


    def _recalculate_mode(self): #called if toggle (i.e. shift) is pressed
        self.set_mode((int(self._toggle_pressed) + int(self._invert_assignment)) % self.number_of_modes())




########NEW FILE########
__FILENAME__ = ShiftableTranslatorComponent
# emacs-mode: -*- python-*-
# -*- coding: utf-8 -*-

from _Framework.ChannelTranslationSelector import ChannelTranslationSelector 
from _Framework.ButtonElement import ButtonElement 
from _Framework.MixerComponent import MixerComponent 
class ShiftableTranslatorComponent(ChannelTranslationSelector):
    ' Class that translates the channel of some buttons as long as a shift button is held '
    __module__ = __name__

    def __init__(self):
        ChannelTranslationSelector.__init__(self)
        self._shift_button = None
        self._shift_pressed = False



    def disconnect(self):
        if (self._shift_button != None):
            self._shift_button.remove_value_listener(self._shift_value)
            self._shift_button = None
        ChannelTranslationSelector.disconnect(self)



    def set_shift_button(self, button):
        assert ((button == None) or (isinstance(button, ButtonElement) and button.is_momentary()))
        if (self._shift_button != None):
            self._shift_button.remove_value_listener(self._shift_value)
        self._shift_button = button
        if (self._shift_button != None):
            self._shift_button.add_value_listener(self._shift_value)
        self.set_mode(0)



    def on_enabled_changed(self):
        if self.is_enabled():
            self.set_mode(int(self._shift_pressed))



    def number_of_modes(self):
        return 2



    def _shift_value(self, value):
        assert (self._shift_button != None)
        assert (value in range(128))
        self._shift_pressed = (value != 0)
        if self.is_enabled():
            self.set_mode(int(self._shift_pressed))



# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = ShiftableTransportComponent
# partial --== Decompile ==-- with fixes
import Live
from _Framework.TransportComponent import TransportComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.EncoderElement import EncoderElement #added

class ShiftableTransportComponent(TransportComponent):
    __doc__ = ' TransportComponent that only uses certain buttons if a shift button is pressed '
    def __init__(self):
        TransportComponent.__init__(self)
        self._shift_button = None
        self._pedal = None
        self._shift_pressed = False
        self._pedal_pressed = False #added
        self._quant_toggle_button = None
        self._last_quant_value = Live.Song.RecordingQuantization.rec_q_eight
        self.song().add_midi_recording_quantization_listener(self._on_quantisation_changed)
        self._on_quantisation_changed()
        self._undo_button = None #added from OpenLabs SpecialTransportComponent script
        self._redo_button = None #added from OpenLabs SpecialTransportComponent script
        self._bts_button = None #added from OpenLabs SpecialTransportComponent script
        self._tempo_encoder_control = None #new addition
        return None

    def disconnect(self):
        TransportComponent.disconnect(self)
        if self._shift_button != None:
            self._shift_button.remove_value_listener(self._shift_value)
            self._shift_button = None
        if self._quant_toggle_button != None:
            self._quant_toggle_button.remove_value_listener(self._quant_toggle_value)
            self._quant_toggle_button = None
        self.song().remove_midi_recording_quantization_listener(self._on_quantisation_changed)
        if (self._undo_button != None): #added from OpenLabs SpecialTransportComponent script
            self._undo_button.remove_value_listener(self._undo_value)
            self._undo_button = None
        if (self._redo_button != None): #added from OpenLabs SpecialTransportComponent script
            self._redo_button.remove_value_listener(self._redo_value)
            self._redo_button = None
        if (self._bts_button != None): #added from OpenLabs SpecialTransportComponent script
            self._bts_button.remove_value_listener(self._bts_value)
            self._bts_button = None
        if (self._tempo_encoder_control != None): #new addition
            self._tempo_encoder_control.remove_value_listener(self._tempo_encoder_value)
            self._tempo_encoder_control = None
        return None

    def set_shift_button(self, button):
        if not(button == None or isinstance(button, ButtonElement) and button.is_momentary()):
            isinstance(button, ButtonElement)
            raise AssertionError
        if self._shift_button != button:
            if self._shift_button != None:
                self._shift_button.remove_value_listener(self._shift_value)
            self._shift_button = button
            if self._shift_button != None:
                self._shift_button.add_value_listener(self._shift_value)
            #self._rebuild_callback()
            self.update()
        return None


    def set_pedal(self, pedal):
        if not(pedal == None or isinstance(pedal, ButtonElement) and pedal.is_momentary()):
            isinstance(pedal, ButtonElement)
            raise AssertionError
        if self._pedal != pedal:
            if self._pedal != None:
                self._pedal.remove_value_listener(self._pedal_value)
            self._pedal = pedal
            if self._pedal != None:
                self._pedal.add_value_listener(self._pedal_value)
            #self._rebuild_callback()
            self.update()
        return None

    def set_quant_toggle_button(self, button):
        if not(button == None or isinstance(button, ButtonElement) and button.is_momentary()):
            isinstance(button, ButtonElement)
            raise AssertionError
        if self._quant_toggle_button != button:
            if self._quant_toggle_button != None:
                self._quant_toggle_button.remove_value_listener(self._quant_toggle_value)
            self._quant_toggle_button = button
            if self._quant_toggle_button != None:
                self._quant_toggle_button.add_value_listener(self._quant_toggle_value)
            #self._rebuild_callback()
            self.update()
        return None

    def update(self):
        self._on_metronome_changed()
        self._on_overdub_changed()
        self._on_quantisation_changed()
        self._on_nudge_up_changed() #added
        self._on_nudge_down_changed #added

    def _shift_value(self, value):
        if not self._shift_button != None:
            raise AssertionError
        if not value in range(128):
            raise AssertionError
        self._shift_pressed = value != 0
        if self.is_enabled():
            self.is_enabled()
            self.update()
        else:
            self.is_enabled()
        return None

    def _pedal_value(self, value):
        if not self._pedal != None:
            raise AssertionError
        if not value in range(128):
            raise AssertionError

        if value == 127:
            self._pedal_pressed = False
        elif value == 0:
            self._pedal_pressed = True
        
        if self.is_enabled():
            self.is_enabled()
            self.update()
        else:
            self.is_enabled()
        return None

    def _metronome_value(self, value):
        if not self._shift_pressed:
        ##if self._shift_pressed: 
            TransportComponent._metronome_value(self, value)


    def _overdub_value(self, value):
        if not self._shift_pressed:
            TransportComponent._overdub_value(self, value)


    def _nudge_up_value(self, value): #added
        if not self._shift_pressed:
            TransportComponent._nudge_up_value(self, value)
            

    def _nudge_down_value(self, value): #added
        if not self._shift_pressed:
            TransportComponent._nudge_down_value(self, value)            
            
            
    def _tap_tempo_value(self, value): # Added as Shift + Tap Tempo
        if not self._shift_pressed:
        #if self._shift_pressed:
            TransportComponent._tap_tempo_value(self, value)


    def _quant_toggle_value(self, value):
        assert (self._quant_toggle_button != None)
        assert (value in range(128))
        assert (self._last_quant_value != Live.Song.RecordingQuantization.rec_q_no_q)
        if (self.is_enabled() and (not self._shift_pressed)):
            if ((value != 0) or (not self._quant_toggle_button.is_momentary())):
                quant_value = self.song().midi_recording_quantization
                if (quant_value != Live.Song.RecordingQuantization.rec_q_no_q):
                    self._last_quant_value = quant_value
                    self.song().midi_recording_quantization = Live.Song.RecordingQuantization.rec_q_no_q
                else:
                    self.song().midi_recording_quantization = self._last_quant_value


    def _on_metronome_changed(self):
        if not self._shift_pressed:
        #if self._shift_pressed:
            TransportComponent._on_metronome_changed(self)


    def _on_overdub_changed(self):
        if not self._shift_pressed:
            TransportComponent._on_overdub_changed(self)


    def _on_nudge_up_changed(self): #added
        if not self._shift_pressed:
            TransportComponent._on_nudge_up_changed(self)


    def _on_nudge_down_changed(self): #added
        if not self._shift_pressed:
            TransportComponent._on_nudge_down_changed(self)


    def _on_quantisation_changed(self):
        if self.is_enabled():
            quant_value = self.song().midi_recording_quantization
            quant_on = (quant_value != Live.Song.RecordingQuantization.rec_q_no_q)
            if quant_on:
                self._last_quant_value = quant_value
            if ((not self._shift_pressed) and (self._quant_toggle_button != None)):
                if quant_on:
                    self._quant_toggle_button.turn_on()
                else:
                    self._quant_toggle_button.turn_off()

    """ from OpenLabs module SpecialTransportComponent """
    
    def set_undo_button(self, undo_button):
        assert isinstance(undo_button, (ButtonElement,
                                        type(None)))
        if (undo_button != self._undo_button):
            if (self._undo_button != None):
                self._undo_button.remove_value_listener(self._undo_value)
            self._undo_button = undo_button
            if (self._undo_button != None):
                self._undo_button.add_value_listener(self._undo_value)
            self.update()



    def set_redo_button(self, redo_button):
        assert isinstance(redo_button, (ButtonElement,
                                        type(None)))
        if (redo_button != self._redo_button):
            if (self._redo_button != None):
                self._redo_button.remove_value_listener(self._redo_value)
            self._redo_button = redo_button
            if (self._redo_button != None):
                self._redo_button.add_value_listener(self._redo_value)
            self.update()


    def set_bts_button(self, bts_button): #"back to start" button
        assert isinstance(bts_button, (ButtonElement,
                                       type(None)))
        if (bts_button != self._bts_button):
            if (self._bts_button != None):
                self._bts_button.remove_value_listener(self._bts_value)
            self._bts_button = bts_button
            if (self._bts_button != None):
                self._bts_button.add_value_listener(self._bts_value)
            self.update()


    def _undo_value(self, value):
        if self._shift_pressed: #added
            assert (self._undo_button != None)
            assert (value in range(128))
            if self.is_enabled():
                if ((value != 0) or (not self._undo_button.is_momentary())):
                    if self.song().can_undo:
                        self.song().undo()


    def _redo_value(self, value):
        if self._shift_pressed: #added
            assert (self._redo_button != None)
            assert (value in range(128))
            if self.is_enabled():
                if ((value != 0) or (not self._redo_button.is_momentary())):
                    if self.song().can_redo:
                        self.song().redo()


    def _bts_value(self, value):
        assert (self._bts_button != None)
        assert (value in range(128))
        if self.is_enabled():
            if ((value != 0) or (not self._bts_button.is_momentary())):
                self.song().current_song_time = 0.0
     
        
    def _tempo_encoder_value(self, value):
        ##if not self._shift_pressed:
        if self._shift_pressed and not (self._pedal_pressed == True):
            assert (self._tempo_encoder_control != None)
            assert (value in range(128))
            backwards = (value >= 64)
            step = 0.1 #step = 1.0 #reduce this for finer control; 1.0 is 1 bpm
            if backwards:
                amount = (value - 128)
            else:
                amount = value
            tempo = max(20, min(999, (self.song().tempo + (amount * step))))
            self.song().tempo = tempo

            
        
    def set_tempo_encoder(self, control):
        assert ((control == None) or (isinstance(control, EncoderElement) and (control.message_map_mode() is Live.MidiMap.MapMode.relative_two_compliment)))
        if (self._tempo_encoder_control != None):
            self._tempo_encoder_control.remove_value_listener(self._tempo_encoder_value)
        self._tempo_encoder_control = control
        if (self._tempo_encoder_control != None):
            self._tempo_encoder_control.add_value_listener(self._tempo_encoder_value)
        self.update()

########NEW FILE########
__FILENAME__ = SliderModesComponent
# emacs-mode: -*- python-*-

import Live 
from _Framework.ModeSelectorComponent import ModeSelectorComponent 
from _Framework.ButtonElement import ButtonElement 
class SliderModesComponent(ModeSelectorComponent):
    ' SelectorComponent that assigns sliders to different functions '
    __module__ = __name__

    def __init__(self, mixer, sliders):
        assert (len(sliders) == 8)
        ModeSelectorComponent.__init__(self)
        self._mixer = mixer
        self._sliders = sliders
        self._mode_index = 0


    def disconnect(self):
        ModeSelectorComponent.disconnect(self)
        self._mixer = None
        self._sliders = None

        
    def set_mode_buttons(self, buttons):
        assert isinstance(buttons, (tuple,
         type(None)))
        for button in self._modes_buttons:
            button.remove_value_listener(self._mode_value)

        self._modes_buttons = []
        if (buttons != None):
            for button in buttons:
                assert isinstance(button, ButtonElement)
                identify_sender = True
                button.add_value_listener(self._mode_value, identify_sender)
                self._modes_buttons.append(button)

        self.update()
        
        
    def number_of_modes(self):
        return 8


    def update(self):
        if self.is_enabled():
            assert (self._mode_index in range(self.number_of_modes()))
            for index in range(len(self._modes_buttons)):
                if (index == self._mode_index):
                    self._modes_buttons[index].turn_on()
                else:
                    self._modes_buttons[index].turn_off()

            for index in range(len(self._sliders)):
                strip = self._mixer.channel_strip(index)
                slider = self._sliders[index]
                slider.use_default_message()
                slider.set_identifier((slider.message_identifier() - self._mode_index))
                strip.set_volume_control(None)
                strip.set_pan_control(None)
                strip.set_send_controls((None, None, None))
                slider.release_parameter()
                if (self._mode_index == 0):
                    strip.set_volume_control(slider)
                elif (self._mode_index == 1):
                    strip.set_pan_control(slider)
                elif (self._mode_index < 5):
                    send_controls = [None,
                     None,
                     None]
                    send_controls[(self._mode_index - 2)] = slider
                    strip.set_send_controls(tuple(send_controls))
                #self._rebuild_callback()


# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = SpecialChannelStripComponent
# emacs-mode: -*- python-*-
# -*- coding: utf-8 -*-

#import Live #added
from _Framework.ChannelStripComponent import ChannelStripComponent 
TRACK_FOLD_DELAY = 5
class SpecialChannelStripComponent(ChannelStripComponent):
    ' Subclass of channel strip component using select button for (un)folding tracks '
    __module__ = __name__

    def __init__(self):
        ChannelStripComponent.__init__(self)
        self._toggle_fold_ticks_delay = -1
        self._register_timer_callback(self._on_timer)


    def disconnect(self):
        self._unregister_timer_callback(self._on_timer)
        ChannelStripComponent.disconnect(self)


    def _select_value(self, value):
        ChannelStripComponent._select_value(self, value)
        if (self.is_enabled() and (self._track != None)):
            if (self._track.is_foldable and (self._select_button.is_momentary() and (value != 0))):
                self._toggle_fold_ticks_delay = TRACK_FOLD_DELAY
            else:
                self._toggle_fold_ticks_delay = -1


    def _on_timer(self):
        if (self.is_enabled() and (self._track != None)):
            if (self._toggle_fold_ticks_delay > -1):
                assert self._track.is_foldable
                if (self._toggle_fold_ticks_delay == 0):
                    self._track.fold_state = (not self._track.fold_state)
                self._toggle_fold_ticks_delay -= 1


# local variables:
# tab-width: 4
########NEW FILE########
__FILENAME__ = SpecialMixerComponent
# emacs-mode: -*- python-*-
# -*- coding: utf-8 -*-

from _Framework.MixerComponent import MixerComponent 
from SpecialChannelStripComponent import SpecialChannelStripComponent 
from _Framework.ButtonElement import ButtonElement #added
from _Framework.EncoderElement import EncoderElement #added    

class SpecialMixerComponent(MixerComponent):
    ' Special mixer class that uses return tracks alongside midi and audio tracks, and only maps prehear when not shifted '
    __module__ = __name__

    def __init__(self, parent, num_tracks):
        self._is_locked = False #added
        self._parent = parent #added
        MixerComponent.__init__(self, num_tracks)
        self._shift_button = None #added
        self._pedal = None
        self._shift_pressed = False #added
        self._pedal_pressed = False #added



    def disconnect(self): #added
        MixerComponent.disconnect(self)
        if (self._shift_button != None):
            self._shift_button.remove_value_listener(self._shift_value)
            self._shift_button = None
        if (self._pedal != None):
            self._pedal.remove_value_listener(self._pedal_value)
            self._pedal = None


    def set_shift_button(self, button): #added
        assert ((button == None) or (isinstance(button, ButtonElement) and button.is_momentary()))
        if (self._shift_button != button):
            if (self._shift_button != None):
                self._shift_button.remove_value_listener(self._shift_value)
            self._shift_button = button
            if (self._shift_button != None):
                self._shift_button.add_value_listener(self._shift_value)
            self.update()

    def set_pedal(self, pedal):
        assert ((pedal == None) or (isinstance(pedal, ButtonElement) and pedal.is_momentary()))
        if (self._pedal != pedal):
            if (self._pedal != None):
                self._pedal.remove_value_listener(self._pedal_value)
            self._pedal = pedal
            if (self._pedal != None):
                self._pedal.add_value_listener(self._pedal_value)
            self.update()


    def _shift_value(self, value): #added
        assert (self._shift_button != None)
        assert (value in range(128))
        self._shift_pressed = (value != 0)
        self.update()

    def _pedal_value(self, value): #added
        assert (self._pedal != None)
        assert (value in range(128))
        self._pedal_pressed = (value == 0)
        self.update()


    def on_selected_track_changed(self): #added override
        selected_track = self.song().view.selected_track
        if (self._selected_strip != None):
            if self._is_locked == False: #added
                self._selected_strip.set_track(selected_track)
        if self.is_enabled():
            if (self._next_track_button != None):
                if (selected_track != self.song().master_track):

                    self._next_track_button.turn_on()
                else:
                    self._next_track_button.turn_off()
            if (self._prev_track_button != None):
                if (selected_track != self.song().tracks[0]):
                    self._prev_track_button.turn_on()
                else:
                    self._prev_track_button.turn_off()        



    def update(self): #added override
        if self._allow_updates:
            master_track = self.song().master_track
            if self.is_enabled():
                if (self._prehear_volume_control != None):
                    #if self._shift_pressed: #added
                    if not self._shift_pressed and not self._pedal_pressed: #added 
                        self._prehear_volume_control.connect_to(master_track.mixer_device.cue_volume)
                    else:
                        self._prehear_volume_control.release_parameter() #added        
                if (self._crossfader_control != None):
                    self._crossfader_control.connect_to(master_track.mixer_device.crossfader)
            else:
                if (self._prehear_volume_control != None):
                    self._prehear_volume_control.release_parameter()
                if (self._crossfader_control != None):
                    self._crossfader_control.release_parameter()
                if (self._bank_up_button != None):
                    self._bank_up_button.turn_off()
                if (self._bank_down_button != None):
                    self._bank_down_button.turn_off()
                if (self._next_track_button != None):
                    self._next_track_button.turn_off()
                if (self._prev_track_button != None):
                    self._prev_track_button.turn_off()
            #self._rebuild_callback()
        else:
            self._update_requests += 1


    def tracks_to_use(self):
        return (self.song().visible_tracks + self.song().return_tracks)



    def _create_strip(self):
        return SpecialChannelStripComponent()


    def set_track_offset(self, new_offset): #added override
        MixerComponent.set_track_offset(self, new_offset)
        if self._parent._slider_modes != None:
            self._parent._slider_modes.update()
        if self._parent._encoder_modes != None:
            self._parent._encoder_modes.update()


# local variables:
# tab-width: 4

########NEW FILE########
__FILENAME__ = VUMeters
import Live
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.SessionComponent import SessionComponent 
import math


# Constants. Tweaking these would let us work with different grid sizes or different templates

#Index of the columns used for VU display
A_COL = [4]
B_COL = [5]
C_COL = [6]
D_COL = [7]
# Which channels we are monitoring for RMS
A_SOURCE = 0
B_SOURCE  = 1
C_SOURCE = 2
D_SOURCE  = 3

# Grid size
CLIP_GRID_X = 8
CLIP_GRID_Y = 5

# Velocity values for clip colours. Different on some devices
LED_RED = 3
LED_ON = 127
LED_OFF = 0
LED_ORANGE = 5

# Scaling constants. Narrows the db range we display to 0db-21db or thereabouts
CHANNEL_SCALE_MAX = 0.92
CHANNEL_SCALE_MIN = 0.52
CHANNEL_SCALE_INCREMENTS = 10

MASTER_SCALE_MAX = 0.92
MASTER_SCALE_MIN = 0.52
MASTER_SCALE_INCREMENTS = 5

RMS_FRAMES = 2
USE_RMS = True

class VUMeter():
  'represents a single VU to store RMS values etc in'
  def __init__(self, parent, track, top, bottom, 
              increments, vu_set, master = False):

    self.frames = [0.0] * RMS_FRAMES
    self.parent = parent
    self.track = track
    self.top = top
    self.bottom = bottom
    self.multiplier = self.calculate_multiplier(top, bottom, increments)
    self.current_level = 0
    self.matrix = self.setup_matrix(vu_set, master)
    self.master = master

  def observe(self):
    new_frame = self.mean_peak() 
    self.store_frame(new_frame)
    if self.master and new_frame >= 0.92:
      self.parent._clipping = True
      self.parent.clip_warning()
    else:

      if self.master and self.parent._clipping:
        self.parent._parent._session._change_offsets(0, 1) 
        self.parent._parent._session._change_offsets(0, -1) 


        self.parent._clipping = False

      if not self.parent._clipping:
        if USE_RMS:
          level = self.scale(self.rms(self.frames))
        else:
          level = self.scale(new_frame)
        if level != self.current_level:
          self.current_level = level
          if self.master:
            self.parent.set_master_leds(level)
          else:
            self.parent.set_leds(self.matrix, level) 

  def store_frame(self, frame):
    self.frames.pop(0)
    self.frames.append(frame)

  def rms(self, frames):
    return math.sqrt(sum(frame*frame for frame in frames)/len(frames))

  # return the mean of the L and R peak values
  def mean_peak(self):
    return (self.track.output_meter_left + self.track.output_meter_right) / 2


  # Perform the scaling as per params. We reduce the range, then round it out to integers
  def scale(self, value):
    if (value > self.top):
      value = self.top
    elif (value < self.bottom):
      value = self.bottom
    value = value - self.bottom
    value = value * self.multiplier #float, scale 0-10
    return int(round(value))
  
  def calculate_multiplier(self, top, bottom, increments):
    return (increments / (top - bottom))


  # Goes from top to bottom: so clip grid, then stop, then select, then activator/solo/arm
  def setup_matrix(self, vu_set, master):
    matrix = []
    if master:
      for scene in self.parent._parent._session._scenes:
        matrix.append(scene._launch_button)
    else:
      for index, column_index in enumerate(vu_set):
        matrix.append([])
        column = matrix[index]
        for row_index in range(CLIP_GRID_Y):
          column.append(self.parent._parent._button_rows[row_index][column_index])
        if master != True:
          strip = self.parent._parent._mixer.channel_strip(column_index)
          column.append(self.parent._parent._track_stop_buttons[column_index])
          column.extend([strip._select_button, strip._mute_button, strip._solo_button, strip._arm_button])
    return matrix


class VUMeters(ControlSurfaceComponent):
    'standalone class used to handle VU meters'

    def __init__(self, parent):
        # Boilerplate
        ControlSurfaceComponent.__init__(self)
        self._parent = parent

        # Default the L/R/Master levels to 0
        self._meter_level = 0
        self._a_level = 0
        self._b_level = 0
        self._c_level = 0
        self._d_level = 0

        # We don't start clipping
        self._clipping = False

        # The tracks we'll be pulling L and R RMS from
        self._a_track = self.song().tracks[A_SOURCE]
        self._b_track = self.song().tracks[B_SOURCE]
        self._c_track = self.song().tracks[C_SOURCE]
        self._d_track = self.song().tracks[D_SOURCE]
        
        #setup classes
        self.a_meter = VUMeter(self, self._a_track, 
                                  CHANNEL_SCALE_MAX, 
                                  CHANNEL_SCALE_MIN, CHANNEL_SCALE_INCREMENTS,
                                  A_COL)
        self.b_meter = VUMeter(self, self._b_track, 
                                  CHANNEL_SCALE_MAX, 
                                  CHANNEL_SCALE_MIN, CHANNEL_SCALE_INCREMENTS,
                                  B_COL)
        self.c_meter = VUMeter(self, self._c_track, 
                                  CHANNEL_SCALE_MAX, 
                                  CHANNEL_SCALE_MIN, CHANNEL_SCALE_INCREMENTS,
                                  C_COL)
        self.d_meter = VUMeter(self, self._d_track, 
                                  CHANNEL_SCALE_MAX, 
                                  CHANNEL_SCALE_MIN, CHANNEL_SCALE_INCREMENTS,
                                  D_COL)
        self.master_meter = VUMeter(self, self.song().master_track,
                                    MASTER_SCALE_MAX,
                                    MASTER_SCALE_MIN, MASTER_SCALE_INCREMENTS,
                                    None, True)
        # Listeners!
        self._a_track.add_output_meter_left_listener(self.a_meter.observe)
        self._b_track.add_output_meter_left_listener(self.b_meter.observe)
        self._c_track.add_output_meter_left_listener(self.c_meter.observe)
        self._d_track.add_output_meter_left_listener(self.d_meter.observe)

        self.song().master_track.add_output_meter_left_listener(self.master_meter.observe)

    # If you fail to kill the listeners on shutdown, Ableton stores them in memory and punches you in the face
    def disconnect(self):
        self._a_track.remove_output_meter_left_listener(self.a_meter.observe)
        self._b_track.remove_output_meter_left_listener(self.b_meter.observe)
        self._c_track.remove_output_meter_left_listener(self.c_meter.observe)
        self._d_track.remove_output_meter_left_listener(self.d_meter.observe)

        self.song().master_track.remove_output_meter_left_listener(self.master_meter.observe)

    # Called when the Master clips. Makes the entire clip grid BRIGHT RED 
    def clip_warning(self):
      for row_index in range(CLIP_GRID_Y):
        row = self._parent._button_rows[row_index]
        for button_index in range(CLIP_GRID_X):
          button = row[button_index]
          # Passing True to send_value forces it to happen even when the button in question is MIDI mapped
          button.send_value(LED_RED, True)

    def set_master_leds(self, level):
        for scene_index in range(CLIP_GRID_Y):
            scene = self._parent._session.scene(scene_index)
            if scene_index >= (CLIP_GRID_Y - level):
              scene._launch_button.send_value(LED_ON, True)
            else:
              scene._launch_button.send_value(LED_OFF, True)


    # Iterate through every column in the matrix, light up the LEDs based on the level
    # Level for channels is scaled to 10 cos we have 10 LEDs
    # Top two LEDs are red, the next is orange
    def set_leds(self, matrix, level):
        for column in matrix:
          for index in range(10):
            button = column[index] 
            if index >= (10 - level): 
              if index < 1:
                button.send_value(LED_RED, True)
              elif index < 2:
                button.send_value(LED_ORANGE, True)
              else:
                button.send_value(LED_ON, True)
            else:
              button.send_value(LED_OFF, True)

    # boilerplate
    def update(self):
        pass

    def on_enabled_changed(self):
        self.update()

    def on_selected_track_changed(self):
        self.update()

    def on_track_list_changed(self):
        self.update()

    def on_selected_scene_changed(self):
        self.update()

    def on_scene_list_changed(self):

        self.update()










########NEW FILE########
