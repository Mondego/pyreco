__FILENAME__ = antidbg_devices
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class AntiDBGDevices(Signature):
    name = "antidbg_devices"
    description = "Checks for the presence of known devices from debuggers and forensic tools"
    severity = 3
    categories = ["anti-debug"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        indicators = [
            ".*SICE$",
            ".*SIWVID$",
            ".*SIWDEBUG$",
            ".*NTICE$",
            ".*REGVXG$",
            ".*FILEVXG$",
            ".*REGSYS$",
            ".*FILEM$",
            ".*TRW$",
            ".*ICEXT$"
        ]

        for indicator in indicators:
            if self.check_file(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = antidbg_windows
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class AntiDBGWindows(Signature):
    name = "antidbg_windows"
    description = "Checks for the presence of known windows from debuggers and forensic tools"
    severity = 3
    categories = ["anti-debug"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        indicators = [
            "OLLYDBG",
            "WinDbgFrameClass",
            "pediy06",
            "GBDYLLO",
            "FilemonClass",
            "PROCMON_WINDOW_CLASS",
            "File Monitor - Sysinternals: www.sysinternals.com",
            "Process Monitor - Sysinternals: www.sysinternals.com",
        ]

        for indicator in indicators:
            if self.check_argument_call(call, pattern=indicator, category="windows"):
                self.data.append({"window" : indicator})
                return True

########NEW FILE########
__FILENAME__ = antiemu_wine
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class WineDetect(Signature):
    name = "antiemu_wine"
    description = "Detects the presence of Wine emulator"
    severity = 3
    categories = ["anti-emulation"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        return self.check_key(pattern="HKEY_CURRENT_USER\\Software\\Wine")

########NEW FILE########
__FILENAME__ = antisandbox_mouse_hook
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class HookMouse(Signature):
    name = "antisandbox_mouse_hook"
    description = "Installs an hook procedure to monitor for mouse events"
    severity = 3
    categories = ["hooking", "anti-sandbox"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        if not call["api"].startswith("SetWindowsHookEx"):
            return

        if int(self.get_argument(call, "HookIdentifier")) in [7, 14]:
            if int(self.get_argument(call, "ThreadId")) == 0:
                return True

########NEW FILE########
__FILENAME__ = antisandbox_productid
# Copyright (C) 2013 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class GetProductID(Signature):
    name = "antisandbox_productid"
    description = "Retrieves Windows ProductID, probably to fingerprint the sandbox"
    severity = 3
    categories = ["anti-sandbox"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        if not call["api"].startswith("RegQueryValueEx"):
            return

        if self.get_argument(call, "ValueName") == "ProductId":
            return True

########NEW FILE########
__FILENAME__ = antivirus_virustotal
# Copyright (C) 2012 Michael Boman (@mboman)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class KnownVirustotal(Signature):
    name = "antivirus_virustotal"
    description = "File has been identified by at least one AntiVirus on VirusTotal as malicious"
    severity = 2
    categories = ["antivirus"]
    authors = ["Michael Boman", "nex"]
    minimum = "0.5"

    def run(self):
        if "virustotal" in self.results:
            if "positives" in self.results["virustotal"]:
                if self.results["virustotal"]["positives"] > 0:
                    return True

        return False

########NEW FILE########
__FILENAME__ = antivm_generic_bios
# Copyright (C) 2013 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class AntiVMBios(Signature):
    name = "antivm_generic_bios"
    description = "Checks the version of Bios, possibly for anti-virtualization"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        #if self.check_key(pattern="HKEY_LOCAL_MACHINE\\HARDWARE\\DESCRIPTION\\System"):
        if (self.check_argument_call(call, pattern="SystemBiosVersion", name="ValueName", category="registry") or
            self.check_argument_call(call, pattern="VideoBiosVersion", name="ValueName", category="registry")):
            return True

########NEW FILE########
__FILENAME__ = antivm_generic_disk
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class DiskInformation(Signature):
    name = "antivm_generic_disk"
    description = "Queries information on disks, possibly for anti-virtualization"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.lastprocess = None

    def on_call(self, call, process):
        indicators = [
            "scsi0",
            "physicaldrive0"
        ]

        ioctls = [
            "2954240", # IOCTL_STORAGE_QUERY_PROPERTY
            "458752", # IOCTL_DISK_GET_DRIVE_GEOMETRY
            "315400" #IOCTL_SCSI_MINIPORT
        ]

        if process is not self.lastprocess:
            self.handle = None
            self.lastprocess = process

        if not self.handle:
            if call["api"] == "NtCreateFile":
                file_name = self.get_argument(call, "FileName")
                for indicator in indicators:
                    if indicator in file_name.lower():
                        self.handle = self.get_argument(call, "FileHandle")
        else:
            if call["api"] == "DeviceIoControl":
                if self.get_argument(call, "DeviceHandle") == self.handle:
                    if str(self.get_argument(call, "IoControlCode")) in ioctls:
                        return True

########NEW FILE########
__FILENAME__ = antivm_generic_ide
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class AntiVMIDE(Signature):
    name = "antivm_generic_ide"
    description = "Checks the presence of IDE drives in the registry, possibly for anti-virtualization"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        return self.check_key(pattern=".*\\\\SYSTEM\\\\CurrentControlSet\\\\Enum\\\\IDE$",
                              regex=True)

########NEW FILE########
__FILENAME__ = antivm_generic_scsi
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class AntiVMSCSI(Signature):
    name = "antivm_generic_scsi"
    description = "Detects virtualization software with SCSI Disk Identifier trick"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.lastprocess = None

    def on_call(self, call, process):
        indicator_registry = "0x80000002"
        indicator_key = "HARDWARE\\DEVICEMAP\\Scsi\\Scsi Port 0\\Scsi Bus 0\\Target Id 0\\Logical Unit Id 0"
        indicator_name = "Identifier"

        if process is not self.lastprocess:
            self.handle = ""
            self.opened = False
            self.lastprocess = process

        # First I check if the malware opens the releavant registry key.
        if call["api"].startswith("RegOpenKeyEx"):
            # Store the number of arguments matched.
            args_matched = 0
            # Store the handle used to open the key.
            self.handle = ""
            # Check if the registry is HKEY_LOCAL_MACHINE.
            if self.get_argument(call,"Registry") == indicator_registry:
                args_matched += 1
            # Check if the subkey opened is the correct one.
            if self.get_argument(call,"SubKey") == indicator_key:
                args_matched += 1

            # If both arguments are matched, I consider the key to be successfully opened.
            if args_matched == 2:
                self.opened = True
                # Store the generated handle.
                self.handle = self.get_argument(call,"Handle")
        # Now I check if the malware verified the value of the key.
        if call["api"].startswith("RegQueryValueEx"):
            # Verify if the key was actually opened.
            if not self.opened:
                return

            # Verify the arguments.
            args_matched = 0
            if self.get_argument(call,"Handle") == self.handle:
                args_matched += 1
            if self.get_argument(call,"ValueName") == indicator_name:
                args_matched += 1

            # Finally, if everything went well, I consider the signature as matched.
            if args_matched == 2:
                return True

########NEW FILE########
__FILENAME__ = antivm_generic_services
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class AntiVMServices(Signature):
    name = "antivm_generic_services"
    description = "Enumerates services, possibly for anti-virtualization"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.lastprocess = None

    def on_call(self, call, process):
        if call["api"].startswith("EnumServicesStatus"):
            return True
            
        if process is not self.lastprocess:
            self.handle = None
            self.lastprocess = process

        if not self.handle:
            if call["api"].startswith("RegOpenKeyEx"):
                correct = False
                if self.get_argument(call,"SubKey") == "SYSTEM\\ControlSet001\\Services":
                    correct = True
                else:
                    self.handle = self.get_argument(call,"Handle")

                if not correct:
                    self.handle = None
        else:
            if call["api"].startswith("RegEnumKeyEx"):
                if self.get_argument(call,"Handle") == self.handle:
                    return True

########NEW FILE########
__FILENAME__ = antivm_vbox_acpi
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class VBoxDetectACPI(Signature):
    name = "antivm_vbox_acpi"
    description = "Detects VirtualBox using ACPI tricks"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.lastprocess = None

    def on_call(self, call, process):
        if process is not self.lastprocess:
            self.opened = False
            self.handle = ""
            self.lastprocess = process

        # First I check if the malware opens the releavant registry key.
        if call["api"].startswith("RegOpenKeyEx"):
            # Store the number of arguments matched.
            args_matched = 0
            # Store the handle used to open the key.
            self.handle = ""
            # Check if the registry is HKEY_LOCAL_MACHINE.
            if self.get_argument(call,"Registry") == "0x80000002":
                args_matched += 1
            # Check if the subkey opened is the correct one.
            elif self.get_argument(call,"SubKey")[:14].upper() == "HARDWARE\\ACPI\\":
                # Since it could appear under different paths, check for all of them.
                if self.get_argument(call,"SubKey")[14:18] in ["DSDT", "FADT", "RSDT"]:
                    if self.get_argument(call,"SubKey")[18:] == "\\VBOX__":
                        return True
                    else:
                        args_matched += 1
            # Store the generated handle.
            else:
                self.handle = self.get_argument(call,"Handle")
            
            # If both arguments are matched, I consider the key to be successfully opened.
            if args_matched == 2:
                self.opened = True
        # Now I check if the malware verified the value of the key.
        elif call["api"].startswith("RegEnumKeyEx"):
            # Verify if the key was actually opened.
            if not self.opened:
                return

            # Verify the arguments.
            args_matched = 0
            if self.get_argument(call,"Handle") == self.handle:
                args_matched += 1
            elif self.get_argument(call,"Name") == "VBOX__":
                args_matched += 1

            # Finally, if everything went well, I consider the signature as matched.
            if args_matched == 2:
                return True

########NEW FILE########
__FILENAME__ = antivm_vbox_devices
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class VBoxDetectDevices(Signature):
    name = "antivm_vbox_devices"
    description = "Detects VirtualBox through the presence of a device"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        indicators = [
            "\\Device\\VBoxGuest",
            "\\Device\\VBoxMouse",
            "\\Device\\VBoxVideo",
            "\\\\.\\VBoxMiniRdrDN",
            "\\\\.\\pipe\\VBoxMiniRdDN",
            "\\\\.\\VBoxTrayIPC",
            "\\\\.\\pipe\\VBoxTrayIPC"
        ]

        for indicator in indicators:
            if self.check_file(pattern=indicator):
                return True

        return False

########NEW FILE########
__FILENAME__ = antivm_vbox_files
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class VBoxDetectFiles(Signature):
    name = "antivm_vbox_files"
    description = "Detects VirtualBox through the presence of a file"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        indicators = [
            ".*VBoxDisp\.dll$",
            ".*VBoxHook\.dll$",
            ".*VBoxMRXNP\.dll$",
            ".*VBoxOGL\.dll$",
            ".*VBoxOGLarrayspu\.dll$",
            ".*VBoxOGLcrutil\.dll$",
            ".*VBoxOGLerrorspu\.dll$",
            ".*VBoxOGLfeedbackspu\.dll$",
            ".*VBoxOGLpackspu\.dll$",
            ".*VBoxOGLpassthroughspu\.dll$"
            ".*VBoxDisp\.dll$",
            ".*VBoxSF\.sys$",
            ".*VBoxControl\.exe$",
            ".*VBoxService\.exe$",
            ".*VBoxTray\.exe$",
            ".*VBoxDrvInst\.exe$",
            ".*VBoxWHQLFake\.exe$",
            ".*VBoxGuest\.[a-zA-Z]{3}$",
            ".*VBoxMouse\.[a-zA-Z]{3}$",
            ".*VBoxVideo\.[a-zA-Z]{3}$"
        ]

        for indicator in indicators:
            if self.check_file(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = antivm_vbox_keys
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class VBoxDetectKeys(Signature):
    name = "antivm_vbox_keys"
    description = "Detects VirtualBox through the presence of a registry key"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        return self.check_key(pattern=".*\\\\SOFTWARE\\\\Oracle\\\\VirtualBox\\ Guest\\ Additions$",
                              regex=True)

########NEW FILE########
__FILENAME__ = antivm_vbox_libs
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class VBoxDetectLibs(Signature):
    name = "antivm_vbox_libs"
    description = "Detects VirtualBox through the presence of a library"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        indicators = [
            "VBoxDisp.dll",
            "VBoxHook.dll",
            "VBoxMRXNP.dll",
            "VBoxOGL.dll",
            "VBoxOGLarrayspu.dll",
            "VBoxOGLcrutil.dll",
            "VBoxOGLerrorspu.dll",
            "VBoxOGLfeedbackspu.dll",
            "VBoxOGLpackspu.dll",
            "VBoxOGLpassthroughspu.dll"
        ]

        for indicator in indicators:
            if self.check_argument_call(call,
                                        pattern=indicator,
                                        name="FileName",
                                        api="LdrLoadDll"):
                return True

########NEW FILE########
__FILENAME__ = antivm_vbox_window
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class VBoxDetectWindow(Signature):
    name = "antivm_vbox_window"
    description = "Detects VirtualBox through the presence of a window"
    severity = 3
    categories = ["anti-vm"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        indicators = [
            "VBoxTrayToolWndClass",
            "VBoxTrayToolWnd"
        ]

        for indicator in indicators:
            if self.check_argument_call(call, pattern=indicator, category="window"):
                self.data.append({"window" : indicator})
                return True

########NEW FILE########
__FILENAME__ = banker_cridex
# Copyright (C) 2014 Robby Zeitfuchs (@robbyFux)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class Cridex(Signature):
    name = "banker_cridex"
    description = "Cridex banking trojan"
    severity = 3
    alert = True
    categories = ["Banking", "Trojan"]
    families = ["Cridex"]
    authors = ["Robby Zeitfuchs", "@robbyFux"]
    minimum = "0.5"
    references = ["http://stopmalvertising.com/rootkits/analysis-of-cridex.html",
                  "http://sempersecurus.blogspot.de/2012/08/cridex-analysis-using-volatility.html",
                  "http://labs.m86security.com/2012/03/the-cridex-trojan-targets-137-financial-organizations-in-one-go/",
                  "https://malwr.com/analysis/NDU2ZWJjZTIwYmRiNGVmNWI3MDUyMGExMGQ0MmVhYTY/",
                  "https://malwr.com/analysis/MTA5YmU4NmIwMjg5NDAxYjlhYzZiZGIwYjZkOTFkOWY/"]

    def run(self):
        indicators = [".*Local.QM.*",
                      ".*Local.XM.*"]
                      
        match_file = self.check_file(pattern=".*\\KB[0-9]{8}\.exe", regex=True)
        match_batch_file = self.check_file(pattern=".*\\\\Temp\\\\\S{4}\.tmp\.bat", regex=True)

        if match_file and match_batch_file:
            self.data.append({"file": match_file})
            self.data.append({"batchfile": match_batch_file})
            for indicator in indicators:
                match_mutex = self.check_mutex(pattern=indicator, regex=True)
                if match_mutex:
                    self.data.append({"mutex": match_mutex})
                    return True

        return False

########NEW FILE########
__FILENAME__ = banker_prinimalka
# Copyright (C) 2013 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class Prinimalka(Signature):
    name = "banker_prinimalka"
    description = "Detected Prinimalka banking trojan"
    severity = 3
    categories = ["banker"]
    families = ["prinimalka"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        if call["api"].startswith("RegSetValueEx"):
            if self.get_argument(call, "ValueName").endswith("_opt_server1"):
                server = self.get_argument(call, "Buffer").rstrip("\\x00")
                self.description += " (C&C: {0})".format(server)
                return True

########NEW FILE########
__FILENAME__ = banker_spyeye_mutex
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class SpyEyeMutexes(Signature):
    name = "banker_spyeye_mutexes"
    description = "Creates known SpyEye mutexes"
    severity = 3
    categories = ["banker"]
    families = ["spyeye"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        indicators = [
            "zXeRY3a_PtW.*",
            "SPYNET",
            "__CLEANSWEEP__",
            "__CLEANSWEEP_UNINSTALL__",
            "__CLEANSWEEP_RELOADCFG__"
        ]

        for indicator in indicators:
            if self.check_mutex(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = banker_zeus_mutex
# Copyright (C) 2014 Robby Zeitfuchs (@robbyFux)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class ZeusMutexes(Signature):
    name = "banker_zeus_mutex"
    description = "Creates Zeus (Banking Trojan) mutexes"
    severity = 3
    categories = ["banker"]
    families = ["zeus"]
    authors = ["Robby Zeitfuchs"]
    minimum = "0.5"
    references = ["https://malwr.com/analysis/NmNhODg5ZWRkYjc0NDY0M2I3YTJhNDRlM2FlOTZiMjA/#summary_mutexes", 
                  "https://malwr.com/analysis/MmMwNDJlMTI0MTNkNGFjNmE0OGY3Y2I5MjhiMGI1NzI/#summary_mutexes",
                  "https://malwr.com/analysis/MzY5ZTM2NzZhMzI3NDY2YjgzMjJiODFkODZkYzIwYmQ/#summary_mutexes",
                  "https://www.virustotal.com/de/file/301fcadf53e6a6167e559c84d6426960af8626d12b2e25aa41de6dce511d0568/analysis/#behavioural-info",
                  "https://www.virustotal.com/de/file/d3cf49a7ac726ee27eae9d29dee648e34cb3e8fd9d494e1b347209677d62cdf9/analysis/#behavioural-info",
                  "https://www.virustotal.com/de/file/d3cf49a7ac726ee27eae9d29dee648e34cb3e8fd9d494e1b347209677d62cdf9/analysis/#behavioural-info",
                  "https://www.virustotal.com/de/file/301fcadf53e6a6167e559c84d6426960af8626d12b2e25aa41de6dce511d0568/analysis/#behavioural-info"]

    def run(self):
        indicators = [
            "_AVIRA_.*",                                
            "__SYSTEM__.*",                        
            "_LILO_.*",                                   
            "_SOSI_.*",                                  
            ".*MSIdent Logon",                            
            ".*MPSWabDataAccessMutex",                    
            ".*MPSWABOlkStoreNotifyMutex"
        ]
            
        for indicator in indicators:
            match = self.check_mutex(pattern=indicator, regex=True)
            if match:
                self.data.append({"mutex": match})
                return True            
        
        return False

########NEW FILE########
__FILENAME__ = banker_zeus_p2p
# Copyright (C) 2014 Robby Zeitfuchs (@robbyFux)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
from lib.cuckoo.common.abstracts import Signature

class ZeusP2P(Signature):
    name = "banker_zeus_p2p"
    description = "Zeus P2P (Banking Trojan)"
    severity = 3
    categories = ["banker"]
    families = ["zeus"]
    authors = ["Robby Zeitfuchs"]
    minimum = "0.5"
    references = ["https://malwr.com/analysis/NmNhODg5ZWRkYjc0NDY0M2I3YTJhNDRlM2FlOTZiMjA/", 
                  "https://malwr.com/analysis/MmMwNDJlMTI0MTNkNGFjNmE0OGY3Y2I5MjhiMGI1NzI/",
                  "https://malwr.com/analysis/MzY5ZTM2NzZhMzI3NDY2YjgzMjJiODFkODZkYzIwYmQ/",
                  "https://www.virustotal.com/de/file/301fcadf53e6a6167e559c84d6426960af8626d12b2e25aa41de6dce511d0568/analysis/#behavioural-info",
                  "https://www.virustotal.com/de/file/d3cf49a7ac726ee27eae9d29dee648e34cb3e8fd9d494e1b347209677d62cdf9/analysis/#behavioural-info",
                  "https://www.virustotal.com/de/file/d3cf49a7ac726ee27eae9d29dee648e34cb3e8fd9d494e1b347209677d62cdf9/analysis/#behavioural-info",
                  "https://www.virustotal.com/de/file/301fcadf53e6a6167e559c84d6426960af8626d12b2e25aa41de6dce511d0568/analysis/#behavioural-info"]

    def run(self):
        # Check zeus synchronization-mutex.
        # Regexp pattern for zeus synchronization-mutex such as for example:
        # 2CCB0BFE-ECAB-89CD-0261-B06D1C10937F
        exp = re.compile(".*[A-Z0-9]{8}-([A-Z0-9]{4}-){3}[A-Z0-9]{12}", re.IGNORECASE)
        mutexes = self.results["behavior"]["summary"]["mutexes"]
        
        count = 0
        for mutex in mutexes:
            if exp.match(mutex):  
                self.data.append({"mutex": mutex})
                count += 1 

        # Check if there are at least 5 mutexes opened matching the pattern?   
        if count < 5:
            return False
        
        # Check for UDP Traffic on remote port greater than 1024.
        # TODO: this might be faulty without checking whether the destination
        # IP is really valid.
        count = 0
        if "network" in self.results:
            for udp in self.results["network"]["udp"]:
                if udp["dport"] > 1024:
                    count += 1
            
        if count < 4:
            return False
    
        return True

########NEW FILE########
__FILENAME__ = banker_zeus_url
# Copyright (C) 2014 Robby Zeitfuchs (@robbyFux)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class ZeusURL(Signature):
    name = "banker_zeus_url"
    description = "Contacts C&C server HTTP check-in (Banking Trojan)"
    severity = 3
    categories = ["banker"]
    authors = ["Robby Zeitfuchs"]
    minimum = "0.5"
    references = ["https://zeustracker.abuse.ch/blocklist.php?download=compromised"]

    def run(self):
        indicators = [
            ".*\/config\.bin",                                  
            ".*\/gate\.php",                               
            ".*\/cfg\.bin",                                   
        ]

        for indicator in indicators:
            match = self.check_url(pattern=indicator, regex=True)
            if match:
                self.data.append({"url": match})
                return True
        
        return False

########NEW FILE########
__FILENAME__ = bitcoin_opencl
# Copyright (C) 2013 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class BitcoinOpenCL(Signature):
    name = "bitcoin_opencl"
    description = "Installs OpenCL library, probably to mine Bitcoins"
    severity = 2
    categories = ["bitcoin"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        if self.check_file(pattern=".*OpenCL\.dll$", regex=True):
            return True

        return False

########NEW FILE########
__FILENAME__ = bot_athenahttp
# Copyright (C) 2014 jjones
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
from lib.cuckoo.common.abstracts import Signature

class AthenaHttp(Signature):
    name = "bot_athenahttp"
    description = "Recognized to be an Athena HTTP bot"
    severity = 3
    categories = ["bot", "ddos"]
    families = ["athenahttp"]
    authors = ["jjones", "nex"]
    minimum = "0.5"

    def run(self):
        indicators = [
            "UPDATE__",
            "MAIN_.*",
            "BACKUP_.*"
        ]

        count = 0
        for indicator in indicators:
            if self.check_mutex(pattern=indicator, regex=True):
                count += 1

        if count == len(indicators):
            return True

        athena_http_re = re.compile("a=(%[A-Fa-f0-9]{2})+&b=[-A-Za-z0-9+/]+(%3[dD])*&c=(%[A-Fa-f0-9]{2})+")

        if "network" in self.results:
            for http in self.results["network"]["http"]:
                if http["method"] == "POST" and athena_http_re.search(http["body"]):
                    self.data.append({"url" : http["uri"], "data" : http["body"]})
                    return True

        return False

########NEW FILE########
__FILENAME__ = bot_dirtjumper
# Copyright (C) 2012-2014 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class DirtJumper(Signature):
    name = "bot_dirtjumper"
    description = "Recognized to be a DirtJumper bot"
    severity = 3
    categories = ["bot", "ddos"]
    families = ["dirtjumper"]
    authors = ["nex","jjones"]
    minimum = "0.5"

    def run(self):
        if "network" in self.results:
            for http in self.results["network"]["http"]:
                if http["method"] == "POST" and http["body"].startswith("k=") and http.get("user-agent", "") == "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US)":
                    self.data.append({"url" : http["uri"], "data" : http["body"]})
                    return True

        return False

########NEW FILE########
__FILENAME__ = bot_drive
# Copyright (C) 2014 jjones
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
from lib.cuckoo.common.abstracts import Signature

class Drive(Signature):
    name = "bot_drive"
    description = "Recognized to be a Drive bot"
    severity = 3
    categories = ["bot", "ddos"]
    families = ["drive"]
    authors = ["jjones", "nex"]
    minimum = "0.5"

    def run(self):
        drive_ua_re = re.compile("Mozilla/5.0 \(Windows NT [56].1; (WOW64; )?rv:(9|1[0-7]).0\) Gecko/20100101 Firefox/(9|1[0-7]).0|Mozilla/4.0 \(compatible; MSIE 8.0; Windows NT [56].1; (WOW64; )?Trident/4.0; SLCC2; .NET CLR 2.0.[0-9]{6}; .NET CLR 3.5.[0-9]{6}; .NET CLR 3.0.[0-9]{6}|Opera/9.80 \(Windows NT [56].1; (WOW64; )?U; Edition [a-zA-Z]+ Local; ru\) Presto/2.10.289 Version/([5-9]|1[0-2]).0[0-9]")

        if "network" in self.results:
            for http in self.results["network"]["http"]:
                if http["method"] == "POST" and http["body"].startswith("k=") and drive_ua_re.search(http.get("user-agent", "")):
                    self.data.append({"url" : http["uri"], "data" : http["body"]})
                    return True

        return False

########NEW FILE########
__FILENAME__ = bot_drive2
# Copyright (C) 2014 jjones
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
from lib.cuckoo.common.abstracts import Signature

class Drive2(Signature):
    name = "bot_drive2"
    description = "Recognized to be a Drive2 bot"
    severity = 3
    categories = ["bot", "ddos"]
    families = ["drive2"]
    authors = ["jjones", "nex"]
    minimum = "0.5"

    def run(self):
        regexp = "Mozilla/5.0 \(Windows NT [56].1; (WOW64; )?rv:(9|1[0-7]).0\) " \
                 "Gecko/20100101 Firefox/(9|1[0-7]).0|Mozilla/4.0 \(compatible; " \
                 "MSIE 8.0; Windows NT [56].1; (WOW64; )Trident/4.0; SLCC2; .NET " \
                 "CLR 2.0.[0-9]{6}; .NET CLR 3.5.[0-9]{6}; .NET CLR 3.0.[0-9]{6}|Opera/9.80 " \
                 "\(Windows NT [56].1; (WOW64; )U; Edition [a-zA-Z]+ Local; ru\) Presto/2.10.289 " \
                 "Version/([5-9]|1[0-2]).0[0-9]"

        drive_ua_re = re.compile(regexp)
        if "network" in self.results:
            for http in self.results["network"]["http"]:
                if http["method"] == "POST" and (http["body"].startswith("req=") or http["body"].startswith("newd=1")) and drive_ua_re.search(http.get("user-agent", "")):
                    self.data.append({"url" : http["uri"], "data" : http["body"]})
                    return True

        return False

########NEW FILE########
__FILENAME__ = bot_madness
# Copyright (C) 2014 thedude13
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
from lib.cuckoo.common.abstracts import Signature

class Madness(Signature):
    name = "bot_madness"
    description = "Recognized to be an Madness bot"
    severity = 3
    categories = ["bot", "ddos"]
    families = ["madness"]
    authors = ["thedude13", "nex"]
    minimum = "0.5"

    def run(self):
        madness_re = re.compile("\?uid\x3d[0-9]{8}&ver\x3d[0-9].[0-9]{2}&mk\x3d[0-9a-f]{6}&os\x3d[A-Za-z0-9]+&rs\x3d[a-z]+&c\x3d[0-1]&rq\x3d[0-1]")
        
        if "network" in self.results:
            for http in self.results["network"]["http"]:
                if http["method"] == "GET" and madness_re.search(http["uri"]):
                    self.data.append({"url" : http["uri"], "data" : http["uri"]})
                    return True

        return False

########NEW FILE########
__FILENAME__ = bot_russkill
# Copyright (C) 2012 JoseMi Holguin (@j0sm1)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class Ruskill(Signature):
    name = "bot_russkill"
    description = "Creates known Ruskill mutexes"
    severity = 3
    alert = True
    categories = ["bot", "ddos"]
    authors = ["JoseMi Holguin", "nex"]

    def run(self):
        return self.check_mutex(pattern="FvLQ49IlzIyLjj6m")

########NEW FILE########
__FILENAME__ = bypass_firewall
# Copyright (C) 2012 Anderson Tamborim (@y2h4ck)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Based on information from http://antivirus.about.com/od/windowsbasics/tp/autostartkeys.htm

from lib.cuckoo.common.abstracts import Signature

class BypassFirewall(Signature):
    name = "bypass_firewall"
    description = "Operates on local firewall's policies and settings"
    severity = 3
    categories = ["bypass"]
    authors = ["Anderson Tamborim", "nex"]
    minimum = "0.5"

    def run(self):
        return self.check_key(pattern=".*\\\\SYSTEM\\\\CurrentControlSet\\\\Services\\\\SharedAccess\\\\Parameters\\\\FirewallPolicy\\\\.*",
                              regex=True)

########NEW FILE########
__FILENAME__ = exec_crash
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class Crash(Signature):
    name = "exec_crash"
    description = "At least one process apparently crashed during execution"
    severity = 1
    categories = ["execution", "crash"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        res = self.check_argument_call(
            call,
            pattern=".*faultrep\.dll$",
            name="FileName",
            api="LdrLoadDll",
            regex=True
        )

        if res:
            return True

########NEW FILE########
__FILENAME__ = infostealer_browser
# Copyright (C) 2012-2014 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re

from lib.cuckoo.common.abstracts import Signature

class BrowserStealer(Signature):
    name = "infostealer_browser"
    description = "Steals private information from local Internet browsers"
    severity = 3
    categories = ["infostealer"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    indicators = [
        re.compile(".*\\\\Mozilla\\\\Firefox\\\\Profiles\\\\.*\\\\.default\\\\signons\.sqlite$"),
        re.compile(".*\\\\Mozilla\\\\Firefox\\\\Profiles\\\\.*\\\\.default\\\\secmod\.db$"),
        re.compile(".*\\\\Mozilla\\\\Firefox\\\\Profiles\\\\.*\\\\.default\\\\cert8\.db$"),
        re.compile(".*\\\\Mozilla\\\\Firefox\\\\Profiles\\\\.*\\\\.default\\\\key3\.db$"),
        re.compile(".*\\\\History\\\\History\.IE5\\\\index\.dat$"),
        re.compile(".*\\\\Temporary\\\\ Internet\\ Files\\\\Content\.IE5\\\\index\.dat$"),
        re.compile(".*\\\\Application\\ Data\\\\Google\\\\Chrome\\\\.*"),
        re.compile(".*\\\\Application\\ Data\\\\Opera\\\\.*"),
        re.compile(".*\\\\Application\\ Data\\\\Chromium\\\\.*"),
        re.compile(".*\\\\Application\\ Data\\\\ChromePlus\\\\.*"),
        re.compile(".*\\\\Application\\ Data\\\\Nichrome\\\\.*"),
        re.compile(".*\\\\Application\\ Data\\\\Bromium\\\\.*"),
        re.compile(".*\\\\Application\\ Data\\\\RockMelt\\\\.*")

    ]

    def on_call(self, call, process):
        # If the current process appears to be a browser, continue.
        if process["process_name"].lower() in ("iexplore.exe", "firefox.exe", "chrome.exe"):
            return None

        # If the call category is not filesystem, continue.
        if call["category"] != "filesystem":
            return None

        for argument in call["arguments"]:
            if argument["name"] == "FileName":
                for indicator in self.indicators:
                    if indicator.match(argument["value"]):
                        self.data.append({
                            "file" : argument["value"],
                            "process_id" : process["process_id"],
                            "process_name" : process["process_name"]}
                        )
                        return True

########NEW FILE########
__FILENAME__ = infostealer_ftp
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class FTPStealer(Signature):
    name = "infostealer_ftp"
    description = "Harvests credentials from local FTP client softwares"
    severity = 3
    categories = ["infostealer"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        file_indicators = [
            ".*\\\\CuteFTP\\\\sm\.dat$",
            ".*\\\\FlashFXP\\\\.*\\\\Sites\.dat$",
            ".*\\\\FlashFXP\\\\.*\\\\Sites\.dat$",
            ".*\\\\FileZilla\\\\sitemanager\.xml$",
            ".*\\\\FileZilla\\\\recentservers\.xml$",
            ".*\\\\VanDyke\\\\Config\\\\Sessions.*",
            ".*\\\\FTP Explorer\\\\.*"
            ".*\\\\SmartFTP\\\\.*",
            ".*\\\\TurboFTP\\\\.*",
            ".*\\\\FTPRush\\\\.*",
            ".*\\\\LeapFTP\\\\.*",
            ".*\\\\FTPGetter\\\\.*",
            ".*\\\\ALFTP\\\\.*",
            ".*\\\\Ipswitch\\\\WS_FTP.*",
        ]
        registry_indicators = [
            ".*Software\\Far*\\Hosts$",
            ".*Software\\Far*\\FTPHost$",
            ".*Software\\Ghisler\\Windows Commander$",
            ".*Software\\Ghisler\\Total Commander$",
            ".*Software\\BPFTP\\$",
            ".*Software\\BulletProof Software\BulletProof FTP Client\\$"
        ]

        for indicator in file_indicators:
            if self.check_file(pattern=indicator, regex=True):
                return True
        for indicator in registry_indicators:
            if self.check_key(pattern=indicator, regex=True):
                return True
        return False

########NEW FILE########
__FILENAME__ = injection_createremotethread
# Copyright (C) 2012 JoseMi "h0rm1" Holguin (@j0sm1)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class InjectionCRT(Signature):
    name = "injection_createremotethread"
    description = "Code injection with CreateRemoteThread in a remote process"
    severity = 2
    categories = ["injection"]
    authors = ["JoseMi Holguin", "nex"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.lastprocess = None

    def on_call(self, call, process):
        if process is not self.lastprocess:
            self.sequence = 0
            self.process_handle = 0
            self.lastprocess = process

        if call["api"]  == "OpenProcess" and self.sequence == 0:
            if self.get_argument(call, "ProcessId") != process["process_id"]:
                self.sequence = 1
                self.process_handle = call["return"]
        elif call["api"] == "VirtualAllocEx" and self.sequence == 1:
            if self.get_argument(call, "ProcessHandle") == self.process_handle:
                self.sequence = 2
        elif (call["api"] == "NtWriteVirtualMemory" or call["api"] == "WriteProcessMemory") and self.sequence == 2:
            if self.get_argument(call, "ProcessHandle") == self.process_handle:
                self.sequence = 3
        elif call["api"].startswith("CreateRemoteThread") and self.sequence == 3:
            if self.get_argument(call, "ProcessHandle") == self.process_handle:
                return True

########NEW FILE########
__FILENAME__ = injection_runpe
# Copyright (C) 2014 glysbays
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class InjectionRUNPE(Signature):
    name = "injection_runpe"
    description = "Executed a process and injected code into it, probably while unpacking"
    severity = 2
    categories = ["injection"]
    authors = ["glysbaysb"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.lastprocess = None

    def on_call(self, call, process):
        if process is not self.lastprocess:
            self.sequence = 0
            self.process_handle = 0
            self.lastprocess = process

        if call["api"]  == "CreateProcessInternalW" and self.sequence == 0:
            self.sequence = 1
            self.process_handle = self.get_argument(call, "ProcessHandle")
            self.thread_handle = self.get_argument(call, "ThreadHandle")
        elif call["api"] == "NtUnmapViewOfSection" and self.sequence == 1:
            if self.get_argument(call, "ProcessHandle") == self.process_handle:
                self.sequence = 2
        elif (call["api"] == "NtWriteVirtualMemory" or call["api"] == "WriteProcessMemory" or call["api"] == "NtMapViewOfSection") and self.sequence == 2:
            if self.get_argument(call, "ProcessHandle") == self.process_handle:
                self.sequence = 3
        elif call["api"].startswith("SetThreadContext") and self.sequence == 3:
            if self.get_argument(call, "ThreadHandle") == self.thread_handle:
                self.sequence = 4
        elif call["api"] == "NtResumeThread" and self.sequence == 4:
            if self.get_argument(call, "ThreadHandle") == self.thread_handle:
                return True

########NEW FILE########
__FILENAME__ = locker_regedit
# Copyright (C) 2012 Thomas "stacks" Birn (@stacksth)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class DisableRegedit(Signature):
    name = "locker_regedit"
    description = "Disables Windows' Registry Editor"
    severity = 3
    categories = ["locker"]
    authors = ["Thomas Birn", "nex"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.saw_disable = False

    def on_call(self, call, process):
        if self.check_argument_call(call,
                                    pattern="DisableRegistryTools",
                                    category="registry"):
            self.saw_disable = True

    def on_complete(self):
        if self.check_key(pattern=".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Policies\\\\System$",
                          regex=True):
            if self.saw_disable:
                return True

########NEW FILE########
__FILENAME__ = locker_taskmgr
# Copyright (C) 2012 Thomas "stacks" Birn (@stacksth)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class DisableTaskMgr(Signature):
    name = "locker_taskmgr"
    description = "Disables Windows' Task Manager"
    severity = 3
    categories = ["locker"]
    authors = ["Thomas Birn", "nex"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.saw_disable = False

    def on_call(self, call, process):
        if self.check_argument_call(call, pattern="DisableTaskMgr",
                               category="registry"):
            self.saw_disable = True

    def run(self):
        if self.check_key(pattern=".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Policies\\\\System$",
                          regex=True):
            if self.saw_disable:
                return True

########NEW FILE########
__FILENAME__ = network_bind
# Copyright (C) 2013 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class NetworkBIND(Signature):
    name = "network_bind"
    description = "Starts servers listening on {0}"
    severity = 2
    categories = ["bind"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.binds = []

    def on_call(self, call, process):
        if call["api"] != "bind":
            return

        bind = "{0}:{1}".format(self.get_argument(call, "ip"), self.get_argument(call, "port"))
        if bind not in self.binds:
            self.binds.append(bind)

    def on_complete(self):
        if self.binds:
            self.description = self.description.format(", ".join(self.binds))
            return True

########NEW FILE########
__FILENAME__ = network_http
# Copyright (C) 2013 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class NetworkHTTP(Signature):
    name = "network_http"
    description = "Performs some HTTP requests"
    severity = 2
    categories = ["http"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        if "http" in self.results["network"]:
            if len(self.results["network"]["http"]) > 0:
                return True

        return False

########NEW FILE########
__FILENAME__ = network_icmp
# Copyright (C) 2013 David Maciejak
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class NetworkICMP(Signature):
    name = "network_icmp"
    description = "Generates some ICMP traffic"
    severity = 4
    categories = ["icmp"]
    authors = ["David Maciejak"]
    minimum = "1.0"

    def run(self):
        if "icmp" in self.results["network"]:
            if len(self.results["network"]["icmp"]) > 0:
                return True

        return False

########NEW FILE########
__FILENAME__ = network_irc
# Copyright (C) 2013 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class NetworkIRC(Signature):
    name = "network_irc"
    description = "Connects to an IRC server, possibly part of a botnet"
    severity = 3
    categories = ["irc"]
    authors = ["nex"]
    minimum = "0.6"

    def run(self):
        if "irc" in self.results["network"]:
            if len(self.results["network"]["irc"]) > 0:
                return True

        return False

########NEW FILE########
__FILENAME__ = network_smtp
# Copyright (C) 2013 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class NetworkSMTP(Signature):
    name = "network_smtp"
    description = "Makes SMTP requests, possibly sending spam"
    severity = 3
    categories = ["smtp", "spam"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        if "smtp" in self.results["network"]:
            if len(self.results["network"]["smtp"]) > 0:
                return True

        return False

########NEW FILE########
__FILENAME__ = network_tor
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class Tor(Signature):
    name = "network_tor"
    description = "Installs Tor on the infected machine"
    severity = 3
    categories = ["network", "anonimity", "tor"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        if self.check_argument_call(call,
                                    pattern="Tor Win32 Service",
                                    api="CreateServiceA",
                                    category="services"):
            return True

    def run(self):
        indicators = [
            ".*\\\\tor\\\\cached-certs$",
            ".*\\\\tor\\\\cached-consensus$",
            ".*\\\\tor\\\\cached-descriptors$",
            ".*\\\\tor\\\\geoip$",
            ".*\\\\tor\\\\lock$",
            ".*\\\\tor\\\\state$",
            ".*\\\\tor\\\\torrc$"
        ]

        for indicator in indicators:
            if self.check_file(pattern=indicator, regex=True):
                return True

########NEW FILE########
__FILENAME__ = network_tor_service
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class TorHiddenService(Signature):
    name = "network_tor_service"
    description = "Creates a Tor Hidden Service on the machine"
    severity = 3
    categories = ["network", "anonimity", "tor"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        indicators = [
            ".*\\\\tor\\\\hidden_service\\\\private_key$",
            ".*\\\\tor\\\\hidden_service\\\\hostname$"
        ]

        for indicator in indicators:
            if self.check_file(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = origin_langid
# Copyright (C) 2012 Benjamin K., Kevin R., Claudio "nex" Guarnieri
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class BuildLangID(Signature):
    name = "origin_langid"
    description = "Unconventionial binary language"
    severity = 2
    authors = ["Benjamin K.", "Kevin R.", "nex"]
    categories = ["origin"]
    minimum = "0.5"

    def run(self):
        languages = [
            {"language" : "Arabic", "code" : "0x0401"},
            {"language" : "Bulgarian", "code" : "0x0402"},
            {"language" : "Traditional Chinese" , "code" : "0x0404"},
            {"language" : "Romanian", "code" : "0x0418"},
            {"language" : "Russian", "code" : "0x0419"},
            {"language" : "Croato-Serbian", "code" : "0x041A"},
            {"language" : "Slovak", "code" : "0x041B"},
            {"language" : "Albanian", "code" : "0x041C"},
            {"language" : "Turkish", "code" : "0x041F"},
            {"language" : "Simplified Chinese", "code" : "0x0804"},
            {"language" : "Hebrew", "code" : "0x040d"}
        ]

        if "static" in self.results:
            if "pe_versioninfo" in self.results["static"]:
                for info in self.results["static"]["pe_versioninfo"]:
                    if info["name"] == "Translation":
                        lang, charset = info["value"].strip().split(" ")
                        for language in languages:
                            if language["code"] == lang:
                                self.description += ": %s" % language["language"]
                                return True

        return False

########NEW FILE########
__FILENAME__ = packer_entropy
# Copyright (C) 2014 Robby Zeitfuchs (@robbyFux)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class PackerEntropy(Signature):
    name = "packer_entropy"
    description = "The binary likely contains encrypted or compressed data."
    severity = 2
    categories = ["packer"]
    authors = ["Robby Zeitfuchs", "nex"]
    minimum = "0.6"
    references = ["http://www.forensickb.com/2013/03/file-entropy-explained.html", 
                  "http://virii.es/U/Using%20Entropy%20Analysis%20to%20Find%20Encrypted%20and%20Packed%20Malware.pdf"]

    def run(self):
        if "static" in self.results:
            if "pe_sections" in self.results["static"]:
                total_compressed = 0
                total_pe_data = 0
                
                for section in self.results["static"]["pe_sections"]:
                    total_pe_data += int(section["size_of_data"], 16)
                     
                    if section["entropy"] > 6.8:
                        self.data.append({"section" : section})
                        total_compressed += int(section["size_of_data"], 16)
                
                if ((1.0 * total_compressed) / total_pe_data) > .2:
                    return True

        return False

########NEW FILE########
__FILENAME__ = packer_upx
# Copyright (C) 2012 Michael Boman (@mboman)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class UPXCompressed(Signature):
    name = "packer_upx"
    description = "The executable is compressed using UPX"
    severity = 2
    categories = ["packer"]
    authors = ["Michael Boman", "nex"]
    minimum = "0.5"

    def run(self):
        if "static" in self.results:
            if "pe_sections" in self.results["static"]:
                for section in self.results["static"]["pe_sections"]:
                    if section["name"].startswith("UPX"):
                        self.data.append({"section" : section})
                        return True

        return False

########NEW FILE########
__FILENAME__ = persistence_ads
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class ADS(Signature):
    name = "persistence_ads"
    description = "Creates an Alternate Data Stream (ADS)"
    severity = 3
    categories = ["persistence", "ads"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        result = False
        for file_path in self.results["behavior"]["summary"]["files"]:
            if len(file_path) <= 3:
                continue

            if ":" in file_path.replace("/", "\\").split("\\")[-1]:
                self.data.append({"file" : file_path})
                result = True

        return result

########NEW FILE########
__FILENAME__ = persistence_autorun
# Copyright (C) 2012 Michael Boman (@mboman)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Based on information from http://antivirus.about.com/od/windowsbasics/tp/autostartkeys.htm

# Additional keys added from SysInternals Administrators Guide

from lib.cuckoo.common.abstracts import Signature

class Autorun(Signature):
    name = "persistence_autorun"
    description = "Installs itself for autorun at Windows startup"
    severity = 3
    categories = ["persistence"]
    authors = ["Michael Boman", "nex","securitykitten"]
    minimum = "0.5"

    def run(self):
        indicators = [
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run$",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\RunOnce$",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\RunServices$",
            ".*\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\RunOnceEx$",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\RunServicesOnce$",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\ NT\\\\CurrentVersion\\\\Winlogon$",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\ NT\\\\CurrentVersion\\\\Winlogon\\\\Notify$",
            ".*\\\\Software\\\\Microsoft\\\\Windows\\ NT\\\\CurrentVersion\\\\Winlogon\\\\Userinit$",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Policies\\\\Explorer\\\\Run$",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Active\\ Setup\\\\Installed Components\\\\.*",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\ NT\\\\CurrentVersion\\\\Windows\\\\Appinit_Dlls.*",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Explorer\\\\SharedTaskScheduler.*",
            ".*\\\\Software\\\\Microsoft\\\\Windows\\ NT\\\\CurrentVersion\\\\Image\\ File\\ Execution\\ Options.*",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\ NT\\\\CurrentVersion\\\\Winlogon\\\\Shell$",
            ".*\\\\System\\\\CurrentControlSet\\\\Services.*",
            ".*\\\\SOFTWARE\\\\Classes\\\\Exefile\\\\Shell\\\\Open\\\\Command\\\\\(Default\).*",
            ".*\\\\Software\\\\Microsoft\\\\Windows NT\\\\CurrentVersion\\\\Windows\\\\load$",
            ".*\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\ShellServiceObjectDelayLoad$"
        ]

        for indicator in indicators:
            if self.check_key(pattern=indicator, regex=True):
                return True

        indicators = [
            ".*\\\\win\.ini$",
            ".*\\\\system\.ini$",
            ".*\\\\Start Menu\\\\Programs\\\\Startup$"
        ]

        for indicator in indicators:
            if self.check_file(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = rat_beebus_mutex
# Copyright (C) 2012 @threatlead
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class BeebusMutexes(Signature):
    name = "rat_beebus_mutexes"
    description = "Creates known Beebus mutexes"
    severity = 3
    categories = ["rat"]
    families = ["beebus"]
    authors = ["threatlead", "nex"]
    minimum = "0.5"
    references = [
        "http://www.fireeye.com/blog/technical/malware-research/2013/04/the-mutter-backdoor-operation-beebus-with-new-targets.html",
        "https://malwr.com/analysis/MjhmNmJhZjdjOWM4NDExZDkzOWMyMDQ2YzUzN2QwZDI/"
    ]

    def run(self):
        indicators = [
            ".*mqe45tex13fw14op0",
            ".*654234576804d",
        ]

        for indicator in indicators:
            if self.check_mutex(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = rat_fynloski_mutex
# Copyright (C) 2014 @threatlead
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class FynloskiMutexes(Signature):
    name = "rat_fynloski_mutexes"
    description = "Creates known Fynloski/DarkComet mutexes"
    severity = 3
    categories = ["rat"]
    families = ["fynloski"]
    authors = ["threatlead"]
    references = ["https://malwr.com/analysis/ODVlOWEyNDU3NzBhNDE3OWJkZjE0ZjIxNTdiMzU1YmM/"]
    minimum = "0.5"

    def run(self):
        indicators = [
            "DC_MUTEX-.*"
        ]

        for indicator in indicators:
            if self.check_mutex(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = rat_pcclient
# Copyright (C) 2014 @threatlead
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class PcClientMutexes(Signature):
    name = "rat_pcclient"
    description = "Creates known PcClient mutex and/or file changes."
    severity = 3
    categories = ["rat"]
    families = ["pcclient", "nex"]
    authors = ["threatlead"]
    references = ["https://malwr.com/analysis/MDIxN2NhMjg4MTg2NDY4MWIyNTE0Zjk5MTY1OGU4YzE/"]
    minimum = "0.5"
    
    def run(self):
        indicators = [
            "BKLANG.*",
            "VSLANG.*",
        ]
        
        for indicator in indicators:
            if self.check_mutex(pattern=indicator, regex=True):
                return True

        indicators = [
            ".*\\\\syslog.dat",
            ".*\\\\.*_lang.ini",
            ".*\\\\[0-9]+_lang.dll",
            ".*\\\\[0-9]+_res.tmp",
        ]

        for indicator in indicators:
            if self.check_file(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = rat_plugx_mutex
# Copyright (C) 2014 @threatlead
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class PlugxMutexes(Signature):
    name = "rat_plugx_mutexes"
    description = "Creates known PlugX mutexes"
    severity = 3
    categories = ["rat"]
    families = ["plugx"]
    authors = ["threatlead", "nex"]
    references = ["https://malwr.com/analysis/YTZjYmUwMzNlNzkwNGU5YmIxNDQwYTcyYjFkYWI0NWE/"]
    minimum = "0.5"

    def run(self):
        indicators = [
            "DoInstPrepare",
        ]

        for indicator in indicators:
            if self.check_mutex(pattern=indicator):
                return True

        return False

########NEW FILE########
__FILENAME__ = rat_spynet
# Copyright (C) 2014 @threatlead
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class SpynetRat(Signature):
    name = "rat_spynet"
    description = "Creates known SpyNet mutexes and/or registry changes."
    severity = 3
    categories = ["rat"]
    families = ["spynet"]
    authors = ["threatlead", "nex"]
    references = [
        "https://malwr.com/analysis/ZDQ1NjBhNWIzNTdkNDRhNjhkZTFmZTBkYTU2YjMwNzg/",
        "https://malwr.com/analysis/MjkxYmE2YzczNzcwNGJiZjljNDcwMzA2ZDkyNDU2Y2M/",
        "https://malwr.com/analysis/N2E3NWRiNDMyYjIwNGE0NTk3Y2E5NWMzN2UwZTVjMzI/",
        "https://malwr.com/analysis/N2Q2NWY0Y2MzOTM0NDEzNmE1MTdhOThiNTQxMzhiNzk/"   
    ]
    minimum = "0.5"

    def run(self):
        indicators = [
            ".*CYBERGATEUPDATE",
            ".*\(\(SpyNet\)\).*",
            ".*Spy-Net.*",
            ".*X_PASSWORDLIST_X.*",
            ".*X_BLOCKMOUSE_X.*",
            #".*PERSIST", # Causes false positive detection on XtremeRAT samples.
            ".*_SAIR",
        ]

        for indicator in indicators:
            if self.check_mutex(pattern=indicator, regex=True):
                return True

        keys = [
            ".*\\SpyNet\\.*",
        ]

        for key in keys:
            if self.check_key(pattern=key, regex=True):
                return True
        
        return False

########NEW FILE########
__FILENAME__ = rat_xtreme_mutex
# Copyright (C) 2014 @threatlead
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class XtremeMutexes(Signature):
    name = "rat_xtreme_mutexes"
    description = "Creates known XtremeRAT mutexes"
    severity = 3
    categories = ["rat"]
    families = ["xtremerat"]
    authors = ["threatlead", "nex"]
    references = [
        "https://malwr.com/analysis/ZWM4YjI2MzI1MmQ2NDBkMjkwNzI3NzhjNWM5Y2FhY2U/",
        "https://malwr.com/analysis/MWY5YTAwZWI1NDc3NDJmMTgyNDA4ODc0NTk0MWIzNjM/"
    ]
    minimum = "0.5"

    def run(self):
        indicators = [
            "XTREMEUPDATE",
            "\(\(Mutex\)\).*"
        ]

        for indicator in indicators:
            if self.check_mutex(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = recon_checkip
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class CheckIP(Signature):
    name = "recon_checkip"
    description = "Looks up the external IP address"
    severity = 2
    categories = ["recon"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        indicators = [
            "checkip.dyndns.org",
            "whatismyip.org",
            "whatsmyipaddress.com",
            "getmyip.org",
            "getmyip.co.uk"
        ]

        for indicator in indicators:
            if self.check_domain(pattern=indicator):
                self.data.append({"domain" : indicator})
                return True

        return False

########NEW FILE########
__FILENAME__ = recon_fingerprint
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class Fingerprint(Signature):
    name = "recon_fingerprint"
    description = "Collects information to fingerprint the system (MachineGuid, DigitalProductId, SystemBiosDate)"
    severity = 3
    categories = ["recon"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def __init__(self, *args, **kwargs):
        Signature.__init__(self, *args, **kwargs)
        self.threshold = 3
        self.matches = 0

    def on_call(self, call, process):
        indicators = [
            "MachineGuid",
            "DigitalProductId",
            "SystemBiosDate"
        ]

        if call["category"] != "registry":
            return

        for argument in call["arguments"]:
            for indicator in indicators:
                if argument["value"] == indicator:
                    indicators.remove(indicator)
                    self.matches += 1

        if self.matches >= self.threshold:
            return True

########NEW FILE########
__FILENAME__ = recon_systeminfo
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class SystemInfo(Signature):
    name = "recon_systeminfo"
    description = "Collects information on the system (ipconfig, netstat, systeminfo)"
    severity = 3
    categories = ["recon"]
    authors = ["nex"]
    minimum = "1.0"
    evented = True

    def on_call(self, call, process):
        return self.check_argument_call(
            call, pattern="(^cmd\.exe).*[(systeminfo)|(ipconfig)|(netstat)]",
            name="CommandLine",
            category="process",
            regex=True
        )

########NEW FILE########
__FILENAME__ = sniffer_winpcap
# Copyright (C) 2012 Thomas "stacks" Birn (@stacksth)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class InstallsWinpcap(Signature):
    name = "sniffer_winpcap"
    description = "Installs WinPCAP"
    severity = 3
    categories = ["sniffer"]
    authors = ["Thomas Birn", "nex"]
    minimum = "0.5"

    def run(self):
        indicators = [
            ".*\\\\packet\.dll$",
            ".*\\\\npf\.sys$",
            ".*\\\\wpcap\.dll$"
        ]

        for indicator in indicators:
            if self.check_file(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
__FILENAME__ = spreading_autoruninf
# Copyright (C) 2012 Thomas "stacks" Birn (@stacksth)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class CreatesAutorunInf(Signature):
    name = "spreading_autoruninf"
    description = "Creates an autorun.inf file"
    severity = 2
    categories = ["spreading"]
    authors = ["Thomas Birn", "nex"]
    minimum = "0.5"

    def run(self):
        return self.check_file(pattern=".*\\\\autorun\.inf$", regex=True)

########NEW FILE########
__FILENAME__ = targeted_flame
# Copyright (C) 2012 Claudio "nex" Guarnieri (@botherder)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from lib.cuckoo.common.abstracts import Signature

class Flame(Signature):
    name = "targeted_flame"
    description = "Shows some indicators associated with the Flame malware"
    severity = 3
    references = ["http://www.crysys.hu/skywiper/skywiper.pdf",
                  "http://www.securelist.com/en/blog/208193522/The_Flame_Questions_and_Answers",
                  "http://www.certcc.ir/index.php?name=news&file=article&sid=1894"]
    categories = ["targeted"]
    families = ["flame", "skywiper"]
    authors = ["nex"]
    minimum = "0.5"

    def run(self):
        indicators = [
            "__fajb.*",
            "DVAAccessGuard.*",
            ".*mssecuritymgr.*"
        ]

        for indicator in indicators:
            if self.check_mutex(pattern=indicator, regex=True):
                return True

        indicators = [
            ".*\\\\Microsoft Shared\\\\MSSecurityMgr\\\\.*",
            ".*\\\\Ef_trace\.log$"
        ]

        for indicator in indicators:
            if self.check_file(pattern=indicator, regex=True):
                return True

        return False

########NEW FILE########
