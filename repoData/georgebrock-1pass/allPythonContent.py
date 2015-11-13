__FILENAME__ = cli
import argparse
import getpass
import os
import sys

from onepassword import Keychain

DEFAULT_KEYCHAIN_PATH = "~/Dropbox/1Password.agilekeychain"

class CLI(object):
    """
    The 1pass command line interface.
    """

    def __init__(self, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr,
                 getpass=getpass.getpass, arguments=sys.argv[1:]):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.getpass = getpass
        self.arguments = self.argument_parser().parse_args(arguments)
        self.keychain = Keychain(self.arguments.path)

    def run(self):
        """
        The main entry point, performs the appropriate action for the given
        arguments.
        """
        self._unlock_keychain()

        item = self.keychain.item(
            self.arguments.item,
            fuzzy_threshold=self._fuzzy_threshold(),
        )

        if item is not None:
            self.stdout.write("%s\n" % item.password)
        else:
            self.stderr.write("1pass: Could not find an item named '%s'\n" % (
                self.arguments.item,
            ))
            sys.exit(os.EX_DATAERR)

    def argument_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("item", help="The name of the password to decrypt")
        parser.add_argument(
            "--path",
            default=os.environ.get('ONEPASSWORD_KEYCHAIN', DEFAULT_KEYCHAIN_PATH),
            help="Path to your 1Password.agilekeychain file",
        )
        parser.add_argument(
            "--fuzzy",
            action="store_true",
            help="Perform fuzzy matching on the item",
        )
        parser.add_argument(
            "--no-prompt",
            action="store_true",
            help="Don't prompt for a password, read from STDIN instead",
        )
        return parser

    def _unlock_keychain(self):
        if self.arguments.no_prompt:
            self._unlock_keychain_stdin()
        else:
            self._unlock_keychain_prompt()

    def _unlock_keychain_stdin(self):
        password = self.stdin.read().strip()
        self.keychain.unlock(password)
        if self.keychain.locked:
            self.stderr.write("1pass: Incorrect master password\n")
            sys.exit(os.EX_DATAERR)

    def _unlock_keychain_prompt(self):
        while self.keychain.locked:
            try:
                self.keychain.unlock(self.getpass("Master password: "))
            except KeyboardInterrupt:
                self.stdout.write("\n")
                sys.exit(0)

    def _fuzzy_threshold(self):
        if self.arguments.fuzzy:
            return 70
        else:
            return 100

########NEW FILE########
__FILENAME__ = encryption_key
from base64 import b64decode
from Crypto.Cipher import AES
from Crypto.Hash import MD5
from pbkdf2 import pbkdf2_bin


class SaltyString(object):
    SALTED_PREFIX = "Salted__"
    ZERO_INIT_VECTOR = "\x00" * 16

    def __init__(self, base64_encoded_string):
        decoded_data = b64decode(base64_encoded_string)
        if decoded_data.startswith(self.SALTED_PREFIX):
            self.salt = decoded_data[8:16]
            self.data = decoded_data[16:]
        else:
            self.salt = self.ZERO_INIT_VECTOR
            self.data = decoded_data


