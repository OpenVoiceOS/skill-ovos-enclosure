# Copyright 2019 j1nx - http://www.j1nx.nl.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import os
import sys

from mycroft.api import is_paired
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import LOG
from mycroft.util.parse import normalize
from mycroft.util import play_wav
from mycroft import intent_file_handler

class MycroftOS(MycroftSkill):
	"""
	The MycroftOS skill handles much of the screen and audio activities
	related to Mycroft's core functionality.
	"""
	def __init__(self):
		super().__init__('MycroftOS')
		self.skip_list = ('MycroftOS')
		self.loading = True
		self.airplay = self.settings.get("airplay")
		self.sshd = self.settings.get("sshd")

	def initialize(self):
		""" Perform initalization.
		Registers messagebus handlers.
		"""
		
		# Handle settings change
		self.settings_change_callback = self.on_websettings_changed
			
		try:
		
			# Handle the 'waking' visual
			self.add_event('recognizer_loop:wakeword',
					self.handle_listener_started)
			self.add_event('recognizer_loop:record_end',
					self.handle_listener_ended)
			self.add_event('mycroft.speech.recognition.unknown',
					self.handle_failed_stt)

			# Handle Device Ready
			self.bus.on('mycroft.ready', self.reset_screen)

			# Handle the 'busy' visual
			self.bus.on('mycroft.skill.handler.start',
					self.on_handler_started)
			self.bus.on('mycroft.skill.handler.complete',
					self.on_handler_complete)

			# Handle the 'speaking' visual
			self.bus.on('recognizer_loop:audio_output_start',
					self.on_handler_audio_start)
			self.bus.on('recognizer_loop:audio_output_end',
					self.on_handler_audio_end)

			# Handle volume setting via PulseAudio
			#self.add_event('mycroft.volume.set', self.on_volume_set)
			#self.add_event('mycroft.volume.get', self.on_volume_get)
			#self.add_event('mycroft.volume.duck', self.on_volume_duck)
			#self.add_event('mycroft.volume.unduck', self.on_volume_unduck)

			# Administrative messages
			self.bus.on("system.shutdown", self.on_shutdown)
			self.bus.on("system.reboot", self.on_reboot)

		except Exception:
			LOG.exception('In MycroftOS Skill')

	def on_websettings_changed(self):
		LOG.info('MycroftOS websettings changed')
		if self.sshd != self.settings.get("sshd"):
			if self.settings.get("sshd") is True:
				enable_ssh()
			else:
				disable_ssh()

		if self.airplay != self.settings.get("airplay"):
			LOG.info('Airplay settings changed')
			if self.settings.get("airplay") is True:
				LOG.info('Airplay is true')
				enable_airplay()
			else:
				LOG.info('Airplay is false')
				disable_airplay()
		else:
			LOG.info('Airplay settings not changed')

	# System volume
	#def on_volume_set(self, message):
	#	self.muted = False
	#	self.set_pulse_volume(vol)

	#def on_volume_get(self, message):
	#	self.bus.emit(message.response(data={'percent': self.volume, 'muted': self.muted}))

	#def on_volume_duck(self, message):
	#	self.muted = True
        #        call(['pactl', 'set-sink-mute', '0', '1'])

	#def on_volume_unduck(self, message):
	#	self.muted = False
	#	call(['pactl', 'set-sink-mute', '0', '0'])

	# Cleanup
	def shutdown(self):
		# Gotta clean up manually since not using add_event()
		self.bus.remove('mycroft.skill.handler.start',
				self.on_handler_started)
		self.bus.remove('mycroft.skill.handler.complete',
				self.on_handler_complete)
		self.bus.remove('recognizer_loop:audio_output_start',
				self.on_handler_audio_start)
		self.bus.remove('recognizer_loop:audio_output_end',
				self.on_handler_audio_end)

	# Handlers
	def on_handler_audio_start(self, message):
		self.speaking = True
		#framebuffer speaking visual
		os.system("fbv -f -d 1 /opt/mycroft/skills/mycroftos-enclosure-skill/ui/speaking.png > /dev/null 2>&1")

	def on_handler_audio_end(self, message):
		self.speaking = False
		#framebuffer background
		os.system("fbv -f -d 1 /opt/mycroft/skills/mycroftos-enclosure-skill/ui/background.png > /dev/null 2>&1")

	def on_handler_started(self, message):
		handler = message.data.get('handler', '')
		if self._skip_handler(handler):
			return
		#framebuffer thinking visual
		os.system("fbv -f -d 1 /opt/mycroft/skills/mycroftos-enclosure-skill/ui/thinking.png > /dev/null 2>&1")

	def on_handler_complete(self, message):
		handler = message.data.get('handler', '')
		if self._skip_handler(handler):
			return

		# If speaking has already begun, on_handler_audio_end will
		# turn off the framebuffer
		if not self.speaking:
			#framebuffer background
			os.system("fbv -f -d 1 /opt/mycroft/skills/mycroftos-enclosure-skill/ui/background.png > /dev/null 2>&1")

	def _skip_handler(self, handler):
		#Ignoring handlers from this skill
		return any(skip in handler for skip in self.skip_list)

	def handle_listener_started(self, message):
		#framebuffer listen visual
		os.system("fbv -f -d 1 /opt/mycroft/skills/mycroftos-enclosure-skill/ui/listen.png > /dev/null 2>&1")

	def handle_listener_ended(self, message):
		#framebuffer background
		os.system("fbv -f -d 1 /opt/mycroft/skills/mycroftos-enclosure-skill/ui/background.png > /dev/null 2>&1")

	def handle_failed_stt(self, message):
		#framebuffer background
		os.system("fbv -f -d 1 /opt/mycroft/skills/mycroftos-enclosure-skill/ui/background.png > /dev/null 2>&1")


	# Device is fully started
	def reset_screen(self, message):
		"""Triggered after skills are initialized."""
		self.loading = False
		if is_paired():
			os.system("fbv -f -d 1 /opt/mycroft/skills/mycroftos-enclosure-skill/ui/background.png > /dev/null 2>&1")
			self.speak_dialog('finished.booting')


	# System actions
	def on_shutdown(self, message):
		self.speak("Till next time")
		sleep(5)
		os.system("sudo halt")

	def on_reboot(self, message):
		self.speak("I'll be right back")
		sleep(5)
		os.system("sudo reboot")

	def enable_ssh(self, message):
		#os.system("sudo systemctl enable sshd.service")
		#os.system("sudo systemctl start sshd.service")
		self.settings["sshd"] = True
		self.sshd = True
	
	def disable_ssh(self, message):
		#os.system("sudo systemctl disable sshd.service")
		#os.system("sudo systemctl stop sshd.service")
		self.settings["sshd"] = False
		self.sshd = False
		
	def enable_airplay(self, message):
		LOG.info('Start of enable_airplay')
		os.system('sudo systemctl enable shairport-sync')
		os.system('sudo systemctl start shairport-sync')
		self.settings["airplay"] = True
		self.airplay = True
		LOG.info('Start of enable_airplay')
		
	def disable_airplay(self, message):
		os.system("sudo systemctl disable shairport-sync.service")
		os.system("sudo systemctl stop shairport-sync.service")
		self.settings["airplay"] = False
		self.airplay = False
		

	# Intent handlers
	@intent_file_handler("EnableSSH.intent")
	def on_enable_ssh(self, message):
		if self.sshd is False:
			self.enable_ssh()
			self.speak_dialog("EnabledSSH")
		else:
			self.speak_dialog("AlreadyEnabledSSH")

	@intent_file_handler("DisableSSH.intent")
	def on_disable_ssh(self, message):
		if self.sshd is True:
			self.disable_ssh()
			self.speak_dialog("DisabledSSH")
		else:
			self.speak_dialog("AlreadyDisabledSSH")

	@intent_file_handler("EnableAirPlay.intent")
	def on_enable_airplay(self, message):
		if self.airplay is False:
			self.enable_airplay()
			self.speak_dialog("EnabledAirPlay")
		else:
			self.speak_dialog("AlreadyEnabledAirPlay")

	@intent_file_handler("DisableAirPlay.intent")
	def on_disable_airplay(self, message):
		if self.airplay is True:
			self.disable_airplay()
			self.speak_dialog("DisabledAirPlay")
		else:
			self.speak_dialog("AlreadyDisabledAirPlay")

def create_skill():
	return MycroftOS()