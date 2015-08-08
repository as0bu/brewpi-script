# Copyright 2013 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time

import serial

try:
    import configobj
except ImportError:
    # TODO: change message below to match platform
    # import platform
    # platform.linux_distribution()
    # should return ('','','') for windows
    # example returns ('Fedora', '21', 'Twenty One')
    print "BrewPi requires ConfigObj to run, please install " \
          "it with 'sudo apt-get install python-configobj"
    sys.exit(1)

import auto_serial


def add_slash(path):
    """
    Adds a slash to the path, but only when it does not already have
    a slash at the end
    Params: a string
    Returns: a string
    """
    if not path.endswith('/'):
        path += '/'
    return path


def read_cfg_with_defaults(cfg):
    """
    Reads a config file with the default config file as fallback

    Params:
    cfg: string, path to cfg file
    defaultCfg: string, path to defaultConfig file.

    Returns:
    ConfigObj of settings
    """
    if not cfg:
        cfg = add_slash(sys.path[0]) + 'settings/config.cfg'

    default_cfg = script_path() + '/settings/defaults.cfg'
    config = configobj.ConfigObj(default_cfg)

    if cfg:
        try:
            user_config = configobj.ConfigObj(cfg)
            config.merge(user_config)
        except configobj.ParseError:
            log_message("ERROR: Could not parse user config file %s" % cfg)
        except IOError:
            log_message("Could not open user config file %s. Using only default config file" % cfg)
    return config


def configSet(configFile, settingName, value):
    if not os.path.isfile(configFile):
        log_message("User config file %s does not exist yet, creating it..." % configFile)
    try:
        config = configobj.ConfigObj(configFile)
        config[settingName] = value
        config.write()
    except IOError as e:
        log_message("I/O error(%d) while updating %s: %s " % (e.errno, configFile, e.strerror))
        log_message("Probably your permissions are not set correctly. " +
                   "To fix this, run 'sudo sh /home/brewpi/fixPermissions.sh'")
    return read_cfg_with_defaults(configFile)  # return updated ConfigObj


def log_message(message):
    """
    Prints a timestamped message to stderr
    """
    print >> sys.stderr, time.strftime("%b %d %Y %H:%M:%S   ") + message


def script_path():
    """
    Return the path of BrewPiUtil.py. __file__ only works in modules, not in the main script.
    That is why this function is needed.
    """
    return os.path.dirname(__file__)


def remove_dont_run_file(path='/var/www/do_not_run_brewpi'):
    if os.path.isfile(path):
        os.remove(path)
        if not sys.platform.startswith('win'):  # cron not available
            print "BrewPi script will restart automatically."
    else:
        print "File do_not_run_brewpi does not exist at " + path


def setup_serial(config, baud_rate=57600, time_out=0.1):
    ser = None
    dumpSerial = config.get('dumpSerial', False)

    error1 = None
    error2 = None
    # open serial port
    tries = 0
    log_message("Opening serial port")
    while tries < 10:
        error = ""
        for portSetting in [config['port'], config['altport']]:
            if portSetting is None or portSetting == 'None' or portSetting == "none":
                continue  # skip None setting
            if portSetting == "auto":
                port, devicetype = auto_serial.detect_port()
                if not port:
                    error = "Could not find compatible serial devices \n"
                    continue # continue with altport
            else:
                port = portSetting
            try:
                ser = serial.Serial(port, baudrate=baud_rate, timeout=time_out)
                if ser:
                    break
            except (IOError, OSError, serial.SerialException) as e:
                # error += '0}.\n({1})'.format(portSetting, str(e))
                error += str(e) + '\n'
        if ser:
            break
        tries += 1
        time.sleep(1)

    if ser:
        # discard everything in serial buffers
        ser.flushInput()
        ser.flushOutput()
    else:
         log_message("Errors while opening serial port: \n" + error)

    # yes this is monkey patching, but I don't see how to replace the
    # methods on a dynamically instantiated type any other way
    # TODO: (rbrady) change monkey patching to metaclass implementation
    if dumpSerial:
        ser.readOriginal = ser.read
        ser.writeOriginal = ser.write

        def readAndDump(size=1):
            r = ser.readOriginal(size)
            sys.stdout.write(r)
            return r

        def writeAndDump(data):
            ser.writeOriginal(data)
            sys.stderr.write(data)

        ser.read = readAndDump
        ser.write = writeAndDump

    return ser


# remove extended ascii characters from string, because they can raise UnicodeDecodeError later
def asciiToUnicode(s):
    s = s.replace(chr(0xB0), '&deg')
    return unicode(s, 'ascii', 'ignore')