class EncryptionKey(object):
    MINIMUM_ITERATIONS = 1000

    def __init__(self, data, iterations=0, validation="", identifier=None,
                 level=None):
        self.identifier = identifier
        self.level = level
        self._encrypted_key = SaltyString(data)
        self._decrypted_key = None
        self._set_iterations(iterations)
        self._validation = validation

    def unlock(self, password):
        key, iv = self._derive_pbkdf2(password)
        self._decrypted_key = self._aes_decrypt(
            key=key,
            iv=iv,
            encrypted_data=self._encrypted_key.data,
        )
        return self._validate_decrypted_key()

    def decrypt(self, b64_data):
        encrypted = SaltyString(b64_data)
        key, iv = self._derive_openssl(self._decrypted_key, encrypted.salt)
        return self._aes_decrypt(key=key, iv=iv, encrypted_data=encrypted.data)

    def _set_iterations(self, iterations):
        self.iterations = max(int(iterations), self.MINIMUM_ITERATIONS)

    def _validate_decrypted_key(self):
        return self.decrypt(self._validation) == self._decrypted_key

    def _aes_decrypt(self, key, iv, encrypted_data):
        aes = AES.new(key, mode=AES.MODE_CBC, IV=iv)
        return self._strip_padding(aes.decrypt(encrypted_data))

    def _strip_padding(self, decrypted):
        padding_size = ord(decrypted[-1])
        if padding_size >= 16:
            return decrypted
        else:
            return decrypted[:-padding_size]

    def _derive_pbkdf2(self, password):
        key_and_iv = pbkdf2_bin(
            password,
            self._encrypted_key.salt,
            self.iterations,
            keylen=32,
        )
        return (
            key_and_iv[0:16],
            key_and_iv[16:],
        )

    def _derive_openssl(self, key, salt):
        key = key[0:-16]
        key_and_iv = ""
        prev = ""
        while len(key_and_iv) < 32:
            prev = MD5.new(prev + key + salt).digest()
            key_and_iv += prev
        return (
            key_and_iv[0:16],
            key_and_iv[16:],
        )

########NEW FILE########
__FILENAME__ = keychain
import json
import os
from fuzzywuzzy import process

from onepassword.encryption_key import EncryptionKey


class Keychain(object):
    def __init__(self, path):
        self._path = os.path.expanduser(path)
        self._load_encryption_keys()
        self._load_item_list()
        self._locked = True

    def unlock(self, password):
        unlocker = lambda key: key.unlock(password)
        unlock_results = map(unlocker, self._encryption_keys.values())
        result = reduce(lambda x, y: x and y, unlock_results)
        self._locked = not result
        return result

    def item(self, name, fuzzy_threshold=100):
        """
        Extract a password from an unlocked Keychain using fuzzy
        matching. ``fuzzy_threshold`` can be an integer between 0 and
        100, where 100 is an exact match.
        """
        match = process.extractOne(
            name,
            self._items.keys(),
            score_cutoff=(fuzzy_threshold-1),
        )
        if match:
            exact_name = match[0]
            item = self._items[exact_name]
            item.decrypt_with(self)
            return item
        else:
            return None

    def key(self, identifier=None, security_level=None):
        """
        Tries to find an encryption key, first using the ``identifier`` and
        if that fails or isn't provided using the ``security_level``.
        Returns ``None`` if nothing matches.
        """
        if identifier:
            try:
                return self._encryption_keys[identifier]
            except KeyError:
                pass
        if security_level:
            for key in self._encryption_keys.values():
                if key.level == security_level:
                    return key

    @property
    def locked(self):
        return self._locked

    def _load_encryption_keys(self):
        path = os.path.join(self._path, "data", "default", "encryptionKeys.js")
        with open(path, "r") as f:
            key_data = json.load(f)

        self._encryption_keys = {}
        for key_definition in key_data["list"]:
            key = EncryptionKey(**key_definition)
            self._encryption_keys[key.identifier] = key

    def _load_item_list(self):
        path = os.path.join(self._path, "data", "default", "contents.js")
        with open(path, "r") as f:
            item_list = json.load(f)

        self._items = {}
        for item_definition in item_list:
            item = KeychainItem.build(item_definition, self._path)
            self._items[item.name] = item


