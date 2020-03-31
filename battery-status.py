#!/usr/bin/env python3

from optparse import OptionParser, make_option
import os, sys, logging
import dbus, dbus.service, dbus.mainloop.glib
from gi.repository import GLib

mainloop = None

BUF_SIZE = 1024
HS_AG_SERVICE_CLASS_UUID = '00001112-0000-1000-8000-00805f9b34fb'

HF_NREC			= 0x0001
HF_3WAY			= 0x0002
HF_CLI			= 0x0004
HF_VOICE_RECOGNITION	= 0x0008
HF_REMOTE_VOL		= 0x0010
HF_ENHANCED_STATUS	= 0x0020
HF_ENHANCED_CONTROL	= 0x0040
HF_CODEC_NEGOTIATION	= 0x0080

HF_FEATURES = (HF_CLI | HF_REMOTE_VOL)

class HfpConnection:
	fd = None
	io_id = 0
	version = 0
	pending = None
	batt_device = None

	def disconnect(self):
		if (self.fd >= 0):
			os.close(self.fd)
			self.fd = -1
			GLib.source_remove(self.io_id)
			self.io_id = 0

	def io_cb(self, fd, cond):
		buf = os.read(fd, BUF_SIZE)
		buf = buf.strip()

		logging.debug("Received: %s" % (buf))

		if (buf == "OK" or buf == "ERROR"):
			return True

		self.send_cmd(b"OK")

		if b"IPHONEACCEV" in buf:
			parts = buf[buf.index(b',') + 1: -1].split(b',')
			if len(parts) < 1 or (len(parts) % 2) != 0:
				return True
			i = 0
			while i < len(parts):
				key = int(parts[i])
				val = int(parts[i + 1])
				if key == 1:
					blevel = (val + 1) * 10
					logging.info("Battery level is %s%%", blevel)
					return False
				i += 2

		return True

	def send_cmd(self, cmd):
		logging.debug("Sending: %s" % (cmd))

		os.write(self.fd, b"\r\n" + cmd + b"\r\n")

	def __init__(self, fd, version, features):
		self.fd = fd
		self.version = version

		logging.debug("Version 0x%04x Features 0x%04x" % (version, features))
		
		self.io_id = GLib.io_add_watch(fd, GLib.IO_IN, self.io_cb)
		#self.send_cmd("AT+CIND: (\"battchg\",(0-5))")


class HfpProfile(dbus.service.Object):
	io_id = 0
	conns = {}

	def __init__(self, bus, path):
		dbus.service.Object.__init__(self, bus, path)

	@dbus.service.method("org.bluez.Profile1", in_signature="", out_signature="")
	def Release(self):
		logging.debug("Release")
		mainloop.quit()

	@dbus.service.method("org.bluez.Profile1", in_signature="", out_signature="")
	def Cancel(self):
		logging.debug("Cancel")

	@dbus.service.method("org.bluez.Profile1", in_signature="o", out_signature="")
	def RequestDisconnection(self, path):
		conn = self.conns.pop(path)
		conn.disconnect()
		logging.debug("Disconnected")

	@dbus.service.method("org.bluez.Profile1", in_signature="oha{sv}", out_signature="")
	def NewConnection(self, path, fd, properties):
		fd = fd.take()
		version = 0x0105
		features = 0
		logging.debug("NewConnection(%s, %d)" % (path, fd))
		for key in properties.keys():
			if key == "Version":
				version = properties[key]
			elif key == "Features":
				features = properties[key]

		conn = HfpConnection(fd, version, features)

		self.conns[path] = conn

if __name__ == '__main__':
	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

	bus = dbus.SystemBus()
	manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")

	option_list = [
			make_option("-p", "--path", action="store",
					type="string", dest="path",
					default="/bluez/hfp/battery"),
			make_option("-n", "--name", action="store",
					type="string", dest="name",
					default=None),
			make_option("-C", "--channel", action="store",
					type="int", dest="channel",
					default=None),
			make_option("-d", "--debug", action="store_true", dest="debug",
					default=False),
			]

	parser = OptionParser(option_list=option_list)
	(options, args) = parser.parse_args()

	if options.debug:
		logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
	else:
		logging.basicConfig(level=logging.INFO, format='%(message)s')

	mainloop = GLib.MainLoop()

	opts = {
			"AutoConnect" : True,
		}

	if (options.name):
		opts["Name"] = options.name

	if (options.channel is not None):
		opts["Channel"] = dbus.UInt16(options.channel)

	profile = HfpProfile(bus, options.path)
	manager.RegisterProfile(options.path, HS_AG_SERVICE_CLASS_UUID, opts)

	logging.debug("Profile registered - waiting for connections")
	mainloop.run()