class KeychainItem(object):
    @classmethod
    def build(cls, row, path):
        identifier = row[0]
        type = row[1]
        name = row[2]
        if type == "webforms.WebForm":
            return WebFormKeychainItem(identifier, name, path, type)
        elif type == "passwords.Password" or type == "wallet.onlineservices.GenericAccount":
            return PasswordKeychainItem(identifier, name, path, type)
        else:
            return KeychainItem(identifier, name, path, type)

    def __init__(self, identifier, name, path, type):
        self.identifier = identifier
        self.name = name
        self.password = None
        self._path = path
        self._type = type

    @property
    def key_identifier(self):
        return self._lazily_load("_key_identifier")

    @property
    def security_level(self):
        return self._lazily_load("_security_level")

    def decrypt_with(self, keychain):
        key = keychain.key(
            identifier=self.key_identifier,
            security_level=self.security_level,
        )
        encrypted_json = self._lazily_load("_encrypted_json")
        decrypted_json = key.decrypt(self._encrypted_json)
        self._data = json.loads(decrypted_json)
        self.password = self._find_password()

    def _find_password(self):
        raise Exception("Cannot extract a password from this type of"
                        " keychain item (%s)" % self._type)

    def _lazily_load(self, attr):
        if not hasattr(self, attr):
            self._read_data_file()
        return getattr(self, attr)

    def _read_data_file(self):
        filename = "%s.1password" % self.identifier
        path = os.path.join(self._path, "data", "default", filename)
        with open(path, "r") as f:
            item_data = json.load(f)

        self._key_identifier = item_data.get("keyID")
        self._security_level = item_data.get("securityLevel")
        self._encrypted_json = item_data["encrypted"]


class WebFormKeychainItem(KeychainItem):
    def _find_password(self):
        for field in self._data["fields"]:
            if field.get("designation") == "password" or \
               field.get("name") == "Password":
                return field["value"]


class PasswordKeychainItem(KeychainItem):
    def _find_password(self):
        return self._data["password"]

########NEW FILE########
__FILENAME__ = cli_test
import os
from unittest import TestCase
from StringIO import StringIO

from onepassword.cli import CLI


class CLITest(TestCase):
    def setUp(self):
        self.output = StringIO()
        self.error = StringIO()
        self.input = StringIO()

    def test_cli_reading_web_form_password_with_multiple_password_attempts(self):
        password_attempts = (i for i in ("incorrect", "badger"))
        cli = self.build_cli(
            getpass=lambda prompt: password_attempts.next(),
            arguments=("--path", self.keychain_path, "onetosix",),
        )
        cli.run()

        self.assert_output("123456\n")
        self.assert_no_error_output()

    def test_cli_with_bad_item_name(self):
        cli = self.build_cli(
            getpass=lambda prompt: "badger",
            arguments=("--path", self.keychain_path, "onetos",),
        )

        self.assert_exit_status(os.EX_DATAERR, cli.run)
        self.assert_no_output()
        self.assert_error_output("1pass: Could not find an item named 'onetos'\n")

    def test_cli_with_fuzzy_matching(self):
        cli = self.build_cli(
            getpass=lambda prompt: "badger",
            arguments=("--fuzzy", "--path", self.keychain_path, "onetos",),
        )
        cli.run()

        self.assert_output("123456\n")
        self.assert_no_error_output()

    def test_cli_cancelled_password_prompt(self):
        def keyboard_interrupt(prompt):
            raise KeyboardInterrupt()
        cli = self.build_cli(
            getpass=keyboard_interrupt,
            arguments=("--path", self.keychain_path, "onetosix",),
        )

        self.assert_exit_status(0, cli.run)
        self.assert_output("\n")
        self.assert_no_error_output()

    def test_correct_password_from_stdin(self):
        def flunker(prompt):
            self.fail("Password prompt was invoked")
        self.input.write("badger\n")
        self.input.seek(0)
        cli = self.build_cli(
            getpass=flunker,
            arguments=("--no-prompt", "--path", self.keychain_path, "onetosix",),
        )
        cli.run()

        self.assert_output("123456\n")
        self.assert_no_error_output()

    def test_incorrect_password_from_stdin(self):
        def flunker(prompt):
            self.fail("Password prompt was invoked")
        self.input.write("wrong-password\n")
        self.input.seek(0)
        cli = self.build_cli(
            getpass=flunker,
            arguments=("--no-prompt", "--path", self.keychain_path, "onetosix",),
        )

        self.assert_exit_status(os.EX_DATAERR, cli.run)
        self.assert_no_output()
        self.assert_error_output("1pass: Incorrect master password\n")

    def build_cli(self, **kwargs):
        cli_kwargs = {
            "stdin": self.input,
            "stdout": self.output,
            "stderr": self.error,
        }
        cli_kwargs.update(kwargs)
        return CLI(**cli_kwargs)

    def assert_exit_status(self, expected_status, func):
        try:
            func()
        except SystemExit as exit:
            self.assertEquals(expected_status, exit.code)
        else:
            self.fail("Expected a SystemExit to be raised")

    def assert_output(self, expected_output):
        self.assertEquals(expected_output, self.output.getvalue())

    def assert_no_output(self):
        self.assert_output("")

    def assert_error_output(self, expected_output):
        self.assertEquals(expected_output, self.error.getvalue())

    def assert_no_error_output(self):
        self.assert_error_output("")

    @property
    def keychain_path(self):
        return os.path.join(os.path.dirname(__file__), "data", "1Password.agilekeychain")

########NEW FILE########
__FILENAME__ = encryption_key_test
from base64 import b64encode, b64decode
from unittest import TestCase

from onepassword.encryption_key import SaltyString, EncryptionKey


class SaltyStringTest(TestCase):
    def test_unsalted_data(self):
        unsalted = SaltyString(b64encode("Unsalted data"))
        self.assertEquals("\x00" * 16, unsalted.salt)
        self.assertEquals("Unsalted data", unsalted.data)

    def test_salted_data(self):
        salted = SaltyString(b64encode("Salted__SSSSSSSSDDDDDDDD"))
        self.assertEquals("SSSSSSSS", salted.salt)
        self.assertEquals("DDDDDDDD", salted.data)


class EncryptionKeyTest(TestCase):
    def test_identifier(self):
        key = EncryptionKey(data="", identifier="ABC123")
        self.assertEquals("ABC123", key.identifier)

    def test_level(self):
        key = EncryptionKey(data="", level="SL3")
        self.assertEquals("SL3", key.level)

    def test_iterations_with_string(self):
        key = EncryptionKey(data="", iterations="40000")
        self.assertEquals(40000, key.iterations)

    def test_iterations_with_number(self):
        key = EncryptionKey(data="", iterations=5000)
        self.assertEquals(5000, key.iterations)

    def test_iterations_default(self):
        key = EncryptionKey(data="")
        self.assertEquals(1000, key.iterations)

    def test_iterations_minimum(self):
        key = EncryptionKey(data="", iterations=500)
        self.assertEquals(1000, key.iterations)

    def test_unlocking_with_correct_password(self):
        key = EncryptionKey(**self.example_data)
        unlock_result = key.unlock(password="badger")

        self.assertTrue(unlock_result)

    def test_unlocking_with_incorrect_password(self):
        key = EncryptionKey(**self.example_data)
        unlock_result = key.unlock(password="not right")

        self.assertFalse(unlock_result)

    @property
    def example_data(self):
        return {
            u'validation': u'U2FsdGVkX1+Sec0P+405ZJ71pI8tX3W/CFYlyxt+NWAVabzf'\
                           u'hDPS6T92AZWPRYT004kUgA6ZRXhcTxUCMuMLta9Kk3+oSPot'\
                           u'4z0Pzp1mUmZDK4MX/y26S6ndvPpXcAwvJbNoi1jiXO5Us5b/'\
                           u'vA6LI49QESPVxbnOhmXhC2RtMigYq7LQs5j8LrXDgOyVGH5L'\
                           u'm5ZsejJul28WuKlE75t5fLyyoU4aQejMEXAkVMiQSZ7794VI'\
                           u'JUrHgmnW0AfGt2OslGfaWsksRcU8QOGyGmFcA9LGp9iEOQok'\
                           u'eir5ZOQ2NnjQ7YxwZ7PGzaz5LspKm2hJMhYbNsGr45H5ml4b'\
                           u'+f+5aXuBGo3LLBvZN9HFDGME8M63Q+5GZLnV6Z8yaXwiJh/9'\
                           u'2JV9qfl9nA3euuiBMppCWSgVUSqQvR1wraSajz3tupAMvm9d'\
                           u'YIq//XVzZRxMbZ/9lDQH5UXLs82ZpP0+4SQQliNPktCbjqbG'\
                           u'F+pHVVLXlmaGb4xljHqLBbMtyAKE5LnFHg7eWBUw3DZAHmtH'\
                           u'EU5CDu4lMlW0UK97TypYc8maVS98yWY4txYDKZzfTFXv9JtA'\
                           u'TbNHSVfmmDmVjyLwHVZ5G/KHGSLCOzQJy05tYQqll1NyboLu'\
                           u'evGBqKsp9vkak28KDiS9AD0hbxFnTOdG+V3RTtXa2P3LuMV1'\
                           u'Z63rrgHaOfrkDZLwhSYA8vtYBMfYewxRmO07175RvI2DrXuy'\
                           u'n71SAoi4WP0f0m0a5wkGfPEZAnWcWmZV1r9xGPevdEUebTYo'\
                           u'SAfqijLJO5qhP8dFqt+L6lszpYillnpQQNNpc1cGKPqzwmp7'\
                           u'v2Im1ShDT8tG34xCqiIJumrGkZllJmNCOSR/yJo2WPj76IxQ'\
                           u'l9jJdOwPG5KaUIOQS1WgofmMJPVkH6Ehz2GWDprsl4jOQewi'\
                           u'cX7rMtb+RBBmABo/xaOuNHjQas6cCsgnaPfG5A/+CNI7tEGo'\
                           u'4DMLOHWMImdX29RjeHxVnvfZrv0UOCwPYUlLLKF8q1aU56Zt'\
                           u'VHVPat0LTUXPdvB0fnDwMQt+Ck1xDwkVbG2n+mTD2JDDgFgb'\
                           u'H5K1yI0dTaYIDyd1eMERIbY4VuwO7dYSTUpD8KXWPuVKWPBw'\
                           u'VMPKGVRmWxrJBIqfGbZcuLmKqblE0hD09Yxu22R+UOhRlgV+'\
                           u'xUHW1IVY+woGebM1kfM6W5e/sw1pLjmhyjO6PiA293S8Vg4/'\
                           u'pGHSoEbz3WhpIy+1zbYv6V0l9k4cuTZ57mR8CIUbAOuwAVVY'\
                           u'FpqZfYTpRf/wOWGgAn2gDTjslrApXCaL83dLEH7chwYJzf6s'\
                           u'E3wAXS/rKCujQr3GT78SRfpSO/ih8QX47tKJtFQA2PksNhfN'\
                           u'WGY4FBDTJCQeD0MkY+ZAkoC5cnHWon4oFlxIAcnUN52Puk9h'\
                           u'CX5hx3nWm27CDV9M\x00',
            u'identifier': u'525E210E0B4C49799D7E47DD8E789C78',
            u'data': u'U2FsdGVkX1+/ON7QBnJMj+Mqalo+LYqG3gBellwrrIjCBK0qBeBgub'\
                     u'gli0GVhaxG01rLySc2GNwK3sVUJKwv9wqCZYHBXeL40IAtfBg6qUWf'\
                     u'SaS+lIkWLdMhPH/RKgzoBWVrfvJXcHnpxAv4mLYjeZni5DLY0wfIO2'\
                     u'X+lujJoNmMs3mwCfoMP6p86WolUtAuQNzi/+13C50WD7MCb7yi+u9e'\
                     u'xNjj8Qx9qsZ8neXfDCEP881pGM5UT+/IzxuHnxXi2nsftQwe/DLPhn'\
                     u'AWbRTw1zFoAE2mAjOImiaO+7LUBZyiicdsgfxQn37RU88akN8GIKYz'\
                     u'qrewFUGRvKgyk3Ndnsw3OjR78Fjd3RdgNLGxyy5uVnrUxhoaQQCnkg'\
                     u'li4etn5XsRqKJziaAU7HCvtA5HskT2QGOtDhO+Y5dK+ui0GxNl7U01'\
                     u'x/LYDVDr0bmiZhW4esmJRFAGMwQhmxKPlNI++3XHMrenvKFU6BNdzT'\
                     u'TUhaY97I59v36USq1mXsW8XHQwQsetZVv0XbvDC/kmoRr96UbSLgtO'\
                     u'0V3cdVGT7SiRl5uhcc2NFGipP4zGrQU9PspltfucGiPMByAsjIKWBp'\
                     u'9wKbYS1GAHR5uUcpKZsmRyVpWYWyapFjlT1qxNWJj29pShd/KDGqQj'\
                     u'yDO/diQhsJakjJmOaAN+dwy1OBRkmFHoSej9XRKOhjv7hGQTTZYHN/'\
                     u'Klbu+6M4ef56um5X0EuNdACq9hLSKX4QkUijqQs52Xl535q7rOGtok'\
                     u'oKzSGbeVDwWwlPnymkVyWfv5qZamQFSV7F53TPAONz2PJD8m+f0D26'\
                     u'YmFvqZovqmVZeXpEzP+f1Y7OHxxWskuiOws/Mjk2jS+1s+rXIm8Z5n'\
                     u'gH60EOvcOIlpaguCqMZxbSltF3GvE6vl6vV/67YkD0U957iT+aApTC'\
                     u'THGOYaAJ00/lowqH/b6c+fDtcWdk8hztAYktWq3kzWwP3LUvqrO9Iz'\
                     u'r/+Ic8rWY6EBR0rEmFPRop1wUV00jUUVAPfFHLaGa4NOS+a/9VIOZY'\
                     u'1bFaFnqYrRSaaa3Q4hyxyDOke0WXSSiYGM0QLaS8WeTFhizzqj1Oeu'\
                     u'0eISFuxluhb9ywYlh6u06apkzIHO2dB46nsoWsgEQ41VYPY2hi0RWZ'\
                     u'OvIKCjGLZs38c/KhzyOeA2K2MNZjwotBBBlm1G4qcqQmRnP2CnNhqy'\
                     u'/ddaFtsokEzMRVvshLsLCmHYv0z42amLxRD5yyz/FkpC9/SwyUQJ+4'\
                     u'mpy+ls7ryOoR11OUeEx2830m97Xz7TBN8hHl+IZPt1FG2HM74uLU19'\
                     u'zL9nNJVxwpzgMgh0gI/1X/yK1JtA6eGEbKg9N/h79WQJR5SIC88VjL'\
                     u'qvCX2TLdqk8IJg7LbO5TavDq/CqKPp00K2Rkv55jjmDBNZFesBOrl7'\
                     u'rMZN\x00',
            u'iterations': 40000,
            u'level': u'SL5',
        }

########NEW FILE########
__FILENAME__ = integration_test
import os
from unittest import TestCase

from onepassword import Keychain


class IntegrationTest(TestCase):
    def test_unlock_and_read_web_form_password(self):
        keychain = Keychain(path=self.keychain_path)

        unlock_result = keychain.unlock("wrong-password")
        self.assertFalse(unlock_result)

        unlock_result = keychain.unlock("badger")
        self.assertTrue(unlock_result)

        self.assertIsNone(keychain.item("does-not-exist"))
        self.assertEquals("123456", keychain.item("onetosix").password)
        self.assertEquals("abcdef", keychain.item("atof").password)

    def test_unlock_and_read_generated_password(self):
        keychain = Keychain(path=self.keychain_path)

        keychain.unlock("badger")
        self.assertEquals("foobar", keychain.item("foobar").password)

    def test_unlock_and_read_generic_account_password(self):
        keychain = Keychain(path=self.keychain_path)

        keychain.unlock("badger")
        self.assertEquals("flibble", keychain.item("Generic Account").password)

    def test_unlock_and_read_with_fuzzy_matching(self):
        keychain = Keychain(path=self.keychain_path)

        keychain.unlock("badger")
        item = keychain.item("foobr", fuzzy_threshold=70)
        self.assertEquals("foobar", item.password)

    @property
    def keychain_path(self):
        return os.path.join(os.path.dirname(__file__), "data", "1Password.agilekeychain")

########NEW FILE########
__FILENAME__ = keychain_test
from mock import Mock
import os
from unittest import TestCase

from onepassword.keychain import Keychain, KeychainItem


class KeychainTest(TestCase):
    def test_locked_flag(self):
        keychain = Keychain(self.data_path)
        self.assertTrue(keychain.locked)
        self.assertTrue(keychain.unlock("badger"))
        self.assertFalse(keychain.locked)

    def test_key_by_security_level(self):
        keychain = Keychain(self.data_path)
        key = keychain.key(security_level="SL5")
        self.assertEquals("525E210E0B4C49799D7E47DD8E789C78", key.identifier)
        self.assertEquals("SL5", key.level)

    def test_key_by_id_with_bad_security_level(self):
        keychain = Keychain(self.data_path)
        key = keychain.key(security_level="not-a-real-key")
        self.assertIsNone(key)

    def test_key_by_id(self):
        keychain = Keychain(self.data_path)
        key = keychain.key(identifier="525E210E0B4C49799D7E47DD8E789C78")
        self.assertEquals("525E210E0B4C49799D7E47DD8E789C78", key.identifier)
        self.assertEquals("SL5", key.level)

    def test_key_by_id_with_bad_id(self):
        keychain = Keychain(self.data_path)
        key = keychain.key(identifier="not-a-real-key")
        self.assertIsNone(key)

    @property
    def data_path(self):
        return os.path.join(os.path.dirname(__file__), "data", "1Password.agilekeychain")


class KeychainItemTest(TestCase):
    def test_initialisation_with_contents_data(self):
        item = KeychainItem.build(self.example_row, path=self.data_path)
        self.assertEquals("onetosix", item.name)
        self.assertEquals("CEA5EA6531FC4BE9B7D7F89B5BB18B66", item.identifier)

    def test_key_identifier(self):
        item = KeychainItem.build(self.example_row, path=self.data_path)
        self.assertEquals("525E210E0B4C49799D7E47DD8E789C78", item.key_identifier)

    def test_security_level(self):
        item = KeychainItem.build(
            ["A37F72DAE965416EA920D2E4A1D7B256", "webforms.WebForm", "atof",
                "example.com", 12345, "", 0, "N"],
            path=self.data_path,
        )
        self.assertEquals("SL5", item.security_level)

    def test_decrypt(self):
        mock_key = Mock()
        mock_key.decrypt.return_value = """{"fields":[
            {"name":"Username","value":"user","designation":"username"},
            {"value":"abcdef","name":"Password","designation":"password"}
        ]}"""
        mock_keychain = Mock()
        mock_keychain.key.return_value = mock_key
        item = KeychainItem.build(self.example_row, path=self.data_path)

        self.assertIsNone(item.password)
        item.decrypt_with(mock_keychain)
        self.assertEquals("abcdef", item.password)

    @property
    def data_path(self):
        return os.path.join(os.path.dirname(__file__), "data", "1Password.agilekeychain")

    @property
    def example_row(self):
        return [
            "CEA5EA6531FC4BE9B7D7F89B5BB18B66",
            "webforms.WebForm",
            "onetosix",
            "example.com",
            1361021221,
            "",
            0,
            "N",
        ]

########NEW FILE########
