__FILENAME__ = android
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.




from __future__ import absolute_import
import android

from electrum import SimpleConfig, Wallet, WalletStorage, format_satoshis, mnemonic_encode, mnemonic_decode
from electrum.bitcoin import is_valid
from electrum import util
from decimal import Decimal
import datetime, re



def modal_dialog(title, msg = None):
    droid.dialogCreateAlert(title,msg)
    droid.dialogSetPositiveButtonText('OK')
    droid.dialogShow()
    droid.dialogGetResponse()
    droid.dialogDismiss()

def modal_input(title, msg, value = None, etype=None):
    droid.dialogCreateInput(title, msg, value, etype)
    droid.dialogSetPositiveButtonText('OK')
    droid.dialogSetNegativeButtonText('Cancel')
    droid.dialogShow()
    response = droid.dialogGetResponse()
    result = response.result
    droid.dialogDismiss()

    if result is None:
        print "modal input: result is none"
        return modal_input(title, msg, value, etype)

    if result.get('which') == 'positive':
        return result.get('value')

def modal_question(q, msg, pos_text = 'OK', neg_text = 'Cancel'):
    droid.dialogCreateAlert(q, msg)
    droid.dialogSetPositiveButtonText(pos_text)
    droid.dialogSetNegativeButtonText(neg_text)
    droid.dialogShow()
    response = droid.dialogGetResponse()
    result = response.result
    droid.dialogDismiss()

    if result is None:
        print "modal question: result is none"
        return modal_question(q,msg, pos_text, neg_text)

    return result.get('which') == 'positive'

def edit_label(addr):
    v = modal_input('Edit label',None,wallet.labels.get(addr))
    if v is not None:
        if v:
            wallet.labels[addr] = v
        else:
            if addr in wallet.labels.keys():
                wallet.labels.pop(addr)
        wallet.update_tx_history()
        wallet.save()
        droid.fullSetProperty("labelTextView", "text", v)

def select_from_contacts():
    title = 'Contacts:'
    droid.dialogCreateAlert(title)
    l = []
    for i in range(len(wallet.addressbook)):
        addr = wallet.addressbook[i]
        label = wallet.labels.get(addr,addr)
        l.append( label )
    droid.dialogSetItems(l)
    droid.dialogSetPositiveButtonText('New contact')
    droid.dialogShow()
    response = droid.dialogGetResponse().result
    droid.dialogDismiss()

    if response.get('which') == 'positive':
        return 'newcontact'

    result = response.get('item')
    print result
    if result is not None:
        addr = wallet.addressbook[result]
        return addr


def select_from_addresses():
    droid.dialogCreateAlert("Addresses:")
    l = []
    addresses = wallet.addresses()
    for i in range(len(addresses)):
        addr = addresses[i]
        label = wallet.labels.get(addr,addr)
        l.append( label )
    droid.dialogSetItems(l)
    droid.dialogShow()
    response = droid.dialogGetResponse()
    result = response.result.get('item')
    droid.dialogDismiss()
    if result is not None:
        addr = addresses[result]
        return addr


def protocol_name(p):
    if p == 't': return 'TCP'
    if p == 'h': return 'HTTP'
    if p == 's': return 'SSL'
    if p == 'g': return 'HTTPS'


def protocol_dialog(host, protocol, z):
    droid.dialogCreateAlert('Protocol',host)
    if z:
        protocols = z.keys()
    else:
        protocols = 'thsg'
    l = []
    current = protocols.index(protocol)
    for p in protocols:
        l.append(protocol_name(p))
    droid.dialogSetSingleChoiceItems(l, current)
    droid.dialogSetPositiveButtonText('OK')
    droid.dialogSetNegativeButtonText('Cancel')
    droid.dialogShow()
    response = droid.dialogGetResponse().result
    selected_item = droid.dialogGetSelectedItems().result
    droid.dialogDismiss()

    if not response: return
    if not selected_item: return
    if response.get('which') == 'positive':
        return protocols[selected_item[0]]




def make_layout(s, scrollable = False):
    content = """

      <LinearLayout 
        android:id="@+id/zz"
        android:layout_width="match_parent"
        android:layout_height="wrap_content" 
        android:background="#ff222222">

        <TextView
          android:id="@+id/textElectrum"
          android:text="Electrum"
          android:textSize="7pt"
          android:textColor="#ff4444ff"
          android:gravity="left"
          android:layout_height="wrap_content"
          android:layout_width="match_parent"
        />
      </LinearLayout>

        %s   """%s

    if scrollable:
        content = """
      <ScrollView 
        android:id="@+id/scrollview"
        android:layout_width="match_parent"
        android:layout_height="match_parent" >

      <LinearLayout
        android:orientation="vertical" 
        android:layout_width="match_parent"
        android:layout_height="wrap_content" >

      %s

      </LinearLayout>
      </ScrollView>
      """%content


    return """<?xml version="1.0" encoding="utf-8"?>
      <LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
        android:id="@+id/background"
        android:orientation="vertical" 
        android:layout_width="match_parent"
        android:layout_height="match_parent" 
        android:background="#ff000022">

      %s 
      </LinearLayout>"""%content




def main_layout():
    return make_layout("""
        <TextView android:id="@+id/balanceTextView" 
                android:layout_width="match_parent"
                android:text=""
                android:textColor="#ffffffff"
                android:textAppearance="?android:attr/textAppearanceLarge" 
                android:padding="7dip"
                android:textSize="8pt"
                android:gravity="center_vertical|center_horizontal|left">
        </TextView>

        <TextView android:id="@+id/historyTextView" 
                android:layout_width="match_parent"
                android:layout_height="wrap_content" 
                android:text="Recent transactions"
                android:textAppearance="?android:attr/textAppearanceLarge" 
                android:gravity="center_vertical|center_horizontal|center">
        </TextView>

        %s """%get_history_layout(15),True)



def qr_layout(addr):
    return make_layout("""

     <TextView android:id="@+id/addrTextView" 
                android:layout_width="match_parent"
                android:layout_height="50" 
                android:text="%s"
                android:textAppearance="?android:attr/textAppearanceLarge" 
                android:gravity="center_vertical|center_horizontal|center">
     </TextView>

     <ImageView
        android:id="@+id/qrView"
        android:gravity="center"
        android:layout_width="match_parent"
        android:layout_height="350"
        android:antialias="false"
        android:src="file:///sdcard/sl4a/qrcode.bmp" /> 

     <TextView android:id="@+id/labelTextView" 
                android:layout_width="match_parent"
                android:layout_height="50" 
                android:text="%s"
                android:textAppearance="?android:attr/textAppearanceLarge" 
                android:gravity="center_vertical|center_horizontal|center">
     </TextView>

     """%(addr,wallet.labels.get(addr,'')), True)

payto_layout = make_layout("""

        <TextView android:id="@+id/recipientTextView" 
                android:layout_width="match_parent"
                android:layout_height="wrap_content" 
                android:text="Pay to:"
                android:textAppearance="?android:attr/textAppearanceLarge" 
                android:gravity="left">
        </TextView>


        <EditText android:id="@+id/recipient"
                android:layout_width="match_parent"
                android:layout_height="wrap_content" 
                android:tag="Tag Me" android:inputType="text">
        </EditText>

        <LinearLayout android:id="@+id/linearLayout1"
                android:layout_width="match_parent"
                android:layout_height="wrap_content">
                <Button android:id="@+id/buttonQR" android:layout_width="wrap_content"
                        android:layout_height="wrap_content" android:text="From QR code"></Button>
                <Button android:id="@+id/buttonContacts" android:layout_width="wrap_content"
                        android:layout_height="wrap_content" android:text="From Contacts"></Button>
        </LinearLayout>


        <TextView android:id="@+id/labelTextView" 
                android:layout_width="match_parent"
                android:layout_height="wrap_content" 
                android:text="Description:"
                android:textAppearance="?android:attr/textAppearanceLarge" 
                android:gravity="left">
        </TextView>

        <EditText android:id="@+id/label"
                android:layout_width="match_parent"
                android:layout_height="wrap_content" 
                android:tag="Tag Me" android:inputType="text">
        </EditText>

        <TextView android:id="@+id/amountLabelTextView" 
                android:layout_width="match_parent"
                android:layout_height="wrap_content" 
                android:text="Amount:"
                android:textAppearance="?android:attr/textAppearanceLarge" 
                android:gravity="left">
        </TextView>

        <EditText android:id="@+id/amount"
                android:layout_width="match_parent"
                android:layout_height="wrap_content" 
                android:tag="Tag Me" android:inputType="numberDecimal">
        </EditText>

        <LinearLayout android:layout_width="match_parent"
                android:layout_height="wrap_content" android:id="@+id/linearLayout1">
                <Button android:id="@+id/buttonPay" android:layout_width="wrap_content"
                        android:layout_height="wrap_content" android:text="Send"></Button>
        </LinearLayout>""",False)



settings_layout = make_layout(""" <ListView
           android:id="@+id/myListView" 
           android:layout_width="match_parent"
           android:layout_height="wrap_content" />""")



def get_history_values(n):
    values = []
    h = wallet.get_tx_history()
    length = min(n, len(h))
    for i in range(length):
        tx_hash, conf, is_mine, value, fee, balance, timestamp = h[-i-1]
        try:
            dt = datetime.datetime.fromtimestamp( timestamp )
            if dt.date() == dt.today().date():
                time_str = str( dt.time() )
            else:
                time_str = str( dt.date() )
        except Exception:
            time_str = 'pending'

        conf_str = 'v' if conf else 'o'
        label, is_default_label = wallet.get_label(tx_hash)
        values.append((conf_str, '  ' + time_str, '  ' + format_satoshis(value,True), '  ' + label ))

    return values


def get_history_layout(n):
    rows = ""
    i = 0
    values = get_history_values(n)
    for v in values:
        a,b,c,d = v
        color = "#ff00ff00" if a == 'v' else "#ffff0000"
        rows += """
        <TableRow>
          <TextView
            android:id="@+id/hl_%d_col1" 
            android:layout_column="0"
            android:text="%s"
            android:textColor="%s"
            android:padding="3" />
          <TextView
            android:id="@+id/hl_%d_col2" 
            android:layout_column="1"
            android:text="%s"
            android:padding="3" />
          <TextView
            android:id="@+id/hl_%d_col3" 
            android:layout_column="2"
            android:text="%s"
            android:padding="3" />
          <TextView
            android:id="@+id/hl_%d_col4" 
            android:layout_column="3"
            android:text="%s"
            android:padding="4" />
        </TableRow>"""%(i,a,color,i,b,i,c,i,d)
        i += 1

    output = """
<TableLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="fill_parent"
    android:layout_height="wrap_content"
    android:stretchColumns="0,1,2,3">
    %s
</TableLayout>"""% rows
    return output


def set_history_layout(n):
    values = get_history_values(n)
    i = 0
    for v in values:
        a,b,c,d = v
        droid.fullSetProperty("hl_%d_col1"%i,"text", a)

        if a == 'v':
            droid.fullSetProperty("hl_%d_col1"%i, "textColor","#ff00ff00")
        else:
            droid.fullSetProperty("hl_%d_col1"%i, "textColor","#ffff0000")

        droid.fullSetProperty("hl_%d_col2"%i,"text", b)
        droid.fullSetProperty("hl_%d_col3"%i,"text", c)
        droid.fullSetProperty("hl_%d_col4"%i,"text", d)
        i += 1




status_text = ''
def update_layout():
    global status_text
    if not network.is_connected():
        text = "Not connected..."
    elif not wallet.up_to_date:
        text = "Synchronizing..."
    else:
        c, u = wallet.get_balance()
        text = "Balance:"+format_satoshis(c) 
        if u : text += '   [' + format_satoshis(u,True).strip() + ']'


    # vibrate if status changed
    if text != status_text:
        if status_text and network.is_connected() and wallet.up_to_date:
            droid.vibrate()
        status_text = text

    droid.fullSetProperty("balanceTextView", "text", status_text)

    if wallet.up_to_date:
        set_history_layout(15)




def pay_to(recipient, amount, fee, label):

    if wallet.use_encryption:
        password  = droid.dialogGetPassword('Password').result
        if not password: return
    else:
        password = None

    droid.dialogCreateSpinnerProgress("Electrum", "signing transaction...")
    droid.dialogShow()

    try:
        tx = wallet.mktx( [(recipient, amount)], password, fee)
    except Exception as e:
        modal_dialog('error', e.message)
        droid.dialogDismiss()
        return

    if label: 
        wallet.labels[tx.hash()] = label

    droid.dialogDismiss()

    r, h = wallet.sendtx( tx )
    if r:
        modal_dialog('Payment sent', h)
        return True
    else:
        modal_dialog('Error', h)







def make_new_contact():
    code = droid.scanBarcode()
    r = code.result
    if r:
        data = r['extras']['SCAN_RESULT']
        if data:
            if re.match('^bitcoin:', data):
                address, _, _, _, _, _, _ = util.parse_url(data)
            elif is_valid(data):
                address = data
            else:
                address = None
            if address:
                if modal_question('Add to contacts?', address):
                    wallet.add_contact(address)
        else:
            modal_dialog('Invalid address', data)


do_refresh = False

def update_callback():
    global do_refresh
    print "gui callback", network.is_connected()
    do_refresh = True
    droid.eventPost("refresh",'z')

def main_loop():
    global do_refresh

    update_layout()
    out = None
    quitting = False
    while out is None:

        event = droid.eventWait(1000).result
        if event is None:
            if do_refresh: 
                update_layout()
                do_refresh = False
            continue

        print "got event in main loop", repr(event)
        if event == 'OK': continue
        if event is None: continue
        if not event.get("name"): continue

        # request 2 taps before we exit
        if event["name"]=="key":
            if event["data"]["key"] == '4':
                if quitting:
                    out = 'quit'
                else: 
                    quitting = True
        else: quitting = False

        if event["name"]=="click":
            id=event["data"]["id"]

        elif event["name"]=="settings":
            out = 'settings'

        elif event["name"] in menu_commands:
            out = event["name"]

            if out == 'contacts':
                global contact_addr
                contact_addr = select_from_contacts()
                if contact_addr == 'newcontact':
                    make_new_contact()
                    contact_addr = None
                if not contact_addr:
                    out = None

            elif out == "receive":
                global receive_addr
                receive_addr = select_from_addresses()
                if receive_addr:
                    amount = modal_input('Amount', 'Amount you want receive. ', '', "numberDecimal")
                    if amount:
                        receive_addr = 'bitcoin:%s?amount=%s'%(receive_addr, amount)

                if not receive_addr:
                    out = None


    return out
                    

def payto_loop():
    global recipient
    if recipient:
        droid.fullSetProperty("recipient","text",recipient)
        recipient = None

    out = None
    while out is None:
        event = droid.eventWait().result
        if not event: continue
        print "got event in payto loop", event
        if event == 'OK': continue
        if not event.get("name"): continue

        if event["name"] == "click":
            id = event["data"]["id"]

            if id=="buttonPay":

                droid.fullQuery()
                recipient = droid.fullQueryDetail("recipient").result.get('text')
                label  = droid.fullQueryDetail("label").result.get('text')
                amount = droid.fullQueryDetail('amount').result.get('text')

                if not is_valid(recipient):
                    modal_dialog('Error','Invalid Bitcoin address')
                    continue

                try:
                    amount = int( 100000000 * Decimal(amount) )
                except Exception:
                    modal_dialog('Error','Invalid amount')
                    continue

                result = pay_to(recipient, amount, wallet.fee, label)
                if result:
                    out = 'main'

            elif id=="buttonContacts":
                addr = select_from_contacts()
                droid.fullSetProperty("recipient","text",addr)

            elif id=="buttonQR":
                code = droid.scanBarcode()
                r = code.result
                if r:
                    data = r['extras']['SCAN_RESULT']
                    if data:
                        if re.match('^bitcoin:', data):
                            payto, amount, label, _, _, _, _ = util.parse_url(data)
                            droid.fullSetProperty("recipient", "text",payto)
                            droid.fullSetProperty("amount", "text", amount)
                            droid.fullSetProperty("label", "text", label)
                        else:
                            droid.fullSetProperty("recipient", "text", data)

                    
        elif event["name"] in menu_commands:
            out = event["name"]

        elif event["name"]=="key":
            if event["data"]["key"] == '4':
                out = 'main'

        #elif event["name"]=="screen":
        #    if event["data"]=="destroy":
        #        out = 'main'

    return out


receive_addr = ''
contact_addr = ''
recipient = ''

def receive_loop():
    out = None
    while out is None:
        event = droid.eventWait().result
        print "got event", event
        if event["name"]=="key":
            if event["data"]["key"] == '4':
                out = 'main'

        elif event["name"]=="clipboard":
            droid.setClipboard(receive_addr)
            modal_dialog('Address copied to clipboard',receive_addr)

        elif event["name"]=="edit":
            edit_label(receive_addr)

    return out

def contacts_loop():
    global recipient
    out = None
    while out is None:
        event = droid.eventWait().result
        print "got event", event
        if event["name"]=="key":
            if event["data"]["key"] == '4':
                out = 'main'

        elif event["name"]=="clipboard":
            droid.setClipboard(contact_addr)
            modal_dialog('Address copied to clipboard',contact_addr)

        elif event["name"]=="edit":
            edit_label(contact_addr)

        elif event["name"]=="paytocontact":
            recipient = contact_addr
            out = 'send'

        elif event["name"]=="deletecontact":
            if modal_question('delete contact', contact_addr):
                out = 'main'

    return out


def server_dialog(servers):
    droid.dialogCreateAlert("Public servers")
    droid.dialogSetItems( servers.keys() )
    droid.dialogSetPositiveButtonText('Private server')
    droid.dialogShow()
    response = droid.dialogGetResponse().result
    droid.dialogDismiss()
    if not response: return

    if response.get('which') == 'positive':
        return modal_input('Private server', None)

    i = response.get('item')
    if i is not None:
        response = servers.keys()[i]
        return response


def show_seed():
    if wallet.use_encryption:
        password  = droid.dialogGetPassword('Seed').result
        if not password: return
    else:
        password = None
    
    try:
        seed = wallet.get_seed(password)
    except Exception:
        modal_dialog('error','incorrect password')
        return

    modal_dialog('Your seed is',seed)
    modal_dialog('Mnemonic code:', ' '.join(mnemonic_encode(seed)) )

def change_password_dialog():
    if wallet.use_encryption:
        password  = droid.dialogGetPassword('Your wallet is encrypted').result
        if password is None: return
    else:
        password = None

    try:
        wallet.get_seed(password)
    except Exception:
        modal_dialog('error','incorrect password')
        return

    new_password  = droid.dialogGetPassword('Choose a password').result
    if new_password == None:
        return

    if new_password != '':
        password2  = droid.dialogGetPassword('Confirm new password').result
        if new_password != password2:
            modal_dialog('error','passwords do not match')
            return

    wallet.update_password(password, new_password)
    if new_password:
        modal_dialog('Password updated','your wallet is encrypted')
    else:
        modal_dialog('No password','your wallet is not encrypted')
    return True


def settings_loop():


    def set_listview():
        host, port, p = network.default_server.split(':')
        fee = str( Decimal( wallet.fee)/100000000 )
        is_encrypted = 'yes' if wallet.use_encryption else 'no'
        protocol = protocol_name(p)
        droid.fullShow(settings_layout)
        droid.fullSetList("myListView",['Server: ' + host, 'Protocol: '+ protocol, 'Port: '+port, 'Transaction fee: '+fee, 'Password: '+is_encrypted, 'Seed'])

    set_listview()

    out = None
    while out is None:
        event = droid.eventWait()
        event = event.result
        print "got event", event
        if event == 'OK': continue
        if not event: continue

        servers = network.get_servers()
        name = event.get("name")
        if not name: continue

        if name == "itemclick":
            pos = event["data"]["position"]
            host, port, protocol = network.default_server.split(':')
            network_changed = False

            if pos == "0": #server
                host = server_dialog(servers)
                if host:
                    p = servers[host]
                    port = p[protocol]
                    network_changed = True

            elif pos == "1": #protocol
                if host in servers:
                    protocol = protocol_dialog(host, protocol, servers[host])
                    z = servers[host]
                    port = z[protocol]
                    network_changed = True

            elif pos == "2": #port
                a_port = modal_input('Port number', 'If you use a public server, this field is set automatically when you set the protocol', port, "number")
                if a_port != port:
                    port = a_port
                    network_changed = True

            elif pos == "3": #fee
                fee = modal_input('Transaction fee', 'The fee will be this amount multiplied by the number of inputs in your transaction. ', str( Decimal( wallet.fee)/100000000 ), "numberDecimal")
                if fee:
                    try:
                        fee = int( 100000000 * Decimal(fee) )
                    except Exception:
                        modal_dialog('error','invalid fee value')
                    wallet.set_fee(fee)
                    set_listview()

            elif pos == "4":
                if change_password_dialog():
                    set_listview()

            elif pos == "5":
                show_seed()

            if network_changed:
                proxy = None
                auto_connect = False
                try:
                    network.set_parameters(host, port, protocol, proxy, auto_connect)
                except Exception:
                    modal_dialog('error','invalid server')
                set_listview()

        elif name in menu_commands:
            out = event["name"]

        elif name == 'cancel':
            out = 'main'

        elif name == "key":
            if event["data"]["key"] == '4':
                out = 'main'

    return out

def add_menu(s):
    droid.clearOptionsMenu()
    if s == 'main':
        droid.addOptionsMenuItem("Send","send",None,"")
        droid.addOptionsMenuItem("Receive","receive",None,"")
        droid.addOptionsMenuItem("Contacts","contacts",None,"")
        droid.addOptionsMenuItem("Settings","settings",None,"")
    elif s == 'receive':
        droid.addOptionsMenuItem("Copy","clipboard",None,"")
        droid.addOptionsMenuItem("Label","edit",None,"")
    elif s == 'contacts':
        droid.addOptionsMenuItem("Copy","clipboard",None,"")
        droid.addOptionsMenuItem("Label","edit",None,"")
        droid.addOptionsMenuItem("Pay to","paytocontact",None,"")
        #droid.addOptionsMenuItem("Delete","deletecontact",None,"")


def make_bitmap(addr):
    # fixme: this is highly inefficient
    droid.dialogCreateSpinnerProgress("please wait")
    droid.dialogShow()
    try:
        import pyqrnative, bmp
        qr = pyqrnative.QRCode(4, pyqrnative.QRErrorCorrectLevel.L)
        qr.addData(addr)
        qr.make()
        k = qr.getModuleCount()
        assert k == 33
        bmp.save_qrcode(qr,"/sdcard/sl4a/qrcode.bmp")
    finally:
        droid.dialogDismiss()

        


droid = android.Android()
menu_commands = ["send", "receive", "settings", "contacts", "main"]
wallet = None
network = None

class ElectrumGui:

    def __init__(self, config, _network):
        global wallet, network
        network = _network
        network.register_callback('updated', update_callback)
        network.register_callback('connected', update_callback)
        network.register_callback('disconnected', update_callback)
        network.register_callback('disconnecting', update_callback)
        
        storage = WalletStorage(config)
        if not storage.file_exists:
            action = self.restore_or_create()
            if not action: exit()

            wallet = Wallet(storage)
            if action == 'create':
                wallet.init_seed(None)
                self.show_seed()
                wallet.save_seed(None)
                wallet.synchronize()  # generate first addresses offline
                
            elif action == 'restore':
                seed = self.seed_dialog()
                if not seed:
                    exit()
                wallet.init_seed(str(seed))
                wallet.save_seed(None)
            else:
                exit()

            wallet.start_threads(network)

            if action == 'restore':
                if not self.restore_wallet():
                    exit()

            self.password_dialog()

        else:
            wallet = Wallet(storage)
            wallet.start_threads(network)


    def main(self, url):
        s = 'main'
        while True:
            add_menu(s)
            if s == 'main':
                droid.fullShow(main_layout())
                s = main_loop()

            elif s == 'send':
                droid.fullShow(payto_layout)
                s = payto_loop()

            elif s == 'receive':
                make_bitmap(receive_addr)
                droid.fullShow(qr_layout(receive_addr))
                s = receive_loop()

            elif s == 'contacts':
                make_bitmap(contact_addr)
                droid.fullShow(qr_layout(contact_addr))
                s = contacts_loop()

            elif s == 'settings':
                s = settings_loop()

            else:
                break

        droid.makeToast("Bye!")


    def restore_or_create(self):
        droid.dialogCreateAlert("Wallet not found","Do you want to create a new wallet, or restore an existing one?")
        droid.dialogSetPositiveButtonText('Create')
        droid.dialogSetNeutralButtonText('Restore')
        droid.dialogSetNegativeButtonText('Cancel')
        droid.dialogShow()
        response = droid.dialogGetResponse().result
        droid.dialogDismiss()
        if not response: return
        if response.get('which') == 'negative':
            return

        return 'restore' if response.get('which') == 'neutral' else 'create'


    def seed_dialog(self):
        if modal_question("Enter your seed","Input method",'QR Code', 'mnemonic'):
            code = droid.scanBarcode()
            r = code.result
            if r:
                seed = r['extras']['SCAN_RESULT']
            else:
                return
        else:
            m = modal_input('Mnemonic','please enter your code')
            try:
                seed = mnemonic_decode(m.split(' '))
            except Exception:
                modal_dialog('error: could not decode this seed')
                return

        return str(seed)


    def network_dialog(self):
        return True

        
    def show_seed(self):
        modal_dialog('Your seed is:', wallet.seed)
        modal_dialog('Mnemonic code:', ' '.join(mnemonic_encode(wallet.seed)) )


    def password_dialog(self):
        change_password_dialog()


    def restore_wallet(self):

        msg = "recovering wallet..."
        droid.dialogCreateSpinnerProgress("Electrum", msg)
        droid.dialogShow()

        wallet.restore(lambda x: None)

        droid.dialogDismiss()
        droid.vibrate()

        if wallet.is_found():
            wallet.fill_addressbook()
            modal_dialog("recovery successful")
        else:
            if not modal_question("no transactions found for this seed","do you want to keep this wallet?"):
                return False

        return True


########NEW FILE########
__FILENAME__ = gtk
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import datetime
import thread, time, ast, sys, re
import socket, traceback
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, cairo
from decimal import Decimal
from electrum.util import print_error
from electrum.bitcoin import is_valid
from electrum import mnemonic, pyqrnative, WalletStorage, Wallet

Gdk.threads_init()
APP_NAME = "Electrum"
import platform
MONOSPACE_FONT = 'Lucida Console' if platform.system() == 'Windows' else 'monospace'

from electrum.util import format_satoshis, parse_url
from electrum.network import DEFAULT_SERVERS
from electrum.bitcoin import MIN_RELAY_TX_FEE

def numbify(entry, is_int = False):
    text = entry.get_text().strip()
    chars = '0123456789'
    if not is_int: chars +='.'
    s = ''.join([i for i in text if i in chars])
    if not is_int:
        if '.' in s:
            p = s.find('.')
            s = s.replace('.','')
            s = s[:p] + '.' + s[p:p+8]
        try:
            amount = int( Decimal(s) * 100000000 )
        except Exception:
            amount = None
    else:
        try:
            amount = int( s )
        except Exception:
            amount = None
    entry.set_text(s)
    return amount




def show_seed_dialog(seed, parent):
    if not seed:
        show_message("No seed")
        return

    dialog = Gtk.MessageDialog(
        parent = parent,
        flags = Gtk.DialogFlags.MODAL, 
        buttons = Gtk.ButtonsType.OK, 
        message_format = "Your wallet generation seed is:\n\n" + '"' + seed + '"'\
            + "\n\nPlease keep it in a safe place; if you lose it, you will not be able to restore your wallet.\n\n" )
    dialog.set_title("Seed")
    dialog.show()
    dialog.run()
    dialog.destroy()

def restore_create_dialog():

    # ask if the user wants to create a new wallet, or recover from a seed. 
    # if he wants to recover, and nothing is found, do not create wallet
    dialog = Gtk.Dialog("electrum", parent=None, 
                        flags=Gtk.DialogFlags.MODAL,
                        buttons= ("create", 0, "restore",1, "cancel",2)  )

    label = Gtk.Label("Wallet file not found.\nDo you want to create a new wallet,\n or to restore an existing one?"  )
    label.show()
    dialog.vbox.pack_start(label, True, True, 0)
    dialog.show()
    r = dialog.run()
    dialog.destroy()

    if r==2: return False
    return 'restore' if r==1 else 'create'



def run_recovery_dialog():
    message = "Please enter your wallet seed or the corresponding mnemonic list of words, and the gap limit of your wallet."
    dialog = Gtk.MessageDialog(
        parent = None,
        flags = Gtk.DialogFlags.MODAL, 
        buttons = Gtk.ButtonsType.OK_CANCEL,
        message_format = message)

    vbox = dialog.vbox
    dialog.set_default_response(Gtk.ResponseType.OK)

    # ask seed, server and gap in the same dialog
    seed_box = Gtk.HBox()
    seed_label = Gtk.Label(label='Seed or mnemonic:')
    seed_label.set_size_request(150,-1)
    seed_box.pack_start(seed_label, False, False, 10)
    seed_label.show()
    seed_entry = Gtk.Entry()
    seed_entry.show()
    seed_entry.set_size_request(450,-1)
    seed_box.pack_start(seed_entry, False, False, 10)
    add_help_button(seed_box, '.')
    seed_box.show()
    vbox.pack_start(seed_box, False, False, 5)    

    dialog.show()
    r = dialog.run()
    seed = seed_entry.get_text()
    dialog.destroy()

    if r==Gtk.ResponseType.CANCEL:
        return False

    if Wallet.is_seed(seed):
        return seed

    show_message("no seed")
    return False



def run_settings_dialog(self):

    message = "Here are the settings of your wallet. For more explanations, click on the question mark buttons next to each input field."
        
    dialog = Gtk.MessageDialog(
        parent = self.window,
        flags = Gtk.DialogFlags.MODAL, 
        buttons = Gtk.ButtonsType.OK_CANCEL,
        message_format = message)

    image = Gtk.Image()
    image.set_from_stock(Gtk.STOCK_PREFERENCES, Gtk.IconSize.DIALOG)
    image.show()
    dialog.set_image(image)
    dialog.set_title("Settings")

    vbox = dialog.vbox
    dialog.set_default_response(Gtk.ResponseType.OK)

    fee = Gtk.HBox()
    fee_entry = Gtk.Entry()
    fee_label = Gtk.Label(label='Transaction fee:')
    fee_label.set_size_request(150,10)
    fee_label.show()
    fee.pack_start(fee_label,False, False, 10)
    fee_entry.set_text( str( Decimal(self.wallet.fee) /100000000 ) )
    fee_entry.connect('changed', numbify, False)
    fee_entry.show()
    fee.pack_start(fee_entry,False,False, 10)
    add_help_button(fee, 'Fee per kilobyte of transaction. Recommended value:0.0001')
    fee.show()
    vbox.pack_start(fee, False,False, 5)
            
    nz = Gtk.HBox()
    nz_entry = Gtk.Entry()
    nz_label = Gtk.Label(label='Display zeros:')
    nz_label.set_size_request(150,10)
    nz_label.show()
    nz.pack_start(nz_label,False, False, 10)
    nz_entry.set_text( str( self.num_zeros ))
    nz_entry.connect('changed', numbify, True)
    nz_entry.show()
    nz.pack_start(nz_entry,False,False, 10)
    add_help_button(nz, "Number of zeros displayed after the decimal point.\nFor example, if this number is 2, then '5.' is displayed as '5.00'")
    nz.show()
    vbox.pack_start(nz, False,False, 5)
            
    dialog.show()
    r = dialog.run()
    fee = fee_entry.get_text()
    nz = nz_entry.get_text()
        
    dialog.destroy()
    if r==Gtk.ResponseType.CANCEL:
        return

    try:
        fee = int( 100000000 * Decimal(fee) )
    except Exception:
        show_message("error")
        return
    self.wallet.set_fee(fee)

    try:
        nz = int( nz )
        if nz>8: nz = 8
    except Exception:
        show_message("error")
        return

    if self.num_zeros != nz:
        self.num_zeros = nz
        self.config.set_key('num_zeros',nz,True)
        self.update_history_tab()




def run_network_dialog( network, parent ):
    image = Gtk.Image()
    image.set_from_stock(Gtk.STOCK_NETWORK, Gtk.IconSize.DIALOG)
    if parent:
        if network.is_connected():
            interface = network.interface
            status = "Connected to %s:%d\n%d blocks"%(interface.host, interface.port, network.blockchain.height())
        else:
            status = "Not connected"
    else:
        import random
        status = "Please choose a server.\nSelect cancel if you are offline."

    if network.is_connected():
        server = interface.server
        host, port, protocol = server.split(':')

    servers = network.get_servers()

    dialog = Gtk.MessageDialog( parent, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                    Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL, status)
    dialog.set_title("Server")
    dialog.set_image(image)
    image.show()
    
    vbox = dialog.vbox
    host_box = Gtk.HBox()
    host_label = Gtk.Label(label='Connect to:')
    host_label.set_size_request(100,-1)
    host_label.show()
    host_box.pack_start(host_label, False, False, 10)
    host_entry = Gtk.Entry()
    host_entry.set_size_request(200,-1)
    if network.is_connected():
        host_entry.set_text(server)
    else:
        host_entry.set_text("Not Connected")
    host_entry.show()
    host_box.pack_start(host_entry, False, False, 10)
    add_help_button(host_box, 'The name, port number and protocol of your Electrum server, separated by a colon. Example: "ecdsa.org:50002:s". Some servers allow you to connect through http (port 80) or https (port 443)')
    host_box.show()

    p_box = Gtk.HBox(False, 10)
    p_box.show()

    p_label = Gtk.Label(label='Protocol:')
    p_label.set_size_request(100,-1)
    p_label.show()
    p_box.pack_start(p_label, False, False, 10)

    combobox = Gtk.ComboBoxText()
    combobox.show()
    combobox.append_text("TCP")
    combobox.append_text("SSL")
    combobox.append_text("HTTP")
    combobox.append_text("HTTPS")

    p_box.pack_start(combobox, True, True, 0)

    def current_line():
        return unicode(host_entry.get_text()).split(':')

    def set_combobox(protocol):
        combobox.set_active('tshg'.index(protocol))

    def set_protocol(protocol):
        host = current_line()[0]
        pp = servers[host]
        if protocol not in pp.keys():
            protocol = pp.keys()[0]
            set_combobox(protocol)
        port = pp[protocol]
        host_entry.set_text( host + ':' + port + ':' + protocol)

    combobox.connect("changed", lambda x:set_protocol('tshg'[combobox.get_active()]))
    if network.is_connected():
        set_combobox(protocol)
        
    server_list = Gtk.ListStore(str)
    for host in servers.keys():
        server_list.append([host])
    
    treeview = Gtk.TreeView(model=server_list)
    treeview.show()

    label = 'Active Servers' if network.irc_servers else 'Default Servers'
    tvcolumn = Gtk.TreeViewColumn(label)
    treeview.append_column(tvcolumn)
    cell = Gtk.CellRendererText()
    tvcolumn.pack_start(cell, False)
    tvcolumn.add_attribute(cell, 'text', 0)

    vbox.pack_start(host_box, False,False, 5)
    vbox.pack_start(p_box, True, True, 0)

    #scroll = Gtk.ScrolledWindow()
    #scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.ALWAYS)
    #scroll.add_with_viewport(treeview)
    #scroll.show()
    #vbox.pack_start(scroll, True)
    vbox.pack_start(treeview, True, True, 0)

    def my_treeview_cb(treeview):
        path, view_column = treeview.get_cursor()
        host = server_list.get_value( server_list.get_iter(path), 0)

        pp = servers[host]
        if 't' in pp.keys():
            protocol = 't'
        else:
            protocol = pp.keys()[0]
        port = pp[protocol]
        host_entry.set_text( host + ':' + port + ':' + protocol)
        set_combobox(protocol)

    treeview.connect('cursor-changed', my_treeview_cb)

    dialog.show_all()
    r = dialog.run()
    server = host_entry.get_text()
    dialog.destroy()

    if r==Gtk.ResponseType.CANCEL:
        return False

    try:
        host, port, protocol = server.split(':')
        proxy = network.config.get('proxy')
        auto_connect = network.config.get('auto_cycle')
        network.set_parameters(host, port, protocol, proxy, auto_connect)
    except Exception:
        show_message("error:" + server)
        return False





def show_message(message, parent=None):
    dialog = Gtk.MessageDialog(
        parent = parent,
        flags = Gtk.DialogFlags.MODAL, 
        buttons = Gtk.ButtonsType.CLOSE, 
        message_format = message )
    dialog.show()
    dialog.run()
    dialog.destroy()

def password_line(label):
    password = Gtk.HBox()
    password_label = Gtk.Label(label=label)
    password_label.set_size_request(120,10)
    password_label.show()
    password.pack_start(password_label,False, False, 10)
    password_entry = Gtk.Entry()
    password_entry.set_size_request(300,-1)
    password_entry.set_visibility(False)
    password_entry.show()
    password.pack_start(password_entry,False,False, 10)
    password.show()
    return password, password_entry

def password_dialog(parent):
    dialog = Gtk.MessageDialog( parent, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL,  "Please enter your password.")
    dialog.get_image().set_visible(False)
    current_pw, current_pw_entry = password_line('Password:')
    current_pw_entry.connect("activate", lambda entry, dialog, response: dialog.response(response), dialog, Gtk.ResponseType.OK)
    dialog.vbox.pack_start(current_pw, False, True, 0)
    dialog.show()
    result = dialog.run()
    pw = current_pw_entry.get_text()
    dialog.destroy()
    if result != Gtk.ResponseType.CANCEL: return pw


def change_password_dialog(is_encrypted, parent):

    if parent:
        msg = 'Your wallet is encrypted. Use this dialog to change the password. To disable wallet encryption, enter an empty new password.' if is_encrypted else 'Your wallet keys are not encrypted'
    else:
        msg = "Please choose a password to encrypt your wallet keys"

    dialog = Gtk.MessageDialog( parent, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL, msg)
    dialog.set_title("Change password")
    image = Gtk.Image()
    image.set_from_stock(Gtk.STOCK_DIALOG_AUTHENTICATION, Gtk.IconSize.DIALOG)
    image.show()
    dialog.set_image(image)

    if is_encrypted:
        current_pw, current_pw_entry = password_line('Current password:')
        dialog.vbox.pack_start(current_pw, False, True, 0)

    password, password_entry = password_line('New password:')
    dialog.vbox.pack_start(password, False, True, 5)
    password2, password2_entry = password_line('Confirm password:')
    dialog.vbox.pack_start(password2, False, True, 5)

    dialog.show()
    result = dialog.run()
    password = current_pw_entry.get_text() if is_encrypted else None
    new_password = password_entry.get_text()
    new_password2 = password2_entry.get_text()
    dialog.destroy()
    if result == Gtk.ResponseType.CANCEL: 
        return

    if new_password != new_password2:
        show_message("passwords do not match")
        return change_password_dialog(is_encrypted, parent)

    if not new_password:
        new_password = None

    return True, password, new_password



def add_help_button(hbox, message):
    button = Gtk.Button('?')
    button.connect("clicked", lambda x: show_message(message))
    button.show()
    hbox.pack_start(button,False, False, 0)


class MyWindow(Gtk.Window): __gsignals__ = dict( mykeypress = (GObject.SignalFlags.RUN_LAST | GObject.SignalFlags.ACTION, None, (str,)) )

GObject.type_register(MyWindow)
#FIXME: can't find docs how to create keybindings in PyGI
#Gtk.binding_entry_add_signall(MyWindow, Gdk.KEY_W, Gdk.ModifierType.CONTROL_MASK, 'mykeypress', ['ctrl+W'])
#Gtk.binding_entry_add_signall(MyWindow, Gdk.KEY_Q, Gdk.ModifierType.CONTROL_MASK, 'mykeypress', ['ctrl+Q'])


class ElectrumWindow:

    def show_message(self, msg):
        show_message(msg, self.window)

    def __init__(self, wallet, config, network):
        self.config = config
        self.wallet = wallet
        self.network = network
        self.funds_error = False # True if not enough funds
        self.num_zeros = int(self.config.get('num_zeros',0))

        self.window = MyWindow(Gtk.WindowType.TOPLEVEL)
        title = 'Electrum ' + self.wallet.electrum_version + '  -  ' + self.config.path
        if not self.wallet.seed: title += ' [seedless]'
        self.window.set_title(title)
        self.window.connect("destroy", Gtk.main_quit)
        self.window.set_border_width(0)
        self.window.connect('mykeypress', Gtk.main_quit)
        self.window.set_default_size(720, 350)
        self.wallet_updated = False

        vbox = Gtk.VBox()

        self.notebook = Gtk.Notebook()
        self.create_history_tab()
        if self.wallet.seed:
            self.create_send_tab()
        self.create_recv_tab()
        self.create_book_tab()
        self.create_about_tab()
        self.notebook.show()
        vbox.pack_start(self.notebook, True, True, 2)
        
        self.status_bar = Gtk.Statusbar()
        vbox.pack_start(self.status_bar, False, False, 0)

        self.status_image = Gtk.Image()
        self.status_image.set_from_stock(Gtk.STOCK_NO, Gtk.IconSize.MENU)
        self.status_image.set_alignment(True, 0.5  )
        self.status_image.show()

        self.network_button = Gtk.Button()
        self.network_button.connect("clicked", lambda x: run_network_dialog(self.network, self.window) )
        self.network_button.add(self.status_image)
        self.network_button.set_relief(Gtk.ReliefStyle.NONE)
        self.network_button.show()
        self.status_bar.pack_end(self.network_button, False, False, 0)

        if self.wallet.seed:
            def seedb(w, wallet):
                if wallet.use_encryption:
                    password = password_dialog(self.window)
                    if not password: return
                else: password = None
                seed = wallet.get_mnemonic(password)
                show_seed_dialog(seed, self.window)
            button = Gtk.Button('S')
            button.connect("clicked", seedb, self.wallet )
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.show()
            self.status_bar.pack_end(button,False, False, 0)

        settings_icon = Gtk.Image()
        settings_icon.set_from_stock(Gtk.STOCK_PREFERENCES, Gtk.IconSize.MENU)
        settings_icon.set_alignment(0.5, 0.5)
        settings_icon.set_size_request(16,16 )
        settings_icon.show()

        prefs_button = Gtk.Button()
        prefs_button.connect("clicked", lambda x: run_settings_dialog(self) )
        prefs_button.add(settings_icon)
        prefs_button.set_tooltip_text("Settings")
        prefs_button.set_relief(Gtk.ReliefStyle.NONE)
        prefs_button.show()
        self.status_bar.pack_end(prefs_button,False,False, 0)

        self.pw_icon = Gtk.Image()
        self.pw_icon.set_from_stock(Gtk.STOCK_DIALOG_AUTHENTICATION, Gtk.IconSize.MENU)
        self.pw_icon.set_alignment(0.5, 0.5)
        self.pw_icon.set_size_request(16,16 )
        self.pw_icon.show()

        if self.wallet.seed:

            if self.wallet.use_encryption:
                self.pw_icon.set_tooltip_text('Wallet is encrypted')
            else:
                self.pw_icon.set_tooltip_text('Wallet is unencrypted')

            password_button = Gtk.Button()
            password_button.connect("clicked", self.do_update_password, self.wallet)
            password_button.add(self.pw_icon)
            password_button.set_relief(Gtk.ReliefStyle.NONE)
            password_button.show()
            self.status_bar.pack_end(password_button,False,False, 0)

        self.window.add(vbox)
        self.window.show_all()
        #self.fee_box.hide()

        self.context_id = self.status_bar.get_context_id("statusbar")
        self.update_status_bar()

        self.network.register_callback('updated', self.update_callback)


        def update_status_bar_thread():
            while True:
                GObject.idle_add( self.update_status_bar )
                time.sleep(0.5)


        def check_recipient_thread():
            old_r = ''
            while True:
                time.sleep(0.5)
                if self.payto_entry.is_focus():
                    continue
                r = self.payto_entry.get_text()
                if r != old_r:
                    old_r = r
                    r = r.strip()
                    if re.match('^(|([\w\-\.]+)@)((\w[\w\-]+\.)+[\w\-]+)$', r):
                        try:
                            to_address = self.wallet.get_alias(r, interactive=False)
                        except Exception:
                            continue
                        if to_address:
                            s = r + ' <' + to_address + '>'
                            GObject.idle_add( lambda: self.payto_entry.set_text(s) )
                

        thread.start_new_thread(update_status_bar_thread, ())
        if self.wallet.seed:
            thread.start_new_thread(check_recipient_thread, ())
        self.notebook.set_current_page(0)

    def update_callback(self):
        self.wallet_updated = True

    def do_update_password(self, button, wallet):
        if not wallet.seed:
            show_message("No seed")
            return

        res = change_password_dialog(wallet.use_encryption, self.window)
        if res:
            _, password, new_password = res

            try:
                wallet.get_seed(password)
            except Exception:
                show_message("Incorrect password")
                return

            wallet.update_password(password, new_password)

            if wallet.use_encryption:
                self.pw_icon.set_tooltip_text('Wallet is encrypted')
            else:
                self.pw_icon.set_tooltip_text('Wallet is unencrypted')


    def add_tab(self, page, name):
        tab_label = Gtk.Label(label=name)
        tab_label.show()
        self.notebook.append_page(page, tab_label)


    def create_send_tab(self):
        
        page = vbox = Gtk.VBox()
        page.show()

        payto = Gtk.HBox()
        payto_label = Gtk.Label(label='Pay to:')
        payto_label.set_size_request(100,-1)
        payto.pack_start(payto_label, False, False, 0)
        payto_entry = Gtk.Entry()
        payto_entry.set_size_request(450, 26)
        payto.pack_start(payto_entry, False, False, 0)
        vbox.pack_start(payto, False, False, 5)

        message = Gtk.HBox()
        message_label = Gtk.Label(label='Description:')
        message_label.set_size_request(100,-1)
        message.pack_start(message_label, False, False, 0)
        message_entry = Gtk.Entry()
        message_entry.set_size_request(450, 26)
        message.pack_start(message_entry, False, False, 0)
        vbox.pack_start(message, False, False, 5)

        amount_box = Gtk.HBox()
        amount_label = Gtk.Label(label='Amount:')
        amount_label.set_size_request(100,-1)
        amount_box.pack_start(amount_label, False, False, 0)
        amount_entry = Gtk.Entry()
        amount_entry.set_size_request(120, -1)
        amount_box.pack_start(amount_entry, False, False, 0)
        vbox.pack_start(amount_box, False, False, 5)

        self.fee_box = fee_box = Gtk.HBox()
        fee_label = Gtk.Label(label='Fee:')
        fee_label.set_size_request(100,-1)
        fee_box.pack_start(fee_label, False, False, 0)
        fee_entry = Gtk.Entry()
        fee_entry.set_size_request(60, 26)
        fee_box.pack_start(fee_entry, False, False, 0)
        vbox.pack_start(fee_box, False, False, 5)

        end_box = Gtk.HBox()
        empty_label = Gtk.Label(label='')
        empty_label.set_size_request(100,-1)
        end_box.pack_start(empty_label, False, False, 0)
        send_button = Gtk.Button("Send")
        send_button.show()
        end_box.pack_start(send_button, False, False, 0)
        clear_button = Gtk.Button("Clear")
        clear_button.show()
        end_box.pack_start(clear_button, False, False, 15)
        send_button.connect("clicked", self.do_send, (payto_entry, message_entry, amount_entry, fee_entry))
        clear_button.connect("clicked", self.do_clear, (payto_entry, message_entry, amount_entry, fee_entry))

        vbox.pack_start(end_box, False, False, 5)

        # display this line only if there is a signature
        payto_sig = Gtk.HBox()
        payto_sig_id = Gtk.Label(label='')
        payto_sig.pack_start(payto_sig_id, False, False, 0)
        vbox.pack_start(payto_sig, True, True, 5)
        

        self.user_fee = False

        def entry_changed( entry, is_fee ):
            self.funds_error = False
            amount = numbify(amount_entry)
            fee = numbify(fee_entry)
            if not is_fee: fee = None
            if amount is None:
                return
            #assume two outputs - one for change
            inputs, total, fee = self.wallet.choose_tx_inputs( amount, fee, 2 )
            if not is_fee:
                fee_entry.set_text( str( Decimal( fee ) / 100000000 ) )
                self.fee_box.show()
            if inputs:
                amount_entry.modify_text(Gtk.StateType.NORMAL, Gdk.color_parse("#000000"))
                fee_entry.modify_text(Gtk.StateType.NORMAL, Gdk.color_parse("#000000"))
                send_button.set_sensitive(True)
            else:
                send_button.set_sensitive(False)
                amount_entry.modify_text(Gtk.StateType.NORMAL, Gdk.color_parse("#cc0000"))
                fee_entry.modify_text(Gtk.StateType.NORMAL, Gdk.color_parse("#cc0000"))
                self.funds_error = True

        amount_entry.connect('changed', entry_changed, False)
        fee_entry.connect('changed', entry_changed, True)        

        self.payto_entry = payto_entry
        self.payto_fee_entry = fee_entry
        self.payto_sig_id = payto_sig_id
        self.payto_sig = payto_sig
        self.amount_entry = amount_entry
        self.message_entry = message_entry
        self.add_tab(page, 'Send')

    def set_frozen(self,entry,frozen):
        if frozen:
            entry.set_editable(False)
            entry.set_has_frame(False)
            entry.modify_base(Gtk.StateType.NORMAL, Gdk.color_parse("#eeeeee"))
        else:
            entry.set_editable(True)
            entry.set_has_frame(True)
            entry.modify_base(Gtk.StateType.NORMAL, Gdk.color_parse("#ffffff"))

    def set_url(self, url):
        payto, amount, label, message, payment_request, url = parse_url(url)
        self.notebook.set_current_page(1)
        self.payto_entry.set_text(payto)
        self.message_entry.set_text(message)
        self.amount_entry.set_text(amount)
        self.payto_sig.set_visible(False)

    def create_about_tab(self):
        from gi.repository import Pango
        page = Gtk.VBox()
        page.show()
        tv = Gtk.TextView()
        tv.set_editable(False)
        tv.set_cursor_visible(False)
        tv.modify_font(Pango.FontDescription(MONOSPACE_FONT))
        scroll = Gtk.ScrolledWindow()
        scroll.add(tv)
        page.pack_start(scroll, True, True, 0)
        self.info = tv.get_buffer()
        self.add_tab(page, 'Wall')

    def do_clear(self, w, data):
        self.payto_sig.set_visible(False)
        self.payto_fee_entry.set_text('')
        for entry in [self.payto_entry,self.amount_entry,self.message_entry]:
            self.set_frozen(entry,False)
            entry.set_text('')

    def question(self,msg):
        dialog = Gtk.MessageDialog( self.window, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.QUESTION, Gtk.ButtonsType.OK_CANCEL, msg)
        dialog.show()
        result = dialog.run()
        dialog.destroy()
        return result == Gtk.ResponseType.OK

    def do_send(self, w, data):
        payto_entry, label_entry, amount_entry, fee_entry = data
        label = label_entry.get_text()
        r = payto_entry.get_text()
        r = r.strip()

        m1 = re.match('^(|([\w\-\.]+)@)((\w[\w\-]+\.)+[\w\-]+)$', r)
        m2 = re.match('(|([\w\-\.]+)@)((\w[\w\-]+\.)+[\w\-]+) \<([1-9A-HJ-NP-Za-km-z]{26,})\>', r)
        
        if m1:
            to_address = self.wallet.get_alias(r, True, self.show_message, self.question)
            if not to_address:
                return
            else:
                self.update_sending_tab()

        elif m2:
            to_address = m2.group(5)
        else:
            to_address = r

        if not is_valid(to_address):
            self.show_message( "invalid bitcoin address:\n"+to_address)
            return

        try:
            amount = int( Decimal(amount_entry.get_text()) * 100000000 )
        except Exception:
            self.show_message( "invalid amount")
            return
        try:
            fee = int( Decimal(fee_entry.get_text()) * 100000000 )
        except Exception:
            self.show_message( "invalid fee")
            return

        if self.wallet.use_encryption:
            password = password_dialog(self.window)
            if not password:
                return
        else:
            password = None

        try:
            tx = self.wallet.mktx( [(to_address, amount)], password, fee )
        except Exception as e:
            self.show_message(str(e))
            return

        if tx.requires_fee(self.wallet.verifier) and fee < MIN_RELAY_TX_FEE:
            self.show_message( "This transaction requires a higher fee, or it will not be propagated by the network." )
            return

            
        if label: 
            self.wallet.labels[tx.hash()] = label

        status, msg = self.wallet.sendtx( tx )
        if status:
            self.show_message( "payment sent.\n" + msg )
            payto_entry.set_text("")
            label_entry.set_text("")
            amount_entry.set_text("")
            fee_entry.set_text("")
            #self.fee_box.hide()
            self.update_sending_tab()
        else:
            self.show_message( msg )


    def treeview_button_press(self, treeview, event):
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            c = treeview.get_cursor()[0]
            if treeview == self.history_treeview:
                tx_details = self.history_list.get_value( self.history_list.get_iter(c), 8)
                self.show_message(tx_details)
            elif treeview == self.contacts_treeview:
                m = self.addressbook_list.get_value( self.addressbook_list.get_iter(c), 0)
                #a = self.wallet.aliases.get(m)
                #if a:
                #    if a[0] in self.wallet.authorities.keys():
                #        s = self.wallet.authorities.get(a[0])
                #    else:
                #        s = "self-signed"
                #    msg = 'Alias: '+ m + '\nTarget address: '+ a[1] + '\n\nSigned by: ' + s + '\nSigning address:' + a[0]
                #    self.show_message(msg)
            

    def treeview_key_press(self, treeview, event):
        c = treeview.get_cursor()[0]
        if event.keyval == Gdk.KEY_Up:
            if c and c[0] == 0:
                treeview.parent.grab_focus()
                treeview.set_cursor((0,))
        elif event.keyval == Gdk.KEY_Return:
            if treeview == self.history_treeview:
                tx_details = self.history_list.get_value( self.history_list.get_iter(c), 8)
                self.show_message(tx_details)
            elif treeview == self.contacts_treeview:
                m = self.addressbook_list.get_value( self.addressbook_list.get_iter(c), 0)
                #a = self.wallet.aliases.get(m)
                #if a:
                #    if a[0] in self.wallet.authorities.keys():
                #        s = self.wallet.authorities.get(a[0])
                #    else:
                #        s = "self"
                #    msg = 'Alias:'+ m + '\n\nTarget: '+ a[1] + '\nSigned by: ' + s + '\nSigning address:' + a[0]
                #    self.show_message(msg)

        return False

    def create_history_tab(self):

        self.history_list = Gtk.ListStore(str, str, str, str, 'gboolean',  str, str, str, str)
        treeview = Gtk.TreeView(model=self.history_list)
        self.history_treeview = treeview
        treeview.set_tooltip_column(7)
        treeview.show()
        treeview.connect('key-press-event', self.treeview_key_press)
        treeview.connect('button-press-event', self.treeview_button_press)

        tvcolumn = Gtk.TreeViewColumn('')
        treeview.append_column(tvcolumn)
        cell = Gtk.CellRendererPixbuf()
        tvcolumn.pack_start(cell, False)
        tvcolumn.set_attributes(cell, stock_id=1)

        tvcolumn = Gtk.TreeViewColumn('Date')
        treeview.append_column(tvcolumn)
        cell = Gtk.CellRendererText()
        tvcolumn.pack_start(cell, False)
        tvcolumn.add_attribute(cell, 'text', 2)

        tvcolumn = Gtk.TreeViewColumn('Description')
        treeview.append_column(tvcolumn)
        cell = Gtk.CellRendererText()
        cell.set_property('foreground', 'grey')
        cell.set_property('family', MONOSPACE_FONT)
        cell.set_property('editable', True)
        def edited_cb(cell, path, new_text, h_list):
            tx = h_list.get_value( h_list.get_iter(path), 0)
            self.wallet.set_label(tx,new_text)
            self.update_history_tab()
        cell.connect('edited', edited_cb, self.history_list)
        def editing_started(cell, entry, path, h_list):
            tx = h_list.get_value( h_list.get_iter(path), 0)
            if not self.wallet.labels.get(tx): entry.set_text('')
        cell.connect('editing-started', editing_started, self.history_list)
        tvcolumn.set_expand(True)
        tvcolumn.pack_start(cell, True)
        tvcolumn.set_attributes(cell, text=3, foreground_set = 4)

        tvcolumn = Gtk.TreeViewColumn('Amount')
        treeview.append_column(tvcolumn)
        cell = Gtk.CellRendererText()
        cell.set_alignment(1, 0.5)
        cell.set_property('family', MONOSPACE_FONT)
        tvcolumn.pack_start(cell, False)
        tvcolumn.add_attribute(cell, 'text', 5)

        tvcolumn = Gtk.TreeViewColumn('Balance')
        treeview.append_column(tvcolumn)
        cell = Gtk.CellRendererText()
        cell.set_alignment(1, 0.5)
        cell.set_property('family', MONOSPACE_FONT)
        tvcolumn.pack_start(cell, False)
        tvcolumn.add_attribute(cell, 'text', 6)

        tvcolumn = Gtk.TreeViewColumn('Tooltip')
        treeview.append_column(tvcolumn)
        cell = Gtk.CellRendererText()
        tvcolumn.pack_start(cell, False)
        tvcolumn.add_attribute(cell, 'text', 7)
        tvcolumn.set_visible(False)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(treeview)

        self.add_tab(scroll, 'History')
        self.update_history_tab()


    def create_recv_tab(self):
        self.recv_list = Gtk.ListStore(str, str, str, str, str)
        self.add_tab( self.make_address_list(True), 'Receive')
        self.update_receiving_tab()

    def create_book_tab(self):
        self.addressbook_list = Gtk.ListStore(str, str, str)
        self.add_tab( self.make_address_list(False), 'Contacts')
        self.update_sending_tab()

    def make_address_list(self, is_recv):
        liststore = self.recv_list if is_recv else self.addressbook_list
        treeview = Gtk.TreeView(model= liststore)
        treeview.connect('key-press-event', self.treeview_key_press)
        treeview.connect('button-press-event', self.treeview_button_press)
        treeview.show()
        if not is_recv:
            self.contacts_treeview = treeview

        tvcolumn = Gtk.TreeViewColumn('Address')
        treeview.append_column(tvcolumn)
        cell = Gtk.CellRendererText()
        cell.set_property('family', MONOSPACE_FONT)
        tvcolumn.pack_start(cell, True)
        tvcolumn.add_attribute(cell, 'text', 0)

        tvcolumn = Gtk.TreeViewColumn('Label')
        tvcolumn.set_expand(True)
        treeview.append_column(tvcolumn)
        cell = Gtk.CellRendererText()
        cell.set_property('editable', True)
        def edited_cb2(cell, path, new_text, liststore):
            address = liststore.get_value( liststore.get_iter(path), 0)
            self.wallet.set_label(address, new_text)
            self.update_receiving_tab()
            self.update_sending_tab()
            self.update_history_tab()
        cell.connect('edited', edited_cb2, liststore)
        tvcolumn.pack_start(cell, True)
        tvcolumn.add_attribute(cell, 'text', 1)

        tvcolumn = Gtk.TreeViewColumn('Tx')
        treeview.append_column(tvcolumn)
        cell = Gtk.CellRendererText()
        tvcolumn.pack_start(cell, True)
        tvcolumn.add_attribute(cell, 'text', 2)

        if is_recv:
            tvcolumn = Gtk.TreeViewColumn('Balance')
            treeview.append_column(tvcolumn)
            cell = Gtk.CellRendererText()
            tvcolumn.pack_start(cell, True)
            tvcolumn.add_attribute(cell, 'text', 3)
            tvcolumn = Gtk.TreeViewColumn('Type')
            treeview.append_column(tvcolumn)
            cell = Gtk.CellRendererText()
            tvcolumn.pack_start(cell, True)
            tvcolumn.add_attribute(cell, 'text', 4)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(treeview)

        hbox = Gtk.HBox()
        if not is_recv:
            button = Gtk.Button("New")
            button.connect("clicked", self.newaddress_dialog)
            button.show()
            hbox.pack_start(button,False, False, 0)

        def showqrcode(w, treeview, liststore):
            path, col = treeview.get_cursor()
            if not path: return
            address = liststore.get_value(liststore.get_iter(path), 0)
            qr = pyqrnative.QRCode(4, pyqrnative.QRErrorCorrectLevel.H)
            qr.addData(address)
            qr.make()
            boxsize = 7
            boxcount_row = qr.getModuleCount()
            size = (boxcount_row + 4) * boxsize
            def area_expose_cb(area, cr):
                style = area.get_style()
                Gdk.cairo_set_source_color(cr, style.white)
                cr.rectangle(0, 0, size, size)
                cr.fill()
                Gdk.cairo_set_source_color(cr, style.black)
                for r in range(boxcount_row):
                    for c in range(boxcount_row):
                        if qr.isDark(r, c):
                            cr.rectangle((c + 2) * boxsize, (r + 2) * boxsize, boxsize, boxsize)
                            cr.fill()
            area = Gtk.DrawingArea()
            area.set_size_request(size, size)
            area.connect("draw", area_expose_cb)
            area.show()
            dialog = Gtk.Dialog(address, parent=self.window, flags=Gtk.DialogFlags.MODAL, buttons = ("ok",1))
            dialog.vbox.add(area)
            dialog.run()
            dialog.destroy()

        button = Gtk.Button("QR")
        button.connect("clicked", showqrcode, treeview, liststore)
        button.show()
        hbox.pack_start(button,False, False, 0)

        button = Gtk.Button("Copy to clipboard")
        def copy2clipboard(w, treeview, liststore):
            import platform
            path, col =  treeview.get_cursor()
            if path:
                address =  liststore.get_value( liststore.get_iter(path), 0)
                if platform.system() == 'Windows':
                    from Tkinter import Tk
                    r = Tk()
                    r.withdraw()
                    r.clipboard_clear()
                    r.clipboard_append( address )
                    r.destroy()
                else:
                    atom = Gdk.atom_intern('CLIPBOARD', True)
                    c = Gtk.Clipboard.get(atom)
                    c.set_text( address, len(address) )
        button.connect("clicked", copy2clipboard, treeview, liststore)
        button.show()
        hbox.pack_start(button,False, False, 0)

        if is_recv:
            button = Gtk.Button("Freeze")
            def freeze_address(w, treeview, liststore, wallet):
                path, col = treeview.get_cursor()
                if path:
                    address = liststore.get_value( liststore.get_iter(path), 0)
                    if address in wallet.frozen_addresses:
                        wallet.unfreeze(address)
                    else:
                        wallet.freeze(address)
                    self.update_receiving_tab()
            button.connect("clicked", freeze_address, treeview, liststore, self.wallet)
            button.show()
            hbox.pack_start(button,False, False, 0)

        if not is_recv:
            button = Gtk.Button("Pay to")
            def payto(w, treeview, liststore):
                path, col =  treeview.get_cursor()
                if path:
                    address =  liststore.get_value( liststore.get_iter(path), 0)
                    self.payto_entry.set_text( address )
                    self.notebook.set_current_page(1)
                    self.amount_entry.grab_focus()

            button.connect("clicked", payto, treeview, liststore)
            button.show()
            hbox.pack_start(button,False, False, 0)

        vbox = Gtk.VBox()
        vbox.pack_start(scroll,True, True, 0)
        vbox.pack_start(hbox, False, False, 0)
        return vbox

    def update_status_bar(self):
        interface = self.network.interface
        if self.funds_error:
            text = "Not enough funds"
        elif interface and interface.is_connected:
            self.network_button.set_tooltip_text("Connected to %s:%d.\n%d blocks"%(interface.host, interface.port, self.network.blockchain.height()))
            if not self.wallet.up_to_date:
                self.status_image.set_from_stock(Gtk.STOCK_REFRESH, Gtk.IconSize.MENU)
                text = "Synchronizing..."
            else:
                self.status_image.set_from_stock(Gtk.STOCK_YES, Gtk.IconSize.MENU)
                self.network_button.set_tooltip_text("Connected to %s:%d.\n%d blocks"%(interface.host, interface.port, self.network.blockchain.height()))
                c, u = self.wallet.get_balance()
                text =  "Balance: %s "%( format_satoshis(c,False,self.num_zeros) )
                if u: text +=  "[%s unconfirmed]"%( format_satoshis(u,True,self.num_zeros).strip() )
        else:
            self.status_image.set_from_stock(Gtk.STOCK_NO, Gtk.IconSize.MENU)
            self.network_button.set_tooltip_text("Not connected.")
            text = "Not connected"

        self.status_bar.pop(self.context_id) 
        self.status_bar.push(self.context_id, text)

        if self.wallet.up_to_date and self.wallet_updated:
            self.update_history_tab()
            self.update_receiving_tab()
            # addressbook too...
            self.info.set_text( self.network.banner )
            self.wallet_updated = False

    def update_receiving_tab(self):
        self.recv_list.clear()
        for address in self.wallet.addresses(True):
            Type = "R"
            c = u = 0
            if self.wallet.is_change(address): Type = "C"
            if address in self.wallet.imported_keys.keys():
                Type = "I"
            c, u = self.wallet.get_addr_balance(address)
            if address in self.wallet.frozen_addresses: Type = Type + "F"
            label = self.wallet.labels.get(address)
            h = self.wallet.history.get(address,[])
            n = len(h)
            tx = "0" if n==0 else "%d"%n
            self.recv_list.append((address, label, tx, format_satoshis(c,False,self.num_zeros), Type ))

    def update_sending_tab(self):
        # detect addresses that are not mine in history, add them here...
        self.addressbook_list.clear()
        #for alias, v in self.wallet.aliases.items():
        #    s, target = v
        #    label = self.wallet.labels.get(alias)
        #    self.addressbook_list.append((alias, label, '-'))
            
        for address in self.wallet.addressbook:
            label = self.wallet.labels.get(address)
            n = self.wallet.get_num_tx(address)
            self.addressbook_list.append((address, label, "%d"%n))

    def update_history_tab(self):
        cursor = self.history_treeview.get_cursor()[0]
        self.history_list.clear()

        for item in self.wallet.get_tx_history():
            tx_hash, conf, is_mine, value, fee, balance, timestamp = item
            if conf > 0:
                try:
                    time_str = datetime.datetime.fromtimestamp( timestamp).isoformat(' ')[:-3]
                except Exception:
                    time_str = "------"
                conf_icon = Gtk.STOCK_APPLY
            elif conf == -1:
                time_str = 'unverified'
                conf_icon = None
            else:
                time_str = 'pending'
                conf_icon = Gtk.STOCK_EXECUTE

            label, is_default_label = self.wallet.get_label(tx_hash)
            tooltip = tx_hash + "\n%d confirmations"%conf if tx_hash else ''
            details = self.get_tx_details(tx_hash)

            self.history_list.prepend( [tx_hash, conf_icon, time_str, label, is_default_label,
                                        format_satoshis(value,True,self.num_zeros, whitespaces=True),
                                        format_satoshis(balance,False,self.num_zeros, whitespaces=True), tooltip, details] )
        if cursor: self.history_treeview.set_cursor( cursor )


    def get_tx_details(self, tx_hash):
        import datetime
        if not tx_hash: return ''
        tx = self.wallet.transactions.get(tx_hash)
        is_relevant, is_mine, v, fee = self.wallet.get_tx_value(tx)
        conf, timestamp = self.wallet.verifier.get_confirmations(tx_hash)

        if timestamp:
            time_str = datetime.datetime.fromtimestamp(timestamp).isoformat(' ')[:-3]
        else:
            time_str = 'pending'

        inputs = map(lambda x: x.get('address'), tx.inputs)
        outputs = map(lambda x: x.get('address'), tx.d['outputs'])
        tx_details = "Transaction Details" +"\n\n" \
            + "Transaction ID:\n" + tx_hash + "\n\n" \
            + "Status: %d confirmations\n"%conf
        if is_mine:
            if fee: 
                tx_details += "Amount sent: %s\n"% format_satoshis(v-fee, False) \
                              + "Transaction fee: %s\n"% format_satoshis(fee, False)
            else:
                tx_details += "Amount sent: %s\n"% format_satoshis(v, False) \
                              + "Transaction fee: unknown\n"
        else:
            tx_details += "Amount received: %s\n"% format_satoshis(v, False) \

        tx_details += "Date: %s\n\n"%time_str \
            + "Inputs:\n-"+ '\n-'.join(inputs) + "\n\n" \
            + "Outputs:\n-"+ '\n-'.join(outputs)

        return tx_details



    def newaddress_dialog(self, w):

        title = "New Contact" 
        dialog = Gtk.Dialog(title, parent=self.window, 
                            flags=Gtk.DialogFlags.MODAL,
                            buttons= ("cancel", 0, "ok",1)  )
        dialog.show()

        label = Gtk.HBox()
        label_label = Gtk.Label(label='Label:')
        label_label.set_size_request(120,10)
        label_label.show()
        label.pack_start(label_label, True, True, 0)
        label_entry = Gtk.Entry()
        label_entry.show()
        label.pack_start(label_entry, True, True, 0)
        label.show()
        dialog.vbox.pack_start(label, False, True, 5)

        address = Gtk.HBox()
        address_label = Gtk.Label(label='Address:')
        address_label.set_size_request(120,10)
        address_label.show()
        address.pack_start(address_label, True, True, 0)
        address_entry = Gtk.Entry()
        address_entry.show()
        address.pack_start(address_entry, True, True, 0)
        address.show()
        dialog.vbox.pack_start(address, False, True, 5)
        
        result = dialog.run()
        address = address_entry.get_text()
        label = label_entry.get_text()
        dialog.destroy()

        if result == 1:
            if is_valid(address):
                self.wallet.add_contact(address,label)
                self.update_sending_tab()
            else:
                errorDialog = Gtk.MessageDialog(
                    parent=self.window,
                    flags=Gtk.DialogFlags.MODAL, 
                    buttons= Gtk.ButtonsType.CLOSE, 
                    message_format = "Invalid address")
                errorDialog.show()
                errorDialog.run()
                errorDialog.destroy()

    

class ElectrumGui():

    def __init__(self, config, network):
        self.network = network
        self.config = config


    def main(self, url=None):

        storage = WalletStorage(self.config)
        if not storage.file_exists:
            action = self.restore_or_create()
            if not action:
                exit()
            self.wallet = wallet = Wallet(storage)
            gap = self.config.get('gap_limit', 5)
            if gap != 5:
                wallet.gap_limit = gap
                wallet.storage.put('gap_limit', gap, True)

            if action == 'create':
                seed = wallet.make_seed()
                show_seed_dialog(seed, None)
                r = change_password_dialog(False, None)
                password = r[2] if r else None
                wallet.add_seed(seed, password)
                wallet.create_accounts(password)
                wallet.synchronize()  # generate first addresses offline

            elif action == 'restore':
                seed = self.seed_dialog()
                if not seed:
                    exit()
                r = change_password_dialog(False, None)
                password = r[2] if r else None
                wallet.add_seed(seed, password)
                wallet.create_accounts(password)
                
            else:
                exit()
        else:
            self.wallet = Wallet(storage)
            action = None

        self.wallet.start_threads(self.network)

        if action == 'restore':
            self.restore_wallet(wallet)

        w = ElectrumWindow(self.wallet, self.config, self.network)
        if url: w.set_url(url)
        Gtk.main()

    def restore_or_create(self):
        return restore_create_dialog()

    def seed_dialog(self):
        return run_recovery_dialog()

    def network_dialog(self):
        return run_network_dialog( self.network, parent=None )


    def restore_wallet(self, wallet):

        dialog = Gtk.MessageDialog(
            parent = None,
            flags = Gtk.DialogFlags.MODAL, 
            buttons = Gtk.ButtonsType.CANCEL, 
            message_format = "Please wait..."  )
        dialog.show()

        def recover_thread( wallet, dialog ):
            wallet.restore(lambda x:x)
            GObject.idle_add( dialog.destroy )

        thread.start_new_thread( recover_thread, ( wallet, dialog ) )
        r = dialog.run()
        dialog.destroy()
        if r==Gtk.ResponseType.CANCEL: return False
        if not wallet.is_found():
            show_message("No transactions found for this seed")

        return True

########NEW FILE########
__FILENAME__ = amountedit
# -*- coding: utf-8 -*-

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class AmountEdit(QLineEdit):

    def __init__(self, text_getter, is_int = False, parent=None):
        QLineEdit.__init__(self, parent)
        self.text_getter = text_getter
        self.textChanged.connect(self.numbify)
        self.is_int = is_int
        self.is_shortcut = False


    def paintEvent(self, event):
        QLineEdit.paintEvent(self, event)
        if self.text_getter:
             panel = QStyleOptionFrameV2()
             self.initStyleOption(panel)
             textRect = self.style().subElementRect(QStyle.SE_LineEditContents, panel, self)
             textRect.adjust(2, 0, -10, 0)
             painter = QPainter(self)
             painter.setPen(self.palette().brush(QPalette.Disabled, QPalette.Text).color())
             painter.drawText(textRect, Qt.AlignRight | Qt.AlignVCenter, self.text_getter())


    def numbify(self):
        text = unicode(self.text()).strip()
        if text == '!':
            self.is_shortcut = True
        pos = self.cursorPosition()
        chars = '0123456789'
        if not self.is_int: chars +='.'
        s = ''.join([i for i in text if i in chars])
        if not self.is_int:
            if '.' in s:
                p = s.find('.')
                s = s.replace('.','')
                s = s[:p] + '.' + s[p:p+8]
        self.setText(s)
        self.setCursorPosition(pos)

########NEW FILE########
__FILENAME__ = console
# source: http://stackoverflow.com/questions/2758159/how-to-embed-a-python-interpreter-in-a-pyqt-widget

import sys, os, re
import traceback, platform
from PyQt4 import QtCore
from PyQt4 import QtGui
from electrum import util


if platform.system() == 'Windows':
    MONOSPACE_FONT = 'Lucida Console'
elif platform.system() == 'Darwin':
    MONOSPACE_FONT = 'Monaco'
else:
    MONOSPACE_FONT = 'monospace'


class Console(QtGui.QPlainTextEdit):
    def __init__(self, prompt='>> ', startup_message='', parent=None):
        QtGui.QPlainTextEdit.__init__(self, parent)

        self.prompt = prompt
        self.history = []
        self.namespace = {}
        self.construct = []

        self.setGeometry(50, 75, 600, 400)
        self.setWordWrapMode(QtGui.QTextOption.WrapAnywhere)
        self.setUndoRedoEnabled(False)
        self.document().setDefaultFont(QtGui.QFont(MONOSPACE_FONT, 10, QtGui.QFont.Normal))
        self.showMessage(startup_message)

        self.updateNamespace({'run':self.run_script})
        self.set_json(False)

    def set_json(self, b):
        self.is_json = b
    
    def run_script(self, filename):
        with open(filename) as f:
            script = f.read()

        # eval is generally considered bad practice. use it wisely!
        result = eval(script, self.namespace, self.namespace)



    def updateNamespace(self, namespace):
        self.namespace.update(namespace)

    def showMessage(self, message):
        self.appendPlainText(message)
        self.newPrompt()

    def clear(self):
        self.setPlainText('')
        self.newPrompt()

    def newPrompt(self):
        if self.construct:
            prompt = '.' * len(self.prompt)
        else:
            prompt = self.prompt

        self.completions_pos = self.textCursor().position()
        self.completions_visible = False

        self.appendPlainText(prompt)
        self.moveCursor(QtGui.QTextCursor.End)

    def getCommand(self):
        doc = self.document()
        curr_line = unicode(doc.findBlockByLineNumber(doc.lineCount() - 1).text())
        curr_line = curr_line.rstrip()
        curr_line = curr_line[len(self.prompt):]
        return curr_line

    def setCommand(self, command):
        if self.getCommand() == command:
            return

        doc = self.document()
        curr_line = unicode(doc.findBlockByLineNumber(doc.lineCount() - 1).text())
        self.moveCursor(QtGui.QTextCursor.End)
        for i in range(len(curr_line) - len(self.prompt)):
            self.moveCursor(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor)

        self.textCursor().removeSelectedText()
        self.textCursor().insertText(command)
        self.moveCursor(QtGui.QTextCursor.End)


    def show_completions(self, completions):
        if self.completions_visible:
            self.hide_completions()

        c = self.textCursor()
        c.setPosition(self.completions_pos)

        completions = map(lambda x: x.split('.')[-1], completions)
        t = '\n' + ' '.join(completions)
        if len(t) > 500:
            t = t[:500] + '...'
        c.insertText(t)
        self.completions_end = c.position()

        self.moveCursor(QtGui.QTextCursor.End)
        self.completions_visible = True
        

    def hide_completions(self):
        if not self.completions_visible:
            return
        c = self.textCursor()
        c.setPosition(self.completions_pos)
        l = self.completions_end - self.completions_pos
        for x in range(l): c.deleteChar()

        self.moveCursor(QtGui.QTextCursor.End)
        self.completions_visible = False


    def getConstruct(self, command):
        if self.construct:
            prev_command = self.construct[-1]
            self.construct.append(command)
            if not prev_command and not command:
                ret_val = '\n'.join(self.construct)
                self.construct = []
                return ret_val
            else:
                return ''
        else:
            if command and command[-1] == (':'):
                self.construct.append(command)
                return ''
            else:
                return command

    def getHistory(self):
        return self.history

    def setHisory(self, history):
        self.history = history

    def addToHistory(self, command):
        if command.find("importprivkey") > -1:
            return
        
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
        self.history_index = len(self.history)

    def getPrevHistoryEntry(self):
        if self.history:
            self.history_index = max(0, self.history_index - 1)
            return self.history[self.history_index]
        return ''

    def getNextHistoryEntry(self):
        if self.history:
            hist_len = len(self.history)
            self.history_index = min(hist_len, self.history_index + 1)
            if self.history_index < hist_len:
                return self.history[self.history_index]
        return ''

    def getCursorPosition(self):
        c = self.textCursor()
        return c.position() - c.block().position() - len(self.prompt)

    def setCursorPosition(self, position):
        self.moveCursor(QtGui.QTextCursor.StartOfLine)
        for i in range(len(self.prompt) + position):
            self.moveCursor(QtGui.QTextCursor.Right)

    def register_command(self, c, func):
        methods = { c: func}
        self.updateNamespace(methods)
        

    def runCommand(self):
        command = self.getCommand()
        self.addToHistory(command)

        command = self.getConstruct(command)

        if command:
            tmp_stdout = sys.stdout

            class stdoutProxy():
                def __init__(self, write_func):
                    self.write_func = write_func
                    self.skip = False

                def flush(self):
                    pass

                def write(self, text):
                    if not self.skip:
                        stripped_text = text.rstrip('\n')
                        self.write_func(stripped_text)
                        QtCore.QCoreApplication.processEvents()
                    self.skip = not self.skip

            if type(self.namespace.get(command)) == type(lambda:None):
                self.appendPlainText("'%s' is a function. Type '%s()' to use it in the Python console."%(command, command))
                self.newPrompt()
                return

            sys.stdout = stdoutProxy(self.appendPlainText)
            try:
                try:
                    # eval is generally considered bad practice. use it wisely!
                    result = eval(command, self.namespace, self.namespace)
                    if result != None:
                        if self.is_json:
                            util.print_json(result)
                        else:
                            self.appendPlainText(repr(result))
                except SyntaxError:
                    # exec is generally considered bad practice. use it wisely!
                    exec command in self.namespace
            except SystemExit:
                self.close()
            except Exception:
                traceback_lines = traceback.format_exc().split('\n')
                # Remove traceback mentioning this file, and a linebreak
                for i in (3,2,1,-1):
                    traceback_lines.pop(i)
                self.appendPlainText('\n'.join(traceback_lines))
            sys.stdout = tmp_stdout
        self.newPrompt()
        self.set_json(False)
                    

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Tab:
            self.completions()
            return

        self.hide_completions()

        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.runCommand()
            return
        if event.key() == QtCore.Qt.Key_Home:
            self.setCursorPosition(0)
            return
        if event.key() == QtCore.Qt.Key_PageUp:
            return
        elif event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Backspace):
            if self.getCursorPosition() == 0:
                return
        elif event.key() == QtCore.Qt.Key_Up:
            self.setCommand(self.getPrevHistoryEntry())
            return
        elif event.key() == QtCore.Qt.Key_Down:
            self.setCommand(self.getNextHistoryEntry())
            return
        elif event.key() == QtCore.Qt.Key_L and event.modifiers() == QtCore.Qt.ControlModifier:
            self.clear()

        super(Console, self).keyPressEvent(event)



    def completions(self):
        cmd = self.getCommand()
        lastword = re.split(' |\(|\)',cmd)[-1]
        beginning = cmd[0:-len(lastword)]

        path = lastword.split('.')
        ns = self.namespace.keys()

        if len(path) == 1:
            ns = ns
            prefix = ''
        else:
            obj = self.namespace.get(path[0])
            prefix = path[0] + '.'
            ns = dir(obj)
            

        completions = []
        for x in ns:
            if x[0] == '_':continue
            xx = prefix + x
            if xx.startswith(lastword):
                completions.append(xx)
        completions.sort()
                
        if not completions:
            self.hide_completions()
        elif len(completions) == 1:
            self.hide_completions()
            self.setCommand(beginning + completions[0])
        else:
            # find common prefix
            p = os.path.commonprefix(completions)
            if len(p)>len(lastword):
                self.hide_completions()
                self.setCommand(beginning + p)
            else:
                self.show_completions(completions)


welcome_message = '''
   ---------------------------------------------------------------
     Welcome to a primitive Python interpreter.
   ---------------------------------------------------------------
'''

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    console = Console(startup_message=welcome_message)
    console.updateNamespace({'myVar1' : app, 'myVar2' : 1234})
    console.show();
    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = history_widget
from PyQt4.QtGui import *
from electrum.i18n import _

class HistoryWidget(QTreeWidget):

    def __init__(self, parent=None):
        QTreeWidget.__init__(self, parent)
        self.setColumnCount(2)
        self.setHeaderLabels([_("Amount"), _("To / From"), _("When")])
        self.setIndentation(0)

    def empty(self):
        self.clear()

    def append(self, address, amount, date):
        if address is None:
          address = _("Unknown")
        if amount is None: 
          amount = _("Unknown")
        if date is None:
          date = _("Unknown")
        item = QTreeWidgetItem([amount, address, date])
        if float(amount) < 0:
          item.setForeground(0, QBrush(QColor("#BC1E1E")))
        self.insertTopLevelItem(0, item)


########NEW FILE########
__FILENAME__ = installwizard
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore

from electrum.i18n import _
from electrum import Wallet, Wallet_2of2, Wallet_2of3
import electrum.bitcoin as bitcoin

import seed_dialog
from network_dialog import NetworkDialog
from util import *
from amountedit import AmountEdit

import sys
import threading
from electrum.plugins import run_hook


MSG_ENTER_ANYTHING    = _("Please enter a wallet seed, a master public key, a list of Bitcoin addresses, or a list of private keys")
MSG_SHOW_MPK          = _("This is your master public key")
MSG_ENTER_MPK         = _("Please enter your master public key")
MSG_ENTER_COLD_MPK    = _("Please enter the master public key of your cosigning wallet")
MSG_ENTER_SEED_OR_MPK = _("Please enter a wallet seed, or master public key")
MSG_VERIFY_SEED       = _("Your seed is important!") + "\n" + _("To make sure that you have properly saved your seed, please retype it here.")


class InstallWizard(QDialog):

    def __init__(self, config, network, storage):
        QDialog.__init__(self)
        self.config = config
        self.network = network
        self.storage = storage
        self.setMinimumSize(575, 400)
        self.setWindowTitle('Electrum')
        self.connect(self, QtCore.SIGNAL('accept'), self.accept)

        self.stack = QStackedLayout()
        self.setLayout(self.stack)


    def set_layout(self, layout):
        w = QWidget()
        w.setLayout(layout)
        self.stack.setCurrentIndex(self.stack.addWidget(w))


    def restore_or_create(self):

        vbox = QVBoxLayout()

        main_label = QLabel(_("Electrum could not find an existing wallet."))
        vbox.addWidget(main_label)

        grid = QGridLayout()
        grid.setSpacing(5)

        label = QLabel(_("What do you want to do?"))
        label.setWordWrap(True)
        grid.addWidget(label, 0, 0)

        gb1 = QGroupBox()
        grid.addWidget(gb1, 0, 0)

        group1 = QButtonGroup()

        b1 = QRadioButton(gb1)
        b1.setText(_("Create new wallet"))
        b1.setChecked(True)

        b2 = QRadioButton(gb1)
        b2.setText(_("Restore an existing wallet"))

        group1.addButton(b1)
        group1.addButton(b2)

        grid.addWidget(b1, 1, 0)
        grid.addWidget(b2, 2, 0)
        vbox.addLayout(grid)

        grid2 = QGridLayout()
        grid2.setSpacing(5)

        class ClickableLabel(QLabel):
            def mouseReleaseEvent(self, ev):
                self.emit(SIGNAL('clicked()'))

        label2 = ClickableLabel(_("Wallet type:") + " [+]")
        hbox = QHBoxLayout()
        hbox.addWidget(label2)
        grid2.addLayout(hbox, 3, 0)
        
        gb2 = QGroupBox()
        grid.addWidget(gb2, 3, 0)

        group2 = QButtonGroup()

        bb1 = QRadioButton(gb2)
        bb1.setText(_("Standard wallet"))
        bb1.setChecked(True)

        bb2 = QRadioButton(gb2)
        bb2.setText(_("Wallet with two-factor authentication (plugin)"))

        bb3 = QRadioButton(gb2)
        bb3.setText(_("Multisig wallet (2 of 2)"))
        bb3.setHidden(True)

        bb4 = QRadioButton(gb2)
        bb4.setText(_("Multisig wallet (2 of 3)"))
        bb4.setHidden(True)

        grid2.addWidget(bb1, 4, 0)
        grid2.addWidget(bb2, 5, 0)
        grid2.addWidget(bb3, 6, 0)
        grid2.addWidget(bb4, 7, 0)

        def toggle():
            x = not bb3.isHidden()
            label2.setText(_("Wallet type:") + (' [+]' if x else ' [-]'))
            bb3.setHidden(x)
            bb4.setHidden(x)
 
        self.connect(label2, SIGNAL('clicked()'), toggle)

        grid2.addWidget(label2)

        group2.addButton(bb1)
        group2.addButton(bb2)
        group2.addButton(bb3)
        group2.addButton(bb4)
 
        vbox.addLayout(grid2)
        vbox.addStretch(1)
        vbox.addLayout(ok_cancel_buttons(self, _('Next')))

        self.set_layout(vbox)
        if not self.exec_():
            return None, None
        
        action = 'create' if b1.isChecked() else 'restore'

        if bb1.isChecked():
            t = 'standard'
        elif bb2.isChecked():
            t = '2fa'
        elif bb3.isChecked():
            t = '2of2'
        elif bb4.isChecked():
            t = '2of3'

        return action, t


    def verify_seed(self, seed, sid):
        r = self.enter_seed_dialog(MSG_VERIFY_SEED, sid)
        if not r:
            return

        if r != seed:
            QMessageBox.warning(None, _('Error'), _('Incorrect seed'), _('OK'))
            return False
        else:
            return True


    def get_seed_text(self, seed_e):
        text = unicode(seed_e.toPlainText()).strip()
        text = ' '.join(text.split())
        return text


    def is_any(self, seed_e):
        text = self.get_seed_text(seed_e)
        return Wallet.is_seed(text) or Wallet.is_mpk(text) or Wallet.is_address(text) or Wallet.is_private_key(text)

    def is_mpk(self, seed_e):
        text = self.get_seed_text(seed_e)
        return Wallet.is_mpk(text)


    def enter_seed_dialog(self, msg, sid):
        vbox, seed_e = seed_dialog.enter_seed_box(msg, sid)
        vbox.addStretch(1)
        hbox, button = ok_cancel_buttons2(self, _('Next'))
        vbox.addLayout(hbox)
        button.setEnabled(False)
        seed_e.textChanged.connect(lambda: button.setEnabled(self.is_any(seed_e)))
        self.set_layout(vbox)
        if not self.exec_():
            return
        return self.get_seed_text(seed_e)


    def multi_mpk_dialog(self, xpub_hot, n):
        vbox = QVBoxLayout()
        vbox0, seed_e0 = seed_dialog.enter_seed_box(MSG_SHOW_MPK, 'hot')
        vbox.addLayout(vbox0)
        seed_e0.setText(xpub_hot)
        seed_e0.setReadOnly(True)
        entries = []
        for i in range(n):
            vbox2, seed_e2 = seed_dialog.enter_seed_box(MSG_ENTER_COLD_MPK, 'cold')
            vbox.addLayout(vbox2)
            entries.append(seed_e2)
        vbox.addStretch(1)
        hbox, button = ok_cancel_buttons2(self, _('Next'))
        vbox.addLayout(hbox)
        button.setEnabled(False)
        f = lambda: button.setEnabled( map(lambda e: self.is_mpk(e), entries) == [True]*len(entries))
        for e in entries:
            e.textChanged.connect(f)
        self.set_layout(vbox)
        if not self.exec_():
            return
        return map(lambda e: self.get_seed_text(e), entries)


    def multi_seed_dialog(self, n):
        vbox = QVBoxLayout()
        vbox1, seed_e1 = seed_dialog.enter_seed_box(MSG_ENTER_SEED_OR_MPK, 'hot')
        vbox.addLayout(vbox1)
        entries = [seed_e1]
        for i in range(n):
            vbox2, seed_e2 = seed_dialog.enter_seed_box(MSG_ENTER_SEED_OR_MPK, 'cold')
            vbox.addLayout(vbox2)
            entries.append(seed_e2)
        vbox.addStretch(1)
        hbox, button = ok_cancel_buttons2(self, _('Next'))
        vbox.addLayout(hbox)
        button.setEnabled(False)

        f = lambda: button.setEnabled( map(lambda e: self.is_any(e), entries) == [True]*len(entries))
        for e in entries:
            e.textChanged.connect(f)

        self.set_layout(vbox)
        if not self.exec_():
            return 
        return map(lambda e: self.get_seed_text(e), entries)





    def waiting_dialog(self, task, msg= _("Electrum is generating your addresses, please wait.")):
        def target():
            task()
            self.emit(QtCore.SIGNAL('accept'))

        vbox = QVBoxLayout()
        self.waiting_label = QLabel(msg)
        vbox.addWidget(self.waiting_label)
        self.set_layout(vbox)
        t = threading.Thread(target = target)
        t.start()
        self.exec_()




    def network_dialog(self):
        
        grid = QGridLayout()
        grid.setSpacing(5)

        label = QLabel(_("Electrum communicates with remote servers to get information about your transactions and addresses. The servers all fulfil the same purpose only differing in hardware. In most cases you simply want to let Electrum pick one at random if you have a preference though feel free to select a server manually.") + "\n\n" \
                      + _("How do you want to connect to a server:")+" ")
        label.setWordWrap(True)
        grid.addWidget(label, 0, 0)

        gb = QGroupBox()

        b1 = QRadioButton(gb)
        b1.setText(_("Auto connect"))
        b1.setChecked(True)

        b2 = QRadioButton(gb)
        b2.setText(_("Select server manually"))

        #b3 = QRadioButton(gb)
        #b3.setText(_("Stay offline"))

        grid.addWidget(b1,1,0)
        grid.addWidget(b2,2,0)
        #grid.addWidget(b3,3,0)

        vbox = QVBoxLayout()
        vbox.addLayout(grid)

        vbox.addStretch(1)
        vbox.addLayout(ok_cancel_buttons(self, _('Next')))

        self.set_layout(vbox)
        if not self.exec_():
            return
        
        if b2.isChecked():
            return NetworkDialog(self.network, self.config, None).do_exec()

        elif b1.isChecked():
            self.config.set_key('auto_cycle', True, True)
            return

        else:
            self.config.set_key("server", None, True)
            self.config.set_key('auto_cycle', False, True)
            return
        

    def show_message(self, msg, icon=None):
        vbox = QVBoxLayout()
        self.set_layout(vbox)
        if icon:
            logo = QLabel()
            logo.setPixmap(icon)
            vbox.addWidget(logo)
        vbox.addWidget(QLabel(msg))
        vbox.addStretch(1)
        vbox.addLayout(close_button(self, _('Next')))
        if not self.exec_(): 
            return None


    def question(self, msg, icon=None):
        vbox = QVBoxLayout()
        self.set_layout(vbox)
        if icon:
            logo = QLabel()
            logo.setPixmap(icon)
            vbox.addWidget(logo)
        vbox.addWidget(QLabel(msg))
        vbox.addStretch(1)
        vbox.addLayout(ok_cancel_buttons(self, _('OK')))
        if not self.exec_(): 
            return None
        return True


    def show_seed(self, seed, sid):
        vbox = seed_dialog.show_seed_box(seed, sid)
        vbox.addLayout(ok_cancel_buttons(self, _("Next")))
        self.set_layout(vbox)
        return self.exec_()


    def password_dialog(self):
        msg = _("Please choose a password to encrypt your wallet keys.")+'\n'\
              +_("Leave these fields empty if you want to disable encryption.")
        from password_dialog import make_password_dialog, run_password_dialog
        self.set_layout( make_password_dialog(self, None, msg) )
        return run_password_dialog(self, None, self)[2]


    def create_cold_seed(self, wallet):
        from electrum.bitcoin import mnemonic_to_seed, bip32_root
        msg = _('You are about to generate the cold storage seed of your wallet.') + '\n' \
              + _('For safety, you should do this on an offline computer.')
        icon = QPixmap( ':icons/cold_seed.png').scaledToWidth(56)
        if not self.question(msg, icon):
            return

        cold_seed = wallet.make_seed()
        if not self.show_seed(cold_seed, 'cold'):
            return
        if not self.verify_seed(cold_seed, 'cold'):
            return

        hex_seed = mnemonic_to_seed(cold_seed,'').encode('hex')
        xpriv, xpub = bip32_root(hex_seed)
        wallet.add_master_public_key('cold/', xpub)

        msg = _('Your master public key was saved in your wallet file.') + '\n'\
              + _('Your cold seed must be stored on paper; it is not in the wallet file.')+ '\n\n' \
              + _('This program is about to close itself.') + '\n'\
              + _('You will need to reopen your wallet on an online computer, in order to complete the creation of your wallet')
        self.show_message(msg)



    def run(self, action):

        if action == 'new':
            action, t = self.restore_or_create()

        if action is None: 
            return
            
        if action == 'create':
            if t == 'standard':
                wallet = Wallet(self.storage)

            elif t == '2fa':
                wallet = Wallet_2of3(self.storage)
                run_hook('create_cold_seed', wallet, self)
                self.create_cold_seed(wallet)
                return

            elif t == '2of2':
                wallet = Wallet_2of2(self.storage)
                action = 'create_2of2_1'

            elif t == '2of3':
                wallet = Wallet_2of3(self.storage)
                action = 'create_2of3_1'


        if action in ['create_2fa_2', 'create_2of3_2']:
            wallet = Wallet_2of3(self.storage)

        if action in ['create', 'create_2of2_1', 'create_2fa_2', 'create_2of3_1']:
            seed = wallet.make_seed()
            sid = None if action == 'create' else 'hot'
            if not self.show_seed(seed, sid):
                return
            if not self.verify_seed(seed, sid):
                return
            password = self.password_dialog()
            wallet.add_seed(seed, password)
            if action == 'create':
                wallet.create_accounts(password)
                self.waiting_dialog(wallet.synchronize)
            elif action == 'create_2of2_1':
                action = 'create_2of2_2'
            elif action == 'create_2of3_1':
                action = 'create_2of3_2'
            elif action == 'create_2fa_2':
                action = 'create_2fa_3'

        if action == 'create_2of2_2':
            xpub_hot = wallet.master_public_keys.get("m/")
            xpub = self.multi_mpk_dialog(xpub_hot, 1)
            if not xpub:
                return
            wallet.add_master_public_key("cold/", xpub)
            wallet.create_account()
            self.waiting_dialog(wallet.synchronize)


        if action == 'create_2of3_2':
            xpub_hot = wallet.master_public_keys.get("m/")
            r = self.multi_mpk_dialog(xpub_hot, 2)
            if not r:
                return
            xpub1, xpub2 = r
            wallet.add_master_public_key("cold/", xpub1)
            wallet.add_master_public_key("remote/", xpub2)
            wallet.create_account()
            self.waiting_dialog(wallet.synchronize)


        if action == 'create_2fa_3':
            run_hook('create_remote_key', wallet, self)
            if not wallet.master_public_keys.get("remote/"):
                return
            wallet.create_account()
            self.waiting_dialog(wallet.synchronize)


        if action == 'restore':

            if t == 'standard':
                text = self.enter_seed_dialog(MSG_ENTER_ANYTHING, None)
                if not text:
                    return
                if Wallet.is_seed(text):
                    password = self.password_dialog()
                    wallet = Wallet.from_seed(text, self.storage)
                    wallet.add_seed(text, password)
                    wallet.create_accounts(password)
                elif Wallet.is_mpk(text):
                    wallet = Wallet.from_mpk(text, self.storage)
                elif Wallet.is_address(text):
                    wallet = Wallet.from_address(text, self.storage)
                elif Wallet.is_private_key(text):
                    wallet = Wallet.from_private_key(text, self.storage)
                else:
                    raise

            elif t in ['2fa', '2of2']:
                r = self.multi_seed_dialog(1)
                if not r: 
                    return
                text1, text2 = r
                password = self.password_dialog()
                if t == '2of2':
                    wallet = Wallet_2of2(self.storage)
                elif t == '2of3':
                    wallet = Wallet_2of3(self.storage)
                elif t == '2fa':
                    wallet = Wallet_2of3(self.storage)

                if Wallet.is_seed(text1):
                    wallet.add_seed(text1, password)
                    if Wallet.is_seed(text2):
                        wallet.add_cold_seed(text2, password)
                    else:
                        wallet.add_master_public_key("cold/", text2)

                elif Wallet.is_mpk(text1):
                    if Wallet.is_seed(text2):
                        wallet.add_seed(text2, password)
                        wallet.add_master_public_key("cold/", text1)
                    else:
                        wallet.add_master_public_key("m/", text1)
                        wallet.add_master_public_key("cold/", text2)

                if t == '2fa':
                    run_hook('restore_third_key', wallet, self)

                wallet.create_account()

            elif t in ['2of3']:
                r = self.multi_seed_dialog(2)
                if not r: 
                    return
                text1, text2, text3 = r
                password = self.password_dialog()
                wallet = Wallet_2of3(self.storage)

                if Wallet.is_seed(text1):
                    wallet.add_seed(text1, password)
                    if Wallet.is_seed(text2):
                        wallet.add_cold_seed(text2, password)
                    else:
                        wallet.add_master_public_key("cold/", text2)

                elif Wallet.is_mpk(text1):
                    if Wallet.is_seed(text2):
                        wallet.add_seed(text2, password)
                        wallet.add_master_public_key("cold/", text1)
                    else:
                        wallet.add_master_public_key("m/", text1)
                        wallet.add_master_public_key("cold/", text2)

                wallet.create_account()

            else:
                raise


                
        #if not self.config.get('server'):
        if self.network:
            if self.network.interfaces:
                self.network_dialog()
            else:
                QMessageBox.information(None, _('Warning'), _('You are offline'), _('OK'))
                self.network.stop()
                self.network = None

        # start wallet threads
        wallet.start_threads(self.network)

        if action == 'restore':

            self.waiting_dialog(lambda: wallet.restore(self.waiting_label.setText))

            if self.network:
                if wallet.is_found():
                    QMessageBox.information(None, _('Information'), _("Recovery successful"), _('OK'))
                else:
                    QMessageBox.information(None, _('Information'), _("No transactions found for this seed"), _('OK'))
            else:
                QMessageBox.information(None, _('Information'), _("This wallet was restored offline. It may contain more addresses than displayed."), _('OK'))

        return wallet

########NEW FILE########
__FILENAME__ = lite_window
import sys

# Let's do some dep checking and handle missing ones gracefully
try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    from PyQt4.Qt import Qt
    import PyQt4.QtCore as QtCore

except ImportError:
    print "You need to have PyQT installed to run Electrum in graphical mode."
    print "If you have pip installed try 'sudo pip install pyqt' if you are on Debian/Ubuntu try 'sudo apt-get install python-qt4'."
    sys.exit(0)

from decimal import Decimal as D
from electrum.util import get_resource_path as rsrc
from electrum.bitcoin import is_valid
from electrum.i18n import _
import decimal
import json
import os.path
import random
import re
import time
from electrum.wallet import Wallet, WalletStorage
import webbrowser
import history_widget
import receiving_widget
from electrum import util
import datetime

from electrum.version import ELECTRUM_VERSION as electrum_version
from electrum.util import format_satoshis, age

from main_window import ElectrumWindow
import shutil

from util import *

bitcoin = lambda v: v * 100000000

def IconButton(filename, parent=None):
    pixmap = QPixmap(filename)
    icon = QIcon(pixmap)
    return QPushButton(icon, "", parent)


def resize_line_edit_width(line_edit, text_input):
    metrics = QFontMetrics(qApp.font())
    # Create an extra character to add some space on the end
    text_input += "A"
    line_edit.setMinimumWidth(metrics.width(text_input))

def load_theme_name(theme_path):
    try:
        with open(os.path.join(theme_path, "name.cfg")) as name_cfg_file:
            return name_cfg_file.read().rstrip("\n").strip()
    except IOError:
        return None


def theme_dirs_from_prefix(prefix):
    if not os.path.exists(prefix):
        return []
    theme_paths = {}
    for potential_theme in os.listdir(prefix):
        theme_full_path = os.path.join(prefix, potential_theme)
        theme_css = os.path.join(theme_full_path, "style.css")
        if not os.path.exists(theme_css):
            continue
        theme_name = load_theme_name(theme_full_path)
        if theme_name is None:
            continue
        theme_paths[theme_name] = prefix, potential_theme
    return theme_paths

def load_theme_paths():
    theme_paths = {}
    prefixes = (util.local_data_dir(), util.appdata_dir())
    for prefix in prefixes:
        theme_paths.update(theme_dirs_from_prefix(prefix))
    return theme_paths




class TransactionWindow(QDialog):

    def set_label(self):
        label = unicode(self.label_edit.text())
        self.parent.wallet.labels[self.tx_id] = label

        super(TransactionWindow, self).accept() 

    def __init__(self, transaction_id, parent):
        super(TransactionWindow, self).__init__()

        self.tx_id = str(transaction_id)
        self.parent = parent

        self.setModal(True)
        self.resize(200,100)
        self.setWindowTitle(_("Transaction successfully sent"))

        self.layout = QGridLayout(self)
        history_label = "%s\n%s" % (_("Your transaction has been sent."), _("Please enter a label for this transaction for future reference."))
        self.layout.addWidget(QLabel(history_label))

        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText(_("Transaction label"))
        self.label_edit.setObjectName("label_input")
        self.label_edit.setAttribute(Qt.WA_MacShowFocusRect, 0)
        self.label_edit.setFocusPolicy(Qt.ClickFocus)
        self.layout.addWidget(self.label_edit)

        self.save_button = QPushButton(_("Save"))
        self.layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.set_label)

        self.exec_()

class MiniWindow(QDialog):

    def __init__(self, actuator, expand_callback, config):
        super(MiniWindow, self).__init__()

        self.actuator = actuator
        self.config = config
        self.btc_balance = None
        self.use_exchanges = ["Blockchain", "CoinDesk"]
        self.quote_currencies = ["BRL", "CNY", "EUR", "GBP", "RUB", "USD"]
        self.actuator.set_configured_currency(self.set_quote_currency)
        self.actuator.set_configured_exchange(self.set_exchange)

        # Needed because price discovery is done in a different thread
        # which needs to be sent back to this main one to update the GUI
        self.connect(self, SIGNAL("refresh_balance()"), self.refresh_balance)

        self.balance_label = BalanceLabel(self.change_quote_currency, self)
        self.balance_label.setObjectName("balance_label")


        # Bitcoin address code
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText(_("Enter a Bitcoin address or contact"))
        self.address_input.setObjectName("address_input")

        self.address_input.setFocusPolicy(Qt.ClickFocus)

        self.address_input.textChanged.connect(self.address_field_changed)
        resize_line_edit_width(self.address_input,
                               "1BtaFUr3qVvAmwrsuDuu5zk6e4s2rxd2Gy")

        self.address_completions = QStringListModel()
        address_completer = QCompleter(self.address_input)
        address_completer.setCaseSensitivity(False)
        address_completer.setModel(self.address_completions)
        self.address_input.setCompleter(address_completer)

        address_layout = QHBoxLayout()
        address_layout.addWidget(self.address_input)

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText(_("... and amount") + " (%s)"%self.actuator.g.base_unit())
        self.amount_input.setObjectName("amount_input")

        self.amount_input.setFocusPolicy(Qt.ClickFocus)
        # This is changed according to the user's displayed balance
        self.amount_validator = QDoubleValidator(self.amount_input)
        self.amount_validator.setNotation(QDoubleValidator.StandardNotation)
        self.amount_validator.setDecimals(8)
        self.amount_input.setValidator(self.amount_validator)

        # This removes the very ugly OSX highlighting, please leave this in :D
        self.address_input.setAttribute(Qt.WA_MacShowFocusRect, 0)
        self.amount_input.setAttribute(Qt.WA_MacShowFocusRect, 0)
        self.amount_input.textChanged.connect(self.amount_input_changed)

        #if self.actuator.g.wallet.seed:
        self.send_button = QPushButton(_("&Send"))
        #else:
        #    self.send_button = QPushButton(_("&Create"))

        self.send_button.setObjectName("send_button")
        self.send_button.setDisabled(True);
        self.send_button.clicked.connect(self.send)

        # Creating the receive button
        self.switch_button = QPushButton( QIcon(":icons/switchgui.png"),'' )
        self.switch_button.setMaximumWidth(25)
        self.switch_button.setFlat(True)
        self.switch_button.clicked.connect(expand_callback)

        main_layout = QGridLayout(self)

        main_layout.addWidget(self.balance_label, 0, 0, 1, 3)
        main_layout.addWidget(self.switch_button, 0, 3)

        main_layout.addWidget(self.address_input, 1, 0, 1, 4)
        main_layout.addWidget(self.amount_input, 2, 0, 1, 2)
        main_layout.addWidget(self.send_button, 2, 2, 1, 2)

        self.send_button.setMaximumWidth(125)

        self.history_list = history_widget.HistoryWidget()
        self.history_list.setObjectName("history")
        self.history_list.hide()
        self.history_list.setAlternatingRowColors(True)

        main_layout.addWidget(self.history_list, 3, 0, 1, 4)

        self.receiving = receiving_widget.ReceivingWidget(self)
        self.receiving.setObjectName("receiving")

        # Add to the right side 
        self.receiving_box = QGroupBox(_("Select a receiving address"))
        extra_layout = QGridLayout()

        # Checkbox to filter used addresses
        hide_used = QCheckBox(_('Hide used addresses'))
        hide_used.setChecked(True)
        hide_used.stateChanged.connect(self.receiving.toggle_used)

        # Events for receiving addresses
        self.receiving.clicked.connect(self.receiving.copy_address)
        self.receiving.itemDoubleClicked.connect(self.receiving.edit_label)
        self.receiving.itemChanged.connect(self.receiving.update_label)


        # Label
        extra_layout.addWidget( QLabel(_('Selecting an address will copy it to the clipboard.') + '\n' + _('Double clicking the label will allow you to edit it.') ),0,0)

        extra_layout.addWidget(self.receiving, 1,0)
        extra_layout.addWidget(hide_used, 2,0)
        extra_layout.setColumnMinimumWidth(0,200)

        self.receiving_box.setLayout(extra_layout)
        main_layout.addWidget(self.receiving_box,0,4,-1,3)
        self.receiving_box.hide()

        self.main_layout = main_layout

        quit_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_shortcut.activated.connect(self.close)
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

        g = self.config.get("winpos-lite",[4, 25, 351, 149])
        self.setGeometry(g[0], g[1], g[2], g[3])

        show_hist = self.config.get("gui_show_history",False)
        self.show_history(show_hist)
        show_hist = self.config.get("gui_show_receiving",False)
        self.toggle_receiving_layout(show_hist)
        
        self.setWindowIcon(QIcon(":icons/electrum.png"))
        self.setWindowTitle("Electrum")
        self.setWindowFlags(Qt.Window|Qt.MSWindowsFixedSizeDialogHint)
        self.layout().setSizeConstraint(QLayout.SetFixedSize)
        self.setObjectName("main_window")


    def context_menu(self):
        view_menu = QMenu()
        themes_menu = view_menu.addMenu(_("&Themes"))
        selected_theme = self.actuator.selected_theme()
        theme_group = QActionGroup(self)
        for theme_name in self.actuator.theme_names():
            theme_action = themes_menu.addAction(theme_name)
            theme_action.setCheckable(True)
            if selected_theme == theme_name:
                theme_action.setChecked(True)
            class SelectThemeFunctor:
                def __init__(self, theme_name, toggle_theme):
                    self.theme_name = theme_name
                    self.toggle_theme = toggle_theme
                def __call__(self, checked):
                    if checked:
                        self.toggle_theme(self.theme_name)
            delegate = SelectThemeFunctor(theme_name, self.toggle_theme)
            theme_action.toggled.connect(delegate)
            theme_group.addAction(theme_action)
        view_menu.addSeparator()

        show_receiving = view_menu.addAction(_("Show Receiving addresses"))
        show_receiving.setCheckable(True)
        show_receiving.toggled.connect(self.toggle_receiving_layout)
        show_receiving.setChecked(self.config.get("gui_show_receiving",False))

        show_history = view_menu.addAction(_("Show History"))
        show_history.setCheckable(True)
        show_history.toggled.connect(self.show_history)
        show_history.setChecked(self.config.get("gui_show_history",False))

        return view_menu



    def toggle_theme(self, theme_name):
        self.actuator.change_theme(theme_name)
        # Recompute style globally
        qApp.style().unpolish(self)
        qApp.style().polish(self)

    def closeEvent(self, event):
        g = self.geometry()
        self.config.set_key("winpos-lite", [g.left(),g.top(),g.width(),g.height()],True)
        self.actuator.g.closeEvent(event)
        qApp.quit()

    def set_payment_fields(self, dest_address, amount):
        self.address_input.setText(dest_address)
        self.address_field_changed(dest_address)
        self.amount_input.setText(amount)

    def activate(self):
        pass

    def deactivate(self):
        pass

    def set_exchange(self, use_exchange):
        if use_exchange not in self.use_exchanges:
            return
        self.use_exchanges.remove(use_exchange)
        self.use_exchanges.insert(0, use_exchange)
        self.refresh_balance()

    def set_quote_currency(self, currency):
        """Set and display the fiat currency country."""
        if currency not in self.quote_currencies:
            return
        self.quote_currencies.remove(currency)
        self.quote_currencies.insert(0, currency)
        self.refresh_balance()

    def change_quote_currency(self, forward=True):
        if forward:
            self.quote_currencies = \
                self.quote_currencies[1:] + self.quote_currencies[0:1]
        else:
            self.quote_currencies = \
                self.quote_currencies[-1:] + self.quote_currencies[0:-1]
        self.actuator.set_config_currency(self.quote_currencies[0])
        self.refresh_balance()

    def refresh_balance(self):
        if self.btc_balance is None:
            # Price has been discovered before wallet has been loaded
            # and server connect... so bail.
            return
        self.set_balances(self.btc_balance)
        self.amount_input_changed(self.amount_input.text())

    def set_balances(self, btc_balance):
        """Set the bitcoin balance and update the amount label accordingly."""
        self.btc_balance = btc_balance
        quote_text = self.create_quote_text(btc_balance)
        if quote_text:
            quote_text = "(%s)" % quote_text

        amount = self.actuator.g.format_amount(btc_balance)
        unit = self.actuator.g.base_unit()

        self.balance_label.set_balance_text(amount, unit, quote_text)
        self.setWindowTitle("Electrum %s - %s %s" % (electrum_version, amount, unit))

    def amount_input_changed(self, amount_text):
        """Update the number of bitcoins displayed."""
        self.check_button_status()

        try:
            amount = D(str(amount_text)) * (10**self.actuator.g.decimal_point)
        except decimal.InvalidOperation:
            self.balance_label.show_balance()
        else:
            quote_text = self.create_quote_text(amount)
            if quote_text:
                self.balance_label.set_amount_text(quote_text)
                self.balance_label.show_amount()
            else:
                self.balance_label.show_balance()

    def create_quote_text(self, btc_balance):
        """Return a string copy of the amount fiat currency the 
        user has in bitcoins."""
        from electrum.plugins import run_hook
        r = {}
        run_hook('get_fiat_balance_text', btc_balance, r)
        return r.get(0,'')

    def send(self):
        if self.actuator.send(self.address_input.text(),
                              self.amount_input.text(), self):
            self.address_input.setText("")
            self.amount_input.setText("")

    def check_button_status(self):
        """Check that the bitcoin address is valid and that something
        is entered in the amount before making the send button clickable."""
        try:
            value = D(str(self.amount_input.text())) * (10**self.actuator.g.decimal_point)
        except decimal.InvalidOperation:
            value = None
        # self.address_input.property(...) returns a qVariant, not a bool.
        # The == is needed to properly invoke a comparison.
        if (self.address_input.property("isValid") == True and
            value is not None and 0 < value <= self.btc_balance):
            self.send_button.setDisabled(False)
        else:
            self.send_button.setDisabled(True)

    def address_field_changed(self, address):
        # label or alias, with address in brackets
        match2 = re.match("(.*?)\s*\<([1-9A-HJ-NP-Za-km-z]{26,})\>",
                          address)
        if match2:
          address = match2.group(2)
          self.address_input.setText(address)

        if is_valid(address):
            self.check_button_status()
            self.address_input.setProperty("isValid", True)
            self.recompute_style(self.address_input)
        else:
            self.send_button.setDisabled(True)
            self.address_input.setProperty("isValid", False)
            self.recompute_style(self.address_input)

        if len(address) == 0:
            self.address_input.setProperty("isValid", None)
            self.recompute_style(self.address_input)

    def recompute_style(self, element):
        self.style().unpolish(element)
        self.style().polish(element)

    def copy_address(self):
        receive_popup = ReceivePopup(self.receive_button)
        self.actuator.copy_address(receive_popup)

    def update_completions(self, completions):
        self.address_completions.setStringList(completions)
 

    def update_history(self, tx_history):

        self.history_list.empty()

        for item in tx_history[-10:]:
            tx_hash, conf, is_mine, value, fee, balance, timestamp = item
            label = self.actuator.g.wallet.get_label(tx_hash)[0]
            v_str = self.actuator.g.format_amount(value, True)
            self.history_list.append(label, v_str, age(timestamp))


    def the_website(self):
        webbrowser.open("http://electrum.org")


    def toggle_receiving_layout(self, toggle_state):
        if toggle_state:
            self.receiving_box.show()
        else:
            self.receiving_box.hide()
        self.config.set_key("gui_show_receiving", toggle_state)

    def show_history(self, toggle_state):
        if toggle_state:
            self.main_layout.setRowMinimumHeight(3,200)
            self.history_list.show()
        else:
            self.main_layout.setRowMinimumHeight(3,0)
            self.history_list.hide()
        self.config.set_key("gui_show_history", toggle_state)

class BalanceLabel(QLabel):

    SHOW_CONNECTING = 1
    SHOW_BALANCE = 2
    SHOW_AMOUNT = 3

    def __init__(self, change_quote_currency, parent=None):
        super(QLabel, self).__init__(_("Connecting..."), parent)
        self.change_quote_currency = change_quote_currency
        self.state = self.SHOW_CONNECTING
        self.balance_text = ""
        self.amount_text = ""
        self.parent = parent

    def mousePressEvent(self, event):
        """Change the fiat currency selection if window background is clicked."""
        if self.state != self.SHOW_CONNECTING:
            if event.button() == Qt.LeftButton:
                self.change_quote_currency()
            else:
                position = event.globalPos()
                menu = self.parent.context_menu()
                menu.exec_(position)
                

    def set_balance_text(self, amount, unit, quote_text):
        """Set the amount of bitcoins in the gui."""
        if self.state == self.SHOW_CONNECTING:
            self.state = self.SHOW_BALANCE

        self.balance_text = "<span style='font-size: 18pt'>%s</span>"%amount\
            + " <span style='font-size: 10pt'>%s</span>" % unit \
            + " <span style='font-size: 10pt'>%s</span>" % quote_text

        if self.state == self.SHOW_BALANCE:
            self.setText(self.balance_text)

    def set_amount_text(self, quote_text):
        self.amount_text = "<span style='font-size: 10pt'>%s</span>" % quote_text
        if self.state == self.SHOW_AMOUNT:
            self.setText(self.amount_text)

    def show_balance(self):
        if self.state == self.SHOW_AMOUNT:
            self.state = self.SHOW_BALANCE
            self.setText(self.balance_text)

    def show_amount(self):
        if self.state == self.SHOW_BALANCE:
            self.state = self.SHOW_AMOUNT
            self.setText(self.amount_text)

def ok_cancel_buttons(dialog):
    row_layout = QHBoxLayout()
    row_layout.addStretch(1)
    ok_button = QPushButton(_("OK"))
    row_layout.addWidget(ok_button)
    ok_button.clicked.connect(dialog.accept)
    cancel_button = QPushButton(_("Cancel"))
    row_layout.addWidget(cancel_button)
    cancel_button.clicked.connect(dialog.reject)
    return row_layout

class PasswordDialog(QDialog):

    def __init__(self, parent):
        super(QDialog, self).__init__(parent)

        self.setModal(True)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        main_layout = QVBoxLayout(self)
        message = _('Please enter your password')
        main_layout.addWidget(QLabel(message))

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.addWidget(QLabel(_('Password')), 1, 0)
        grid.addWidget(self.password_input, 1, 1)
        main_layout.addLayout(grid)

        main_layout.addLayout(ok_cancel_buttons(self))
        self.setLayout(main_layout) 

    def run(self):
        if not self.exec_():
            return
        return unicode(self.password_input.text())

class ReceivePopup(QDialog):

    def leaveEvent(self, event):
        self.close()

    def setup(self, address):
        label = QLabel(_("Copied your Bitcoin address to the clipboard!"))
        address_display = QLineEdit(address)
        address_display.setReadOnly(True)
        resize_line_edit_width(address_display, address)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(label)
        main_layout.addWidget(address_display)

        self.setMouseTracking(True)
        self.setWindowTitle("Electrum - " + _("Receive Bitcoin payment"))
        self.setWindowFlags(Qt.Window|Qt.FramelessWindowHint|
                            Qt.MSWindowsFixedSizeDialogHint)
        self.layout().setSizeConstraint(QLayout.SetFixedSize)
        #self.setFrameStyle(QFrame.WinPanel|QFrame.Raised)
        #self.setAlignment(Qt.AlignCenter)

    def popup(self):
        parent = self.parent()
        top_left_pos = parent.mapToGlobal(parent.rect().bottomLeft())
        self.move(top_left_pos)
        center_mouse_pos = self.mapToGlobal(self.rect().center())
        QCursor.setPos(center_mouse_pos)
        self.show()

class MiniActuator:
    """Initialize the definitions relating to themes and 
    sending/receiving bitcoins."""
    
    
    def __init__(self, main_window):
        """Retrieve the gui theme used in previous session."""
        self.g = main_window
        self.theme_name = self.g.config.get('litegui_theme','Cleanlook')
        self.themes = load_theme_paths()
        self.load_theme()

    def load_theme(self):
        """Load theme retrieved from wallet file."""
        try:
            theme_prefix, theme_path = self.themes[self.theme_name]
        except KeyError:
            util.print_error("Theme not found!", self.theme_name)
            return
        full_theme_path = "%s/%s/style.css" % (theme_prefix, theme_path)
        with open(full_theme_path) as style_file:
            qApp.setStyleSheet(style_file.read())

    def theme_names(self):
        """Sort themes."""
        return sorted(self.themes.keys())
    
    def selected_theme(self):
        """Select theme."""
        return self.theme_name

    def change_theme(self, theme_name):
        """Change theme."""
        self.theme_name = theme_name
        self.g.config.set_key('litegui_theme',theme_name)
        self.load_theme()
   
    def set_configured_exchange(self, set_exchange):
        use_exchange = self.g.config.get('use_exchange')
        if use_exchange is not None:
            set_exchange(use_exchange)
    
    def set_configured_currency(self, set_quote_currency):
        """Set the inital fiat currency conversion country (USD/EUR/GBP) in 
        the GUI to what it was set to in the wallet."""
        currency = self.g.config.get('currency')
        # currency can be none when Electrum is used for the first
        # time and no setting has been created yet.
        if currency is not None:
            set_quote_currency(currency)

    def set_config_exchange(self, conversion_exchange):
        self.g.config.set_key('exchange',conversion_exchange,True)
        self.g.update_status()

    def set_config_currency(self, conversion_currency):
        """Change the wallet fiat currency country."""
        self.g.config.set_key('currency',conversion_currency,True)
        self.g.update_status()

    def copy_address(self, receive_popup):
        """Copy the wallet addresses into the client."""
        addrs = [addr for addr in self.g.wallet.addresses(True)
                 if not self.g.wallet.is_change(addr)]
        # Select most recent addresses from gap limit
        addrs = addrs[-self.g.wallet.gap_limit:]
        copied_address = random.choice(addrs)
        qApp.clipboard().setText(copied_address)
        receive_popup.setup(copied_address)
        receive_popup.popup()

    def waiting_dialog(self, f):
        s = Timer()
        s.start()
        w = QDialog()
        w.resize(200, 70)
        w.setWindowTitle('Electrum')
        l = QLabel(_('Sending transaction, please wait.'))
        vbox = QVBoxLayout()
        vbox.addWidget(l)
        w.setLayout(vbox)
        w.show()
        def ff():
            s = f()
            if s: l.setText(s)
            else: w.close()
        w.connect(s, QtCore.SIGNAL('timersignal'), ff)
        w.exec_()
        w.destroy()


    def send(self, address, amount, parent_window):
        """Send bitcoins to the target address."""
        dest_address = self.fetch_destination(address)

        if dest_address is None or not is_valid(dest_address):
            QMessageBox.warning(parent_window, _('Error'), 
                _('Invalid Bitcoin Address') + ':\n' + address, _('OK'))
            return False

        amount = D(unicode(amount)) * (10*self.g.decimal_point)
        print "amount", amount
        return

        if self.g.wallet.use_encryption:
            password_dialog = PasswordDialog(parent_window)
            password = password_dialog.run()
            if not password:
                return
        else:
            password = None

        fee = 0
        # 0.1 BTC = 10000000
        if amount < bitcoin(1) / 10:
            # 0.001 BTC
            fee = bitcoin(1) / 1000

        try:
            tx = self.g.wallet.mktx([(dest_address, amount)], password, fee)
        except Exception as error:
            QMessageBox.warning(parent_window, _('Error'), str(error), _('OK'))
            return False

        if tx.is_complete():
            h = self.g.wallet.send_tx(tx)

            self.waiting_dialog(lambda: False if self.g.wallet.tx_event.isSet() else _("Sending transaction, please wait..."))
              
            status, message = self.g.wallet.receive_tx(h, tx)

            if not status:
                import tempfile
                dumpf = tempfile.NamedTemporaryFile(delete=False)
                dumpf.write(tx)
                dumpf.close()
                print "Dumped error tx to", dumpf.name
                QMessageBox.warning(parent_window, _('Error'), message, _('OK'))
                return False
          
            TransactionWindow(message, self)
        else:
            filename = 'unsigned_tx_%s' % (time.mktime(time.gmtime()))
            try:
                fileName = QFileDialog.getSaveFileName(QWidget(), _("Select a transaction filename"), os.path.expanduser('~/%s' % (filename)))
                with open(fileName,'w') as f:
                    f.write(json.dumps(tx.as_dict(),indent=4) + '\n')
                QMessageBox.information(QWidget(), _('Unsigned transaction created'), _("Unsigned transaction was saved to file:") + " " +fileName, _('OK'))
            except Exception as e:
                QMessageBox.warning(QWidget(), _('Error'), _('Could not write transaction to file: %s' % e), _('OK'))
        return True

    def fetch_destination(self, address):
        recipient = unicode(address).strip()

        # alias
        match1 = re.match("^(|([\w\-\.]+)@)((\w[\w\-]+\.)+[\w\-]+)$",
                          recipient)

        # label or alias, with address in brackets
        match2 = re.match("(.*?)\s*\<([1-9A-HJ-NP-Za-km-z]{26,})\>",
                          recipient)
        
        if match1:
            dest_address = \
                self.g.wallet.get_alias(recipient, True, 
                                      self.show_message, self.question)
            return dest_address
        elif match2:
            return match2.group(2)
        else:
            return recipient


        


class MiniDriver(QObject):

    INITIALIZING = 0
    CONNECTING = 1
    SYNCHRONIZING = 2
    READY = 3

    def __init__(self, main_window, mini_window):
        super(QObject, self).__init__()

        self.g = main_window
        self.network = main_window.network
        self.window = mini_window

        if self.network:
            self.network.register_callback('updated',self.update_callback)
            self.network.register_callback('connected', self.update_callback)
            self.network.register_callback('disconnected', self.update_callback)

        self.state = None

        self.initializing()
        self.connect(self, SIGNAL("updatesignal()"), self.update)
        self.update_callback()

    # This is a hack to workaround that Qt does not like changing the
    # window properties from this other thread before the runloop has
    # been called from.
    def update_callback(self):
        self.emit(SIGNAL("updatesignal()"))

    def update(self):
        if not self.network:
            self.initializing()
        elif not self.network.interface:
            self.initializing()
        elif not self.network.interface.is_connected:
            self.connecting()

        if self.g.wallet is None:
            self.ready()
        elif not self.g.wallet.up_to_date:
            self.synchronizing()
        else:
            self.ready()
            self.update_balance()
            self.update_completions()
            self.update_history()
            self.window.receiving.update_list()


    def initializing(self):
        if self.state == self.INITIALIZING:
            return
        self.state = self.INITIALIZING
        self.window.deactivate()

    def connecting(self):
        if self.state == self.CONNECTING:
            return
        self.state = self.CONNECTING
        self.window.deactivate()

    def synchronizing(self):
        if self.state == self.SYNCHRONIZING:
            return
        self.state = self.SYNCHRONIZING
        self.window.deactivate()

    def ready(self):
        if self.state == self.READY:
            return
        self.state = self.READY
        self.window.activate()

    def update_balance(self):
        conf_balance, unconf_balance = self.g.wallet.get_balance()
        balance = D(conf_balance + unconf_balance)
        self.window.set_balances(balance)

    def update_completions(self):
        completions = []
        for addr, label in self.g.wallet.labels.items():
            if addr in self.g.wallet.addressbook:
                completions.append("%s <%s>" % (label, addr))
        self.window.update_completions(completions)

    def update_history(self):
        tx_history = self.g.wallet.get_tx_history()
        self.window.update_history(tx_history)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    with open(rsrc("style.css")) as style_file:
        app.setStyleSheet(style_file.read())
    mini = MiniWindow()
    sys.exit(app.exec_())


########NEW FILE########
__FILENAME__ = main_window
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys, time, datetime, re, threading
from electrum.i18n import _, set_language
from electrum.util import print_error, print_msg
import os.path, json, ast, traceback
import webbrowser
import shutil
import StringIO


import PyQt4
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore

from electrum.bitcoin import MIN_RELAY_TX_FEE, is_valid
from electrum.plugins import run_hook

import icons_rc

from electrum.wallet import format_satoshis
from electrum import Transaction
from electrum import mnemonic
from electrum import util, bitcoin, commands, Interface, Wallet
from electrum import SimpleConfig, Wallet, WalletStorage


from electrum import bmp, pyqrnative

from amountedit import AmountEdit
from network_dialog import NetworkDialog
from qrcodewidget import QRCodeWidget

from decimal import Decimal

import platform
import httplib
import socket
import webbrowser
import csv

if platform.system() == 'Windows':
    MONOSPACE_FONT = 'Lucida Console'
elif platform.system() == 'Darwin':
    MONOSPACE_FONT = 'Monaco'
else:
    MONOSPACE_FONT = 'monospace'

from electrum import ELECTRUM_VERSION
import re

from util import *






class StatusBarButton(QPushButton):
    def __init__(self, icon, tooltip, func):
        QPushButton.__init__(self, icon, '')
        self.setToolTip(tooltip)
        self.setFlat(True)
        self.setMaximumWidth(25)
        self.clicked.connect(func)
        self.func = func
        self.setIconSize(QSize(25,25))

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Return:
            apply(self.func,())










default_column_widths = { "history":[40,140,350,140], "contacts":[350,330], "receive": [370,200,130] }

class ElectrumWindow(QMainWindow):



    def __init__(self, config, network, gui_object):
        QMainWindow.__init__(self)

        self.config = config
        self.network = network
        self.gui_object = gui_object
        self.tray = gui_object.tray
        self.go_lite = gui_object.go_lite
        self.lite = None

        self.create_status_bar()
        self.need_update = threading.Event()

        self.decimal_point = config.get('decimal_point', 5)
        self.num_zeros     = int(config.get('num_zeros',0))

        set_language(config.get('language'))

        self.funds_error = False
        self.completions = QStringListModel()

        self.tabs = tabs = QTabWidget(self)
        self.column_widths = self.config.get("column_widths_2", default_column_widths )
        tabs.addTab(self.create_history_tab(), _('History') )
        tabs.addTab(self.create_send_tab(), _('Send') )
        tabs.addTab(self.create_receive_tab(), _('Receive') )
        tabs.addTab(self.create_contacts_tab(), _('Contacts') )
        tabs.addTab(self.create_console_tab(), _('Console') )
        tabs.setMinimumSize(600, 400)
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(tabs)

        g = self.config.get("winpos-qt",[100, 100, 840, 400])
        self.setGeometry(g[0], g[1], g[2], g[3])
        if self.config.get("is_maximized"):
            self.showMaximized()

        self.setWindowIcon(QIcon(":icons/electrum.png"))
        self.init_menubar()

        QShortcut(QKeySequence("Ctrl+W"), self, self.close)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+R"), self, self.update_wallet)
        QShortcut(QKeySequence("Ctrl+PgUp"), self, lambda: tabs.setCurrentIndex( (tabs.currentIndex() - 1 )%tabs.count() ))
        QShortcut(QKeySequence("Ctrl+PgDown"), self, lambda: tabs.setCurrentIndex( (tabs.currentIndex() + 1 )%tabs.count() ))

        for i in range(tabs.count()):
            QShortcut(QKeySequence("Alt+" + str(i + 1)), self, lambda i=i: tabs.setCurrentIndex(i))

        self.connect(self, QtCore.SIGNAL('update_status'), self.update_status)
        self.connect(self, QtCore.SIGNAL('banner_signal'), lambda: self.console.showMessage(self.network.banner) )
        self.connect(self, QtCore.SIGNAL('transaction_signal'), lambda: self.notify_transactions() )
        self.connect(self, QtCore.SIGNAL('payment_request_ok'), self.payment_request_ok)
        self.connect(self, QtCore.SIGNAL('payment_request_error'), self.payment_request_error)

        self.history_list.setFocus(True)

        # network callbacks
        if self.network:
            self.network.register_callback('updated', lambda: self.need_update.set())
            self.network.register_callback('banner', lambda: self.emit(QtCore.SIGNAL('banner_signal')))
            self.network.register_callback('disconnected', lambda: self.emit(QtCore.SIGNAL('update_status')))
            self.network.register_callback('disconnecting', lambda: self.emit(QtCore.SIGNAL('update_status')))
            self.network.register_callback('new_transaction', lambda: self.emit(QtCore.SIGNAL('transaction_signal')))

            # set initial message
            self.console.showMessage(self.network.banner)

        self.wallet = None


    def update_account_selector(self):
        # account selector
        accounts = self.wallet.get_account_names()
        self.account_selector.clear()
        if len(accounts) > 1:
            self.account_selector.addItems([_("All accounts")] + accounts.values())
            self.account_selector.setCurrentIndex(0)
            self.account_selector.show()
        else:
            self.account_selector.hide()


    def load_wallet(self, wallet):
        import electrum
        self.wallet = wallet
        self.accounts_expanded = self.wallet.storage.get('accounts_expanded',{})
        self.current_account = self.wallet.storage.get("current_account", None)

        title = 'Electrum ' + self.wallet.electrum_version + '  -  ' + self.wallet.storage.path
        if self.wallet.is_watching_only(): title += ' [%s]' % (_('watching only'))
        self.setWindowTitle( title )
        self.update_wallet()
        # Once GUI has been initialized check if we want to announce something since the callback has been called before the GUI was initialized
        self.notify_transactions()
        self.update_account_selector()
        # update menus
        self.new_account_menu.setEnabled(self.wallet.can_create_accounts())
        self.private_keys_menu.setEnabled(not self.wallet.is_watching_only())
        self.password_menu.setEnabled(not self.wallet.is_watching_only())
        self.seed_menu.setEnabled(self.wallet.has_seed())
        self.mpk_menu.setEnabled(self.wallet.is_deterministic())
        self.import_menu.setEnabled(self.wallet.can_import())

        self.update_lock_icon()
        self.update_buttons_on_seed()
        self.update_console()

        run_hook('load_wallet', wallet)


    def open_wallet(self):
        wallet_folder = self.wallet.storage.path
        filename = unicode( QFileDialog.getOpenFileName(self, "Select your wallet file", wallet_folder) )
        if not filename:
            return

        storage = WalletStorage({'wallet_path': filename})
        if not storage.file_exists:
            self.show_message("file not found "+ filename)
            return

        self.wallet.stop_threads()

        # create new wallet
        wallet = Wallet(storage)
        wallet.start_threads(self.network)

        self.load_wallet(wallet)



    def backup_wallet(self):
        import shutil
        path = self.wallet.storage.path
        wallet_folder = os.path.dirname(path)
        filename = unicode( QFileDialog.getSaveFileName(self, _('Enter a filename for the copy of your wallet'), wallet_folder) )
        if not filename:
            return

        new_path = os.path.join(wallet_folder, filename)
        if new_path != path:
            try:
                shutil.copy2(path, new_path)
                QMessageBox.information(None,"Wallet backup created", _("A copy of your wallet file was created in")+" '%s'" % str(new_path))
            except (IOError, os.error), reason:
                QMessageBox.critical(None,"Unable to create backup", _("Electrum was unable to copy your wallet file to the specified location.")+"\n" + str(reason))


    def new_wallet(self):
        import installwizard

        wallet_folder = os.path.dirname(self.wallet.storage.path)
        filename = unicode( QFileDialog.getSaveFileName(self, _('Enter a new file name'), wallet_folder) )
        if not filename:
            return
        filename = os.path.join(wallet_folder, filename)

        storage = WalletStorage({'wallet_path': filename})
        if storage.file_exists:
            QMessageBox.critical(None, "Error", _("File exists"))
            return

        wizard = installwizard.InstallWizard(self.config, self.network, storage)
        wallet = wizard.run('new')
        if wallet:
            self.load_wallet(wallet)



    def init_menubar(self):
        menubar = QMenuBar()

        file_menu = menubar.addMenu(_("&File"))
        file_menu.addAction(_("&Open"), self.open_wallet).setShortcut(QKeySequence.Open)
        file_menu.addAction(_("&New/Restore"), self.new_wallet).setShortcut(QKeySequence.New)
        file_menu.addAction(_("&Save Copy"), self.backup_wallet).setShortcut(QKeySequence.SaveAs)
        file_menu.addAction(_("&Quit"), self.close)

        wallet_menu = menubar.addMenu(_("&Wallet"))
        wallet_menu.addAction(_("&New contact"), self.new_contact_dialog)
        self.new_account_menu = wallet_menu.addAction(_("&New account"), self.new_account_dialog)

        wallet_menu.addSeparator()

        self.password_menu = wallet_menu.addAction(_("&Password"), self.change_password_dialog)
        self.seed_menu = wallet_menu.addAction(_("&Seed"), self.show_seed_dialog)
        self.mpk_menu = wallet_menu.addAction(_("&Master Public Keys"), self.show_master_public_keys)

        wallet_menu.addSeparator()
        labels_menu = wallet_menu.addMenu(_("&Labels"))
        labels_menu.addAction(_("&Import"), self.do_import_labels)
        labels_menu.addAction(_("&Export"), self.do_export_labels)

        self.private_keys_menu = wallet_menu.addMenu(_("&Private keys"))
        self.private_keys_menu.addAction(_("&Sweep"), self.sweep_key_dialog)
        self.import_menu = self.private_keys_menu.addAction(_("&Import"), self.do_import_privkey)
        self.private_keys_menu.addAction(_("&Export"), self.export_privkeys_dialog)
        wallet_menu.addAction(_("&Export History"), self.export_history_dialog)

        tools_menu = menubar.addMenu(_("&Tools"))

        # Settings / Preferences are all reserved keywords in OSX using this as work around
        tools_menu.addAction(_("Electrum preferences") if sys.platform == 'darwin' else _("Preferences"), self.settings_dialog)
        tools_menu.addAction(_("&Network"), self.run_network_dialog)
        tools_menu.addAction(_("&Plugins"), self.plugins_dialog)
        tools_menu.addSeparator()
        tools_menu.addAction(_("&Sign/verify message"), self.sign_verify_message)
        #tools_menu.addAction(_("&Encrypt/decrypt message"), self.encrypt_message)
        tools_menu.addSeparator()

        csv_transaction_menu = tools_menu.addMenu(_("&Create transaction"))
        csv_transaction_menu.addAction(_("&From CSV file"), self.do_process_from_csv_file)
        csv_transaction_menu.addAction(_("&From CSV text"), self.do_process_from_csv_text)

        raw_transaction_menu = tools_menu.addMenu(_("&Load transaction"))
        raw_transaction_menu.addAction(_("&From file"), self.do_process_from_file)
        raw_transaction_menu.addAction(_("&From text"), self.do_process_from_text)
        raw_transaction_menu.addAction(_("&From the blockchain"), self.do_process_from_txid)

        help_menu = menubar.addMenu(_("&Help"))
        help_menu.addAction(_("&About"), self.show_about)
        help_menu.addAction(_("&Official website"), lambda: webbrowser.open("http://electrum.org"))
        help_menu.addSeparator()
        help_menu.addAction(_("&Documentation"), lambda: webbrowser.open("http://electrum.org/documentation.html")).setShortcut(QKeySequence.HelpContents)
        help_menu.addAction(_("&Report Bug"), self.show_report_bug)

        self.setMenuBar(menubar)

    def show_about(self):
        QMessageBox.about(self, "Electrum",
            _("Version")+" %s" % (self.wallet.electrum_version) + "\n\n" + _("Electrum's focus is speed, with low resource usage and simplifying Bitcoin. You do not need to perform regular backups, because your wallet can be recovered from a secret phrase that you can memorize or write on paper. Startup times are instant because it operates in conjunction with high-performance servers that handle the most complicated parts of the Bitcoin system."))

    def show_report_bug(self):
        QMessageBox.information(self, "Electrum - " + _("Reporting Bugs"),
            _("Please report any bugs as issues on github:")+" <a href=\"https://github.com/spesmilo/electrum/issues\">https://github.com/spesmilo/electrum/issues</a>")


    def notify_transactions(self):
        if not self.network or not self.network.is_connected():
            return

        print_error("Notifying GUI")
        if len(self.network.pending_transactions_for_notifications) > 0:
            # Combine the transactions if there are more then three
            tx_amount = len(self.network.pending_transactions_for_notifications)
            if(tx_amount >= 3):
                total_amount = 0
                for tx in self.network.pending_transactions_for_notifications:
                    is_relevant, is_mine, v, fee = self.wallet.get_tx_value(tx)
                    if(v > 0):
                        total_amount += v

                self.notify(_("%(txs)s new transactions received. Total amount received in the new transactions %(amount)s %(unit)s") \
                                % { 'txs' : tx_amount, 'amount' : self.format_amount(total_amount), 'unit' : self.base_unit()})

                self.network.pending_transactions_for_notifications = []
            else:
              for tx in self.network.pending_transactions_for_notifications:
                  if tx:
                      self.network.pending_transactions_for_notifications.remove(tx)
                      is_relevant, is_mine, v, fee = self.wallet.get_tx_value(tx)
                      if(v > 0):
                          self.notify(_("New transaction received. %(amount)s %(unit)s") % { 'amount' : self.format_amount(v), 'unit' : self.base_unit()})

    def notify(self, message):
        self.tray.showMessage("Electrum", message, QSystemTrayIcon.Information, 20000)



    # custom wrappers for getOpenFileName and getSaveFileName, that remember the path selected by the user
    def getOpenFileName(self, title, filter = ""):
        directory = self.config.get('io_dir', unicode(os.path.expanduser('~')))
        fileName = unicode( QFileDialog.getOpenFileName(self, title, directory, filter) )
        if fileName and directory != os.path.dirname(fileName):
            self.config.set_key('io_dir', os.path.dirname(fileName), True)
        return fileName

    def getSaveFileName(self, title, filename, filter = ""):
        directory = self.config.get('io_dir', unicode(os.path.expanduser('~')))
        path = os.path.join( directory, filename )
        fileName = unicode( QFileDialog.getSaveFileName(self, title, path, filter) )
        if fileName and directory != os.path.dirname(fileName):
            self.config.set_key('io_dir', os.path.dirname(fileName), True)
        return fileName

    def close(self):
        QMainWindow.close(self)
        run_hook('close_main_window')

    def connect_slots(self, sender):
        self.connect(sender, QtCore.SIGNAL('timersignal'), self.timer_actions)
        self.previous_payto_e=''

    def timer_actions(self):
        if self.need_update.is_set():
            self.update_wallet()
            self.need_update.clear()
        run_hook('timer_actions')

    def format_amount(self, x, is_diff=False, whitespaces=False):
        return format_satoshis(x, is_diff, self.num_zeros, self.decimal_point, whitespaces)

    def read_amount(self, x):
        if x in['.', '']: return None
        p = pow(10, self.decimal_point)
        return int( p * Decimal(x) )

    def base_unit(self):
        assert self.decimal_point in [5,8]
        return "BTC" if self.decimal_point == 8 else "mBTC"


    def update_status(self):
        if self.network is None or not self.network.is_running():
            text = _("Offline")
            icon = QIcon(":icons/status_disconnected.png")

        elif self.network.is_connected():
            if not self.wallet.up_to_date:
                text = _("Synchronizing...")
                icon = QIcon(":icons/status_waiting.png")
            elif self.network.server_lag > 1:
                text = _("Server is lagging (%d blocks)"%self.network.server_lag)
                icon = QIcon(":icons/status_lagging.png")
            else:
                c, u = self.wallet.get_account_balance(self.current_account)
                text =  _( "Balance" ) + ": %s "%( self.format_amount(c) ) + self.base_unit()
                if u: text +=  " [%s unconfirmed]"%( self.format_amount(u,True).strip() )

                # append fiat balance and price from exchange rate plugin
                r = {}
                run_hook('get_fiat_status_text', c+u, r)
                quote = r.get(0)
                if quote:
                    text += "%s"%quote

                self.tray.setToolTip(text)
                icon = QIcon(":icons/status_connected.png")
        else:
            text = _("Not connected")
            icon = QIcon(":icons/status_disconnected.png")

        self.balance_label.setText(text)
        self.status_button.setIcon( icon )


    def update_wallet(self):
        self.update_status()
        if self.wallet.up_to_date or not self.network or not self.network.is_connected():
            self.update_history_tab()
            self.update_receive_tab()
            self.update_contacts_tab()
            self.update_completions()


    def create_history_tab(self):
        self.history_list = l = MyTreeWidget(self)
        l.setColumnCount(5)
        for i,width in enumerate(self.column_widths['history']):
            l.setColumnWidth(i, width)
        l.setHeaderLabels( [ '', _('Date'), _('Description') , _('Amount'), _('Balance')] )
        self.connect(l, SIGNAL('itemDoubleClicked(QTreeWidgetItem*, int)'), self.tx_label_clicked)
        self.connect(l, SIGNAL('itemChanged(QTreeWidgetItem*, int)'), self.tx_label_changed)

        l.customContextMenuRequested.connect(self.create_history_menu)
        return l


    def create_history_menu(self, position):
        self.history_list.selectedIndexes()
        item = self.history_list.currentItem()
        be = self.config.get('block_explorer', 'Blockchain.info')
        if be == 'Blockchain.info':
            block_explorer = 'https://blockchain.info/tx/'
        elif be == 'Blockr.io':
            block_explorer = 'https://blockr.io/tx/info/'
        elif be == 'Insight.is':
            block_explorer = 'http://live.insight.is/tx/'
        if not item: return
        tx_hash = str(item.data(0, Qt.UserRole).toString())
        if not tx_hash: return
        menu = QMenu()
        menu.addAction(_("Copy ID to Clipboard"), lambda: self.app.clipboard().setText(tx_hash))
        menu.addAction(_("Details"), lambda: self.show_transaction(self.wallet.transactions.get(tx_hash)))
        menu.addAction(_("Edit description"), lambda: self.tx_label_clicked(item,2))
        menu.addAction(_("View on block explorer"), lambda: webbrowser.open(block_explorer + tx_hash))
        menu.exec_(self.contacts_list.viewport().mapToGlobal(position))


    def show_transaction(self, tx):
        import transaction_dialog
        d = transaction_dialog.TxDialog(tx, self)
        d.exec_()

    def tx_label_clicked(self, item, column):
        if column==2 and item.isSelected():
            self.is_edit=True
            item.setFlags(Qt.ItemIsEditable|Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
            self.history_list.editItem( item, column )
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
            self.is_edit=False

    def tx_label_changed(self, item, column):
        if self.is_edit:
            return
        self.is_edit=True
        tx_hash = str(item.data(0, Qt.UserRole).toString())
        tx = self.wallet.transactions.get(tx_hash)
        text = unicode( item.text(2) )
        self.wallet.set_label(tx_hash, text)
        if text:
            item.setForeground(2, QBrush(QColor('black')))
        else:
            text = self.wallet.get_default_label(tx_hash)
            item.setText(2, text)
            item.setForeground(2, QBrush(QColor('gray')))
        self.is_edit=False


    def edit_label(self, is_recv):
        l = self.receive_list if is_recv else self.contacts_list
        item = l.currentItem()
        item.setFlags(Qt.ItemIsEditable|Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
        l.editItem( item, 1 )
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)



    def address_label_clicked(self, item, column, l, column_addr, column_label):
        if column == column_label and item.isSelected():
            is_editable = item.data(0, 32).toBool()
            if not is_editable:
                return
            addr = unicode( item.text(column_addr) )
            label = unicode( item.text(column_label) )
            item.setFlags(Qt.ItemIsEditable|Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
            l.editItem( item, column )
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)


    def address_label_changed(self, item, column, l, column_addr, column_label):
        if column == column_label:
            addr = unicode( item.text(column_addr) )
            text = unicode( item.text(column_label) )
            is_editable = item.data(0, 32).toBool()
            if not is_editable:
                return

            changed = self.wallet.set_label(addr, text)
            if changed:
                self.update_history_tab()
                self.update_completions()

            self.current_item_changed(item)

        run_hook('item_changed', item, column)


    def current_item_changed(self, a):
        run_hook('current_item_changed', a)



    def update_history_tab(self):

        self.history_list.clear()
        for item in self.wallet.get_tx_history(self.current_account):
            tx_hash, conf, is_mine, value, fee, balance, timestamp = item
            time_str = _("unknown")
            if conf > 0:
                try:
                    time_str = datetime.datetime.fromtimestamp( timestamp).isoformat(' ')[:-3]
                except Exception:
                    time_str = _("error")

            if conf == -1:
                time_str = 'unverified'
                icon = QIcon(":icons/unconfirmed.png")
            elif conf == 0:
                time_str = 'pending'
                icon = QIcon(":icons/unconfirmed.png")
            elif conf < 6:
                icon = QIcon(":icons/clock%d.png"%conf)
            else:
                icon = QIcon(":icons/confirmed.png")

            if value is not None:
                v_str = self.format_amount(value, True, whitespaces=True)
            else:
                v_str = '--'

            balance_str = self.format_amount(balance, whitespaces=True)

            if tx_hash:
                label, is_default_label = self.wallet.get_label(tx_hash)
            else:
                label = _('Pruned transaction outputs')
                is_default_label = False

            item = QTreeWidgetItem( [ '', time_str, label, v_str, balance_str] )
            item.setFont(2, QFont(MONOSPACE_FONT))
            item.setFont(3, QFont(MONOSPACE_FONT))
            item.setFont(4, QFont(MONOSPACE_FONT))
            if value < 0:
                item.setForeground(3, QBrush(QColor("#BC1E1E")))
            if tx_hash:
                item.setData(0, Qt.UserRole, tx_hash)
                item.setToolTip(0, "%d %s\nTxId:%s" % (conf, _('Confirmations'), tx_hash) )
            if is_default_label:
                item.setForeground(2, QBrush(QColor('grey')))

            item.setIcon(0, icon)
            self.history_list.insertTopLevelItem(0,item)


        self.history_list.setCurrentItem(self.history_list.topLevelItem(0))
        run_hook('history_tab_update')


    def create_send_tab(self):
        w = QWidget()

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(3,300)
        grid.setColumnStretch(5,1)


        self.payto_e = QLineEdit()
        self.payto_help = HelpButton(_('Recipient of the funds.') + '\n\n' + _('You may enter a Bitcoin address, a label from your list of contacts (a list of completions will be proposed), or an alias (email-like address that forwards to a Bitcoin address)'))
        grid.addWidget(QLabel(_('Pay to')), 1, 0)
        grid.addWidget(self.payto_e, 1, 1, 1, 3)
        grid.addWidget(self.payto_help, 1, 4)

        completer = QCompleter()
        completer.setCaseSensitivity(False)
        self.payto_e.setCompleter(completer)
        completer.setModel(self.completions)

        self.message_e = QLineEdit()
        self.message_help = HelpButton(_('Description of the transaction (not mandatory).') + '\n\n' + _('The description is not sent to the recipient of the funds. It is stored in your wallet file, and displayed in the \'History\' tab.'))
        grid.addWidget(QLabel(_('Description')), 2, 0)
        grid.addWidget(self.message_e, 2, 1, 1, 3)
        grid.addWidget(self.message_help, 2, 4)

        self.from_label = QLabel(_('From'))
        grid.addWidget(self.from_label, 3, 0)
        self.from_list = QTreeWidget(self)
        self.from_list.setColumnCount(2)
        self.from_list.setColumnWidth(0, 350)
        self.from_list.setColumnWidth(1, 50)
        self.from_list.setHeaderHidden (True)
        self.from_list.setMaximumHeight(80)
        grid.addWidget(self.from_list, 3, 1, 1, 3)
        self.set_pay_from([])

        self.amount_e = AmountEdit(self.base_unit)
        self.amount_help = HelpButton(_('Amount to be sent.') + '\n\n' \
                                      + _('The amount will be displayed in red if you do not have enough funds in your wallet. Note that if you have frozen some of your addresses, the available funds will be lower than your total balance.') \
                                      + '\n\n' + _('Keyboard shortcut: type "!" to send all your coins.'))
        grid.addWidget(QLabel(_('Amount')), 4, 0)
        grid.addWidget(self.amount_e, 4, 1, 1, 2)
        grid.addWidget(self.amount_help, 4, 3)

        self.fee_e = AmountEdit(self.base_unit)
        grid.addWidget(QLabel(_('Fee')), 5, 0)
        grid.addWidget(self.fee_e, 5, 1, 1, 2)
        grid.addWidget(HelpButton(
                _('Bitcoin transactions are in general not free. A transaction fee is paid by the sender of the funds.') + '\n\n'\
                    + _('The amount of fee can be decided freely by the sender. However, transactions with low fees take more time to be processed.') + '\n\n'\
                    + _('A suggested fee is automatically added to this field. You may override it. The suggested fee increases with the size of the transaction.')), 5, 3)

        run_hook('exchange_rate_button', grid)

        self.send_button = EnterButton(_("Send"), self.do_send)
        grid.addWidget(self.send_button, 6, 1)

        b = EnterButton(_("Clear"),self.do_clear)
        grid.addWidget(b, 6, 2)

        self.payto_sig = QLabel('')
        grid.addWidget(self.payto_sig, 7, 0, 1, 4)

        QShortcut(QKeySequence("Up"), w, w.focusPreviousChild)
        QShortcut(QKeySequence("Down"), w, w.focusNextChild)
        w.setLayout(grid)

        w2 = QWidget()
        vbox = QVBoxLayout()
        vbox.addWidget(w)
        vbox.addStretch(1)
        w2.setLayout(vbox)

        def entry_changed( is_fee ):
            self.funds_error = False

            if self.amount_e.is_shortcut:
                self.amount_e.is_shortcut = False
                sendable = self.get_sendable_balance()
                # there is only one output because we are completely spending inputs
                inputs, total, fee = self.wallet.choose_tx_inputs( sendable, 0, 1, self.get_payment_sources())
                fee = self.wallet.estimated_fee(inputs, 1)
                amount = total - fee
                self.amount_e.setText( self.format_amount(amount) )
                self.fee_e.setText( self.format_amount( fee ) )
                return

            amount = self.read_amount(str(self.amount_e.text()))
            fee = self.read_amount(str(self.fee_e.text()))

            if not is_fee: fee = None
            if amount is None:
                return
            # assume that there will be 2 outputs (one for change)
            inputs, total, fee = self.wallet.choose_tx_inputs(amount, fee, 2, self.get_payment_sources())
            if not is_fee:
                self.fee_e.setText( self.format_amount( fee ) )
            if inputs:
                palette = QPalette()
                palette.setColor(self.amount_e.foregroundRole(), QColor('black'))
                text = ""
            else:
                palette = QPalette()
                palette.setColor(self.amount_e.foregroundRole(), QColor('red'))
                self.funds_error = True
                text = _( "Not enough funds" )
                c, u = self.wallet.get_frozen_balance()
                if c+u: text += ' (' + self.format_amount(c+u).strip() + ' ' + self.base_unit() + ' ' +_("are frozen") + ')'

            self.statusBar().showMessage(text)
            self.amount_e.setPalette(palette)
            self.fee_e.setPalette(palette)

        self.amount_e.textChanged.connect(lambda: entry_changed(False) )
        self.fee_e.textChanged.connect(lambda: entry_changed(True) )

        run_hook('create_send_tab', grid)
        return w2


    def set_pay_from(self, l):
        self.pay_from = l
        self.from_list.clear()
        self.from_label.setHidden(len(self.pay_from) == 0)
        self.from_list.setHidden(len(self.pay_from) == 0)
        for addr in self.pay_from:
            c, u = self.wallet.get_addr_balance(addr)
            balance = self.format_amount(c + u)
            self.from_list.addTopLevelItem(QTreeWidgetItem( [addr, balance] ))


    def update_completions(self):
        l = []
        for addr,label in self.wallet.labels.items():
            if addr in self.wallet.addressbook:
                l.append( label + '  <' + addr + '>')

        run_hook('update_completions', l)
        self.completions.setStringList(l)


    def protected(func):
        return lambda s, *args: s.do_protect(func, args)


    def do_send(self):
        label = unicode( self.message_e.text() )

        if self.gui_object.payment_request:
            outputs = self.gui_object.payment_request.outputs
            amount = self.gui_object.payment_request.get_amount()

        else:
            r = unicode( self.payto_e.text() )
            r = r.strip()

            # label or alias, with address in brackets
            m = re.match('(.*?)\s*\<([1-9A-HJ-NP-Za-km-z]{26,})\>', r)
            to_address = m.group(2) if m else r
            if not is_valid(to_address):
                QMessageBox.warning(self, _('Error'), _('Invalid Bitcoin Address') + ':\n' + to_address, _('OK'))
                return

            try:
                amount = self.read_amount(unicode( self.amount_e.text()))
            except Exception:
                QMessageBox.warning(self, _('Error'), _('Invalid Amount'), _('OK'))
                return

            outputs = [(to_address, amount)]

        try:
            fee = self.read_amount(unicode( self.fee_e.text()))
        except Exception:
            QMessageBox.warning(self, _('Error'), _('Invalid Fee'), _('OK'))
            return

        confirm_amount = self.config.get('confirm_amount', 100000000)
        if amount >= confirm_amount:
            if not self.question(_("send %(amount)s to %(address)s?")%{ 'amount' : self.format_amount(amount) + ' '+ self.base_unit(), 'address' : to_address}):
                return
            
        confirm_fee = self.config.get('confirm_fee', 100000)
        if fee >= confirm_fee:
            if not self.question(_("The fee for this transaction seems unusually high.\nAre you really sure you want to pay %(fee)s in fees?")%{ 'fee' : self.format_amount(fee) + ' '+ self.base_unit()}):
                return

        self.send_tx(outputs, fee, label)



    @protected
    def send_tx(self, outputs, fee, label, password):

        # first, create an unsigned tx 
        domain = self.get_payment_sources()
        try:
            tx = self.wallet.make_unsigned_transaction(outputs, fee, None, domain)
            tx.error = None
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.show_message(str(e))
            return

        # call hook to see if plugin needs gui interaction
        run_hook('send_tx', tx)

        # sign the tx
        def sign_thread():
            time.sleep(0.1)
            keypairs = {}
            self.wallet.add_keypairs_from_wallet(tx, keypairs, password)
            self.wallet.sign_transaction(tx, keypairs, password)
            return tx, fee, label

        def sign_done(tx, fee, label):
            if tx.error:
                self.show_message(tx.error)
                return
            if tx.requires_fee(self.wallet.verifier) and fee < MIN_RELAY_TX_FEE:
                QMessageBox.warning(self, _('Error'), _("This transaction requires a higher fee, or it will not be propagated by the network."), _('OK'))
                return
            if label:
                self.wallet.set_label(tx.hash(), label)

            if not self.gui_object.payment_request:
                if not tx.is_complete() or self.config.get('show_before_broadcast'):
                    self.show_transaction(tx)
                    return

            self.broadcast_transaction(tx)

        self.waiting_dialog = WaitingDialog(self, 'Signing..', sign_thread, sign_done)
        self.waiting_dialog.start()



    def broadcast_transaction(self, tx):

        def broadcast_thread():
            if self.gui_object.payment_request:
                refund_address = self.wallet.addresses()[0]
                status, msg = self.gui_object.payment_request.send_ack(str(tx), refund_address)
                self.gui_object.payment_request = None
            else:
                status, msg =  self.wallet.sendtx(tx)
            return status, msg

        def broadcast_done(status, msg):
            if status:
                QMessageBox.information(self, '', _('Payment sent.') + '\n' + msg, _('OK'))
                self.do_clear()
            else:
                QMessageBox.warning(self, _('Error'), msg, _('OK'))

        self.waiting_dialog = WaitingDialog(self, 'Broadcasting..', broadcast_thread, broadcast_done)
        self.waiting_dialog.start()



    def prepare_for_payment_request(self):
        style = "QWidget { background-color:none;border:none;}"
        self.tabs.setCurrentIndex(1)
        for e in [self.payto_e, self.amount_e, self.message_e]:
            e.setReadOnly(True)
            e.setStyleSheet(style)
        for h in [self.payto_help, self.amount_help, self.message_help]:
            h.hide()
        self.payto_e.setText(_("please wait..."))
        return True

    def payment_request_ok(self):
        self.payto_e.setText(self.gui_object.payment_request.domain)
        self.amount_e.setText(self.format_amount(self.gui_object.payment_request.get_amount()))
        self.message_e.setText(self.gui_object.payment_request.memo)

    def payment_request_error(self):
        self.do_clear()
        self.show_message(self.gui_object.payment_request.error)


    def set_send(self, address, amount, label, message):

        if label and self.wallet.labels.get(address) != label:
            if self.question('Give label "%s" to address %s ?'%(label,address)):
                if address not in self.wallet.addressbook and not self.wallet.is_mine(address):
                    self.wallet.addressbook.append(address)
                self.wallet.set_label(address, label)

        self.tabs.setCurrentIndex(1)
        label = self.wallet.labels.get(address)
        m_addr = label + '  <'+ address +'>' if label else address
        self.payto_e.setText(m_addr)

        self.message_e.setText(message)
        if amount:
            self.amount_e.setText(amount)


    def do_clear(self):
        self.payto_sig.setVisible(False)
        for e in [self.payto_e, self.message_e, self.amount_e, self.fee_e]:
            e.setText('')
            self.set_frozen(e,False)
            e.setStyleSheet("")
        for h in [self.payto_help, self.amount_help, self.message_help]:
            h.show()

        self.set_pay_from([])
        self.update_status()

    def set_frozen(self,entry,frozen):
        if frozen:
            entry.setReadOnly(True)
            entry.setFrame(False)
            palette = QPalette()
            palette.setColor(entry.backgroundRole(), QColor('lightgray'))
            entry.setPalette(palette)
        else:
            entry.setReadOnly(False)
            entry.setFrame(True)
            palette = QPalette()
            palette.setColor(entry.backgroundRole(), QColor('white'))
            entry.setPalette(palette)


    def set_addrs_frozen(self,addrs,freeze):
        for addr in addrs:
            if not addr: continue
            if addr in self.wallet.frozen_addresses and not freeze:
                self.wallet.unfreeze(addr)
            elif addr not in self.wallet.frozen_addresses and freeze:
                self.wallet.freeze(addr)
        self.update_receive_tab()



    def create_list_tab(self, headers):
        "generic tab creation method"
        l = MyTreeWidget(self)
        l.setColumnCount( len(headers) )
        l.setHeaderLabels( headers )

        w = QWidget()
        vbox = QVBoxLayout()
        w.setLayout(vbox)

        vbox.setMargin(0)
        vbox.setSpacing(0)
        vbox.addWidget(l)
        buttons = QWidget()
        vbox.addWidget(buttons)

        hbox = QHBoxLayout()
        hbox.setMargin(0)
        hbox.setSpacing(0)
        buttons.setLayout(hbox)

        return l,w,hbox


    def create_receive_tab(self):
        l,w,hbox = self.create_list_tab([ _('Address'), _('Label'), _('Balance'), _('Tx')])
        l.setContextMenuPolicy(Qt.CustomContextMenu)
        l.customContextMenuRequested.connect(self.create_receive_menu)
        l.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.connect(l, SIGNAL('itemDoubleClicked(QTreeWidgetItem*, int)'), lambda a, b: self.address_label_clicked(a,b,l,0,1))
        self.connect(l, SIGNAL('itemChanged(QTreeWidgetItem*, int)'), lambda a,b: self.address_label_changed(a,b,l,0,1))
        self.connect(l, SIGNAL('currentItemChanged(QTreeWidgetItem*, QTreeWidgetItem*)'), lambda a,b: self.current_item_changed(a))
        self.receive_list = l
        self.receive_buttons_hbox = hbox
        hbox.addStretch(1)
        return w




    def save_column_widths(self):
        self.column_widths["receive"] = []
        for i in range(self.receive_list.columnCount() -1):
            self.column_widths["receive"].append(self.receive_list.columnWidth(i))

        self.column_widths["history"] = []
        for i in range(self.history_list.columnCount() - 1):
            self.column_widths["history"].append(self.history_list.columnWidth(i))

        self.column_widths["contacts"] = []
        for i in range(self.contacts_list.columnCount() - 1):
            self.column_widths["contacts"].append(self.contacts_list.columnWidth(i))

        self.config.set_key("column_widths_2", self.column_widths, True)


    def create_contacts_tab(self):
        l,w,hbox = self.create_list_tab([_('Address'), _('Label'), _('Tx')])
        l.setContextMenuPolicy(Qt.CustomContextMenu)
        l.customContextMenuRequested.connect(self.create_contact_menu)
        for i,width in enumerate(self.column_widths['contacts']):
            l.setColumnWidth(i, width)

        self.connect(l, SIGNAL('itemDoubleClicked(QTreeWidgetItem*, int)'), lambda a, b: self.address_label_clicked(a,b,l,0,1))
        self.connect(l, SIGNAL('itemChanged(QTreeWidgetItem*, int)'), lambda a,b: self.address_label_changed(a,b,l,0,1))
        self.contacts_list = l
        self.contacts_buttons_hbox = hbox
        hbox.addStretch(1)
        return w


    def delete_imported_key(self, addr):
        if self.question(_("Do you want to remove")+" %s "%addr +_("from your wallet?")):
            self.wallet.delete_imported_key(addr)
            self.update_receive_tab()
            self.update_history_tab()

    def edit_account_label(self, k):
        text, ok = QInputDialog.getText(self, _('Rename account'), _('Name') + ':', text = self.wallet.labels.get(k,''))
        if ok:
            label = unicode(text)
            self.wallet.set_label(k,label)
            self.update_receive_tab()

    def account_set_expanded(self, item, k, b):
        item.setExpanded(b)
        self.accounts_expanded[k] = b

    def create_account_menu(self, position, k, item):
        menu = QMenu()
        if item.isExpanded():
            menu.addAction(_("Minimize"), lambda: self.account_set_expanded(item, k, False))
        else:
            menu.addAction(_("Maximize"), lambda: self.account_set_expanded(item, k, True))
        menu.addAction(_("Rename"), lambda: self.edit_account_label(k))
        if self.wallet.seed_version > 4:
            menu.addAction(_("View details"), lambda: self.show_account_details(k))
        if self.wallet.account_is_pending(k):
            menu.addAction(_("Delete"), lambda: self.delete_pending_account(k))
        menu.exec_(self.receive_list.viewport().mapToGlobal(position))

    def delete_pending_account(self, k):
        self.wallet.delete_pending_account(k)
        self.update_receive_tab()

    def create_receive_menu(self, position):
        # fixme: this function apparently has a side effect.
        # if it is not called the menu pops up several times
        #self.receive_list.selectedIndexes()

        selected = self.receive_list.selectedItems()
        multi_select = len(selected) > 1
        addrs = [unicode(item.text(0)) for item in selected]
        if not multi_select:
            item = self.receive_list.itemAt(position)
            if not item: return

            addr = addrs[0]
            if not is_valid(addr):
                k = str(item.data(0,32).toString())
                if k:
                    self.create_account_menu(position, k, item)
                else:
                    item.setExpanded(not item.isExpanded())
                return

        menu = QMenu()
        if not multi_select:
            menu.addAction(_("Copy to clipboard"), lambda: self.app.clipboard().setText(addr))
            menu.addAction(_("QR code"), lambda: self.show_qrcode("bitcoin:" + addr, _("Address")) )
            menu.addAction(_("Edit label"), lambda: self.edit_label(True))
            menu.addAction(_("Public keys"), lambda: self.show_public_keys(addr))
            if not self.wallet.is_watching_only():
                menu.addAction(_("Private key"), lambda: self.show_private_key(addr))
                menu.addAction(_("Sign/verify message"), lambda: self.sign_verify_message(addr))
                #menu.addAction(_("Encrypt/decrypt message"), lambda: self.encrypt_message(addr))
            if self.wallet.is_imported(addr):
                menu.addAction(_("Remove from wallet"), lambda: self.delete_imported_key(addr))

        if any(addr not in self.wallet.frozen_addresses for addr in addrs):
            menu.addAction(_("Freeze"), lambda: self.set_addrs_frozen(addrs, True))
        if any(addr in self.wallet.frozen_addresses for addr in addrs):
            menu.addAction(_("Unfreeze"), lambda: self.set_addrs_frozen(addrs, False))

        if any(addr not in self.wallet.frozen_addresses for addr in addrs):
            menu.addAction(_("Send From"), lambda: self.send_from_addresses(addrs))

        run_hook('receive_menu', menu, addrs)
        menu.exec_(self.receive_list.viewport().mapToGlobal(position))


    def get_sendable_balance(self):
        return sum(sum(self.wallet.get_addr_balance(a)) for a in self.get_payment_sources())


    def get_payment_sources(self):
        if self.pay_from:
            return self.pay_from
        else:
            return self.wallet.get_account_addresses(self.current_account)


    def send_from_addresses(self, addrs):
        self.set_pay_from( addrs )
        self.tabs.setCurrentIndex(1)


    def payto(self, addr):
        if not addr: return
        label = self.wallet.labels.get(addr)
        m_addr = label + '  <' + addr + '>' if label else addr
        self.tabs.setCurrentIndex(1)
        self.payto_e.setText(m_addr)
        self.amount_e.setFocus()


    def delete_contact(self, x):
        if self.question(_("Do you want to remove")+" %s "%x +_("from your list of contacts?")):
            self.wallet.delete_contact(x)
            self.wallet.set_label(x, None)
            self.update_history_tab()
            self.update_contacts_tab()
            self.update_completions()


    def create_contact_menu(self, position):
        item = self.contacts_list.itemAt(position)
        menu = QMenu()
        if not item:
            menu.addAction(_("New contact"), lambda: self.new_contact_dialog())
        else:
            addr = unicode(item.text(0))
            label = unicode(item.text(1))
            is_editable = item.data(0,32).toBool()
            payto_addr = item.data(0,33).toString()
            menu.addAction(_("Copy to Clipboard"), lambda: self.app.clipboard().setText(addr))
            menu.addAction(_("Pay to"), lambda: self.payto(payto_addr))
            menu.addAction(_("QR code"), lambda: self.show_qrcode("bitcoin:" + addr, _("Address")))
            if is_editable:
                menu.addAction(_("Edit label"), lambda: self.edit_label(False))
                menu.addAction(_("Delete"), lambda: self.delete_contact(addr))

        run_hook('create_contact_menu', menu, item)
        menu.exec_(self.contacts_list.viewport().mapToGlobal(position))


    def update_receive_item(self, item):
        item.setFont(0, QFont(MONOSPACE_FONT))
        address = str(item.data(0,0).toString())
        label = self.wallet.labels.get(address,'')
        item.setData(1,0,label)
        item.setData(0,32, True) # is editable

        run_hook('update_receive_item', address, item)

        if not self.wallet.is_mine(address): return

        c, u = self.wallet.get_addr_balance(address)
        balance = self.format_amount(c + u)
        item.setData(2,0,balance)

        if address in self.wallet.frozen_addresses:
            item.setBackgroundColor(0, QColor('lightblue'))


    def update_receive_tab(self):
        l = self.receive_list
        # extend the syntax for consistency
        l.addChild = l.addTopLevelItem
        l.insertChild = l.insertTopLevelItem

        l.clear()
        for i,width in enumerate(self.column_widths['receive']):
            l.setColumnWidth(i, width)

        accounts = self.wallet.get_accounts()
        if self.current_account is None:
            account_items = sorted(accounts.items())
        else:
            account_items = [(self.current_account, accounts.get(self.current_account))]


        for k, account in account_items:

            if len(accounts) > 1:
                name = self.wallet.get_account_name(k)
                c,u = self.wallet.get_account_balance(k)
                account_item = QTreeWidgetItem( [ name, '', self.format_amount(c+u), ''] )
                l.addTopLevelItem(account_item)
                account_item.setExpanded(self.accounts_expanded.get(k, True))
                account_item.setData(0, 32, k)
            else:
                account_item = l

            sequences = [0,1] if account.has_change() else [0]
            for is_change in sequences:
                if len(sequences) > 1:
                    name = _("Receiving") if not is_change else _("Change")
                    seq_item = QTreeWidgetItem( [ name, '', '', '', ''] )
                    account_item.addChild(seq_item)
                    if not is_change: 
                        seq_item.setExpanded(True)
                else:
                    seq_item = account_item
                    
                used_item = QTreeWidgetItem( [ _("Used"), '', '', '', ''] )
                used_flag = False

                is_red = False
                gap = 0

                for address in account.get_addresses(is_change):

                    num, is_used = self.wallet.is_used(address)
                    if num == 0:
                        gap += 1
                        if gap > self.wallet.gap_limit:
                            is_red = True
                    else:
                        gap = 0

                    item = QTreeWidgetItem( [ address, '', '', "%d"%num] )
                    self.update_receive_item(item)
                    if is_red:
                        item.setBackgroundColor(1, QColor('red'))

                    if is_used:
                        if not used_flag:
                            seq_item.insertChild(0,used_item)
                            used_flag = True
                        used_item.addChild(item)
                    else:
                        seq_item.addChild(item)

        # we use column 1 because column 0 may be hidden
        l.setCurrentItem(l.topLevelItem(0),1)


    def update_contacts_tab(self):
        l = self.contacts_list
        l.clear()

        for address in self.wallet.addressbook:
            label = self.wallet.labels.get(address,'')
            n = self.wallet.get_num_tx(address)
            item = QTreeWidgetItem( [ address, label, "%d"%n] )
            item.setFont(0, QFont(MONOSPACE_FONT))
            # 32 = label can be edited (bool)
            item.setData(0,32, True)
            # 33 = payto string
            item.setData(0,33, address)
            l.addTopLevelItem(item)

        run_hook('update_contacts_tab', l)
        l.setCurrentItem(l.topLevelItem(0))



    def create_console_tab(self):
        from console import Console
        self.console = console = Console()
        return console


    def update_console(self):
        console = self.console
        console.history = self.config.get("console-history",[])
        console.history_index = len(console.history)

        console.updateNamespace({'wallet' : self.wallet, 'network' : self.network, 'gui':self})
        console.updateNamespace({'util' : util, 'bitcoin':bitcoin})

        c = commands.Commands(self.wallet, self.network, lambda: self.console.set_json(True))
        methods = {}
        def mkfunc(f, method):
            return lambda *args: apply( f, (method, args, self.password_dialog ))
        for m in dir(c):
            if m[0]=='_' or m in ['network','wallet']: continue
            methods[m] = mkfunc(c._run, m)

        console.updateNamespace(methods)


    def change_account(self,s):
        if s == _("All accounts"):
            self.current_account = None
        else:
            accounts = self.wallet.get_account_names()
            for k, v in accounts.items():
                if v == s:
                    self.current_account = k
        self.update_history_tab()
        self.update_status()
        self.update_receive_tab()

    def create_status_bar(self):

        sb = QStatusBar()
        sb.setFixedHeight(35)
        qtVersion = qVersion()

        self.balance_label = QLabel("")
        sb.addWidget(self.balance_label)

        from version_getter import UpdateLabel
        self.updatelabel = UpdateLabel(self.config, sb)

        self.account_selector = QComboBox()
        self.account_selector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.connect(self.account_selector,SIGNAL("activated(QString)"),self.change_account)
        sb.addPermanentWidget(self.account_selector)

        if (int(qtVersion[0]) >= 4 and int(qtVersion[2]) >= 7):
            sb.addPermanentWidget( StatusBarButton( QIcon(":icons/switchgui.png"), _("Switch to Lite Mode"), self.go_lite ) )

        self.lock_icon = QIcon()
        self.password_button = StatusBarButton( self.lock_icon, _("Password"), self.change_password_dialog )
        sb.addPermanentWidget( self.password_button )

        sb.addPermanentWidget( StatusBarButton( QIcon(":icons/preferences.png"), _("Preferences"), self.settings_dialog ) )
        self.seed_button = StatusBarButton( QIcon(":icons/seed.png"), _("Seed"), self.show_seed_dialog )
        sb.addPermanentWidget( self.seed_button )
        self.status_button = StatusBarButton( QIcon(":icons/status_disconnected.png"), _("Network"), self.run_network_dialog )
        sb.addPermanentWidget( self.status_button )

        run_hook('create_status_bar', (sb,))

        self.setStatusBar(sb)


    def update_lock_icon(self):
        icon = QIcon(":icons/lock.png") if self.wallet.use_encryption else QIcon(":icons/unlock.png")
        self.password_button.setIcon( icon )


    def update_buttons_on_seed(self):
        if self.wallet.has_seed():
           self.seed_button.show()
        else:
           self.seed_button.hide()

        if not self.wallet.is_watching_only():
           self.password_button.show()
           self.send_button.setText(_("Send"))
        else:
           self.password_button.hide()
           self.send_button.setText(_("Create unsigned transaction"))


    def change_password_dialog(self):
        from password_dialog import PasswordDialog
        d = PasswordDialog(self.wallet, self)
        d.run()
        self.update_lock_icon()


    def new_contact_dialog(self):

        d = QDialog(self)
        d.setWindowTitle(_("New Contact"))
        vbox = QVBoxLayout(d)
        vbox.addWidget(QLabel(_('New Contact')+':'))

        grid = QGridLayout()
        line1 = QLineEdit()
        line2 = QLineEdit()
        grid.addWidget(QLabel(_("Address")), 1, 0)
        grid.addWidget(line1, 1, 1)
        grid.addWidget(QLabel(_("Name")), 2, 0)
        grid.addWidget(line2, 2, 1)

        vbox.addLayout(grid)
        vbox.addLayout(ok_cancel_buttons(d))

        if not d.exec_():
            return

        address = str(line1.text())
        label = unicode(line2.text())

        if not is_valid(address):
            QMessageBox.warning(self, _('Error'), _('Invalid Address'), _('OK'))
            return

        self.wallet.add_contact(address)
        if label:
            self.wallet.set_label(address, label)

        self.update_contacts_tab()
        self.update_history_tab()
        self.update_completions()
        self.tabs.setCurrentIndex(3)


    @protected
    def new_account_dialog(self, password):

        dialog = QDialog(self)
        dialog.setModal(1)
        dialog.setWindowTitle(_("New Account"))

        vbox = QVBoxLayout()
        vbox.addWidget(QLabel(_('Account name')+':'))
        e = QLineEdit()
        vbox.addWidget(e)
        msg = _("Note: Newly created accounts are 'pending' until they receive bitcoins.") + " " \
            + _("You will need to wait for 2 confirmations until the correct balance is displayed and more addresses are created for that account.")
        l = QLabel(msg)
        l.setWordWrap(True)
        vbox.addWidget(l)

        vbox.addLayout(ok_cancel_buttons(dialog))
        dialog.setLayout(vbox)
        r = dialog.exec_()
        if not r: return

        name = str(e.text())
        if not name: return

        self.wallet.create_pending_account(name, password)
        self.update_receive_tab()
        self.tabs.setCurrentIndex(2)




    def show_master_public_keys(self):

        dialog = QDialog(self)
        dialog.setModal(1)
        dialog.setWindowTitle(_("Master Public Keys"))

        main_layout = QGridLayout()
        mpk_dict = self.wallet.get_master_public_keys()
        i = 0
        for key, value in mpk_dict.items():
            main_layout.addWidget(QLabel(key), i, 0)
            mpk_text = QTextEdit()
            mpk_text.setReadOnly(True)
            mpk_text.setMaximumHeight(170)
            mpk_text.setText(value)
            main_layout.addWidget(mpk_text, i + 1, 0)
            i += 2

        vbox = QVBoxLayout()
        vbox.addLayout(main_layout)
        vbox.addLayout(close_button(dialog))

        dialog.setLayout(vbox)
        dialog.exec_()


    @protected
    def show_seed_dialog(self, password):
        if not self.wallet.has_seed():
            QMessageBox.information(self, _('Message'), _('This wallet has no seed'), _('OK'))
            return

        try:
            mnemonic = self.wallet.get_mnemonic(password)
        except Exception:
            QMessageBox.warning(self, _('Error'), _('Incorrect Password'), _('OK'))
            return
        from seed_dialog import SeedDialog
        d = SeedDialog(self, mnemonic, self.wallet.imported_keys)
        d.exec_()



    def show_qrcode(self, data, title = _("QR code")):
        if not data: return
        d = QDialog(self)
        d.setModal(1)
        d.setWindowTitle(title)
        d.setMinimumSize(270, 300)
        vbox = QVBoxLayout()
        qrw = QRCodeWidget(data)
        vbox.addWidget(qrw, 1)
        vbox.addWidget(QLabel(data), 0, Qt.AlignHCenter)
        hbox = QHBoxLayout()
        hbox.addStretch(1)

        filename = os.path.join(self.config.path, "qrcode.bmp")

        def print_qr():
            bmp.save_qrcode(qrw.qr, filename)
            QMessageBox.information(None, _('Message'), _("QR code saved to file") + " " + filename, _('OK'))

        def copy_to_clipboard():
            bmp.save_qrcode(qrw.qr, filename)
            self.app.clipboard().setImage(QImage(filename))
            QMessageBox.information(None, _('Message'), _("QR code saved to clipboard"), _('OK'))

        b = QPushButton(_("Copy"))
        hbox.addWidget(b)
        b.clicked.connect(copy_to_clipboard)

        b = QPushButton(_("Save"))
        hbox.addWidget(b)
        b.clicked.connect(print_qr)

        b = QPushButton(_("Close"))
        hbox.addWidget(b)
        b.clicked.connect(d.accept)
        b.setDefault(True)

        vbox.addLayout(hbox)
        d.setLayout(vbox)
        d.exec_()


    def do_protect(self, func, args):
        if self.wallet.use_encryption:
            password = self.password_dialog()
            if not password:
                return
        else:
            password = None

        if args != (False,):
            args = (self,) + args + (password,)
        else:
            args = (self,password)
        apply( func, args)


    def show_public_keys(self, address):
        if not address: return
        try:
            pubkey_list = self.wallet.get_public_keys(address)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.show_message(str(e))
            return

        d = QDialog(self)
        d.setMinimumSize(600, 200)
        d.setModal(1)
        vbox = QVBoxLayout()
        vbox.addWidget( QLabel(_("Address") + ': ' + address))
        vbox.addWidget( QLabel(_("Public key") + ':'))
        keys = QTextEdit()
        keys.setReadOnly(True)
        keys.setText('\n'.join(pubkey_list))
        vbox.addWidget(keys)
        #vbox.addWidget( QRCodeWidget('\n'.join(pk_list)) )
        vbox.addLayout(close_button(d))
        d.setLayout(vbox)
        d.exec_()

    @protected
    def show_private_key(self, address, password):
        if not address: return
        try:
            pk_list = self.wallet.get_private_key(address, password)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
            self.show_message(str(e))
            return

        d = QDialog(self)
        d.setMinimumSize(600, 200)
        d.setModal(1)
        vbox = QVBoxLayout()
        vbox.addWidget( QLabel(_("Address") + ': ' + address))
        vbox.addWidget( QLabel(_("Private key") + ':'))
        keys = QTextEdit()
        keys.setReadOnly(True)
        keys.setText('\n'.join(pk_list))
        vbox.addWidget(keys)
        vbox.addWidget( QRCodeWidget('\n'.join(pk_list)) )
        vbox.addLayout(close_button(d))
        d.setLayout(vbox)
        d.exec_()


    @protected
    def do_sign(self, address, message, signature, password):
        message = unicode(message.toPlainText())
        message = message.encode('utf-8')
        try:
            sig = self.wallet.sign_message(str(address.text()), message, password)
            signature.setText(sig)
        except Exception as e:
            self.show_message(str(e))

    def do_verify(self, address, message, signature):
        message = unicode(message.toPlainText())
        message = message.encode('utf-8')
        if bitcoin.verify_message(address.text(), str(signature.toPlainText()), message):
            self.show_message(_("Signature verified"))
        else:
            self.show_message(_("Error: wrong signature"))


    def sign_verify_message(self, address=''):
        d = QDialog(self)
        d.setModal(1)
        d.setWindowTitle(_('Sign/verify Message'))
        d.setMinimumSize(410, 290)

        layout = QGridLayout(d)

        message_e = QTextEdit()
        layout.addWidget(QLabel(_('Message')), 1, 0)
        layout.addWidget(message_e, 1, 1)
        layout.setRowStretch(2,3)

        address_e = QLineEdit()
        address_e.setText(address)
        layout.addWidget(QLabel(_('Address')), 2, 0)
        layout.addWidget(address_e, 2, 1)

        signature_e = QTextEdit()
        layout.addWidget(QLabel(_('Signature')), 3, 0)
        layout.addWidget(signature_e, 3, 1)
        layout.setRowStretch(3,1)

        hbox = QHBoxLayout()

        b = QPushButton(_("Sign"))
        b.clicked.connect(lambda: self.do_sign(address_e, message_e, signature_e))
        hbox.addWidget(b)

        b = QPushButton(_("Verify"))
        b.clicked.connect(lambda: self.do_verify(address_e, message_e, signature_e))
        hbox.addWidget(b)

        b = QPushButton(_("Close"))
        b.clicked.connect(d.accept)
        hbox.addWidget(b)
        layout.addLayout(hbox, 4, 1)
        d.exec_()


    @protected
    def do_decrypt(self, message_e, pubkey_e, encrypted_e, password):
        try:
            decrypted = self.wallet.decrypt_message(str(pubkey_e.text()), str(encrypted_e.toPlainText()), password)
            message_e.setText(decrypted)
        except Exception as e:
            self.show_message(str(e))


    def do_encrypt(self, message_e, pubkey_e, encrypted_e):
        message = unicode(message_e.toPlainText())
        message = message.encode('utf-8')
        try:
            encrypted = bitcoin.encrypt_message(message, str(pubkey_e.text()))
            encrypted_e.setText(encrypted)
        except Exception as e:
            self.show_message(str(e))



    def encrypt_message(self, address = ''):
        d = QDialog(self)
        d.setModal(1)
        d.setWindowTitle(_('Encrypt/decrypt Message'))
        d.setMinimumSize(610, 490)

        layout = QGridLayout(d)

        message_e = QTextEdit()
        layout.addWidget(QLabel(_('Message')), 1, 0)
        layout.addWidget(message_e, 1, 1)
        layout.setRowStretch(2,3)

        pubkey_e = QLineEdit()
        if address:
            pubkey = self.wallet.getpubkeys(address)[0]
            pubkey_e.setText(pubkey)
        layout.addWidget(QLabel(_('Public key')), 2, 0)
        layout.addWidget(pubkey_e, 2, 1)

        encrypted_e = QTextEdit()
        layout.addWidget(QLabel(_('Encrypted')), 3, 0)
        layout.addWidget(encrypted_e, 3, 1)
        layout.setRowStretch(3,1)

        hbox = QHBoxLayout()
        b = QPushButton(_("Encrypt"))
        b.clicked.connect(lambda: self.do_encrypt(message_e, pubkey_e, encrypted_e))
        hbox.addWidget(b)

        b = QPushButton(_("Decrypt"))
        b.clicked.connect(lambda: self.do_decrypt(message_e, pubkey_e, encrypted_e))
        hbox.addWidget(b)

        b = QPushButton(_("Close"))
        b.clicked.connect(d.accept)
        hbox.addWidget(b)

        layout.addLayout(hbox, 4, 1)
        d.exec_()


    def question(self, msg):
        return QMessageBox.question(self, _('Message'), msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes

    def show_message(self, msg):
        QMessageBox.information(self, _('Message'), msg, _('OK'))

    def password_dialog(self ):
        d = QDialog(self)
        d.setModal(1)
        d.setWindowTitle(_("Enter Password"))

        pw = QLineEdit()
        pw.setEchoMode(2)

        vbox = QVBoxLayout()
        msg = _('Please enter your password')
        vbox.addWidget(QLabel(msg))

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.addWidget(QLabel(_('Password')), 1, 0)
        grid.addWidget(pw, 1, 1)
        vbox.addLayout(grid)

        vbox.addLayout(ok_cancel_buttons(d))
        d.setLayout(vbox)

        run_hook('password_dialog', pw, grid, 1)
        if not d.exec_(): return
        return unicode(pw.text())








    def tx_from_text(self, txt):
        "json or raw hexadecimal"
        try:
            txt.decode('hex')
            tx = Transaction(txt)
            return tx
        except Exception:
            pass

        try:
            tx_dict = json.loads(str(txt))
            assert "hex" in tx_dict.keys()
            tx = Transaction(tx_dict["hex"])
            if tx_dict.has_key("input_info"):
                input_info = json.loads(tx_dict['input_info'])
                tx.add_input_info(input_info)
            return tx
        except Exception:
            traceback.print_exc(file=sys.stdout)
            pass

        QMessageBox.critical(None, _("Unable to parse transaction"), _("Electrum was unable to parse your transaction"))



    def read_tx_from_file(self):
        fileName = self.getOpenFileName(_("Select your transaction file"), "*.txn")
        if not fileName:
            return
        try:
            with open(fileName, "r") as f:
                file_content = f.read()
        except (ValueError, IOError, os.error), reason:
            QMessageBox.critical(None, _("Unable to read file or no transaction found"), _("Electrum was unable to open your transaction file") + "\n" + str(reason))

        return self.tx_from_text(file_content)


    @protected
    def sign_raw_transaction(self, tx, input_info, password):
        self.wallet.signrawtransaction(tx, input_info, [], password)

    def do_process_from_text(self):
        text = text_dialog(self, _('Input raw transaction'), _("Transaction:"), _("Load transaction"))
        if not text:
            return
        tx = self.tx_from_text(text)
        if tx:
            self.show_transaction(tx)

    def do_process_from_file(self):
        tx = self.read_tx_from_file()
        if tx:
            self.show_transaction(tx)

    def do_process_from_txid(self):
        from electrum import transaction
        txid, ok = QInputDialog.getText(self, _('Lookup transaction'), _('Transaction ID') + ':')
        if ok and txid:
            r = self.network.synchronous_get([ ('blockchain.transaction.get',[str(txid)]) ])[0]
            if r:
                tx = transaction.Transaction(r)
                if tx:
                    self.show_transaction(tx)
                else:
                    self.show_message("unknown transaction")

    def do_process_from_csvReader(self, csvReader):
        outputs = []
        errors = []
        errtext = ""
        try:
            for position, row in enumerate(csvReader):
                address = row[0]
                if not is_valid(address):
                    errors.append((position, address))
                    continue
                amount = Decimal(row[1])
                amount = int(100000000*amount)
                outputs.append((address, amount))
        except (ValueError, IOError, os.error), reason:
            QMessageBox.critical(None, _("Unable to read file or no transaction found"), _("Electrum was unable to open your transaction file") + "\n" + str(reason))
            return
        if errors != []:
            for x in errors:
                errtext += "CSV Row " + str(x[0]+1) + ": " + x[1] + "\n"
            QMessageBox.critical(None, _("Invalid Addresses"), _("ABORTING! Invalid Addresses found:") + "\n\n" + errtext)
            return

        try:
            tx = self.wallet.make_unsigned_transaction(outputs, None, None)
        except Exception as e:
            self.show_message(str(e))
            return

        self.show_transaction(tx)

    def do_process_from_csv_file(self):
        fileName = self.getOpenFileName(_("Select your transaction CSV"), "*.csv")
        if not fileName:
            return
        try:
            with open(fileName, "r") as f:
                csvReader = csv.reader(f)
                self.do_process_from_csvReader(csvReader)
        except (ValueError, IOError, os.error), reason:
            QMessageBox.critical(None, _("Unable to read file or no transaction found"), _("Electrum was unable to open your transaction file") + "\n" + str(reason))
            return

    def do_process_from_csv_text(self):
        text = text_dialog(self, _('Input CSV'), _("Please enter a list of outputs.") + '\n' \
                               + _("Format: address, amount. One output per line"), _("Load CSV"))
        if not text:
            return
        f = StringIO.StringIO(text)
        csvReader = csv.reader(f)
        self.do_process_from_csvReader(csvReader)



    @protected
    def export_privkeys_dialog(self, password):
        if self.wallet.is_watching_only():
            self.show_message(_("This is a watching-only wallet"))
            return

        d = QDialog(self)
        d.setWindowTitle(_('Private keys'))
        d.setMinimumSize(850, 300)
        vbox = QVBoxLayout(d)

        msg = "%s\n%s\n%s" % (_("WARNING: ALL your private keys are secret."), 
                              _("Exposing a single private key can compromise your entire wallet!"), 
                              _("In particular, DO NOT use 'redeem private key' services proposed by third parties."))
        vbox.addWidget(QLabel(msg))

        e = QTextEdit()
        e.setReadOnly(True)
        vbox.addWidget(e)

        defaultname = 'electrum-private-keys.csv'
        select_msg = _('Select file to export your private keys to')
        hbox, filename_e, csv_button = filename_field(self, self.config, defaultname, select_msg)
        vbox.addLayout(hbox)

        h, b = ok_cancel_buttons2(d, _('Export'))
        b.setEnabled(False)
        vbox.addLayout(h)

        private_keys = {}
        addresses = self.wallet.addresses(True)
        done = False
        def privkeys_thread():
            for addr in addresses:
                time.sleep(0.1)
                if done: 
                    break
                private_keys[addr] = "\n".join(self.wallet.get_private_key(addr, password))
                d.emit(SIGNAL('computing_privkeys'))
            d.emit(SIGNAL('show_privkeys'))

        def show_privkeys():
            s = "\n".join( map( lambda x: x[0] + "\t"+ x[1], private_keys.items()))
            e.setText(s)
            b.setEnabled(True)

        d.connect(d, QtCore.SIGNAL('computing_privkeys'), lambda: e.setText("Please wait... %d/%d"%(len(private_keys),len(addresses))))
        d.connect(d, QtCore.SIGNAL('show_privkeys'), show_privkeys)
        threading.Thread(target=privkeys_thread).start()

        if not d.exec_():
            done = True
            return

        filename = filename_e.text()
        if not filename:
            return

        try:
            self.do_export_privkeys(filename, private_keys, csv_button.isChecked())
        except (IOError, os.error), reason:
            export_error_label = _("Electrum was unable to produce a private key-export.")
            QMessageBox.critical(None, _("Unable to create csv"), export_error_label + "\n" + str(reason))

        except Exception as e:
            self.show_message(str(e))
            return

        self.show_message(_("Private keys exported."))


    def do_export_privkeys(self, fileName, pklist, is_csv):
        with open(fileName, "w+") as f:
            if is_csv:
                transaction = csv.writer(f)
                transaction.writerow(["address", "private_key"])
                for addr, pk in pklist.items():
                    transaction.writerow(["%34s"%addr,pk])
            else:
                import json
                f.write(json.dumps(pklist, indent = 4))


    def do_import_labels(self):
        labelsFile = self.getOpenFileName(_("Open labels file"), "*.dat")
        if not labelsFile: return
        try:
            f = open(labelsFile, 'r')
            data = f.read()
            f.close()
            for key, value in json.loads(data).items():
                self.wallet.set_label(key, value)
            QMessageBox.information(None, _("Labels imported"), _("Your labels were imported from")+" '%s'" % str(labelsFile))
        except (IOError, os.error), reason:
            QMessageBox.critical(None, _("Unable to import labels"), _("Electrum was unable to import your labels.")+"\n" + str(reason))


    def do_export_labels(self):
        labels = self.wallet.labels
        try:
            fileName = self.getSaveFileName(_("Select file to save your labels"), 'electrum_labels.dat', "*.dat")
            if fileName:
                with open(fileName, 'w+') as f:
                    json.dump(labels, f)
                QMessageBox.information(None, _("Labels exported"), _("Your labels where exported to")+" '%s'" % str(fileName))
        except (IOError, os.error), reason:
            QMessageBox.critical(None, _("Unable to export labels"), _("Electrum was unable to export your labels.")+"\n" + str(reason))


    def export_history_dialog(self):

        d = QDialog(self)
        d.setWindowTitle(_('Export History'))
        d.setMinimumSize(400, 200)
        vbox = QVBoxLayout(d)

        defaultname = os.path.expanduser('~/electrum-history.csv')
        select_msg = _('Select file to export your wallet transactions to')

        hbox, filename_e, csv_button = filename_field(self, self.config, defaultname, select_msg)
        vbox.addLayout(hbox)

        vbox.addStretch(1)

        h, b = ok_cancel_buttons2(d, _('Export'))
        vbox.addLayout(h)
        if not d.exec_():
            return

        filename = filename_e.text()
        if not filename:
            return

        try:
            self.do_export_history(self.wallet, filename, csv_button.isChecked())
        except (IOError, os.error), reason:
            export_error_label = _("Electrum was unable to produce a transaction export.")
            QMessageBox.critical(self, _("Unable to export history"), export_error_label + "\n" + str(reason))
            return

        QMessageBox.information(self,_("History exported"), _("Your wallet history has been successfully exported."))


    def do_export_history(self, wallet, fileName, is_csv):
        history = wallet.get_tx_history()
        lines = []
        for item in history:
            tx_hash, confirmations, is_mine, value, fee, balance, timestamp = item
            if confirmations:
                if timestamp is not None:
                    try:
                        time_string = datetime.datetime.fromtimestamp(timestamp).isoformat(' ')[:-3]
                    except [RuntimeError, TypeError, NameError] as reason:
                        time_string = "unknown"
                        pass
                else:
                    time_string = "unknown"
            else:
                time_string = "pending"

            if value is not None:
                value_string = format_satoshis(value, True)
            else:
                value_string = '--'

            if fee is not None:
                fee_string = format_satoshis(fee, True)
            else:
                fee_string = '0'

            if tx_hash:
                label, is_default_label = wallet.get_label(tx_hash)
                label = label.encode('utf-8')
            else:
                label = ""

            balance_string = format_satoshis(balance, False)
            if is_csv:
                lines.append([tx_hash, label, confirmations, value_string, fee_string, balance_string, time_string])
            else:
                lines.append({'txid':tx_hash, 'date':"%16s"%time_string, 'label':label, 'value':value_string})

        with open(fileName, "w+") as f:
            if is_csv:
                transaction = csv.writer(f)
                transaction.writerow(["transaction_hash","label", "confirmations", "value", "fee", "balance", "timestamp"])
                for line in lines:
                    transaction.writerow(line)
            else:
                import json
                f.write(json.dumps(lines, indent = 4))


    def sweep_key_dialog(self):
        d = QDialog(self)
        d.setWindowTitle(_('Sweep private keys'))
        d.setMinimumSize(600, 300)

        vbox = QVBoxLayout(d)
        vbox.addWidget(QLabel(_("Enter private keys")))

        keys_e = QTextEdit()
        keys_e.setTabChangesFocus(True)
        vbox.addWidget(keys_e)

        h, address_e = address_field(self.wallet.addresses())
        vbox.addLayout(h)

        vbox.addStretch(1)
        hbox, button = ok_cancel_buttons2(d, _('Sweep'))
        vbox.addLayout(hbox)
        button.setEnabled(False)

        def get_address():
            addr = str(address_e.text())
            if bitcoin.is_address(addr):
                return addr

        def get_pk():
            pk = str(keys_e.toPlainText()).strip()
            if Wallet.is_private_key(pk):
                return pk.split()

        f = lambda: button.setEnabled(get_address() is not None and get_pk() is not None)
        keys_e.textChanged.connect(f)
        address_e.textChanged.connect(f)
        if not d.exec_():
            return

        fee = self.wallet.fee
        tx = Transaction.sweep(get_pk(), self.network, get_address(), fee)
        self.show_transaction(tx)


    @protected
    def do_import_privkey(self, password):
        if not self.wallet.imported_keys:
            r = QMessageBox.question(None, _('Warning'), '<b>'+_('Warning') +':\n</b><br/>'+ _('Imported keys are not recoverable from seed.') + ' ' \
                                         + _('If you ever need to restore your wallet from its seed, these keys will be lost.') + '<p>' \
                                         + _('Are you sure you understand what you are doing?'), 3, 4)
            if r == 4: return

        text = text_dialog(self, _('Import private keys'), _("Enter private keys")+':', _("Import"))
        if not text: return

        text = str(text).split()
        badkeys = []
        addrlist = []
        for key in text:
            try:
                addr = self.wallet.import_key(key, password)
            except Exception as e:
                badkeys.append(key)
                continue
            if not addr:
                badkeys.append(key)
            else:
                addrlist.append(addr)
        if addrlist:
            QMessageBox.information(self, _('Information'), _("The following addresses were added") + ':\n' + '\n'.join(addrlist))
        if badkeys:
            QMessageBox.critical(self, _('Error'), _("The following inputs could not be imported") + ':\n'+ '\n'.join(badkeys))
        self.update_receive_tab()
        self.update_history_tab()


    def settings_dialog(self):
        d = QDialog(self)
        d.setWindowTitle(_('Electrum Settings'))
        d.setModal(1)
        vbox = QVBoxLayout()
        grid = QGridLayout()
        grid.setColumnStretch(0,1)

        nz_label = QLabel(_('Display zeros') + ':')
        grid.addWidget(nz_label, 0, 0)
        nz_e = AmountEdit(None,True)
        nz_e.setText("%d"% self.num_zeros)
        grid.addWidget(nz_e, 0, 1)
        msg = _('Number of zeros displayed after the decimal point. For example, if this is set to 2, "1." will be displayed as "1.00"')
        grid.addWidget(HelpButton(msg), 0, 2)
        if not self.config.is_modifiable('num_zeros'):
            for w in [nz_e, nz_label]: w.setEnabled(False)

        lang_label=QLabel(_('Language') + ':')
        grid.addWidget(lang_label, 1, 0)
        lang_combo = QComboBox()
        from electrum.i18n import languages
        lang_combo.addItems(languages.values())
        try:
            index = languages.keys().index(self.config.get("language",''))
        except Exception:
            index = 0
        lang_combo.setCurrentIndex(index)
        grid.addWidget(lang_combo, 1, 1)
        grid.addWidget(HelpButton(_('Select which language is used in the GUI (after restart).')+' '), 1, 2)
        if not self.config.is_modifiable('language'):
            for w in [lang_combo, lang_label]: w.setEnabled(False)


        fee_label = QLabel(_('Transaction fee') + ':')
        grid.addWidget(fee_label, 2, 0)
        fee_e = AmountEdit(self.base_unit)
        fee_e.setText(self.format_amount(self.wallet.fee).strip())
        grid.addWidget(fee_e, 2, 1)
        msg = _('Fee per kilobyte of transaction.') + ' ' \
            + _('Recommended value') + ': ' + self.format_amount(20000)
        grid.addWidget(HelpButton(msg), 2, 2)
        if not self.config.is_modifiable('fee_per_kb'):
            for w in [fee_e, fee_label]: w.setEnabled(False)

        units = ['BTC', 'mBTC']
        unit_label = QLabel(_('Base unit') + ':')
        grid.addWidget(unit_label, 3, 0)
        unit_combo = QComboBox()
        unit_combo.addItems(units)
        unit_combo.setCurrentIndex(units.index(self.base_unit()))
        grid.addWidget(unit_combo, 3, 1)
        grid.addWidget(HelpButton(_('Base unit of your wallet.')\
                                             + '\n1BTC=1000mBTC.\n' \
                                             + _(' These settings affects the fields in the Send tab')+' '), 3, 2)

        usechange_cb = QCheckBox(_('Use change addresses'))
        usechange_cb.setChecked(self.wallet.use_change)
        grid.addWidget(usechange_cb, 4, 0)
        grid.addWidget(HelpButton(_('Using change addresses makes it more difficult for other people to track your transactions.')+' '), 4, 2)
        if not self.config.is_modifiable('use_change'): usechange_cb.setEnabled(False)

        block_explorers = ['Blockchain.info', 'Blockr.io', 'Insight.is']
        block_ex_label = QLabel(_('Online Block Explorer') + ':')
        grid.addWidget(block_ex_label, 5, 0)
        block_ex_combo = QComboBox()
        block_ex_combo.addItems(block_explorers)
        block_ex_combo.setCurrentIndex(block_explorers.index(self.config.get('block_explorer', 'Blockchain.info')))
        grid.addWidget(block_ex_combo, 5, 1)
        grid.addWidget(HelpButton(_('Choose which online block explorer to use for functions that open a web browser')+' '), 5, 2)

        show_tx = self.config.get('show_before_broadcast', False)
        showtx_cb = QCheckBox(_('Show before broadcast'))
        showtx_cb.setChecked(show_tx)
        grid.addWidget(showtx_cb, 6, 0)
        grid.addWidget(HelpButton(_('Display the details of your transactions before broadcasting it.')), 6, 2)

        vbox.addLayout(grid)
        vbox.addStretch(1)
        vbox.addLayout(ok_cancel_buttons(d))
        d.setLayout(vbox)

        # run the dialog
        if not d.exec_(): return

        fee = unicode(fee_e.text())
        try:
            fee = self.read_amount(fee)
        except Exception:
            QMessageBox.warning(self, _('Error'), _('Invalid value') +': %s'%fee, _('OK'))
            return

        self.wallet.set_fee(fee)

        nz = unicode(nz_e.text())
        try:
            nz = int( nz )
            if nz>8: nz=8
        except Exception:
            QMessageBox.warning(self, _('Error'), _('Invalid value')+':%s'%nz, _('OK'))
            return

        if self.num_zeros != nz:
            self.num_zeros = nz
            self.config.set_key('num_zeros', nz, True)
            self.update_history_tab()
            self.update_receive_tab()

        usechange_result = usechange_cb.isChecked()
        if self.wallet.use_change != usechange_result:
            self.wallet.use_change = usechange_result
            self.wallet.storage.put('use_change', self.wallet.use_change)

        if showtx_cb.isChecked() != show_tx:
            self.config.set_key('show_before_broadcast', not show_tx)

        unit_result = units[unit_combo.currentIndex()]
        if self.base_unit() != unit_result:
            self.decimal_point = 8 if unit_result == 'BTC' else 5
            self.config.set_key('decimal_point', self.decimal_point, True)
            self.update_history_tab()
            self.update_status()

        need_restart = False

        lang_request = languages.keys()[lang_combo.currentIndex()]
        if lang_request != self.config.get('language'):
            self.config.set_key("language", lang_request, True)
            need_restart = True

        be_result = block_explorers[block_ex_combo.currentIndex()]
        self.config.set_key('block_explorer', be_result, True)

        run_hook('close_settings_dialog')

        if need_restart:
            QMessageBox.warning(self, _('Success'), _('Please restart Electrum to activate the new GUI settings'), _('OK'))


    def run_network_dialog(self):
        if not self.network:
            return
        NetworkDialog(self.wallet.network, self.config, self).do_exec()

    def closeEvent(self, event):
        self.tray.hide()
        self.config.set_key("is_maximized", self.isMaximized())
        if not self.isMaximized():
            g = self.geometry()
            self.config.set_key("winpos-qt", [g.left(),g.top(),g.width(),g.height()])
        self.save_column_widths()
        self.config.set_key("console-history", self.console.history[-50:], True)
        self.wallet.storage.put('accounts_expanded', self.accounts_expanded)
        event.accept()


    def plugins_dialog(self):
        from electrum.plugins import plugins

        d = QDialog(self)
        d.setWindowTitle(_('Electrum Plugins'))
        d.setModal(1)

        vbox = QVBoxLayout(d)

        # plugins
        scroll = QScrollArea()
        scroll.setEnabled(True)
        scroll.setWidgetResizable(True)
        scroll.setMinimumSize(400,250)
        vbox.addWidget(scroll)

        w = QWidget()
        scroll.setWidget(w)
        w.setMinimumHeight(len(plugins)*35)

        grid = QGridLayout()
        grid.setColumnStretch(0,1)
        w.setLayout(grid)

        def do_toggle(cb, p, w):
            r = p.toggle()
            cb.setChecked(r)
            if w: w.setEnabled(r)

        def mk_toggle(cb, p, w):
            return lambda: do_toggle(cb,p,w)

        for i, p in enumerate(plugins):
            try:
                cb = QCheckBox(p.fullname())
                cb.setDisabled(not p.is_available())
                cb.setChecked(p.is_enabled())
                grid.addWidget(cb, i, 0)
                if p.requires_settings():
                    w = p.settings_widget(self)
                    w.setEnabled( p.is_enabled() )
                    grid.addWidget(w, i, 1)
                else:
                    w = None
                cb.clicked.connect(mk_toggle(cb,p,w))
                grid.addWidget(HelpButton(p.description()), i, 2)
            except Exception:
                print_msg(_("Error: cannot display plugin"), p)
                traceback.print_exc(file=sys.stdout)
        grid.setRowStretch(i+1,1)

        vbox.addLayout(close_button(d))

        d.exec_()


    def show_account_details(self, k):
        account = self.wallet.accounts[k]

        d = QDialog(self)
        d.setWindowTitle(_('Account Details'))
        d.setModal(1)

        vbox = QVBoxLayout(d)
        name = self.wallet.get_account_name(k)
        label = QLabel('Name: ' + name)
        vbox.addWidget(label)

        vbox.addWidget(QLabel(_('Address type') + ': ' + account.get_type()))

        vbox.addWidget(QLabel(_('Derivation') + ': ' + k))

        vbox.addWidget(QLabel(_('Master Public Key:')))

        text = QTextEdit()
        text.setReadOnly(True)
        text.setMaximumHeight(170)
        vbox.addWidget(text)

        mpk_text = '\n'.join( account.get_master_pubkeys() )
        text.setText(mpk_text)

        vbox.addLayout(close_button(d))
        d.exec_()

########NEW FILE########
__FILENAME__ = network_dialog
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys, time, datetime, re, threading
from electrum.i18n import _
from electrum.util import print_error, print_msg
import os.path, json, ast, traceback

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from electrum import DEFAULT_SERVERS, DEFAULT_PORTS

from util import *

protocol_names = ['TCP', 'HTTP', 'SSL', 'HTTPS']
protocol_letters = 'thsg'

class NetworkDialog(QDialog):
    def __init__(self, network, config, parent):

        QDialog.__init__(self,parent)
        self.setModal(1)
        self.setWindowTitle(_('Network'))
        self.setMinimumSize(375, 20)

        self.network = network
        self.config = config
        self.protocol = None

        if parent:
            n = len(network.interfaces)
            if n:
                status = _("Blockchain") + ": " + "%d "%(network.blockchain.height()) + _("blocks") +  ".\n" + _("Getting block headers from %d nodes.")%n
            else:
                status = _("Not connected")

            if network.is_connected():
                status += "\n" + _("Server") + ": %s"%(network.interface.host) 
            else:
                status += "\n" + _("Disconnected from server")
                
        else:
            import random
            status = _("Please choose a server.") + "\n" + _("Select 'Cancel' if you are offline.")

        server = network.default_server
        self.servers = network.get_servers()


        vbox = QVBoxLayout()
        vbox.setSpacing(30)

        hbox = QHBoxLayout()
        l = QLabel()
        l.setPixmap(QPixmap(":icons/network.png"))
        hbox.addStretch(10)
        hbox.addWidget(l)
        hbox.addWidget(QLabel(status))
        hbox.addStretch(50)
        msg = _("Electrum sends your wallet addresses to a single server, in order to receive your transaction history.") + "\n\n" \
            + _("In addition, Electrum connects to several nodes in order to download block headers and find out the longest blockchain.") + " " \
            + _("This blockchain is used to verify the transactions sent by the address server.")
        hbox.addWidget(HelpButton(msg))
        vbox.addLayout(hbox)

        # grid layout
        grid = QGridLayout()
        grid.setSpacing(8)
        vbox.addLayout(grid)

        # protocol
        self.server_protocol = QComboBox()
        self.server_host = QLineEdit()
        self.server_host.setFixedWidth(200)
        self.server_port = QLineEdit()
        self.server_port.setFixedWidth(60)
        self.server_protocol.addItems(protocol_names)
        self.server_protocol.connect(self.server_protocol, SIGNAL('currentIndexChanged(int)'), self.change_protocol)

        grid.addWidget(QLabel(_('Protocol') + ':'), 3, 0)
        grid.addWidget(self.server_protocol, 3, 1)


        # server
        grid.addWidget(QLabel(_('Server') + ':'), 0, 0)

        # auto connect
        self.autocycle_cb = QCheckBox(_('Auto-connect'))
        self.autocycle_cb.setChecked(self.config.get('auto_cycle', True))
        grid.addWidget(self.autocycle_cb, 0, 1)
        if not self.config.is_modifiable('auto_cycle'): self.autocycle_cb.setEnabled(False)
        msg = _("If auto-connect is enabled, Electrum will always use a server that is on the longest blockchain.") + " " \
            + _("If it is disabled, Electrum will warn you if your server is lagging.")
        grid.addWidget(HelpButton(msg), 0, 4)

        grid.addWidget(self.server_host, 0, 2, 1, 2)
        grid.addWidget(self.server_port, 0, 3)


        label = _('Active Servers') if network.irc_servers else _('Default Servers')
        self.servers_list_widget = QTreeWidget(parent)
        self.servers_list_widget.setHeaderLabels( [ label, _('Limit') ] )
        self.servers_list_widget.setMaximumHeight(150)
        self.servers_list_widget.setColumnWidth(0, 240)

        if server:
            host, port, protocol = server.split(':')
            self.change_server(host, protocol)

        self.set_protocol(self.network.protocol)

        self.servers_list_widget.connect(self.servers_list_widget, 
                                         SIGNAL('currentItemChanged(QTreeWidgetItem*,QTreeWidgetItem*)'), 
                                         lambda x,y: self.server_changed(x))
        grid.addWidget(self.servers_list_widget, 1, 1, 1, 3)

        if not config.is_modifiable('server'):
            for w in [self.server_host, self.server_port, self.server_protocol, self.servers_list_widget]: w.setEnabled(False)


        
        def enable_set_server():
            enabled = not self.autocycle_cb.isChecked()
            self.server_host.setEnabled(enabled)
            self.server_port.setEnabled(enabled)
            self.servers_list_widget.setEnabled(enabled)

        self.autocycle_cb.clicked.connect(enable_set_server)
        enable_set_server()

        # proxy setting
        self.proxy_mode = QComboBox()
        self.proxy_host = QLineEdit()
        self.proxy_host.setFixedWidth(200)
        self.proxy_port = QLineEdit()
        self.proxy_port.setFixedWidth(60)
        self.proxy_mode.addItems(['NONE', 'SOCKS4', 'SOCKS5', 'HTTP'])

        def check_for_disable(index = False):
            if self.proxy_mode.currentText() != 'NONE':
                self.proxy_host.setEnabled(True)
                self.proxy_port.setEnabled(True)
            else:
                self.proxy_host.setEnabled(False)
                self.proxy_port.setEnabled(False)

        check_for_disable()
        self.proxy_mode.connect(self.proxy_mode, SIGNAL('currentIndexChanged(int)'), check_for_disable)

        if not self.config.is_modifiable('proxy'):
            for w in [self.proxy_host, self.proxy_port, self.proxy_mode]: w.setEnabled(False)

        proxy_config = network.proxy if network.proxy else { "mode":"none", "host":"localhost", "port":"8080"}
        self.proxy_mode.setCurrentIndex(self.proxy_mode.findText(str(proxy_config.get("mode").upper())))
        self.proxy_host.setText(proxy_config.get("host"))
        self.proxy_port.setText(proxy_config.get("port"))

        grid.addWidget(QLabel(_('Proxy') + ':'), 4, 0)
        grid.addWidget(self.proxy_mode, 4, 1)
        grid.addWidget(self.proxy_host, 4, 2)
        grid.addWidget(self.proxy_port, 4, 3)

        # buttons
        vbox.addLayout(ok_cancel_buttons(self))
        self.setLayout(vbox) 


    def init_servers_list(self):
        self.servers_list_widget.clear()
        for _host, d in self.servers.items():
            if d.get(self.protocol):
                pruning_level = d.get('pruning','')
                self.servers_list_widget.addTopLevelItem(QTreeWidgetItem( [ _host, pruning_level ] ))


    def set_protocol(self, protocol):
        if protocol != self.protocol:
            self.protocol = protocol
            self.init_servers_list()
        
    def change_protocol(self, index):
        p = protocol_letters[index]
        host = unicode(self.server_host.text())
        pp = self.servers.get(host, DEFAULT_PORTS)
        if p not in pp.keys():
            p = pp.keys()[0]
        port = pp[p]
        self.server_host.setText( host )
        self.server_port.setText( port )
        self.set_protocol(p)

    def server_changed(self, x):
        if x: 
            self.change_server(str(x.text(0)), self.protocol)

    def change_server(self, host, protocol):

        pp = self.servers.get(host, DEFAULT_PORTS)
        if protocol:
            port = pp.get(protocol)
            if not port: protocol = None
                    
        if not protocol:
            if 's' in pp.keys():
                protocol = 's'
                port = pp.get(protocol)
            else:
                protocol = pp.keys()[0]
                port = pp.get(protocol)
            
        self.server_host.setText( host )
        self.server_port.setText( port )
        self.server_protocol.setCurrentIndex(protocol_letters.index(protocol))

        if not self.servers: return
        for p in protocol_letters:
            i = protocol_letters.index(p)
            j = self.server_protocol.model().index(i,0)
            #if p not in pp.keys(): # and self.interface.is_connected:
            #    self.server_protocol.model().setData(j, QVariant(0), Qt.UserRole-1)
            #else:
            #    self.server_protocol.model().setData(j, QVariant(33), Qt.UserRole-1)


    def do_exec(self):

        if not self.exec_():
            return

        host = str( self.server_host.text() )
        port = str( self.server_port.text() )
        protocol = protocol_letters[self.server_protocol.currentIndex()]

        if self.proxy_mode.currentText() != 'NONE':
            proxy = { 'mode':str(self.proxy_mode.currentText()).lower(), 
                      'host':str(self.proxy_host.text()), 
                      'port':str(self.proxy_port.text()) }
        else:
            proxy = None

        auto_connect = self.autocycle_cb.isChecked()

        self.network.set_parameters(host, port, protocol, proxy, auto_connect)
        return True

########NEW FILE########
__FILENAME__ = password_dialog
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2013 ecdsa@github
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from electrum.i18n import _
from util import *



def make_password_dialog(self, wallet, msg):

    self.pw = QLineEdit()
    self.pw.setEchoMode(2)
    self.new_pw = QLineEdit()
    self.new_pw.setEchoMode(2)
    self.conf_pw = QLineEdit()
    self.conf_pw.setEchoMode(2)
    
    vbox = QVBoxLayout()
    label = QLabel(msg)
    label.setWordWrap(True)

    grid = QGridLayout()
    grid.setSpacing(8)
    grid.setColumnMinimumWidth(0, 70)
    grid.setColumnStretch(1,1)

    logo = QLabel()
    lockfile = ":icons/lock.png" if wallet and wallet.use_encryption else ":icons/unlock.png"
    logo.setPixmap(QPixmap(lockfile).scaledToWidth(36))
    logo.setAlignment(Qt.AlignCenter)

    grid.addWidget(logo,  0, 0)
    grid.addWidget(label, 0, 1, 1, 2)
    vbox.addLayout(grid)

    grid = QGridLayout()
    grid.setSpacing(8)
    grid.setColumnMinimumWidth(0, 250)
    grid.setColumnStretch(1,1)
    
    if wallet and wallet.use_encryption:
        grid.addWidget(QLabel(_('Password')), 0, 0)
        grid.addWidget(self.pw, 0, 1)
        
    grid.addWidget(QLabel(_('New Password')), 1, 0)
    grid.addWidget(self.new_pw, 1, 1)

    grid.addWidget(QLabel(_('Confirm Password')), 2, 0)
    grid.addWidget(self.conf_pw, 2, 1)
    vbox.addLayout(grid)

    vbox.addStretch(1)
    vbox.addLayout(ok_cancel_buttons(self))
    return vbox


def run_password_dialog(self, wallet, parent):
        
    if wallet and wallet.is_watching_only():
        QMessageBox.information(parent, _('Error'), _('This is a watching-only wallet'), _('OK'))
        return False, None, None

    if not self.exec_():
        return False, None, None

    password = unicode(self.pw.text()) if wallet and wallet.use_encryption else None
    new_password = unicode(self.new_pw.text())
    new_password2 = unicode(self.conf_pw.text())

    if new_password != new_password2:
        QMessageBox.warning(parent, _('Error'), _('Passwords do not match'), _('OK'))
        # Retry
        return run_password_dialog(self, wallet, parent)

    if not new_password:
        new_password = None

    return True, password, new_password



class PasswordDialog(QDialog):

    def __init__(self, wallet, parent):
        QDialog.__init__(self, parent)
        self.setModal(1)
        self.wallet = wallet
        self.parent = parent
        self.setWindowTitle(_("Set Password"))
        msg = (_('Your wallet is encrypted. Use this dialog to change your password.') + ' '\
               +_('To disable wallet encryption, enter an empty new password.')) \
               if wallet.use_encryption else _('Your wallet keys are not encrypted')
        self.setLayout(make_password_dialog(self, wallet, msg))


    def run(self):
        ok, password, new_password = run_password_dialog(self, self.wallet, self.parent)
        if not ok:
            return

        try:
            self.wallet.check_password(password)
        except Exception:
            QMessageBox.warning(self.parent, _('Error'), _('Incorrect Password'), _('OK'))
            return False, None, None

        try:
            self.wallet.update_password(password, new_password)
        except:
            import traceback, sys
            traceback.print_exc(file=sys.stdout)
            QMessageBox.warning(self.parent, _('Error'), _('Failed to update password'), _('OK'))
            return

        if new_password:
            QMessageBox.information(self.parent, _('Success'), _('Password was updated successfully'), _('OK'))
        else:
            QMessageBox.information(self.parent, _('Success'), _('This wallet is not encrypted'), _('OK'))





########NEW FILE########
__FILENAME__ = qrcodewidget
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui

from electrum import bmp, pyqrnative


class QRCodeWidget(QWidget):

    def __init__(self, data = None):
        QWidget.__init__(self)
        self.addr = None
        self.qr = None
        if data:
            self.set_addr(data)
            self.update_qr()

    def set_addr(self, addr):
        if self.addr != addr:
            if len(addr) < 128:
                MinSize = 210
            else:
                MinSize = 500
            self.setMinimumSize(MinSize, MinSize)
            self.addr = addr
            self.qr = None
            self.update()

    def update_qr(self):
        if self.addr and not self.qr:
            for size in range(len(pyqrnative.QRUtil.PATTERN_POSITION_TABLE)): # [4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32]:
                try:
                    self.qr = pyqrnative.QRCode(size, pyqrnative.QRErrorCorrectLevel.L)
                    self.qr.addData(self.addr)
                    self.qr.make()
                    break
                except Exception:
                    self.qr=None
                    continue
            self.update()

    def paintEvent(self, e):

        if not self.addr:
            return

        black = QColor(0, 0, 0, 255)
        white = QColor(255, 255, 255, 255)

        if not self.qr:
            qp = QtGui.QPainter()
            qp.begin(self)
            qp.setBrush(white)
            qp.setPen(white)
            qp.drawRect(0, 0, 198, 198)
            qp.end()
            return
 
        k = self.qr.getModuleCount()
        qp = QtGui.QPainter()
        qp.begin(self)
        r = qp.viewport()
        boxsize = min(r.width(), r.height())*0.8/k
        size = k*boxsize
        left = (r.width() - size)/2
        top = (r.height() - size)/2         

        # Make a white margin around the QR in case of dark theme use:
        margin = 10
        qp.setBrush(white)
        qp.drawRect(left-margin, top-margin, size+(margin*2), size+(margin*2))

        for r in range(k):
            for c in range(k):
                if self.qr.isDark(r, c):
                    qp.setBrush(black)
                    qp.setPen(black)
                else:
                    qp.setBrush(white)
                    qp.setPen(white)
                qp.drawRect(left+c*boxsize, top+r*boxsize, boxsize, boxsize)
        qp.end()
        

########NEW FILE########
__FILENAME__ = receiving_widget
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from electrum.i18n import _

class ReceivingWidget(QTreeWidget):

    def toggle_used(self):
        if self.hide_used:
            self.hide_used = False
            self.setColumnHidden(2, False)
        else:
            self.hide_used = True
            self.setColumnHidden(2, True)
        self.update_list()

    def edit_label(self, item, column):
      if column == 1 and item.isSelected():
        self.editing = True
        item.setFlags(Qt.ItemIsEditable|Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
        self.editItem(item, column)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
        self.editing = False

    def update_label(self, item, column):
      if self.editing: 
          return
      else:
          address = str(item.text(0))
          label = unicode( item.text(1) )
          self.owner.actuator.g.wallet.set_label(address, label)

    def copy_address(self):
        address = self.currentItem().text(0)
        qApp.clipboard().setText(address)
        

    def update_list(self):
        return
        self.clear()
        addresses = self.owner.actuator.g.wallet.addresses(False)
        for address in addresses:
            history = self.owner.actuator.g.wallet.history.get(address,[])

            used = "No"
            # It appears that at this moment history can either be an array with tx and block height
            # Or just a tx that's why this ugly code duplication is in, will fix
            if len(history) == 1:
                # This means pruned data. If that's the case the address has to been used at one point
                if history[0] == "*":
                    used = "Yes"
                else:
                    for tx_hash in history:
                        tx = self.owner.actuator.g.wallet.transactions.get(tx_hash)
                        if tx:
                            used = "Yes"
            else:
                for tx_hash, height in history:
                    tx = self.owner.actuator.g.wallet.transactions.get(tx_hash)
                    if tx:
                        used = "Yes"

            if(self.hide_used == True and used == "No") or self.hide_used == False:
                label = self.owner.actuator.g.wallet.labels.get(address,'')
                item = QTreeWidgetItem([address, label, used])
                self.insertTopLevelItem(0, item)

    def __init__(self, owner=None):
        self.owner = owner
        self.editing = False

        QTreeWidget.__init__(self, owner)
        self.setColumnCount(3)
        self.setHeaderLabels([_("Address"), _("Label"), _("Used")])
        self.setIndentation(0)

        self.hide_used = True
        self.setColumnHidden(2, True)

########NEW FILE########
__FILENAME__ = seed_dialog
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2013 ecdsa@github
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore
from electrum.i18n import _
from electrum import mnemonic
from qrcodewidget import QRCodeWidget
from util import close_button

class SeedDialog(QDialog):
    def __init__(self, parent, seed, imported_keys):
        QDialog.__init__(self, parent)
        self.setModal(1)
        self.setWindowTitle('Electrum' + ' - ' + _('Seed'))
        vbox = show_seed_box(seed)
        if imported_keys:
            vbox.addWidget(QLabel("<b>"+_("WARNING")+":</b> " + _("Your wallet contains imported keys. These keys cannot be recovered from seed.") + "</b><p>"))
        vbox.addLayout(close_button(self))
        self.setLayout(vbox)


def icon_filename(sid):
    if sid == 'cold':
        return ":icons/cold_seed.png" 
    elif sid == 'hot':
        return ":icons/hot_seed.png" 
    else:
        return ":icons/seed.png" 
    



def show_seed_box(seed, sid=None):

    save_msg = _("Please save these %d words on paper (order is important).")%len(seed.split()) + " " 
    qr_msg = _("Your seed is also displayed as QR code, in case you want to transfer it to a mobile phone.") + "<p>"
    warning_msg = "<b>"+_("WARNING")+":</b> " + _("Never disclose your seed. Never type it on a website.") + "</b><p>"

    if sid is None:
        msg =  _("Your wallet generation seed is")
        msg2 = save_msg + " " \
               + _("This seed will allow you to recover your wallet in case of computer failure.") + "<br/>" \
               + warning_msg
        
    elif sid == 'cold':
        msg =  _("Your cold storage seed is")
        msg2 = save_msg + " " \
               + _("This seed will be permanently deleted from your wallet file. Make sure you have saved it before you press 'next'") + " " \
            
    elif sid == 'hot':
        msg =  _("Your hot seed is")
        msg2 = save_msg + " " \
               + _("If you ever need to recover your wallet from seed, you will need both this seed and your cold seed.") + " " \

    label1 = QLabel(msg+ ":")
    seed_text = QTextEdit(seed)
    seed_text.setReadOnly(True)
    seed_text.setMaximumHeight(130)

    label2 = QLabel(msg2)
    label2.setWordWrap(True)

    logo = QLabel()

    logo.setPixmap(QPixmap(icon_filename(sid)).scaledToWidth(56))
    logo.setMaximumWidth(60)

    grid = QGridLayout()
    grid.addWidget(logo, 0, 0)
    grid.addWidget(label1, 0, 1)
    grid.addWidget(seed_text, 1, 0, 1, 2)
    #qrw = QRCodeWidget(seed)
    #grid.addWidget(qrw, 0, 2, 2, 1)
    vbox = QVBoxLayout()
    vbox.addLayout(grid)
    vbox.addWidget(label2)
    vbox.addStretch(1)
    
    return vbox


def enter_seed_box(msg, sid=None):

    vbox = QVBoxLayout()
    logo = QLabel()
    logo.setPixmap(QPixmap(icon_filename(sid)).scaledToWidth(56))
    logo.setMaximumWidth(60)

    label = QLabel(msg)
    label.setWordWrap(True)

    seed_e = QTextEdit()
    seed_e.setMaximumHeight(100)
    seed_e.setTabChangesFocus(True)

    vbox.addWidget(label)

    grid = QGridLayout()
    grid.addWidget(logo, 0, 0)
    grid.addWidget(seed_e, 0, 1)

    vbox.addLayout(grid)
    return vbox, seed_e

########NEW FILE########
__FILENAME__ = transaction_dialog
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys, time, datetime, re, threading
from electrum.i18n import _, set_language
from electrum.util import print_error, print_msg
import os.path, json, ast, traceback
import shutil
import StringIO


try:
    import PyQt4
except Exception:
    sys.exit("Error: Could not import PyQt4 on Linux systems, you may try 'sudo apt-get install python-qt4'")

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore

from electrum import transaction
from util import MyTreeWidget

class TxDialog(QDialog):

    def __init__(self, tx, parent):
        self.tx = tx
        tx_dict = tx.as_dict()
        self.parent = parent
        self.wallet = parent.wallet
            
        QDialog.__init__(self)
        self.setMinimumWidth(600)
        self.setWindowTitle(_("Transaction"))
        self.setModal(1)

        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel(_("Transaction ID:")))
        self.tx_hash_e  = QLineEdit()
        self.tx_hash_e.setReadOnly(True)
        vbox.addWidget(self.tx_hash_e)
        self.status_label = QLabel()
        vbox.addWidget(self.status_label)

        self.date_label = QLabel()
        vbox.addWidget(self.date_label)
        self.amount_label = QLabel()
        vbox.addWidget(self.amount_label)
        self.fee_label = QLabel()
        vbox.addWidget(self.fee_label)

        self.add_io(vbox)

        vbox.addStretch(1)

        buttons = QHBoxLayout()
        vbox.addLayout( buttons )

        buttons.addStretch(1)

        self.sign_button = b = QPushButton(_("Sign"))
        b.clicked.connect(self.sign)
        buttons.addWidget(b)

        self.broadcast_button = b = QPushButton(_("Broadcast"))
        b.clicked.connect(self.broadcast)
        b.hide()
        buttons.addWidget(b)

        self.save_button = b = QPushButton(_("Save"))
        b.clicked.connect(self.save)
        buttons.addWidget(b)

        cancelButton = QPushButton(_("Close"))
        cancelButton.clicked.connect(lambda: self.done(0))
        buttons.addWidget(cancelButton)
        cancelButton.setDefault(True)
        
        self.update()




    def sign(self):
        tx_dict = self.tx.as_dict()
        input_info = json.loads(tx_dict["input_info"])
        self.parent.sign_raw_transaction(self.tx, input_info)
        self.update()


    def save(self):
        name = 'signed_%s.txn' % (self.tx.hash()[0:8]) if self.tx.is_complete() else 'unsigned.txn'
        fileName = self.parent.getSaveFileName(_("Select where to save your signed transaction"), name, "*.txn")
        if fileName:
            with open(fileName, "w+") as f:
                f.write(json.dumps(self.tx.as_dict(),indent=4) + '\n')
            self.show_message(_("Transaction saved successfully"))



    def update(self):

        is_relevant, is_mine, v, fee = self.wallet.get_tx_value(self.tx)

        if self.tx.is_complete():
            status = _("Status: Signed")
            self.sign_button.hide()
            tx_hash = self.tx.hash()

            if tx_hash in self.wallet.transactions.keys():
                conf, timestamp = self.wallet.verifier.get_confirmations(tx_hash)
                if timestamp:
                    time_str = datetime.datetime.fromtimestamp(timestamp).isoformat(' ')[:-3]
                else:
                    time_str = 'pending'
                status = _("Status: %d confirmations")%conf
                self.broadcast_button.hide()
            else:
                time_str = None
                conf = 0
                self.broadcast_button.show()
        else:
            status = _("Status: Unsigned")
            time_str = None
            if not self.wallet.is_watching_only():
                self.sign_button.show()
            else:
                self.sign_button.hide()
            self.broadcast_button.hide()
            tx_hash = 'unknown'

        self.tx_hash_e.setText(tx_hash)
        self.status_label.setText(status)

        if time_str is not None:
            self.date_label.setText(_("Date: %s")%time_str)
            self.date_label.show()
        else:
            self.date_label.hide()


        # if we are not synchronized, we cannot tell
        if self.parent.network is None or not self.parent.network.is_running() or not self.parent.network.is_connected():
            return
        if not self.wallet.up_to_date:
            return

        if is_relevant:    
            if is_mine:
                if fee is not None: 
                    self.amount_label.setText(_("Amount sent:")+' %s'% self.parent.format_amount(v-fee) + ' ' + self.parent.base_unit())
                    self.fee_label.setText(_("Transaction fee")+': %s'% self.parent.format_amount(fee) + ' ' + self.parent.base_unit())
                else:
                    self.amount_label.setText(_("Amount sent:")+' %s'% self.parent.format_amount(v) + ' ' + self.parent.base_unit())
                    self.fee_label.setText(_("Transaction fee")+': '+ _("unknown"))
            else:
                self.amount_label.setText(_("Amount received:")+' %s'% self.parent.format_amount(v) + ' ' + self.parent.base_unit())
        else:
            self.amount_label.setText(_("Transaction unrelated to your wallet"))


    def exec_menu(self, position,l):
        item = l.itemAt(position)
        if not item: return
        addr = unicode(item.text(0))
        menu = QMenu()
        menu.addAction(_("Copy to clipboard"), lambda: self.parent.app.clipboard().setText(addr))
        menu.exec_(l.viewport().mapToGlobal(position))


    def add_io(self, vbox):

        if self.tx.locktime > 0:
            vbox.addWidget(QLabel("LockTime: %d\n" % self.tx.locktime))

        vbox.addWidget(QLabel(_("Inputs")))
        def format_input(x):
            if x.get('is_coinbase'):
                return 'coinbase'
            else:
                _hash = x.get('prevout_hash')
                return _hash[0:16] + '...' + _hash[-8:] + ":%d"%x.get('prevout_n') + u'\t' + "%s"%x.get('address')
        lines = map(format_input, self.tx.inputs )
        i_text = QTextEdit()
        i_text.setText('\n'.join(lines))
        i_text.setReadOnly(True)
        i_text.setMaximumHeight(100)
        vbox.addWidget(i_text)

        vbox.addWidget(QLabel(_("Outputs")))
        lines = map(lambda x: x[0] + u'\t\t' + self.parent.format_amount(x[1]), self.tx.outputs)
        o_text = QTextEdit()
        o_text.setText('\n'.join(lines))
        o_text.setReadOnly(True)
        o_text.setMaximumHeight(100)
        vbox.addWidget(o_text)

        


    def broadcast(self):
        result, result_message = self.wallet.sendtx( self.tx )
        if result:
            self.show_message(_("Transaction successfully sent")+': %s' % (result_message))
        else:
            self.show_message(_("There was a problem sending your transaction:") + '\n %s' % (result_message))

    def show_message(self, msg):
        QMessageBox.information(self, _('Message'), msg, _('OK'))





########NEW FILE########
__FILENAME__ = util
from electrum.i18n import _
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os.path
import time

import threading

class WaitingDialog(QThread):
    def __init__(self, parent, message, run_task, on_complete=None):
        QThread.__init__(self)
        self.parent = parent
        self.d = QDialog(parent)
        self.d.setWindowTitle('Please wait')
        l = QLabel(message)
        vbox = QVBoxLayout(self.d)
        vbox.addWidget(l)
        self.run_task = run_task
        self.on_complete = on_complete
        self.d.connect(self.d, SIGNAL('done'), self.close)
        self.d.show()

    def run(self):
        self.result = self.run_task()
        self.d.emit(SIGNAL('done'))

    def close(self):
        self.d.accept()
        if self.on_complete:
            self.on_complete(*self.result)



class Timer(QThread):
    def run(self):
        while True:
            self.emit(SIGNAL('timersignal'))
            time.sleep(0.5)


class EnterButton(QPushButton):
    def __init__(self, text, func):
        QPushButton.__init__(self, text)
        self.func = func
        self.clicked.connect(func)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Return:
            apply(self.func,())





class HelpButton(QPushButton):
    def __init__(self, text):
        QPushButton.__init__(self, '?')
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedWidth(20)
        self.clicked.connect(lambda: QMessageBox.information(self, 'Help', text, 'OK') )




def close_button(dialog, label=_("Close") ):
    hbox = QHBoxLayout()
    hbox.addStretch(1)
    b = QPushButton(label)
    hbox.addWidget(b)
    b.clicked.connect(dialog.close)
    b.setDefault(True)
    return hbox

def ok_cancel_buttons2(dialog, ok_label=_("OK") ):
    hbox = QHBoxLayout()
    hbox.addStretch(1)
    b = QPushButton(_("Cancel"))
    hbox.addWidget(b)
    b.clicked.connect(dialog.reject)
    b = QPushButton(ok_label)
    hbox.addWidget(b)
    b.clicked.connect(dialog.accept)
    b.setDefault(True)
    return hbox, b

def ok_cancel_buttons(dialog, ok_label=_("OK") ):
    hbox, b = ok_cancel_buttons2(dialog, ok_label)
    return hbox

def text_dialog(parent, title, label, ok_label, default=None):
    dialog = QDialog(parent)
    dialog.setMinimumWidth(500)
    dialog.setWindowTitle(title)
    dialog.setModal(1)
    l = QVBoxLayout()
    dialog.setLayout(l)
    l.addWidget(QLabel(label))
    txt = QTextEdit()
    if default:
        txt.setText(default)
    l.addWidget(txt)
    l.addLayout(ok_cancel_buttons(dialog, ok_label))
    if dialog.exec_():
        return unicode(txt.toPlainText())



def address_field(addresses):
    hbox = QHBoxLayout()
    address_e = QLineEdit()
    if addresses:
        address_e.setText(addresses[0])
    def func():
        i = addresses.index(str(address_e.text())) + 1
        i = i % len(addresses)
        address_e.setText(addresses[i])
    button = QPushButton(_('Address'))
    button.clicked.connect(func)
    hbox.addWidget(button)
    hbox.addWidget(address_e)
    return hbox, address_e


def filename_field(parent, config, defaultname, select_msg):

    vbox = QVBoxLayout()
    vbox.addWidget(QLabel(_("Format")))
    gb = QGroupBox("format", parent)
    b1 = QRadioButton(gb)
    b1.setText(_("CSV"))
    b1.setChecked(True)
    b2 = QRadioButton(gb)
    b2.setText(_("json"))
    vbox.addWidget(b1)
    vbox.addWidget(b2)
        
    hbox = QHBoxLayout()

    directory = config.get('io_dir', unicode(os.path.expanduser('~')))
    path = os.path.join( directory, defaultname )
    filename_e = QLineEdit()
    filename_e.setText(path)

    def func():
        text = unicode(filename_e.text())
        _filter = "*.csv" if text.endswith(".csv") else "*.json" if text.endswith(".json") else None
        p = unicode( QFileDialog.getSaveFileName(None, select_msg, text, _filter))
        if p:
            filename_e.setText(p)

    button = QPushButton(_('File'))
    button.clicked.connect(func)
    hbox.addWidget(button)
    hbox.addWidget(filename_e)
    vbox.addLayout(hbox)

    def set_csv(v):
        text = unicode(filename_e.text())
        text = text.replace(".json",".csv") if v else text.replace(".csv",".json")
        filename_e.setText(text)

    b1.clicked.connect(lambda: set_csv(True))
    b2.clicked.connect(lambda: set_csv(False))

    return vbox, filename_e, b1



class MyTreeWidget(QTreeWidget):
    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.connect(self, SIGNAL('itemActivated(QTreeWidgetItem*, int)'), self.itemactivated)

    def itemactivated(self, item):
        if not item: return
        for i in range(0,self.viewport().height()/5):
            if self.itemAt(QPoint(0,i*5)) == item:
                break
        else:
            return
        for j in range(0,30):
            if self.itemAt(QPoint(0,i*5 + j)) != item:
                break
        self.emit(SIGNAL('customContextMenuRequested(const QPoint&)'), QPoint(50, i*5 + j - 1))




if __name__ == "__main__":
    app = QApplication([])
    t = WaitingDialog(None, 'testing ...', lambda: [time.sleep(1)], lambda x: QMessageBox.information(None, 'done', "done", _('OK')))
    t.start()
    app.exec_()

########NEW FILE########
__FILENAME__ = version_getter
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import threading, httplib, re, socket
import webbrowser
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore

from electrum.i18n import _
from electrum import ELECTRUM_VERSION, print_error

class VersionGetter(threading.Thread):

    def __init__(self, label):
        threading.Thread.__init__(self)
        self.label = label
        
    def run(self):
        try:
            con = httplib.HTTPConnection('electrum.org', 80, timeout=5)
            con.request("GET", "/version")
            res = con.getresponse()
        except socket.error as msg:
            print_error("Could not retrieve version information")
            return
            
        if res.status == 200:
            latest_version = res.read()
            latest_version = latest_version.replace("\n","")
            if(re.match('^\d+(\.\d+)*$', latest_version)):
                self.label.callback(latest_version)

class UpdateLabel(QLabel):
    def __init__(self, config, sb):
        QLabel.__init__(self)
        self.new_version = False
        self.sb = sb
        self.config = config
        self.current_version = ELECTRUM_VERSION
        self.connect(self, QtCore.SIGNAL('new_electrum_version'), self.new_electrum_version)
        # prevent HTTP leaks if a proxy is set
        if self.config.get('proxy'):
            return
        VersionGetter(self).start()

    def callback(self, version):
        self.latest_version = version
        if(self.compare_versions(self.latest_version, self.current_version) == 1):
            latest_seen = self.config.get("last_seen_version",ELECTRUM_VERSION)
            if(self.compare_versions(self.latest_version, latest_seen) == 1):
                self.new_version = True
                self.emit(QtCore.SIGNAL('new_electrum_version'))

    def new_electrum_version(self):
        if self.new_version:
            self.setText(_("New version available") + ": " + self.latest_version)
            self.sb.insertPermanentWidget(1, self)

    def compare_versions(self, version1, version2):
        def normalize(v):
            return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]
        return cmp(normalize(version1), normalize(version2))

    def ignore_this_version(self):
        self.setText("")
        self.config.set_key("last_seen_version", self.latest_version, True)
        QMessageBox.information(self, _("Preference saved"), _("Notifications about this update will not be shown again."))
        self.dialog.done(0)

    def ignore_all_version(self):
        self.setText("")
        self.config.set_key("last_seen_version", "9.9.9", True)
        QMessageBox.information(self, _("Preference saved"), _("No more notifications about version updates will be shown."))
        self.dialog.done(0)
  
    def open_website(self):
        webbrowser.open("http://electrum.org/download.html")
        self.dialog.done(0)

    def mouseReleaseEvent(self, event):
        dialog = QDialog(self)
        dialog.setWindowTitle(_('Electrum update'))
        dialog.setModal(1)

        main_layout = QGridLayout()
        main_layout.addWidget(QLabel(_("A new version of Electrum is available:")+" " + self.latest_version), 0,0,1,3)
        
        ignore_version = QPushButton(_("Ignore this version"))
        ignore_version.clicked.connect(self.ignore_this_version)

        ignore_all_versions = QPushButton(_("Ignore all versions"))
        ignore_all_versions.clicked.connect(self.ignore_all_version)

        open_website = QPushButton(_("Goto download page"))
        open_website.clicked.connect(self.open_website)

        main_layout.addWidget(ignore_version, 1, 0)
        main_layout.addWidget(ignore_all_versions, 1, 1)
        main_layout.addWidget(open_website, 1, 2)

        dialog.setLayout(main_layout)

        self.dialog = dialog
        
        if not dialog.exec_(): return



########NEW FILE########
__FILENAME__ = stdio
from decimal import Decimal
_ = lambda x:x
#from i18n import _
from electrum import mnemonic_encode, WalletStorage, Wallet
from electrum.util import format_satoshis, set_verbosity
from electrum.bitcoin import is_valid
from electrum.network import filter_protocol
import sys, getpass, datetime

# minimal fdisk like gui for console usage
# written by rofl0r, with some bits stolen from the text gui (ncurses)

class ElectrumGui:

    def __init__(self, config, network):
        self.network = network
        self.config = config
        storage = WalletStorage(config)
        if not storage.file_exists:
            print "Wallet not found. try 'electrum create'"
            exit()

	self.done = 0
        self.last_balance = ""

        set_verbosity(False)

        self.str_recipient = ""
        self.str_description = ""
        self.str_amount = ""
        self.str_fee = ""

        self.wallet = Wallet(storage)
        self.wallet.start_threads(network)
        
        self.wallet.network.register_callback('updated', self.updated)
        self.wallet.network.register_callback('connected', self.connected)
        self.wallet.network.register_callback('disconnected', self.disconnected)
        self.wallet.network.register_callback('disconnecting', self.disconnecting)
        self.wallet.network.register_callback('peers', self.peers)
        self.wallet.network.register_callback('banner', self.print_banner)
        self.commands = [_("[h] - displays this help text"), \
                         _("[i] - display transaction history"), \
                         _("[o] - enter payment order"), \
                         _("[p] - print stored payment order"), \
                         _("[s] - send stored payment order"), \
                         _("[r] - show own receipt addresses"), \
                         _("[c] - display contacts"), \
                         _("[b] - print server banner"), \
                         _("[q] - quit") ]
        self.num_commands = len(self.commands)

    def main_command(self):
        self.print_balance()
        c = raw_input("enter command: ")
        if   c == "h" : self.print_commands()
        elif c == "i" : self.print_history()
        elif c == "o" : self.enter_order()
        elif c == "p" : self.print_order()
        elif c == "s" : self.send_order()
        elif c == "r" : self.print_addresses()
        elif c == "c" : self.print_contacts()
        elif c == "b" : self.print_banner()
        elif c == "n" : self.network_dialog()
        elif c == "e" : self.settings_dialog()
        elif c == "q" : self.done = 1
        else: self.print_commands()

    def peers(self):
        print("got peers list:")
        l = filter_protocol(self.wallet.network.get_servers(), 's')
        for s in l:
            print (s)

    def connected(self):
        print ("connected")

    def disconnected(self):
        print ("disconnected")

    def disconnecting(self):
        print ("disconnecting")

    def updated(self):
        s = self.get_balance()
        if s != self.last_balance:
            print(s)
        self.last_balance = s
        return True

    def print_commands(self):
        self.print_list(self.commands, "Available commands")

    def print_history(self):
        width = [20, 40, 14, 14]
        delta = (80 - sum(width) - 4)/3
        format_str = "%"+"%d"%width[0]+"s"+"%"+"%d"%(width[1]+delta)+"s"+"%" \
        + "%d"%(width[2]+delta)+"s"+"%"+"%d"%(width[3]+delta)+"s"
        b = 0 
        messages = []

        for item in self.wallet.get_tx_history():
            tx_hash, confirmations, is_mine, value, fee, balance, timestamp = item
            if confirmations:
                try:
                    time_str = datetime.datetime.fromtimestamp( timestamp).isoformat(' ')[:-3]
                except Exception:
                    time_str = "unknown"
            else:
                time_str = 'pending'

            label, is_default_label = self.wallet.get_label(tx_hash)
            messages.append( format_str%( time_str, label, format_satoshis(value, whitespaces=True), format_satoshis(balance, whitespaces=True) ) )

        self.print_list(messages[::-1], format_str%( _("Date"), _("Description"), _("Amount"), _("Balance")))


    def print_balance(self):
        print(self.get_balance())

    def get_balance(self):
        if self.wallet.network.interface and self.wallet.network.interface.is_connected:
            if not self.wallet.up_to_date:
                msg = _( "Synchronizing..." )
            else: 
                c, u =  self.wallet.get_balance()
                msg = _("Balance")+": %f  "%(Decimal( c ) / 100000000)
                if u: msg += "  [%f unconfirmed]"%(Decimal( u ) / 100000000)
        else:
                msg = _( "Not connected" )
            
        return(msg)


    def print_contacts(self):
        messages = map(lambda addr: "%30s    %30s       "%(addr, self.wallet.labels.get(addr,"")), self.wallet.addressbook)
        self.print_list(messages, "%19s  %25s "%("Address", "Label"))

    def print_addresses(self):
        messages = map(lambda addr: "%30s    %30s       "%(addr, self.wallet.labels.get(addr,"")), self.wallet.addresses())
        self.print_list(messages, "%19s  %25s "%("Address", "Label"))

    def print_order(self):
        print("send order to " + self.str_recipient + ", amount: " + self.str_amount \
              + "\nfee: " + self.str_fee + ", desc: " + self.str_description)

    def enter_order(self):
        self.str_recipient = raw_input("Pay to: ")
        self.str_description = raw_input("Description : ")
        self.str_amount = raw_input("Amount: ")
        self.str_fee = raw_input("Fee: ")

    def send_order(self):
        self.do_send()

    def print_banner(self):
        for i, x in enumerate( self.wallet.network.banner.split('\n') ):
            print( x )

    def print_list(self, list, firstline):
        self.maxpos = len(list)
        if not self.maxpos: return
        print(firstline)
        for i in range(self.maxpos):
            msg = list[i] if i < len(list) else ""
            print(msg)

           
    def main(self,url):
        while self.done == 0: self.main_command()

    def do_send(self):
        if not is_valid(self.str_recipient):
            print(_('Invalid Bitcoin address'))
            return
        try:
            amount = int( Decimal( self.str_amount) * 100000000 )
        except Exception:
            print(_('Invalid Amount'))
            return
        try:
            fee = int( Decimal( self.str_fee) * 100000000 )
        except Exception:
            print(_('Invalid Fee'))
            return

        if self.wallet.use_encryption:
            password = self.password_dialog()
            if not password:
                return
        else:
            password = None

        c = ""
        while c != "y":
            c = raw_input("ok to send (y/n)?")
            if c == "n": return

        try:
            tx = self.wallet.mktx( [(self.str_recipient, amount)], password, fee)
        except Exception as e:
            print(str(e))
            return
            
        if self.str_description: 
            self.wallet.labels[tx.hash()] = self.str_description

        h = self.wallet.send_tx(tx)
        print(_("Please wait..."))
        self.wallet.tx_event.wait()
        status, msg = self.wallet.receive_tx( h, tx )

        if status:
            print(_('Payment sent.'))
            #self.do_clear()
            #self.update_contacts_tab()
        else:
            print(_('Error'))

    def network_dialog(self):
        print("use 'electrum setconfig server/proxy' to change your network settings")
        return True


    def settings_dialog(self):
        print("use 'electrum setconfig' to change your settings")
        return True

    def password_dialog(self):
        return getpass.getpass()
        

#   XXX unused

    def run_receive_tab(self, c):
        #if c == 10:
        #    out = self.run_popup('Address', ["Edit label", "Freeze", "Prioritize"])
        return
            
    def run_contacts_tab(self, c):
        pass
#        if c == 10 and self.wallet.addressbook:
#            out = self.run_popup('Adress', ["Copy", "Pay to", "Edit label", "Delete"]).get('button')
#            address = self.wallet.addressbook[self.pos%len(self.wallet.addressbook)]
#            if out == "Pay to":
#                self.tab = 1
#                self.str_recipient = address 
#                self.pos = 2
#            elif out == "Edit label":
#                s = self.get_string(6 + self.pos, 18)
#                if s:
#                    self.wallet.labels[address] = s

########NEW FILE########
__FILENAME__ = text
import curses, datetime, locale
from decimal import Decimal
_ = lambda x:x
#from i18n import _
from electrum.util import format_satoshis, set_verbosity
from electrum.bitcoin import is_valid

from electrum import Wallet, WalletStorage

import tty, sys


class ElectrumGui:

    def __init__(self, config, network):

        self.config = config
        self.network = network
        storage = WalletStorage(config)
        if not storage.file_exists:
            print "Wallet not found. try 'electrum create'"
            exit()

        self.wallet = Wallet(storage)
        self.wallet.start_threads(self.network)

        locale.setlocale(locale.LC_ALL, '')
        self.encoding = locale.getpreferredencoding()

        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_CYAN)
        self.stdscr.keypad(1)
        self.stdscr.border(0)
        self.maxy, self.maxx = self.stdscr.getmaxyx()
        self.set_cursor(0)
        self.w = curses.newwin(10, 50, 5, 5)

        set_verbosity(False)
        self.tab = 0
        self.pos = 0
        self.popup_pos = 0

        self.str_recipient = ""
        self.str_description = ""
        self.str_amount = ""
        self.str_fee = ""
        self.history = None
       
        if self.network: 
            self.network.register_callback('updated', self.update)
            self.network.register_callback('connected', self.refresh)
            self.network.register_callback('disconnected', self.refresh)
            self.network.register_callback('disconnecting', self.refresh)

        self.tab_names = [_("History"), _("Send"), _("Receive"), _("Contacts"), _("Wall")]
        self.num_tabs = len(self.tab_names)


    def set_cursor(self, x):
        try:
            curses.curs_set(x)
        except Exception:
            pass

    def restore_or_create(self):
        pass

    def verify_seed(self):
        pass
    
    def get_string(self, y, x):
        self.set_cursor(1)
        curses.echo()
        self.stdscr.addstr( y, x, " "*20, curses.A_REVERSE)
        s = self.stdscr.getstr(y,x)
        curses.noecho()
        self.set_cursor(0)
        return s

    def update(self):
        self.update_history()
        if self.tab == 0: 
            self.print_history()
        self.refresh()

    def print_history(self):

        width = [20, 40, 14, 14]
        delta = (self.maxx - sum(width) - 4)/3
        format_str = "%"+"%d"%width[0]+"s"+"%"+"%d"%(width[1]+delta)+"s"+"%"+"%d"%(width[2]+delta)+"s"+"%"+"%d"%(width[3]+delta)+"s"

        if self.history is None:
            self.update_history()

        self.print_list(self.history[::-1], format_str%( _("Date"), _("Description"), _("Amount"), _("Balance")))

    def update_history(self):
        width = [20, 40, 14, 14]
        delta = (self.maxx - sum(width) - 4)/3
        format_str = "%"+"%d"%width[0]+"s"+"%"+"%d"%(width[1]+delta)+"s"+"%"+"%d"%(width[2]+delta)+"s"+"%"+"%d"%(width[3]+delta)+"s"

        b = 0 
        self.history = []

        for item in self.wallet.get_tx_history():
            tx_hash, conf, is_mine, value, fee, balance, timestamp = item
            if conf:
                try:
                    time_str = datetime.datetime.fromtimestamp( timestamp).isoformat(' ')[:-3]
                except Exception:
                    time_str = "------"
            else:
                time_str = 'pending'

            label, is_default_label = self.wallet.get_label(tx_hash)
            self.history.append( format_str%( time_str, label, format_satoshis(value, whitespaces=True), format_satoshis(balance, whitespaces=True) ) )


    def print_balance(self):
        if not self.network:
            msg = _("Offline")
        elif self.network.interface and self.network.interface.is_connected:
            if not self.wallet.up_to_date:
                msg = _("Synchronizing...")
            else: 
                c, u =  self.wallet.get_balance()
                msg = _("Balance")+": %f  "%(Decimal( c ) / 100000000)
                if u: msg += "  [%f unconfirmed]"%(Decimal( u ) / 100000000)
        else:
            msg = _("Not connected")
            
        self.stdscr.addstr( self.maxy -1, 3, msg)

        for i in range(self.num_tabs):
            self.stdscr.addstr( 0, 2 + 2*i + len(''.join(self.tab_names[0:i])), ' '+self.tab_names[i]+' ', curses.A_BOLD if self.tab == i else 0)
            
        self.stdscr.addstr( self.maxy -1, self.maxx-30, ' '.join([_("Settings"), _("Network"), _("Quit")]))


    def print_contacts(self):
        messages = map(lambda addr: "%30s    %30s       "%(addr, self.wallet.labels.get(addr,"")), self.wallet.addressbook)
        self.print_list(messages, "%19s  %25s "%("Address", "Label"))

    def print_receive(self):
        fmt = "%-35s  %-30s"
        messages = map(lambda addr: fmt % (addr, self.wallet.labels.get(addr,"")), self.wallet.addresses())
        self.print_list(messages,   fmt % ("Address", "Label"))

    def print_edit_line(self, y, label, text, index, size):
        text += " "*(size - len(text) )
        self.stdscr.addstr( y, 2, label)
        self.stdscr.addstr( y, 15, text, curses.A_REVERSE if self.pos%6==index else curses.color_pair(1))

    def print_send_tab(self):
        self.stdscr.clear()
        self.print_edit_line(3, _("Pay to"), self.str_recipient, 0, 40)
        self.print_edit_line(5, _("Description"), self.str_description, 1, 40)
        self.print_edit_line(7, _("Amount"), self.str_amount, 2, 15)
        self.print_edit_line(9, _("Fee"), self.str_fee, 3, 15)
        self.stdscr.addstr( 12, 15, _("[Send]"), curses.A_REVERSE if self.pos%6==4 else curses.color_pair(2))
        self.stdscr.addstr( 12, 25, _("[Clear]"), curses.A_REVERSE if self.pos%6==5 else curses.color_pair(2))

    def print_banner(self):
        if self.network:
            self.print_list( self.network.banner.split('\n'))

    def print_list(self, list, firstline = None):
        self.maxpos = len(list)
        if not self.maxpos: return
        if firstline:
            firstline += " "*(self.maxx -2 - len(firstline))
            self.stdscr.addstr( 1, 1, firstline )
        for i in range(self.maxy-4):
            msg = list[i] if i < len(list) else ""
            msg += " "*(self.maxx - 2 - len(msg))
            m = msg[0:self.maxx - 2]
            m = m.encode(self.encoding)
            self.stdscr.addstr( i+2, 1, m, curses.A_REVERSE if i == (self.pos % self.maxpos) else 0)

    def refresh(self):
        if self.tab == -1: return
        self.stdscr.border(0)
        self.print_balance()
        self.stdscr.refresh()

    def main_command(self):
        c = self.stdscr.getch()
        print c
        if   c == curses.KEY_RIGHT: self.tab = (self.tab + 1)%self.num_tabs
        elif c == curses.KEY_LEFT: self.tab = (self.tab - 1)%self.num_tabs
        elif c == curses.KEY_DOWN: self.pos +=1
        elif c == curses.KEY_UP: self.pos -= 1
        elif c == 9: self.pos +=1 # tab
        elif curses.unctrl(c) in ['^W', '^C', '^X', '^Q']: self.tab = -1
        elif curses.unctrl(c) in ['^N']: self.network_dialog()
        elif curses.unctrl(c) == '^S': self.settings_dialog()
        else: return c
        if self.pos<0: self.pos=0
        if self.pos>=self.maxpos: self.pos=self.maxpos - 1

    def run_tab(self, i, print_func, exec_func):
        while self.tab == i:
            self.stdscr.clear()
            print_func()
            self.refresh()
            c = self.main_command()
            if c: exec_func(c)


    def run_history_tab(self, c):
        if c == 10:
            out = self.run_popup('',["blah","foo"])
            

    def edit_str(self, target, c, is_num=False):
        # detect backspace
        if c in [8, 127, 263] and target:
            target = target[:-1]
        elif not is_num or curses.unctrl(c) in '0123456789.':
            target += curses.unctrl(c)
        return target


    def run_send_tab(self, c):
        if self.pos%6 == 0:
            self.str_recipient = self.edit_str(self.str_recipient, c)
        if self.pos%6 == 1:
            self.str_description = self.edit_str(self.str_description, c)
        if self.pos%6 == 2:
            self.str_amount = self.edit_str(self.str_amount, c, True)
        elif self.pos%6 == 3:
            self.str_fee = self.edit_str(self.str_fee, c, True)
        elif self.pos%6==4:
            if c == 10: self.do_send()
        elif self.pos%6==5:
            if c == 10: self.do_clear()

            
    def run_receive_tab(self, c):
        if c == 10:
            out = self.run_popup('Address', ["Edit label", "Freeze", "Prioritize"])
            
    def run_contacts_tab(self, c):
        if c == 10 and self.wallet.addressbook:
            out = self.run_popup('Adress', ["Copy", "Pay to", "Edit label", "Delete"]).get('button')
            address = self.wallet.addressbook[self.pos%len(self.wallet.addressbook)]
            if out == "Pay to":
                self.tab = 1
                self.str_recipient = address 
                self.pos = 2
            elif out == "Edit label":
                s = self.get_string(6 + self.pos, 18)
                if s:
                    self.wallet.labels[address] = s
            
    def run_banner_tab(self, c):
        self.show_message(repr(c))
        pass

    def main(self,url):

        tty.setraw(sys.stdin)
        while self.tab != -1:
            self.run_tab(0, self.print_history, self.run_history_tab)
            self.run_tab(1, self.print_send_tab, self.run_send_tab)
            self.run_tab(2, self.print_receive, self.run_receive_tab)
            self.run_tab(3, self.print_contacts, self.run_contacts_tab)
            self.run_tab(4, self.print_banner, self.run_banner_tab)

        tty.setcbreak(sys.stdin)
        curses.nocbreak()
        self.stdscr.keypad(0)
        curses.echo()
        curses.endwin()


    def do_clear(self):
        self.str_amount = ''
        self.str_recipient = ''
        self.str_fee = ''
        self.str_description = ''

    def do_send(self):
        if not is_valid(self.str_recipient):
            self.show_message(_('Invalid Bitcoin address'))
            return
        try:
            amount = int( Decimal( self.str_amount) * 100000000 )
        except Exception:
            self.show_message(_('Invalid Amount'))
            return
        try:
            fee = int( Decimal( self.str_fee) * 100000000 )
        except Exception:
            self.show_message(_('Invalid Fee'))
            return

        if self.wallet.use_encryption:
            password = self.password_dialog()
            if not password:
                return
        else:
            password = None

        try:
            tx = self.wallet.mktx( [(self.str_recipient, amount)], password, fee)
        except Exception as e:
            self.show_message(str(e))
            return
            
        if self.str_description: 
            self.wallet.labels[tx.hash()] = self.str_description

        h = self.wallet.send_tx(tx)
        self.show_message(_("Please wait..."), getchar=False)
        self.wallet.tx_event.wait()
        status, msg = self.wallet.receive_tx( h, tx )

        if status:
            self.show_message(_('Payment sent.'))
            self.do_clear()
            #self.update_contacts_tab()
        else:
            self.show_message(_('Error'))


    def show_message(self, message, getchar = True):
        w = self.w
        w.clear()
        w.border(0)
        for i, line in enumerate(message.split('\n')):
            w.addstr(2+i,2,line)
        w.refresh()
        if getchar: c = self.stdscr.getch()


    def run_popup(self, title, items):
        return self.run_dialog(title, map(lambda x: {'type':'button','label':x}, items), interval=1, y_pos = self.pos+3)


    def network_dialog(self):
        if not self.network: return
        auto_connect = self.network.config.get('auto_cycle')
        host, port, protocol = self.network.default_server.split(':')
        srv = 'auto-connect' if auto_connect else self.network.default_server

        out = self.run_dialog('Network', [
            {'label':'server', 'type':'str', 'value':srv},
            {'label':'proxy', 'type':'str', 'value':self.config.get('proxy', '')},
            ], buttons = 1)
        if out:
            if out.get('server'):
                server = out.get('server')
                auto_connect = server == 'auto-connect'
                if not auto_connect:
                    try:
                        host, port, protocol = server.split(':')
                    except Exception:
                        self.show_message("Error:" + server + "\nIn doubt, type \"auto-connect\"")
                        return False

                if out.get('proxy'):
                    proxy = self.parse_proxy_options(out.get('proxy'))
                else:
                    proxy = None

                self.network.set_parameters(host, port, protocol, proxy, auto_connect)
                


    def settings_dialog(self):
        out = self.run_dialog('Settings', [
            {'label':'Default GUI', 'type':'list', 'choices':['classic','lite','gtk','text'], 'value':self.config.get('gui')},
            {'label':'Default fee', 'type':'satoshis', 'value': format_satoshis(self.wallet.fee).strip() }
            ], buttons = 1)
        if out:
            if out.get('Default GUI'):
                self.config.set_key('gui', out['Default GUI'], True)
            if out.get('Default fee'):
                fee = int ( Decimal( out['Default fee']) *10000000 )
                self.config.set_key('fee_per_kb', fee, True)


    def password_dialog(self):
        out = self.run_dialog('Password', [
            {'label':'Password', 'type':'password', 'value':''}
            ], buttons = 1)
        return out.get('Password')
        

    def run_dialog(self, title, items, interval=2, buttons=None, y_pos=3):
        self.popup_pos = 0
        
        self.w = curses.newwin( 5 + len(items)*interval + (2 if buttons else 0), 50, y_pos, 5)
        w = self.w
        out = {}
        while True:
            w.clear()
            w.border(0)
            w.addstr( 0, 2, title)

            num = len(items)

            numpos = num
            if buttons: numpos += 2

            for i in range(num):
                item = items[i]
                label = item.get('label')
                if item.get('type') == 'list':
                    value = item.get('value','')
                elif item.get('type') == 'satoshis':
                    value = item.get('value','')
                elif item.get('type') == 'str':
                    value = item.get('value','')
                elif item.get('type') == 'password':
                    value = '*'*len(item.get('value',''))
                else:
                    value = ''

                if len(value)<20: value += ' '*(20-len(value))

                if item.has_key('value'):
                    w.addstr( 2+interval*i, 2, label)
                    w.addstr( 2+interval*i, 15, value, curses.A_REVERSE if self.popup_pos%numpos==i else curses.color_pair(1) )
                else:
                    w.addstr( 2+interval*i, 2, label, curses.A_REVERSE if self.popup_pos%numpos==i else 0)

            if buttons:
                w.addstr( 5+interval*i, 10, "[  ok  ]",     curses.A_REVERSE if self.popup_pos%numpos==(numpos-2) else curses.color_pair(2))
                w.addstr( 5+interval*i, 25, "[cancel]", curses.A_REVERSE if self.popup_pos%numpos==(numpos-1) else curses.color_pair(2))
                
            w.refresh()

            c = self.stdscr.getch()
            if c in [ord('q'), 27]: break
            elif c in [curses.KEY_LEFT, curses.KEY_UP]: self.popup_pos -= 1
            elif c in [curses.KEY_RIGHT, curses.KEY_DOWN]: self.popup_pos +=1
            else:
                i = self.popup_pos%numpos
                if buttons and c==10:
                    if i == numpos-2:
                        return out
                    elif i == numpos -1:
                        return {}

                item = items[i]
                _type = item.get('type')

                if _type == 'str':
                    item['value'] = self.edit_str(item['value'], c)
                    out[item.get('label')] = item.get('value')

                elif _type == 'password':
                    item['value'] = self.edit_str(item['value'], c)
                    out[item.get('label')] = item ['value']

                elif _type == 'satoshis':
                    item['value'] = self.edit_str(item['value'], c, True)
                    out[item.get('label')] = item.get('value')

                elif _type == 'list':
                    choices = item.get('choices')
                    try:
                        j = choices.index(item.get('value'))
                    except Exception:
                        j = 0
                    new_choice = choices[(j + 1)% len(choices)]
                    item['value'] = new_choice
                    out[item.get('label')] = item.get('value')
                    
                elif _type == 'button':
                    out['button'] = item.get('label')
                    break

        return out


########NEW FILE########
__FILENAME__ = account
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2013 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from bitcoin import *
from i18n import _
from transaction import Transaction



class Account(object):
    def __init__(self, v):
        self.addresses = v.get('0', [])
        self.change = v.get('1', [])

    def dump(self):
        return {'0':self.addresses, '1':self.change}

    def get_addresses(self, for_change):
        return self.change[:] if for_change else self.addresses[:]

    def create_new_address(self, for_change):
        addresses = self.change if for_change else self.addresses
        n = len(addresses)
        address = self.get_address( for_change, n)
        addresses.append(address)
        print address
        return address

    def get_address(self, for_change, n):
        pass
        
    def get_pubkeys(self, sequence):
        return [ self.get_pubkey( *sequence )]

    def has_change(self):
        return True

    def get_name(self, k):
        return _('Main account')

    def get_keyID(self, *sequence):
        pass

    def redeem_script(self, *sequence):
        pass


class PendingAccount(Account):
    def __init__(self, v):
        self.addresses = [ v['pending'] ]
        self.change = []

    def has_change(self):
        return False

    def dump(self):
        return {'pending':self.addresses[0]}

    def get_name(self, k):
        return _('Pending account')


class ImportedAccount(Account):
    def __init__(self, d):
        self.keypairs = d['imported']

    def get_addresses(self, for_change):
        return [] if for_change else sorted(self.keypairs.keys())

    def get_pubkey(self, *sequence):
        for_change, i = sequence
        assert for_change == 0
        addr = self.get_addresses(0)[i]
        return self.keypairs[addr][i][0]

    def get_private_key(self, sequence, wallet, password):
        from wallet import pw_decode
        for_change, i = sequence
        assert for_change == 0
        address = self.get_addresses(0)[i]
        pk = pw_decode(self.keypairs[address][1], password)
        # this checks the password
        assert address == address_from_private_key(pk)
        return [pk]

    def has_change(self):
        return False

    def add(self, address, pubkey, privkey, password):
        from wallet import pw_encode
        self.keypairs[address] = (pubkey, pw_encode(privkey, password ))

    def remove(self, address):
        self.keypairs.pop(address)

    def dump(self):
        return {'imported':self.keypairs}

    def get_name(self, k):
        return _('Imported keys')


    def update_password(self, old_password, new_password):
        for k, v in self.keypairs.items():
            pubkey, a = v
            b = pw_decode(a, old_password)
            c = pw_encode(b, new_password)
            self.keypairs[k] = (pubkey, c)


class OldAccount(Account):
    """  Privatekey(type,n) = Master_private_key + H(n|S|type)  """

    def __init__(self, v):
        self.addresses = v.get(0, [])
        self.change = v.get(1, [])
        self.mpk = v['mpk'].decode('hex')

    def dump(self):
        return {0:self.addresses, 1:self.change}

    @classmethod
    def mpk_from_seed(klass, seed):
        curve = SECP256k1
        secexp = klass.stretch_key(seed)
        master_private_key = ecdsa.SigningKey.from_secret_exponent( secexp, curve = SECP256k1 )
        master_public_key = master_private_key.get_verifying_key().to_string().encode('hex')
        return master_public_key

    @classmethod
    def stretch_key(self,seed):
        oldseed = seed
        for i in range(100000):
            seed = hashlib.sha256(seed + oldseed).digest()
        return string_to_number( seed )

    def get_sequence(self, for_change, n):
        return string_to_number( Hash( "%d:%d:"%(n,for_change) + self.mpk ) )

    def get_address(self, for_change, n):
        pubkey = self.get_pubkey(for_change, n)
        address = public_key_to_bc_address( pubkey.decode('hex') )
        return address

    def get_pubkey(self, for_change, n):
        curve = SECP256k1
        mpk = self.mpk
        z = self.get_sequence(for_change, n)
        master_public_key = ecdsa.VerifyingKey.from_string( mpk, curve = SECP256k1 )
        pubkey_point = master_public_key.pubkey.point + z*curve.generator
        public_key2 = ecdsa.VerifyingKey.from_public_point( pubkey_point, curve = SECP256k1 )
        return '04' + public_key2.to_string().encode('hex')

    def get_private_key_from_stretched_exponent(self, for_change, n, secexp):
        order = generator_secp256k1.order()
        secexp = ( secexp + self.get_sequence(for_change, n) ) % order
        pk = number_to_string( secexp, generator_secp256k1.order() )
        compressed = False
        return SecretToASecret( pk, compressed )
        

    def get_private_key(self, sequence, wallet, password):
        seed = wallet.get_seed(password)
        self.check_seed(seed)
        for_change, n = sequence
        secexp = self.stretch_key(seed)
        pk = self.get_private_key_from_stretched_exponent(for_change, n, secexp)
        return [pk]


    def check_seed(self, seed):
        curve = SECP256k1
        secexp = self.stretch_key(seed)
        master_private_key = ecdsa.SigningKey.from_secret_exponent( secexp, curve = SECP256k1 )
        master_public_key = master_private_key.get_verifying_key().to_string()
        if master_public_key != self.mpk:
            print_error('invalid password (mpk)', self.mpk.encode('hex'), master_public_key.encode('hex'))
            raise Exception('Invalid password')
        return True

    def redeem_script(self, sequence):
        return None

    def get_master_pubkeys(self):
        return [self.mpk.encode('hex')]

    def get_type(self):
        return _('Old Electrum format')

    def get_keyID(self, sequence):
        a, b = sequence
        return 'old(%s,%d,%d)'%(self.mpk.encode('hex'),a,b)



class BIP32_Account(Account):

    def __init__(self, v):
        Account.__init__(self, v)
        self.xpub = v['xpub']

    def dump(self):
        d = Account.dump(self)
        d['xpub'] = self.xpub
        return d

    def get_address(self, for_change, n):
        pubkey = self.get_pubkey(for_change, n)
        address = public_key_to_bc_address( pubkey.decode('hex') )
        return address

    def first_address(self):
        return self.get_address(0,0)

    def get_master_pubkeys(self):
        return [self.xpub]

    def get_pubkey_from_x(self, xpub, for_change, n):
        _, _, _, c, cK = deserialize_xkey(xpub)
        for i in [for_change, n]:
            cK, c = CKD_pub(cK, c, i)
        return cK.encode('hex')

    def get_pubkeys(self, sequence):
        return sorted(map(lambda x: self.get_pubkey_from_x(x, *sequence), self.get_master_pubkeys()))

    def get_pubkey(self, for_change, n):
        return self.get_pubkeys((for_change, n))[0]


    def get_private_key(self, sequence, wallet, password):
        out = []
        xpubs = self.get_master_pubkeys()
        roots = [k for k, v in wallet.master_public_keys.iteritems() if v in xpubs]
        for root in roots:
            xpriv = wallet.get_master_private_key(root, password)
            if not xpriv:
                continue
            _, _, _, c, k = deserialize_xkey(xpriv)
            pk = bip32_private_key( sequence, k, c )
            out.append(pk)
                    
        return out


    def redeem_script(self, sequence):
        return None

    def get_type(self):
        return _('Standard 1 of 1')

    def get_keyID(self, sequence):
        s = '/' + '/'.join( map(lambda x:str(x), sequence) )
        return '&'.join( map(lambda x: 'bip32(%s,%s)'%(x, s), self.get_master_pubkeys() ) )

    def get_name(self, k):
        name = "Unnamed account"
        m = re.match("m/(\d+)'", k)
        if m:
            num = m.group(1)
            if num == '0':
                name = "Main account"
            else:
                name = "Account %s"%num
                    
        return name



class BIP32_Account_2of2(BIP32_Account):

    def __init__(self, v):
        BIP32_Account.__init__(self, v)
        self.xpub2 = v['xpub2']

    def dump(self):
        d = BIP32_Account.dump(self)
        d['xpub2'] = self.xpub2
        return d

    def redeem_script(self, sequence):
        pubkeys = self.get_pubkeys(sequence)
        return Transaction.multisig_script(pubkeys, 2)

    def get_address(self, for_change, n):
        address = hash_160_to_bc_address(hash_160(self.redeem_script((for_change, n)).decode('hex')), 5)
        return address

    def get_master_pubkeys(self):
        return [self.xpub, self.xpub2]

    def get_type(self):
        return _('Multisig 2 of 2')


class BIP32_Account_2of3(BIP32_Account_2of2):

    def __init__(self, v):
        BIP32_Account_2of2.__init__(self, v)
        self.xpub3 = v['xpub3']

    def dump(self):
        d = BIP32_Account_2of2.dump(self)
        d['xpub3'] = self.xpub3
        return d

    def get_master_pubkeys(self):
        return [self.xpub, self.xpub2, self.xpub3]

    def get_type(self):
        return _('Multisig 2 of 3')





########NEW FILE########
__FILENAME__ = bitcoin
# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import hashlib, base64, ecdsa, re
import hmac
import aes
from util import print_error

# AES encryption
EncodeAES = lambda secret, s: base64.b64encode(aes.encryptData(secret,s))
DecodeAES = lambda secret, e: aes.decryptData(secret, base64.b64decode(e))

def pw_encode(s, password):
    if password:
        secret = Hash(password)
        return EncodeAES(secret, s.encode("utf8"))
    else:
        return s

def pw_decode(s, password):
    if password is not None:
        secret = Hash(password)
        try:
            d = DecodeAES(secret, s).decode("utf8")
        except Exception:
            raise Exception('Invalid password')
        return d
    else:
        return s





def rev_hex(s):
    return s.decode('hex')[::-1].encode('hex')

def int_to_hex(i, length=1):
    s = hex(i)[2:].rstrip('L')
    s = "0"*(2*length - len(s)) + s
    return rev_hex(s)

def var_int(i):
    # https://en.bitcoin.it/wiki/Protocol_specification#Variable_length_integer
    if i<0xfd:
        return int_to_hex(i)
    elif i<=0xffff:
        return "fd"+int_to_hex(i,2)
    elif i<=0xffffffff:
        return "fe"+int_to_hex(i,4)
    else:
        return "ff"+int_to_hex(i,8)

def op_push(i):
    if i<0x4c:
        return int_to_hex(i)
    elif i<0xff:
        return '4c' + int_to_hex(i)
    elif i<0xffff:
        return '4d' + int_to_hex(i,2)
    else:
        return '4e' + int_to_hex(i,4)
    


def sha256(x):
    return hashlib.sha256(x).digest()

def Hash(x):
    if type(x) is unicode: x=x.encode('utf-8')
    return sha256(sha256(x))

hash_encode = lambda x: x[::-1].encode('hex')
hash_decode = lambda x: x.decode('hex')[::-1]
hmac_sha_512 = lambda x,y: hmac.new(x, y, hashlib.sha512).digest()

def mnemonic_to_seed(mnemonic, passphrase):
    from pbkdf2 import PBKDF2
    import hmac
    PBKDF2_ROUNDS = 2048
    return PBKDF2(mnemonic, 'mnemonic' + passphrase, iterations = PBKDF2_ROUNDS, macmodule = hmac, digestmodule = hashlib.sha512).read(64)

from version import SEED_PREFIX
is_new_seed = lambda x: hmac_sha_512("Seed version", x.encode('utf8')).encode('hex')[0:2].startswith(SEED_PREFIX)

def is_old_seed(seed):
    import mnemonic
    words = seed.strip().split()
    try:
        mnemonic.mn_decode(words)
        uses_electrum_words = True
    except Exception:
        uses_electrum_words = False

    try:
        seed.decode('hex')
        is_hex = (len(seed) == 32)
    except Exception:
        is_hex = False
         
    return is_hex or (uses_electrum_words and len(words) == 12)


# pywallet openssl private key implementation

def i2d_ECPrivateKey(pkey, compressed=False):
    if compressed:
        key = '3081d30201010420' + \
              '%064x' % pkey.secret + \
              'a081a53081a2020101302c06072a8648ce3d0101022100' + \
              '%064x' % _p + \
              '3006040100040107042102' + \
              '%064x' % _Gx + \
              '022100' + \
              '%064x' % _r + \
              '020101a124032200'
    else:
        key = '308201130201010420' + \
              '%064x' % pkey.secret + \
              'a081a53081a2020101302c06072a8648ce3d0101022100' + \
              '%064x' % _p + \
              '3006040100040107044104' + \
              '%064x' % _Gx + \
              '%064x' % _Gy + \
              '022100' + \
              '%064x' % _r + \
              '020101a144034200'
        
    return key.decode('hex') + i2o_ECPublicKey(pkey.pubkey, compressed)
    
def i2o_ECPublicKey(pubkey, compressed=False):
    # public keys are 65 bytes long (520 bits)
    # 0x04 + 32-byte X-coordinate + 32-byte Y-coordinate
    # 0x00 = point at infinity, 0x02 and 0x03 = compressed, 0x04 = uncompressed
    # compressed keys: <sign> <x> where <sign> is 0x02 if y is even and 0x03 if y is odd
    if compressed:
        if pubkey.point.y() & 1:
            key = '03' + '%064x' % pubkey.point.x()
        else:
            key = '02' + '%064x' % pubkey.point.x()
    else:
        key = '04' + \
              '%064x' % pubkey.point.x() + \
              '%064x' % pubkey.point.y()
            
    return key.decode('hex')
            
# end pywallet openssl private key implementation

                                                
            
############ functions from pywallet ##################### 

def hash_160(public_key):
    try:
        md = hashlib.new('ripemd160')
        md.update(sha256(public_key))
        return md.digest()
    except Exception:
        import ripemd
        md = ripemd.new(sha256(public_key))
        return md.digest()


def public_key_to_bc_address(public_key):
    h160 = hash_160(public_key)
    return hash_160_to_bc_address(h160)

def hash_160_to_bc_address(h160, addrtype = 0):
    vh160 = chr(addrtype) + h160
    h = Hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)

def bc_address_to_hash_160(addr):
    bytes = b58decode(addr, 25)
    return ord(bytes[0]), bytes[1:21]


__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)

def b58encode(v):
    """ encode v, which is a string of bytes, to base58."""

    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += (256**i) * ord(c)

    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == '\0': nPad += 1
        else: break

    return (__b58chars[0]*nPad) + result

def b58decode(v, length):
    """ decode v into a string of len bytes."""
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)

    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]: nPad += 1
        else: break

    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None

    return result


def EncodeBase58Check(vchIn):
    hash = Hash(vchIn)
    return b58encode(vchIn + hash[0:4])

def DecodeBase58Check(psz):
    vchRet = b58decode(psz, None)
    key = vchRet[0:-4]
    csum = vchRet[-4:]
    hash = Hash(key)
    cs32 = hash[0:4]
    if cs32 != csum:
        return None
    else:
        return key

def PrivKeyToSecret(privkey):
    return privkey[9:9+32]

def SecretToASecret(secret, compressed=False, addrtype=0):
    vchIn = chr((addrtype+128)&255) + secret
    if compressed: vchIn += '\01'
    return EncodeBase58Check(vchIn)

def ASecretToSecret(key, addrtype=0):
    vch = DecodeBase58Check(key)
    if vch and vch[0] == chr((addrtype+128)&255):
        return vch[1:]
    else:
        return False

def regenerate_key(sec):
    b = ASecretToSecret(sec)
    if not b:
        return False
    b = b[0:32]
    return EC_KEY(b)

def GetPubKey(pubkey, compressed=False):
    return i2o_ECPublicKey(pubkey, compressed)

def GetPrivKey(pkey, compressed=False):
    return i2d_ECPrivateKey(pkey, compressed)

def GetSecret(pkey):
    return ('%064x' % pkey.secret).decode('hex')

def is_compressed(sec):
    b = ASecretToSecret(sec)
    return len(b) == 33


def public_key_from_private_key(sec):
    # rebuild public key from private key, compressed or uncompressed
    pkey = regenerate_key(sec)
    assert pkey
    compressed = is_compressed(sec)
    public_key = GetPubKey(pkey.pubkey, compressed)
    return public_key.encode('hex')


def address_from_private_key(sec):
    public_key = public_key_from_private_key(sec)
    address = public_key_to_bc_address(public_key.decode('hex'))
    return address


def is_valid(addr):
    return is_address(addr)


def is_address(addr):
    ADDRESS_RE = re.compile('[1-9A-HJ-NP-Za-km-z]{26,}\\Z')
    if not ADDRESS_RE.match(addr): return False
    try:
        addrtype, h = bc_address_to_hash_160(addr)
    except Exception:
        return False
    return addr == hash_160_to_bc_address(h, addrtype)


def is_private_key(key):
    try:
        k = ASecretToSecret(key) 
        return k is not False
    except:
        return False


########### end pywallet functions #######################

try:
    from ecdsa.ecdsa import curve_secp256k1, generator_secp256k1
except Exception:
    print "cannot import ecdsa.curve_secp256k1. You probably need to upgrade ecdsa.\nTry: sudo pip install --upgrade ecdsa"
    exit()

from ecdsa.curves import SECP256k1
from ecdsa.ellipticcurve import Point
from ecdsa.util import string_to_number, number_to_string

def msg_magic(message):
    varint = var_int(len(message))
    encoded_varint = "".join([chr(int(varint[i:i+2], 16)) for i in xrange(0, len(varint), 2)])
    return "\x18Bitcoin Signed Message:\n" + encoded_varint + message


def verify_message(address, signature, message):
    try:
        EC_KEY.verify_message(address, signature, message)
        return True
    except Exception as e:
        print_error("Verification error: {0}".format(e))
        return False


def encrypt_message(message, pubkey):
    return EC_KEY.encrypt_message(message, pubkey.decode('hex'))


def chunks(l, n):
    return [l[i:i+n] for i in xrange(0, len(l), n)]


def ECC_YfromX(x,curved=curve_secp256k1, odd=True):
    _p = curved.p()
    _a = curved.a()
    _b = curved.b()
    for offset in range(128):
        Mx = x + offset
        My2 = pow(Mx, 3, _p) + _a * pow(Mx, 2, _p) + _b % _p
        My = pow(My2, (_p+1)/4, _p )

        if curved.contains_point(Mx,My):
            if odd == bool(My&1):
                return [My,offset]
            return [_p-My,offset]
    raise Exception('ECC_YfromX: No Y found')


def negative_point(P):
    return Point( P.curve(), P.x(), -P.y(), P.order() )


def point_to_ser(P, comp=True ):
    if comp:
        return ( ('%02x'%(2+(P.y()&1)))+('%064x'%P.x()) ).decode('hex')
    return ( '04'+('%064x'%P.x())+('%064x'%P.y()) ).decode('hex')


def ser_to_point(Aser):
    curve = curve_secp256k1
    generator = generator_secp256k1
    _r  = generator.order()
    assert Aser[0] in ['\x02','\x03','\x04']
    if Aser[0] == '\x04':
        return Point( curve, string_to_number(Aser[1:33]), string_to_number(Aser[33:]), _r )
    Mx = string_to_number(Aser[1:])
    return Point( curve, Mx, ECC_YfromX(Mx, curve, Aser[0]=='\x03')[0], _r )



class EC_KEY(object):
    def __init__( self, k ):
        secret = string_to_number(k)
        self.pubkey = ecdsa.ecdsa.Public_key( generator_secp256k1, generator_secp256k1 * secret )
        self.privkey = ecdsa.ecdsa.Private_key( self.pubkey, secret )
        self.secret = secret

    def get_public_key(self, compressed=True):
        return point_to_ser(self.pubkey.point, compressed).encode('hex')

    def sign_message(self, message, compressed, address):
        private_key = ecdsa.SigningKey.from_secret_exponent( self.secret, curve = SECP256k1 )
        public_key = private_key.get_verifying_key()
        signature = private_key.sign_digest_deterministic( Hash( msg_magic(message) ), hashfunc=hashlib.sha256, sigencode = ecdsa.util.sigencode_string )
        assert public_key.verify_digest( signature, Hash( msg_magic(message) ), sigdecode = ecdsa.util.sigdecode_string)
        for i in range(4):
            sig = base64.b64encode( chr(27 + i + (4 if compressed else 0)) + signature )
            try:
                self.verify_message( address, sig, message)
                return sig
            except Exception:
                continue
        else:
            raise Exception("error: cannot sign message")


    @classmethod
    def verify_message(self, address, signature, message):
        """ See http://www.secg.org/download/aid-780/sec1-v2.pdf for the math """
        from ecdsa import numbertheory, util
        import msqr
        curve = curve_secp256k1
        G = generator_secp256k1
        order = G.order()
        # extract r,s from signature
        sig = base64.b64decode(signature)
        if len(sig) != 65: raise Exception("Wrong encoding")
        r,s = util.sigdecode_string(sig[1:], order)
        nV = ord(sig[0])
        if nV < 27 or nV >= 35:
            raise Exception("Bad encoding")
        if nV >= 31:
            compressed = True
            nV -= 4
        else:
            compressed = False

        recid = nV - 27
        # 1.1
        x = r + (recid/2) * order
        # 1.3
        alpha = ( x * x * x  + curve.a() * x + curve.b() ) % curve.p()
        beta = msqr.modular_sqrt(alpha, curve.p())
        y = beta if (beta - recid) % 2 == 0 else curve.p() - beta
        # 1.4 the constructor checks that nR is at infinity
        R = Point(curve, x, y, order)
        # 1.5 compute e from message:
        h = Hash( msg_magic(message) )
        e = string_to_number(h)
        minus_e = -e % order
        # 1.6 compute Q = r^-1 (sR - eG)
        inv_r = numbertheory.inverse_mod(r,order)
        Q = inv_r * ( s * R + minus_e * G )
        public_key = ecdsa.VerifyingKey.from_public_point( Q, curve = SECP256k1 )
        # check that Q is the public key
        public_key.verify_digest( sig[1:], h, sigdecode = ecdsa.util.sigdecode_string)
        # check that we get the original signing address
        addr = public_key_to_bc_address( point_to_ser(public_key.pubkey.point, compressed) )
        if address != addr:
            raise Exception("Bad signature")


    # ecies encryption/decryption methods; aes-256-cbc is used as the cipher; hmac-sha256 is used as the mac

    @classmethod
    def encrypt_message(self, message, pubkey):
        
        pk = ser_to_point(pubkey)
        if not ecdsa.ecdsa.point_is_valid(generator_secp256k1, pk.x(), pk.y()):
            raise Exception('invalid pubkey')
        
        ephemeral_exponent = number_to_string(ecdsa.util.randrange(pow(2,256)), generator_secp256k1.order())
        ephemeral = EC_KEY(ephemeral_exponent)
        
        ecdh_key = (pk * ephemeral.privkey.secret_multiplier).x()
        ecdh_key = ('%064x' % ecdh_key).decode('hex')
        key = hashlib.sha512(ecdh_key).digest()
        key_e, key_m = key[:32], key[32:]
        
        iv_ciphertext = aes.encryptData(key_e, message)

        ephemeral_pubkey = ephemeral.get_public_key(compressed=True).decode('hex')
        encrypted = 'BIE1' + ephemeral_pubkey + iv_ciphertext
        mac = hmac.new(key_m, encrypted, hashlib.sha256).digest()

        return base64.b64encode(encrypted + mac)


    def decrypt_message(self, encrypted):
        
        encrypted = base64.b64decode(encrypted)
        
        if len(encrypted) < 85:
            raise Exception('invalid ciphertext: length')
        
        magic = encrypted[:4]
        ephemeral_pubkey = encrypted[4:37]
        iv_ciphertext = encrypted[37:-32]
        mac = encrypted[-32:]
        
        if magic != 'BIE1':
            raise Exception('invalid ciphertext: invalid magic bytes')
        
        try:
            ephemeral_pubkey = ser_to_point(ephemeral_pubkey)
        except AssertionError, e:
            raise Exception('invalid ciphertext: invalid ephemeral pubkey')

        if not ecdsa.ecdsa.point_is_valid(generator_secp256k1, ephemeral_pubkey.x(), ephemeral_pubkey.y()):
            raise Exception('invalid ciphertext: invalid ephemeral pubkey')

        ecdh_key = (ephemeral_pubkey * self.privkey.secret_multiplier).x()
        ecdh_key = ('%064x' % ecdh_key).decode('hex')
        key = hashlib.sha512(ecdh_key).digest()
        key_e, key_m = key[:32], key[32:]
        if mac != hmac.new(key_m, encrypted[:-32], hashlib.sha256).digest():
            raise Exception('invalid ciphertext: invalid mac')

        return aes.decryptData(key_e, iv_ciphertext)


###################################### BIP32 ##############################

random_seed = lambda n: "%032x"%ecdsa.util.randrange( pow(2,n) )
BIP32_PRIME = 0x80000000


def get_pubkeys_from_secret(secret):
    # public key
    private_key = ecdsa.SigningKey.from_string( secret, curve = SECP256k1 )
    public_key = private_key.get_verifying_key()
    K = public_key.to_string()
    K_compressed = GetPubKey(public_key.pubkey,True)
    return K, K_compressed


# Child private key derivation function (from master private key)
# k = master private key (32 bytes)
# c = master chain code (extra entropy for key derivation) (32 bytes)
# n = the index of the key we want to derive. (only 32 bits will be used)
# If n is negative (i.e. the 32nd bit is set), the resulting private key's
#  corresponding public key can NOT be determined without the master private key.
# However, if n is positive, the resulting private key's corresponding
#  public key can be determined without the master private key.
def CKD_priv(k, c, n):
    is_prime = n & BIP32_PRIME
    return _CKD_priv(k, c, rev_hex(int_to_hex(n,4)).decode('hex'), is_prime)

def _CKD_priv(k, c, s, is_prime):
    import hmac
    from ecdsa.util import string_to_number, number_to_string
    order = generator_secp256k1.order()
    keypair = EC_KEY(k)
    cK = GetPubKey(keypair.pubkey,True)
    data = chr(0) + k + s if is_prime else cK + s
    I = hmac.new(c, data, hashlib.sha512).digest()
    k_n = number_to_string( (string_to_number(I[0:32]) + string_to_number(k)) % order , order )
    c_n = I[32:]
    return k_n, c_n

# Child public key derivation function (from public key only)
# K = master public key 
# c = master chain code
# n = index of key we want to derive
# This function allows us to find the nth public key, as long as n is 
#  non-negative. If n is negative, we need the master private key to find it.
def CKD_pub(cK, c, n):
    if n & BIP32_PRIME: raise
    return _CKD_pub(cK, c, rev_hex(int_to_hex(n,4)).decode('hex'))

# helper function, callable with arbitrary string
def _CKD_pub(cK, c, s):
    import hmac
    from ecdsa.util import string_to_number, number_to_string
    order = generator_secp256k1.order()
    I = hmac.new(c, cK + s, hashlib.sha512).digest()
    curve = SECP256k1
    pubkey_point = string_to_number(I[0:32])*curve.generator + ser_to_point(cK)
    public_key = ecdsa.VerifyingKey.from_public_point( pubkey_point, curve = SECP256k1 )
    c_n = I[32:]
    cK_n = GetPubKey(public_key.pubkey,True)
    return cK_n, c_n



def deserialize_xkey(xkey):
    xkey = DecodeBase58Check(xkey) 
    assert len(xkey) == 78
    assert xkey[0:4].encode('hex') in ["0488ade4", "0488b21e"]
    depth = ord(xkey[4])
    fingerprint = xkey[5:9]
    child_number = xkey[9:13]
    c = xkey[13:13+32]
    if xkey[0:4].encode('hex') == "0488ade4":
        K_or_k = xkey[13+33:]
    else:
        K_or_k = xkey[13+32:]
    return depth, fingerprint, child_number, c, K_or_k



def bip32_root(seed):
    import hmac
    seed = seed.decode('hex')        
    I = hmac.new("Bitcoin seed", seed, hashlib.sha512).digest()
    master_k = I[0:32]
    master_c = I[32:]
    K, cK = get_pubkeys_from_secret(master_k)
    xprv = ("0488ADE4" + "00" + "00000000" + "00000000").decode("hex") + master_c + chr(0) + master_k
    xpub = ("0488B21E" + "00" + "00000000" + "00000000").decode("hex") + master_c + cK
    return EncodeBase58Check(xprv), EncodeBase58Check(xpub)



def bip32_private_derivation(xprv, branch, sequence):
    depth, fingerprint, child_number, c, k = deserialize_xkey(xprv)
    assert sequence.startswith(branch)
    sequence = sequence[len(branch):]
    for n in sequence.split('/'):
        if n == '': continue
        i = int(n[:-1]) + BIP32_PRIME if n[-1] == "'" else int(n)
        parent_k = k
        k, c = CKD_priv(k, c, i)
        depth += 1

    _, parent_cK = get_pubkeys_from_secret(parent_k)
    fingerprint = hash_160(parent_cK)[0:4]
    child_number = ("%08X"%i).decode('hex')
    K, cK = get_pubkeys_from_secret(k)
    xprv = "0488ADE4".decode('hex') + chr(depth) + fingerprint + child_number + c + chr(0) + k
    xpub = "0488B21E".decode('hex') + chr(depth) + fingerprint + child_number + c + cK
    return EncodeBase58Check(xprv), EncodeBase58Check(xpub)



def bip32_public_derivation(xpub, branch, sequence):
    depth, fingerprint, child_number, c, cK = deserialize_xkey(xpub)
    assert sequence.startswith(branch)
    sequence = sequence[len(branch):]
    for n in sequence.split('/'):
        if n == '': continue
        i = int(n)
        parent_cK = cK
        cK, c = CKD_pub(cK, c, i)
        depth += 1

    fingerprint = hash_160(parent_cK)[0:4]
    child_number = ("%08X"%i).decode('hex')
    xpub = "0488B21E".decode('hex') + chr(depth) + fingerprint + child_number + c + cK
    return EncodeBase58Check(xpub)




def bip32_private_key(sequence, k, chain):
    for i in sequence:
        k, chain = CKD_priv(k, chain, i)
    return SecretToASecret(k, True)




################################## transactions

MIN_RELAY_TX_FEE = 1000



def test_bip32(seed, sequence):
    """
    run a test vector,
    see https://en.bitcoin.it/wiki/BIP_0032_TestVectors
    """

    xprv, xpub = bip32_root(seed)
    print xpub
    print xprv

    assert sequence[0:2] == "m/"
    path = 'm'
    sequence = sequence[2:]
    for n in sequence.split('/'):
        child_path = path + '/' + n
        if n[-1] != "'":
            xpub2 = bip32_public_derivation(xpub, path, child_path)
        xprv, xpub = bip32_private_derivation(xprv, path, child_path)
        if n[-1] != "'":
            assert xpub == xpub2
        

        path = child_path
        print path
        print xpub
        print xprv

    print "----"

        

def test_crypto(message):
    G = generator_secp256k1
    _r  = G.order()
    pvk = ecdsa.util.randrange( pow(2,256) ) %_r

    Pub = pvk*G
    pubkey_c = point_to_ser(Pub,True)
    pubkey_u = point_to_ser(Pub,False)
    addr_c = public_key_to_bc_address(pubkey_c)
    addr_u = public_key_to_bc_address(pubkey_u)

    print "Private key            ", '%064x'%pvk
    eck = EC_KEY(number_to_string(pvk,_r))

    print "Compressed public key  ", pubkey_c.encode('hex')
    enc = EC_KEY.encrypt_message(message, pubkey_c)
    dec = eck.decrypt_message(enc)
    assert dec == message

    print "Uncompressed public key", pubkey_u.encode('hex')
    enc2 = EC_KEY.encrypt_message(message, pubkey_u)
    dec2 = eck.decrypt_message(enc)
    assert dec2 == message

    signature = eck.sign_message(message, True, addr_c)
    print signature
    EC_KEY.verify_message(addr_c, signature, message)


if __name__ == '__main__':

    for message in ["Chancellor on brink of second bailout for banks", chr(255)*512]:
        test_crypto(message)

    test_bip32("000102030405060708090a0b0c0d0e0f", "m/0'/1/2'/2/1000000000")
    test_bip32("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542","m/0/2147483647'/1/2147483646'/2")



########NEW FILE########
__FILENAME__ = blockchain
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@ecdsa.org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import threading, time, Queue, os, sys, shutil
from util import user_dir, appdata_dir, print_error
from bitcoin import *


class Blockchain(threading.Thread):

    def __init__(self, config, network):
        threading.Thread.__init__(self)
        self.daemon = True
        self.config = config
        self.network = network
        self.lock = threading.Lock()
        self.local_height = 0
        self.running = False
        self.headers_url = 'http://headers.electrum.org/blockchain_headers'
        self.set_local_height()
        self.queue = Queue.Queue()

    
    def height(self):
        return self.local_height


    def stop(self):
        with self.lock: self.running = False


    def is_running(self):
        with self.lock: return self.running


    def run(self):
        self.init_headers_file()
        self.set_local_height()
        print_error( "blocks:", self.local_height )

        with self.lock:
            self.running = True

        while self.is_running():

            try:
                result = self.queue.get()
            except Queue.Empty:
                continue

            if not result: continue

            i, header = result
            if not header: continue
            
            height = header.get('block_height')

            if height <= self.local_height:
                continue

            if height > self.local_height + 50:
                if not self.get_and_verify_chunks(i, header, height):
                    continue

            if height > self.local_height:
                # get missing parts from interface (until it connects to my chain)
                chain = self.get_chain( i, header )

                # skip that server if the result is not consistent
                if not chain: 
                    print_error('e')
                    continue
                
                # verify the chain
                if self.verify_chain( chain ):
                    print_error("height:", height, i.server)
                    for header in chain:
                        self.save_header(header)
                else:
                    print_error("error", i.server)
                    # todo: dismiss that server
                    continue


            self.network.new_blockchain_height(height, i)


                    
            
    def verify_chain(self, chain):

        first_header = chain[0]
        prev_header = self.read_header(first_header.get('block_height') -1)
        
        for header in chain:

            height = header.get('block_height')

            prev_hash = self.hash_header(prev_header)
            bits, target = self.get_target(height/2016, chain)
            _hash = self.hash_header(header)
            try:
                assert prev_hash == header.get('prev_block_hash')
                assert bits == header.get('bits')
                assert int('0x'+_hash,16) < target
            except Exception:
                return False

            prev_header = header

        return True



    def verify_chunk(self, index, hexdata):
        data = hexdata.decode('hex')
        height = index*2016
        num = len(data)/80

        if index == 0:  
            previous_hash = ("0"*64)
        else:
            prev_header = self.read_header(index*2016-1)
            if prev_header is None: raise
            previous_hash = self.hash_header(prev_header)

        bits, target = self.get_target(index)

        for i in range(num):
            height = index*2016 + i
            raw_header = data[i*80:(i+1)*80]
            header = self.header_from_string(raw_header)
            _hash = self.hash_header(header)
            assert previous_hash == header.get('prev_block_hash')
            assert bits == header.get('bits')
            assert int('0x'+_hash,16) < target

            previous_header = header
            previous_hash = _hash 

        self.save_chunk(index, data)
        print_error("validated chunk %d"%height)

        

    def header_to_string(self, res):
        s = int_to_hex(res.get('version'),4) \
            + rev_hex(res.get('prev_block_hash')) \
            + rev_hex(res.get('merkle_root')) \
            + int_to_hex(int(res.get('timestamp')),4) \
            + int_to_hex(int(res.get('bits')),4) \
            + int_to_hex(int(res.get('nonce')),4)
        return s


    def header_from_string(self, s):
        hex_to_int = lambda s: int('0x' + s[::-1].encode('hex'), 16)
        h = {}
        h['version'] = hex_to_int(s[0:4])
        h['prev_block_hash'] = hash_encode(s[4:36])
        h['merkle_root'] = hash_encode(s[36:68])
        h['timestamp'] = hex_to_int(s[68:72])
        h['bits'] = hex_to_int(s[72:76])
        h['nonce'] = hex_to_int(s[76:80])
        return h

    def hash_header(self, header):
        return rev_hex(Hash(self.header_to_string(header).decode('hex')).encode('hex'))

    def path(self):
        return os.path.join( self.config.path, 'blockchain_headers')

    def init_headers_file(self):
        filename = self.path()
        if os.path.exists(filename):
            return
        
        try:
            import urllib, socket
            socket.setdefaulttimeout(30)
            print_error("downloading ", self.headers_url )
            urllib.urlretrieve(self.headers_url, filename)
            print_error("done.")
        except Exception:
            print_error( "download failed. creating file", filename )
            open(filename,'wb+').close()

    def save_chunk(self, index, chunk):
        filename = self.path()
        f = open(filename,'rb+')
        f.seek(index*2016*80)
        h = f.write(chunk)
        f.close()
        self.set_local_height()

    def save_header(self, header):
        data = self.header_to_string(header).decode('hex')
        assert len(data) == 80
        height = header.get('block_height')
        filename = self.path()
        f = open(filename,'rb+')
        f.seek(height*80)
        h = f.write(data)
        f.close()
        self.set_local_height()


    def set_local_height(self):
        name = self.path()
        if os.path.exists(name):
            h = os.path.getsize(name)/80 - 1
            if self.local_height != h:
                self.local_height = h


    def read_header(self, block_height):
        name = self.path()
        if os.path.exists(name):
            f = open(name,'rb')
            f.seek(block_height*80)
            h = f.read(80)
            f.close()
            if len(h) == 80:
                h = self.header_from_string(h)
                return h 


    def get_target(self, index, chain=[]):

        max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000
        if index == 0: return 0x1d00ffff, max_target

        first = self.read_header((index-1)*2016)
        last = self.read_header(index*2016-1)
        if last is None:
            for h in chain:
                if h.get('block_height') == index*2016-1:
                    last = h
 
        nActualTimespan = last.get('timestamp') - first.get('timestamp')
        nTargetTimespan = 14*24*60*60
        nActualTimespan = max(nActualTimespan, nTargetTimespan/4)
        nActualTimespan = min(nActualTimespan, nTargetTimespan*4)

        bits = last.get('bits') 
        # convert to bignum
        MM = 256*256*256
        a = bits%MM
        if a < 0x8000:
            a *= 256
        target = (a) * pow(2, 8 * (bits/MM - 3))

        # new target
        new_target = min( max_target, (target * nActualTimespan)/nTargetTimespan )
        
        # convert it to bits
        c = ("%064X"%new_target)[2:]
        i = 31
        while c[0:2]=="00":
            c = c[2:]
            i -= 1

        c = int('0x'+c[0:6],16)
        if c >= 0x800000: 
            c /= 256
            i += 1

        new_bits = c + MM * i
        return new_bits, new_target


    def request_header(self, i, h, queue):
        print_error("requesting header %d from %s"%(h, i.server))
        i.send([ ('blockchain.block.get_header',[h])], lambda i,r: queue.put((i,r)))

    def retrieve_header(self, i, queue):
        while True:
            try:
                ir = queue.get(timeout=1)
            except Queue.Empty:
                print_error('timeout')
                continue

            if not ir: 
                continue

            i, r = ir

            if r.get('error'):
                print_error('Verifier received an error:', r)
                continue

            # 3. handle response
            method = r['method']
            params = r['params']
            result = r['result']

            if method == 'blockchain.block.get_header':
                return result
                


    def get_chain(self, interface, final_header):

        header = final_header
        chain = [ final_header ]
        requested_header = False
        queue = Queue.Queue()

        while self.is_running():

            if requested_header:
                header = self.retrieve_header(interface, queue)
                if not header: return
                chain = [ header ] + chain
                requested_header = False

            height = header.get('block_height')
            previous_header = self.read_header(height -1)
            if not previous_header:
                self.request_header(interface, height - 1, queue)
                requested_header = True
                continue

            # verify that it connects to my chain
            prev_hash = self.hash_header(previous_header)
            if prev_hash != header.get('prev_block_hash'):
                print_error("reorg")
                self.request_header(interface, height - 1, queue)
                requested_header = True
                continue

            else:
                # the chain is complete
                return chain


    def get_and_verify_chunks(self, i, header, height):

        queue = Queue.Queue()
        min_index = (self.local_height + 1)/2016
        max_index = (height + 1)/2016
        n = min_index
        while n < max_index + 1:
            print_error( "Requesting chunk:", n )
            r = i.synchronous_get([ ('blockchain.block.get_chunk',[n])])[0]
            if not r: 
                continue
            try:
                self.verify_chunk(n, r)
                n = n + 1
            except Exception:
                print_error('Verify chunk failed!')
                n = n - 1
                if n < 0:
                    return False

        return True


########NEW FILE########
__FILENAME__ = bmp
# -*- coding: utf-8 -*-
"""
bmp.py - module for constructing simple BMP graphics files

 Permission is hereby granted, free of charge, to any person obtaining
 a copy of this software and associated documentation files (the
 "Software"), to deal in the Software without restriction, including
 without limitation the rights to use, copy, modify, merge, publish,
 distribute, sublicense, and/or sell copies of the Software, and to
 permit persons to whom the Software is furnished to do so, subject to
 the following conditions:

 The above copyright notice and this permission notice shall be
 included in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
__version__ = "0.3"
__about =  "bmp module, version %s, written by Paul McGuire, October, 2003, updated by Margus Laak, September, 2009" % __version__ 

from math import ceil, hypot


def shortToString(i):
  hi = (i & 0xff00) >> 8
  lo = i & 0x00ff
  return chr(lo) + chr(hi)

def longToString(i):
  hi = (long(i) & 0x7fff0000) >> 16
  lo = long(i) & 0x0000ffff
  return shortToString(lo) + shortToString(hi)

def long24ToString(i):
  return chr(i & 0xff) + chr(i >> 8 & 0xff) + chr(i >> 16 & 0xff)

def stringToLong(input_string, offset):
  return ord(input_string[offset+3]) << 24 | ord(input_string[offset+2]) << 16 | ord(input_string[offset+1]) << 8 | ord(input_string[offset])

def stringToLong24(input_string, offset):
  return ord(input_string[offset+2]) << 16 | ord(input_string[offset+1]) << 8 | ord(input_string[offset])

class Color(object):
  """class for specifying colors while drawing BitMap elements"""
  __slots__ = [ 'red', 'grn', 'blu' ]
  __shade = 32
  
  def __init__( self, r=0, g=0, b=0 ):
    self.red = r
    self.grn = g
    self.blu = b

  def __setattr__(self, name, value):
    if hasattr(self, name):
      raise AttributeError, "Color is immutable"
    else:
      object.__setattr__(self, name, value)

  def __str__( self ):
    return "R:%d G:%d B:%d" % (self.red, self.grn, self.blu )
    
  def __hash__( self ):
    return ( ( long(self.blu) ) + 
              ( long(self.grn) <<  8 ) + 
              ( long(self.red) << 16 ) )
  
  def __eq__( self, other ):
    return (self is other) or (self.toLong == other.toLong)

  def lighten( self ):
    return Color( 
      min( self.red + Color.__shade, 255), 
      min( self.grn + Color.__shade, 255), 
      min( self.blu + Color.__shade, 255)  
      )
  
  def darken( self ):
    return Color( 
      max( self.red - Color.__shade, 0), 
      max( self.grn - Color.__shade, 0), 
      max( self.blu - Color.__shade, 0)  
      )
       
  def toLong( self ):
    return self.__hash__()
    
  def fromLong( l ):
    b = l & 0xff
    l = l >> 8
    g = l & 0xff
    l = l >> 8
    r = l & 0xff
    return Color( r, g, b )
  fromLong = staticmethod(fromLong)

# define class constants for common colors
Color.BLACK    = Color(   0,   0,   0 )
Color.RED      = Color( 255,   0,   0 )
Color.GREEN    = Color(   0, 255,   0 )
Color.BLUE     = Color(   0,   0, 255 )
Color.CYAN     = Color(   0, 255, 255 )
Color.MAGENTA  = Color( 255,   0, 255 )
Color.YELLOW   = Color( 255, 255,   0 )
Color.WHITE    = Color( 255, 255, 255 )
Color.DKRED    = Color( 128,   0,   0 )
Color.DKGREEN  = Color(   0, 128,   0 )
Color.DKBLUE   = Color(   0,   0, 128 )
Color.TEAL     = Color(   0, 128, 128 )
Color.PURPLE   = Color( 128,   0, 128 )
Color.BROWN    = Color( 128, 128,   0 )
Color.GRAY     = Color( 128, 128, 128 )


class BitMap(object):
  """class for drawing and saving simple Windows bitmap files"""
  
  LINE_SOLID  = 0
  LINE_DASHED = 1
  LINE_DOTTED = 2
  LINE_DOT_DASH=3
  _DASH_LEN = 12.0
  _DOT_LEN = 6.0
  _DOT_DASH_LEN = _DOT_LEN + _DASH_LEN
  
  def __init__( self, width, height, 
                 bkgd = Color.WHITE, frgd = Color.BLACK ):
    self.wd = int( ceil(width) )
    self.ht = int( ceil(height) )
    self.bgcolor = 0
    self.fgcolor = 1
    self.palette = []
    self.palette.append( bkgd.toLong() )
    self.palette.append( frgd.toLong() )
    self.currentPen = self.fgcolor

    tmparray = [ self.bgcolor ] * self.wd
    self.bitarray = [ tmparray[:] for i in range( self.ht ) ]
    self.currentPen = 1
    

  def plotPoint( self, x, y ):
    if ( 0 <= x < self.wd and 0 <= y < self.ht ):
      x = int(x)
      y = int(y)
      self.bitarray[y][x] = self.currentPen
      

  def _saveBitMapNoCompression( self ):
    line_padding = (4 - (self.wd % 4)) % 4
    
    # write bitmap header
    _bitmap = "BM"
    _bitmap += longToString( 54 + self.ht*(self.wd*3 + line_padding) )   # DWORD size in bytes of the file
    _bitmap += longToString( 0 )    # DWORD 0
    _bitmap += longToString( 54  )
    _bitmap += longToString( 40 )    # DWORD header size = 40
    _bitmap += longToString( self.wd )    # DWORD image width
    _bitmap += longToString( self.ht )    # DWORD image height
    _bitmap += shortToString( 1 )    # WORD planes = 1
    _bitmap += shortToString( 24 )    # WORD bits per pixel = 8
    _bitmap += longToString( 0 )    # DWORD compression = 0
    _bitmap += longToString( self.ht * (self.wd * 3 + line_padding) )    # DWORD sizeimage = size in bytes of the bitmap = width * height
    _bitmap += longToString( 0 )    # DWORD horiz pixels per meter (?)
    _bitmap += longToString( 0 )    # DWORD ver pixels per meter (?)
    _bitmap += longToString( 0 )    # DWORD number of colors used = 256
    _bitmap += longToString( 0 )    # DWORD number of "import colors = len( self.palette )

    # write pixels
    self.bitarray.reverse()
    for row in self.bitarray:
      for pixel in row:
        c = self.palette[pixel]
        _bitmap += long24ToString(c)
      for i in range(line_padding):
        _bitmap += chr( 0 )

    return _bitmap

    
    
  def saveFile( self, filename):
    _b = self._saveBitMapNoCompression( )
    
    f = file(filename, 'wb')
    f.write(_b)
    f.close()
  

def save_qrcode(qr, filename):
    k = qr.moduleCount
    bitmap = BitMap( (k+2)*8, (k+2)*8 )
    bitmap.bitarray = []
    for r in range(k+2):
        tmparray = [ 0 ] * (k+2)*8

        if 0 < r < k+1:
            for c in range(k):
                if qr.isDark(r-1, c):
                    tmparray[ (1+c)*8:(2+c)*8] = [1]*8

        for i in range(8):
            bitmap.bitarray.append( tmparray[:] )

    bitmap.saveFile( filename )

  
    
if __name__ == "__main__":
  
  bmp = BitMap( 10, 10 )
  bmp.plotPoint( 5, 5 )
  bmp.plotPoint( 0, 0 )
  bmp.saveFile( "test.bmp" )


########NEW FILE########
__FILENAME__ = commands
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import time
from util import *
from bitcoin import *
from decimal import Decimal
import bitcoin
from transaction import Transaction

class Command:
    def __init__(self, name, min_args, max_args, requires_network, requires_wallet, requires_password, description, syntax = '', options_syntax = ''):
        self.name = name
        self.min_args=min_args
        self.max_args = max_args
        self.requires_network = requires_network
        self.requires_wallet = requires_wallet
        self.requires_password = requires_password
        self.description = description
        self.syntax = syntax
        self.options = options_syntax

known_commands = {}
def register_command(*args):
    global known_commands
    name = args[0]
    known_commands[name] = Command(*args)



payto_options = ' --fee, -f: set transaction fee\n --fromaddr, -F: send from address -\n --changeaddr, -c: send change to address'
listaddr_options = " -a: show all addresses, including change addresses\n -l: include labels in results"
restore_options = " accepts a seed or master public key."
mksendmany_syntax = 'mksendmanytx <recipient> <amount> [<recipient> <amount> ...]'
payto_syntax = "payto <recipient> <amount> [label]\n<recipient> can be a bitcoin address or a label"
paytomany_syntax = "paytomany <recipient> <amount> [<recipient> <amount> ...]\n<recipient> can be a bitcoin address or a label"
signmessage_syntax = 'signmessage <address> <message>\nIf you want to lead or end a message with spaces, or want double spaces inside the message make sure you quote the string. I.e. " Hello  This is a weird String "'
verifymessage_syntax = 'verifymessage <address> <signature> <message>\nIf you want to lead or end a message with spaces, or want double spaces inside the message make sure you quote the string. I.e. " Hello  This is a weird String "'


#                command
#                                              requires_network
#                                                     requires_wallet
#                                                            requires_password
register_command('contacts',             0, 0, False, True,  False, 'Show your list of contacts')
register_command('create',               0, 0, False, True,  False, 'Create a new wallet')
register_command('createmultisig',       2, 2, False, True,  False, 'similar to bitcoind\'s command')
register_command('createrawtransaction', 2, 2, False, True,  False, 'similar to bitcoind\'s command')
register_command('deseed',               0, 0, False, True,  False, 'Remove seed from wallet, creating a seedless, watching-only wallet.')
register_command('decoderawtransaction', 1, 1, False, False, False, 'similar to bitcoind\'s command')
register_command('getprivatekeys',       1, 1, False, True,  True,  'Get the private keys of a given address', 'getprivatekeys <bitcoin address>')
register_command('dumpprivkeys',         0, 0, False, True,  True,  'Dump all private keys in your wallet')
register_command('freeze',               1, 1, False, True,  True,  'Freeze the funds at one of your wallet\'s addresses', 'freeze <address>')
register_command('getbalance',           0, 1, True,  True,  False, 'Return the balance of your wallet, or of one account in your wallet', 'getbalance [<account>]')
register_command('getservers',           0, 0, True,  False, False, 'Return the list of available servers')
register_command('getversion',           0, 0, False, False, False, 'Return the version of your client', 'getversion')
register_command('getaddressbalance',    1, 1, True,  False, False, 'Return the balance of an address', 'getaddressbalance <address>')
register_command('getaddresshistory',    1, 1, True,  False, False, 'Return the transaction history of a wallet address', 'getaddresshistory <address>')
register_command('getconfig',            1, 1, False, False, False, 'Return a configuration variable', 'getconfig <name>')
register_command('getpubkeys',           1, 1, False, True,  False, 'Return the public keys for a wallet address', 'getpubkeys <bitcoin address>')
register_command('getrawtransaction',    1, 1, True,  False, False, 'Retrieve a transaction', 'getrawtransaction <txhash>')
register_command('getseed',              0, 0, False, True,  True,  'Print the generation seed of your wallet.')
register_command('getmpk',               0, 0, False, True,  False, 'Return your wallet\'s master public key', 'getmpk')
register_command('help',                 0, 1, False, False, False, 'Prints this help')
register_command('history',              0, 0, True,  True,  False, 'Returns the transaction history of your wallet')
register_command('importprivkey',        1, 1, False, True,  True,  'Import a private key', 'importprivkey <privatekey>')
register_command('listaddresses',        2, 2, False, True,  False, 'Returns your list of addresses.', '', listaddr_options)
register_command('listunspent',          0, 0, True,  True,  False, 'Returns the list of unspent inputs in your wallet.')
register_command('getaddressunspent',    1, 1, True,  False, False, 'Returns the list of unspent inputs for an address.')
register_command('mktx',                 5, 5, False, True,  True,  'Create a signed transaction', 'mktx <recipient> <amount> [label]', payto_options)
register_command('mksendmanytx',         4, 4, False, True,  True,  'Create a signed transaction', mksendmany_syntax, payto_options)
register_command('payto',                5, 5, True,  True,  True,  'Create and broadcast a transaction.', payto_syntax, payto_options)
register_command('paytomany',            4, 4, True,  True,  True,  'Create and broadcast a transaction.', paytomany_syntax, payto_options)
register_command('password',             0, 0, False, True,  True,  'Change your password')
register_command('restore',              0, 0, True,  True,  False, 'Restore a wallet', '', restore_options)
register_command('setconfig',            2, 2, False, False, False, 'Set a configuration variable', 'setconfig <name> <value>')
register_command('setlabel',             2,-1, False, True,  False, 'Assign a label to an item', 'setlabel <tx_hash> <label>')
register_command('sendrawtransaction',   1, 1, True,  False, False, 'Broadcasts a transaction to the network.', 'sendrawtransaction <tx in hexadecimal>')
register_command('signrawtransaction',   1, 3, False, True,  True,  'similar to bitcoind\'s command')
register_command('signmessage',          2,-1, False, True,  True,  'Sign a message with a key', signmessage_syntax)
register_command('unfreeze',             1, 1, False, True,  False, 'Unfreeze the funds at one of your wallet\'s address', 'unfreeze <address>')
register_command('validateaddress',      1, 1, False, False, False, 'Check that the address is valid', 'validateaddress <address>')
register_command('verifymessage',        3,-1, False, False, False, 'Verifies a signature', verifymessage_syntax)

register_command('encrypt',              2,-1, False, False, False, 'encrypt a message with pubkey','encrypt <pubkey> <message>')
register_command('decrypt',              2,-1, False, True, True,   'decrypt a message encrypted with pubkey','decrypt <pubkey> <message>')
register_command('daemon',               1, 1, True, False, False,  '<stop|status>')
register_command('getproof',             1, 1, True, False, False, 'get merkle proof', 'getproof <address>')
register_command('getutxoaddress',       2, 2, True, False, False, 'get the address of an unspent transaction output','getutxoaddress <txid> <pos>')
register_command('sweep',                2, 3, True, False, False, 'Sweep a private key.', 'sweep privkey addr [fee]')




class Commands:

    def __init__(self, wallet, network, callback = None):
        self.wallet = wallet
        self.network = network
        self._callback = callback
        self.password = None


    def _run(self, method, args, password_getter):
        cmd = known_commands[method]
        if cmd.requires_password and self.wallet.use_encryption:
            self.password = apply(password_getter,())
        f = getattr(self, method)
        result = f(*args)
        self.password = None
        if self._callback:
            apply(self._callback, ())
        return result


    def getaddresshistory(self, addr):
        return self.network.synchronous_get([ ('blockchain.address.get_history',[addr]) ])[0]


    def daemon(self, arg):
        if arg=='stop':
            return self.network.stop()
        elif arg=='status':
            return { 
                'server':self.network.main_server(), 
                'connected':self.network.is_connected()
            }
        else:
            return "unknown command \"%s\""% arg


    def listunspent(self):
        import copy
        l = copy.deepcopy(self.wallet.get_unspent_coins())
        for i in l: i["value"] = str(Decimal(i["value"])/100000000)
        return l


    def getaddressunspent(self, addr):
        return self.network.synchronous_get([ ('blockchain.address.listunspent',[addr]) ])[0]


    def getutxoaddress(self, txid, num):
        r = self.network.synchronous_get([ ('blockchain.utxo.get_address',[txid, num]) ])
        if r: 
            return {'address':r[0] }


    def createrawtransaction(self, inputs, outputs):
        for i in inputs:
            i['prevout_hash'] = i['txid']
            i['prevout_n'] = i['vout']
        outputs = map(lambda x: (x[0],int(1e8*x[1])), outputs.items())
        tx = Transaction.from_io(inputs, outputs)
        return tx


    def signrawtransaction(self, raw_tx, input_info, private_keys):
        tx = Transaction(raw_tx)
        self.wallet.signrawtransaction(tx, input_info, private_keys, self.password)
        return tx

    def decoderawtransaction(self, raw):
        tx = Transaction(raw)
        return tx.deserialize()

    def sendrawtransaction(self, raw):
        tx = Transaction(raw)
        return self.network.synchronous_get([('blockchain.transaction.broadcast', [str(tx)])])[0]

    def createmultisig(self, num, pubkeys):
        assert isinstance(pubkeys, list)
        redeem_script = Transaction.multisig_script(pubkeys, num)
        address = hash_160_to_bc_address(hash_160(redeem_script.decode('hex')), 5)
        return {'address':address, 'redeemScript':redeem_script}
    
    def freeze(self,addr):
        return self.wallet.freeze(addr)
        
    def unfreeze(self,addr):
        return self.wallet.unfreeze(addr)

    def getprivatekeys(self, addr):
        return self.wallet.get_private_key(addr, self.password)

    def dumpprivkeys(self, addresses = None):
        if addresses is None:
            addresses = self.wallet.addresses(True)
        return [self.wallet.get_private_key(address, self.password) for address in addresses]

    def validateaddress(self, addr):
        isvalid = is_valid(addr)
        out = { 'isvalid':isvalid }
        if isvalid:
            out['address'] = addr
        return out

    def getpubkeys(self, addr):
        out = { 'address':addr }
        out['pubkeys'] = self.wallet.getpubkeys(addr)
        return out


    def getbalance(self, account= None):
        if account is None:
            c, u = self.wallet.get_balance()
        else:
            c, u = self.wallet.get_account_balance(account)

        out = { "confirmed": str(Decimal(c)/100000000) }
        if u: out["unconfirmed"] = str(Decimal(u)/100000000)
        return out

    def getaddressbalance(self, addr):
        out = self.network.synchronous_get([ ('blockchain.address.get_balance',[addr]) ])[0]
        out["confirmed"] =  str(Decimal(out["confirmed"])/100000000)
        out["unconfirmed"] =  str(Decimal(out["unconfirmed"])/100000000)
        return out


    def getproof(self, addr):
        p = self.network.synchronous_get([ ('blockchain.address.get_proof',[addr]) ])[0]
        out = []
        for i,s in p:
            out.append(i)
        return out

    def getservers(self):
        while not self.network.is_up_to_date():
            time.sleep(0.1)
        return self.network.get_servers()

    def getversion(self):
        import electrum 
        return electrum.ELECTRUM_VERSION
 
    def getmpk(self):
        return self.wallet.get_master_public_key()

    def getseed(self):
        mnemonic = self.wallet.get_mnemonic(self.password)
        return { 'mnemonic':mnemonic, 'version':self.wallet.seed_version }

    def importprivkey(self, sec):
        try:
            addr = self.wallet.import_key(sec,self.password)
            out = "Keypair imported: ", addr
        except Exception as e:
            out = "Error: Keypair import failed: " + str(e)
        return out


    def sweep(self, privkey, to_address, fee = 0.0001):
        fee = int(Decimal(fee)*100000000)
        return Transaction.sweep([privkey], self.network, to_address, fee)


    def signmessage(self, address, message):
        return self.wallet.sign_message(address, message, self.password)


    def verifymessage(self, address, signature, message):
        return bitcoin.verify_message(address, signature, message)


    def _mktx(self, outputs, fee = None, change_addr = None, domain = None):

        for to_address, amount in outputs:
            if not is_valid(to_address):
                raise Exception("Invalid Bitcoin address", to_address)

        if change_addr:
            if not is_valid(change_addr):
                raise Exception("Invalid Bitcoin address", change_addr)

        if domain is not None:
            for addr in domain:
                if not is_valid(addr):
                    raise Exception("invalid Bitcoin address", addr)
            
                if not self.wallet.is_mine(addr):
                    raise Exception("address not in wallet", addr)

        for k, v in self.wallet.labels.items():
            if change_addr and v == change_addr:
                change_addr = k

        final_outputs = []
        for to_address, amount in outputs:
            for k, v in self.wallet.labels.items():
                if v == to_address:
                    to_address = k
                    print_msg("alias", to_address)
                    break

            amount = int(100000000*amount)
            final_outputs.append((to_address, amount))
            
        if fee: fee = int(100000000*fee)
        return self.wallet.mktx(final_outputs, self.password, fee , change_addr, domain)


    def mktx(self, to_address, amount, fee = None, change_addr = None, domain = None):
        tx = self._mktx([(to_address, amount)], fee, change_addr, domain)
        return tx

    def mksendmanytx(self, outputs, fee = None, change_addr = None, domain = None):
        tx = self._mktx(outputs, fee, change_addr, domain)
        return tx


    def payto(self, to_address, amount, fee = None, change_addr = None, domain = None):
        tx = self._mktx([(to_address, amount)], fee, change_addr, domain)
        r, h = self.wallet.sendtx( tx )
        return h

    def paytomany(self, outputs, fee = None, change_addr = None, domain = None):
        tx = self._mktx(outputs, fee, change_addr, domain)
        r, h = self.wallet.sendtx( tx )
        return h


    def history(self):
        import datetime
        balance = 0
        out = []
        for item in self.wallet.get_tx_history():
            tx_hash, conf, is_mine, value, fee, balance, timestamp = item
            try:
                time_str = datetime.datetime.fromtimestamp( timestamp).isoformat(' ')[:-3]
            except Exception:
                time_str = "----"

            label, is_default_label = self.wallet.get_label(tx_hash)

            out.append({'txid':tx_hash, 'date':"%16s"%time_str, 'label':label, 'value':format_satoshis(value)})
        return out



    def setlabel(self, key, label):
        self.wallet.set_label(key, label)

            

    def contacts(self):
        c = {}
        for addr in self.wallet.addressbook:
            c[addr] = self.wallet.labels.get(addr)
        return c


    def listaddresses(self, show_all = False, show_label = False):
        out = []
        for addr in self.wallet.addresses(True):
            if show_all or not self.wallet.is_change(addr):
                if show_label:
                    item = { 'address': addr }
                    if show_label:
                        label = self.wallet.labels.get(addr,'')
                        if label:
                            item['label'] = label
                else:
                    item = addr
                out.append( item )
        return out
                         
    def help(self, cmd=None):
        if cmd not in known_commands:
            print_msg("\nList of commands:", ', '.join(sorted(known_commands)))
        else:
            cmd = known_commands[cmd]
            print_msg(cmd.description)
            if cmd.syntax: print_msg("Syntax: " + cmd.syntax)
            if cmd.options: print_msg("options:\n" + cmd.options)
        return None


    def getrawtransaction(self, tx_hash):
        import transaction
        if self.wallet:
            tx = self.wallet.transactions.get(tx_hash)
            if tx:
                return tx

        r = self.network.synchronous_get([ ('blockchain.transaction.get',[tx_hash]) ])[0]
        if r:
            return transaction.Transaction(r)
        else:
            return "unknown transaction"


    def encrypt(self, pubkey, message):
        return bitcoin.encrypt_message(message, pubkey)


    def decrypt(self, pubkey, message):
        return self.wallet.decrypt_message(pubkey, message, self.password)




########NEW FILE########
__FILENAME__ = daemon
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2014 Thomas Voegtlin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import socket
import time
import sys
import os
import threading
import traceback
import json
import Queue
from network import Network
from util import print_msg, print_stderr
from simple_config import SimpleConfig


class NetworkProxy(threading.Thread):
    # connects to daemon
    # sends requests, runs callbacks

    def __init__(self, config = {}):
        threading.Thread.__init__(self)
        self.daemon = True
        self.config = SimpleConfig(config) if type(config) == type({}) else config
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.daemon_port = config.get('daemon_port', 8000)
        self.message_id = 0
        self.unanswered_requests = {}
        self.subscriptions = {}
        self.debug = False
        self.lock = threading.Lock()
        self.pending_transactions_for_notifications = []


    def start(self, start_daemon=False):
        daemon_started = False
        while True:
            try:
                self.socket.connect(('', self.daemon_port))
                threading.Thread.start(self)
                return True

            except socket.error:
                if not start_daemon:
                    return False

                elif not daemon_started:
                    print_stderr( "Starting daemon [%s]"%self.config.get('server'))
                    daemon_started = True
                    pid = os.fork()
                    if (pid == 0): # The first child.
                        os.chdir("/")
                        os.setsid()
                        os.umask(0)
                        pid2 = os.fork()
                        if (pid2 == 0):  # Second child
                            server = NetworkServer(self.config)
                            try:
                                server.main_loop()
                            except KeyboardInterrupt:
                                print "Ctrl C - Stopping server"
                            sys.exit(1)
                        sys.exit(0)
                else:
                    time.sleep(0.1)



    def parse_json(self, message):
        s = message.find('\n')
        if s==-1: 
            return None, message
        j = json.loads( message[0:s] )
        return j, message[s+1:]


    def run(self):
        # read responses and trigger callbacks
        message = ''
        while True:
            try:
                data = self.socket.recv(1024)
            except:
                data = ''
            if not data:
                break

            message += data
            while True:
                response, message = self.parse_json(message)
                if response is not None: 
                    self.process(response)
                else:
                    break

        print "NetworkProxy: exiting"


    def process(self, response):
        # runs callbacks
        if self.debug: print "<--", response

        msg_id = response.get('id')
        with self.lock: 
            method, params, callback = self.unanswered_requests.pop(msg_id)

        result = response.get('result')
        callback(None, {'method':method, 'params':params, 'result':result, 'id':msg_id})


    def subscribe(self, messages, callback):
        # detect if it is a subscription
        with self.lock:
            if self.subscriptions.get(callback) is None: 
                self.subscriptions[callback] = []
            for message in messages:
                if message not in self.subscriptions[callback]:
                    self.subscriptions[callback].append(message)

        self.send( messages, callback )


    def send(self, messages, callback):
        """return the ids of the requests that we sent"""
        out = ''
        ids = []
        for m in messages:
            method, params = m 
            request = json.dumps( { 'id':self.message_id, 'method':method, 'params':params } )
            self.unanswered_requests[self.message_id] = method, params, callback
            ids.append(self.message_id)
            if self.debug: print "-->", request
            self.message_id += 1
            out += request + '\n'
        while out:
            sent = self.socket.send( out )
            out = out[sent:]
        return ids


    def synchronous_get(self, requests, timeout=100000000):
        queue = Queue.Queue()
        ids = self.send(requests, lambda i,x: queue.put(x))
        id2 = ids[:]
        res = {}
        while ids:
            r = queue.get(True, timeout)
            _id = r.get('id')
            if _id in ids:
                ids.remove(_id)
                res[_id] = r.get('result')
        out = []
        for _id in id2:
            out.append(res[_id])
        return out


    def get_servers(self):
        return self.synchronous_get([('network.get_servers',[])])[0]

    def get_header(self, height):
        return self.synchronous_get([('network.get_header',[height])])[0]

    def get_local_height(self):
        return self.synchronous_get([('network.get_local_height',[])])[0]

    def is_connected(self):
        return self.synchronous_get([('network.is_connected',[])])[0]

    def is_up_to_date(self):
        return self.synchronous_get([('network.is_up_to_date',[])])[0]

    def main_server(self):
        return self.synchronous_get([('network.main_server',[])])[0]

    def stop(self):
        return self.synchronous_get([('daemon.shutdown',[])])[0]


    def trigger_callback(self, cb):
        pass






class ClientThread(threading.Thread):
    # read messages from client (socket), and sends them to Network
    # responses are sent back on the same socket

    def __init__(self, server, network, socket):
        threading.Thread.__init__(self)
        self.server = server
        self.daemon = True
        self.s = socket
        self.s.settimeout(0.1)
        self.network = network
        self.queue = Queue.Queue()
        self.unanswered_requests = {}
        self.debug = False


    def run(self):
        message = ''
        while True:
            self.send_responses()
            try:
                data = self.s.recv(1024)
            except socket.timeout:
                continue

            if not data:
                break
            message += data

            while True:
                cmd, message = self.parse_json(message)
                if not cmd:
                    break
                self.process(cmd)

        #print "client thread terminating"


    def parse_json(self, message):
        n = message.find('\n')
        if n==-1: 
            return None, message
        j = json.loads( message[0:n] )
        return j, message[n+1:]


    def process(self, request):
        if self.debug: print "<--", request
        method = request['method']
        params = request['params']
        _id = request['id']

        if method.startswith('network.'):
            out = {'id':_id}
            try:
                f = getattr(self.network, method[8:])
            except AttributeError:
                out['error'] = "unknown method"
            try:
                out['result'] = f(*params)
            except BaseException as e:
                out['error'] =str(e)
            self.queue.put(out) 
            return

        if method == 'daemon.shutdown':
            self.server.running = False
            self.queue.put({'id':_id, 'result':True})
            return

        def cb(i,r):
            _id = r.get('id')
            if _id is not None:
                my_id = self.unanswered_requests.pop(_id)
                r['id'] = my_id
            self.queue.put(r)

        new_id = self.network.interface.send([(method, params)], cb) [0]
        self.unanswered_requests[new_id] = _id


    def send_responses(self):
        while True:
            try:
                r = self.queue.get_nowait()
            except Queue.Empty:
                break
            out = json.dumps(r) + '\n'
            while out:
                n = self.s.send(out)
                out = out[n:]
            if self.debug: print "-->", r
        



class NetworkServer:

    def __init__(self, config):
        network = Network(config)
        if not network.start(wait=True):
            print_msg("Not connected, aborting.")
            sys.exit(1)
        self.network = network
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.daemon_port = config.get('daemon_port', 8000)
        self.server.bind(('', self.daemon_port))
        self.server.listen(5)
        self.server.settimeout(1)
        self.running = False
        self.timeout = config.get('daemon_timeout', 60)


    def main_loop(self):
        self.running = True
        t = time.time()
        while self.running:
            try:
                connection, address = self.server.accept()
            except socket.timeout:
                if time.time() - t > self.timeout:
                    break
                continue
            t = time.time()
            client = ClientThread(self, self.network, connection)
            client.start()



if __name__ == '__main__':
    import simple_config
    config = simple_config.SimpleConfig({'verbose':True, 'server':'ecdsa.net:50002:s'})
    server = NetworkServer(config)
    try:
        server.main_loop()
    except KeyboardInterrupt:
        print "Ctrl C - Stopping server"
        sys.exit(1)

########NEW FILE########
__FILENAME__ = i18n
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import gettext, os

if os.path.exists('./locale'):
    LOCALE_DIR = './locale'
else:
    LOCALE_DIR = '/usr/share/locale'

language = gettext.translation('electrum', LOCALE_DIR, fallback = True)

def _(x):
    global language
    return language.ugettext(x)

def set_language(x):
    global language
    if x: language = gettext.translation('electrum', LOCALE_DIR, fallback = True, languages=[x])
    
    
languages = {
    '':_('Default'),
    'pt_PT':_('Portuguese'),
    'pt_BR':_('Brasilian'),
    'cs_CZ':_('Czech'),
    'de_DE':_('German'),
    'eo_UY':_('Esperanto'),
    'en_UK':_('English'),
    'es_ES':_('Spanish'),
    'fr_FR':_('French'),
    'it_IT':_('Italian'),
    'ja_JP':_('Japanese'),
    'lv_LV':_('Latvian'),
    'nl_NL':_('Dutch'),
    'ru_RU':_('Russian'),
    'sl_SI':_('Slovenian'),
    'ta_IN':_('Tamil'),
    'vi_VN':_('Vietnamese'),
    'zh_CN':_('Chinese')
    }

########NEW FILE########
__FILENAME__ = interface
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import random, ast, re, errno, os
import threading, traceback, sys, time, json, Queue
import socks
import socket
import ssl

from version import ELECTRUM_VERSION, PROTOCOL_VERSION
from util import print_error, print_msg
from simple_config import SimpleConfig


DEFAULT_TIMEOUT = 5
proxy_modes = ['socks4', 'socks5', 'http']


def check_cert(host, cert):
    from OpenSSL import crypto as c
    _cert = c.load_certificate(c.FILETYPE_PEM, cert)

    m = "host: %s\n"%host
    m += "has_expired: %s\n"% _cert.has_expired()
    m += "pubkey: %s bits\n" % _cert.get_pubkey().bits()
    m += "serial number: %s\n"% _cert.get_serial_number() 
    #m += "issuer: %s\n"% _cert.get_issuer()
    #m += "algo: %s\n"% _cert.get_signature_algorithm() 
    m += "version: %s\n"% _cert.get_version()
    print_msg(m)


def cert_has_expired(cert_path):
    try:
        import OpenSSL
    except Exception:
        print_error("Warning: cannot import OpenSSL")
        return False
    from OpenSSL import crypto as c
    with open(cert_path) as f:
        cert = f.read()
    _cert = c.load_certificate(c.FILETYPE_PEM, cert)
    return _cert.has_expired()


def check_certificates():
    config = SimpleConfig()
    mydir = os.path.join(config.path, "certs")
    certs = os.listdir(mydir)
    for c in certs:
        print c
        p = os.path.join(mydir,c)
        with open(p) as f:
            cert = f.read()
        check_cert(c, cert)
    

def cert_verify_hostname(s):
    # hostname verification (disabled)
    from backports.ssl_match_hostname import match_hostname, CertificateError
    try:
        match_hostname(s.getpeercert(True), host)
        print_error("hostname matches", host)
    except CertificateError, ce:
        print_error("hostname did not match", host)



class Interface(threading.Thread):


    def __init__(self, server, config = None):

        threading.Thread.__init__(self)
        self.daemon = True
        self.config = config if config is not None else SimpleConfig()
        self.connect_event = threading.Event()

        self.subscriptions = {}
        self.lock = threading.Lock()

        self.rtime = 0
        self.bytes_received = 0
        self.is_connected = False
        self.poll_interval = 1

        self.debug = False # dump network messages. can be changed at runtime using the console

        #json
        self.message_id = 0
        self.unanswered_requests = {}

        # parse server
        self.server = server
        try:
            host, port, protocol = self.server.split(':')
            port = int(port)
        except Exception:
            self.server = None
            return

        if protocol not in 'ghst':
            raise Exception('Unknown protocol: %s'%protocol)

        self.host = host
        self.port = port
        self.protocol = protocol
        self.use_ssl = ( protocol in 'sg' )
        self.proxy = self.parse_proxy_options(self.config.get('proxy'))
        if self.proxy:
            self.proxy_mode = proxy_modes.index(self.proxy["mode"]) + 1





    def queue_json_response(self, c):

        # uncomment to debug
        if self.debug:
            print_error( "<--",c )

        msg_id = c.get('id')
        error = c.get('error')
        
        if error:
            print_error("received error:", c)
            if msg_id is not None:
                with self.lock: 
                    method, params, callback = self.unanswered_requests.pop(msg_id)
                callback(self,{'method':method, 'params':params, 'error':error, 'id':msg_id})

            return

        if msg_id is not None:
            with self.lock: 
                method, params, callback = self.unanswered_requests.pop(msg_id)
            result = c.get('result')

        else:
            # notification
            method = c.get('method')
            params = c.get('params')

            if method == 'blockchain.numblocks.subscribe':
                result = params[0]
                params = []

            elif method == 'blockchain.headers.subscribe':
                result = params[0]
                params = []

            elif method == 'blockchain.address.subscribe':
                addr = params[0]
                result = params[1]
                params = [addr]

            with self.lock:
                for k,v in self.subscriptions.items():
                    if (method, params) in v:
                        callback = k
                        break
                else:
                    print_error( "received unexpected notification", method, params)
                    print_error( self.subscriptions )
                    return


        callback(self, {'method':method, 'params':params, 'result':result, 'id':msg_id})


    def on_version(self, i, result):
        self.server_version = result


    def start_http(self):
        self.session_id = None
        self.is_connected = True
        self.connection_msg = ('https' if self.use_ssl else 'http') + '://%s:%d'%( self.host, self.port )
        try:
            self.poll()
        except Exception:
            print_error("http init session failed")
            self.is_connected = False
            return

        if self.session_id:
            print_error('http session:',self.session_id)
            self.is_connected = True
        else:
            self.is_connected = False

    def run_http(self):
        self.is_connected = True
        while self.is_connected:
            try:
                if self.session_id:
                    self.poll()
                time.sleep(self.poll_interval)
            except socket.gaierror:
                break
            except socket.error:
                break
            except Exception:
                traceback.print_exc(file=sys.stdout)
                break
            
        self.is_connected = False

                
    def poll(self):
        self.send([], None)


    def send_http(self, messages, callback):
        import urllib2, json, time, cookielib
        print_error( "send_http", messages )
        
        if self.proxy:
            socks.setdefaultproxy(self.proxy_mode, self.proxy["host"], int(self.proxy["port"]) )
            socks.wrapmodule(urllib2)

        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)

        t1 = time.time()

        data = []
        ids = []
        for m in messages:
            method, params = m
            if type(params) != type([]): params = [params]
            data.append( { 'method':method, 'id':self.message_id, 'params':params } )
            self.unanswered_requests[self.message_id] = method, params, callback
            ids.append(self.message_id)
            self.message_id += 1

        if data:
            data_json = json.dumps(data)
        else:
            # poll with GET
            data_json = None 

            
        headers = {'content-type': 'application/json'}
        if self.session_id:
            headers['cookie'] = 'SESSION=%s'%self.session_id

        try:
            req = urllib2.Request(self.connection_msg, data_json, headers)
            response_stream = urllib2.urlopen(req, timeout=DEFAULT_TIMEOUT)
        except Exception:
            return

        for index, cookie in enumerate(cj):
            if cookie.name=='SESSION':
                self.session_id = cookie.value

        response = response_stream.read()
        self.bytes_received += len(response)
        if response: 
            response = json.loads( response )
            if type(response) is not type([]):
                self.queue_json_response(response)
            else:
                for item in response:
                    self.queue_json_response(item)

        if response: 
            self.poll_interval = 1
        else:
            if self.poll_interval < 15: 
                self.poll_interval += 1
        #print self.poll_interval, response

        self.rtime = time.time() - t1
        self.is_connected = True
        return ids




    def start_tcp(self):

        self.connection_msg = self.host + ':%d' % self.port

        if self.proxy is not None:

            socks.setdefaultproxy(self.proxy_mode, self.proxy["host"], int(self.proxy["port"]))
            socket.socket = socks.socksocket
            # prevent dns leaks, see http://stackoverflow.com/questions/13184205/dns-over-proxy
            def getaddrinfo(*args):
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]
            socket.getaddrinfo = getaddrinfo

        if self.use_ssl:
            cert_path = os.path.join( self.config.path, 'certs', self.host)

            if not os.path.exists(cert_path):
                is_new = True
                # get server certificate.
                # Do not use ssl.get_server_certificate because it does not work with proxy
                try:
                    l = socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM)
                except socket.gaierror:
                    print_error("error: cannot resolve", self.host)
                    return

                for res in l:
                    try:
                        s = socket.socket( res[0], socket.SOCK_STREAM )
                        s.connect(res[4])
                    except:
                        s = None
                        continue

                    try:
                        s = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_SSLv3, cert_reqs=ssl.CERT_NONE, ca_certs=None)
                    except ssl.SSLError, e:
                        print_error("SSL error retrieving SSL certificate:", self.host, e)
                        s = None

                    break

                if s is None:
                    return

                dercert = s.getpeercert(True)
                s.close()
                cert = ssl.DER_cert_to_PEM_cert(dercert)
                # workaround android bug
                cert = re.sub("([^\n])-----END CERTIFICATE-----","\\1\n-----END CERTIFICATE-----",cert)
                temporary_path = cert_path + '.temp'
                with open(temporary_path,"w") as f:
                    f.write(cert)

            else:
                is_new = False

        try:
            addrinfo = socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror:
            print_error("error: cannot resolve", self.host)
            return

        for res in addrinfo:
            try:
                s = socket.socket( res[0], socket.SOCK_STREAM )
                s.settimeout(2)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                s.connect(res[4])
            except:
                s = None
                continue
            break

        if s is None:
            print_error("failed to connect", self.host, self.port)
            return

        if self.use_ssl:
            try:
                s = ssl.wrap_socket(s,
                                    ssl_version=ssl.PROTOCOL_SSLv3,
                                    cert_reqs=ssl.CERT_REQUIRED,
                                    ca_certs= (temporary_path if is_new else cert_path),
                                    do_handshake_on_connect=True)
            except ssl.SSLError, e:
                print_error("SSL error:", self.host, e)
                if e.errno != 1:
                    return
                if is_new:
                    rej = cert_path + '.rej'
                    if os.path.exists(rej):
                        os.unlink(rej)
                    os.rename(temporary_path, rej)
                else:
                    if cert_has_expired(cert_path):
                        print_error("certificate has expired:", cert_path)
                        os.unlink(cert_path)
                    else:
                        print_error("wrong certificate", self.host)
                return
            except Exception:
                print_error("wrap_socket failed", self.host)
                traceback.print_exc(file=sys.stdout)
                return

            if is_new:
                print_error("saving certificate for", self.host)
                os.rename(temporary_path, cert_path)

        s.settimeout(60)
        self.s = s
        self.is_connected = True
        print_error("connected to", self.host, self.port)


    def run_tcp(self):
        try:
            #if self.use_ssl: self.s.do_handshake()
            out = ''
            while self.is_connected:
                try: 
                    timeout = False
                    msg = self.s.recv(1024)
                except socket.timeout:
                    timeout = True
                except ssl.SSLError:
                    timeout = True
                except socket.error, err:
                    if err.errno == 60:
                        timeout = True
                    elif err.errno in [11, 10035]:
                        print_error("socket errno", err.errno)
                        time.sleep(0.1)
                        continue
                    else:
                        traceback.print_exc(file=sys.stdout)
                        raise

                if timeout:
                    # ping the server with server.version, as a real ping does not exist yet
                    self.send([('server.version', [ELECTRUM_VERSION, PROTOCOL_VERSION])], self.on_version)
                    continue

                out += msg
                self.bytes_received += len(msg)
                if msg == '': 
                    self.is_connected = False

                while True:
                    s = out.find('\n')
                    if s==-1: break
                    c = out[0:s]
                    out = out[s+1:]
                    c = json.loads(c)
                    self.queue_json_response(c)

        except Exception:
            traceback.print_exc(file=sys.stdout)

        self.is_connected = False


    def send_tcp(self, messages, callback):
        """return the ids of the requests that we sent"""
        out = ''
        ids = []
        for m in messages:
            method, params = m 
            request = json.dumps( { 'id':self.message_id, 'method':method, 'params':params } )
            self.unanswered_requests[self.message_id] = method, params, callback
            ids.append(self.message_id)
            if self.debug:
                print "-->", request
            self.message_id += 1
            out += request + '\n'
        while out:
            try:
                sent = self.s.send( out )
                out = out[sent:]
            except socket.error,e:
                if e[0] in (errno.EWOULDBLOCK,errno.EAGAIN):
                    print_error( "EAGAIN: retrying")
                    time.sleep(0.1)
                    continue
                else:
                    traceback.print_exc(file=sys.stdout)
                    # this happens when we get disconnected
                    print_error( "Not connected, cannot send" )
                    return None
        return ids





    def start_interface(self):

        if self.protocol in 'st':
            self.start_tcp()
        elif self.protocol in 'gh':
            self.start_http()

        self.connect_event.set()



    def stop_subscriptions(self):
        for callback in self.subscriptions.keys():
            callback(self, None)
        self.subscriptions = {}


    def send(self, messages, callback):

        sub = []
        for message in messages:
            m, v = message
            if m[-10:] == '.subscribe':
                sub.append(message)

        if sub:
            with self.lock:
                if self.subscriptions.get(callback) is None: 
                    self.subscriptions[callback] = []
                for message in sub:
                    if message not in self.subscriptions[callback]:
                        self.subscriptions[callback].append(message)

        if not self.is_connected: 
            print_error("interface: trying to send while not connected")
            return

        if self.protocol in 'st':
            with self.lock:
                out = self.send_tcp(messages, callback)
        else:
            # do not use lock, http is synchronous
            out = self.send_http(messages, callback)

        return out


    def parse_proxy_options(self, s):
        if type(s) == type({}): return s  # fixme: type should be fixed
        if type(s) != type(""): return None  
        if s.lower() == 'none': return None
        proxy = { "mode":"socks5", "host":"localhost" }
        args = s.split(':')
        n = 0
        if proxy_modes.count(args[n]) == 1:
            proxy["mode"] = args[n]
            n += 1
        if len(args) > n:
            proxy["host"] = args[n]
            n += 1
        if len(args) > n:
            proxy["port"] = args[n]
        else:
            proxy["port"] = "8080" if proxy["mode"] == "http" else "1080"
        return proxy



    def stop(self):
        if self.is_connected and self.protocol in 'st' and self.s:
            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()

        self.is_connected = False


    def is_up_to_date(self):
        return self.unanswered_requests == {}



    def start(self, queue = None, wait = False):
        if not self.server:
            return
        self.queue = queue if queue else Queue.Queue()
        threading.Thread.start(self)
        if wait:
            self.connect_event.wait()


    def run(self):
        self.start_interface()
        if self.is_connected:
            self.send([('server.version', [ELECTRUM_VERSION, PROTOCOL_VERSION])], self.on_version)
            self.change_status()
            self.run_tcp() if self.protocol in 'st' else self.run_http()
        self.change_status()
        

    def change_status(self):
        #print "change status", self.server, self.is_connected
        self.queue.put(self)


    def synchronous_get(self, requests, timeout=100000000):
        queue = Queue.Queue()
        ids = self.send(requests, lambda i,r: queue.put(r))
        id2 = ids[:]
        res = {}
        while ids:
            r = queue.get(True, timeout)
            _id = r.get('id')
            if _id in ids:
                ids.remove(_id)
                res[_id] = r.get('result')
        out = []
        for _id in id2:
            out.append(res[_id])
        return out


if __name__ == "__main__":

    check_certificates()

########NEW FILE########
__FILENAME__ = mnemonic
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.



# list of words from http://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/Contemporary_poetry

words = [
"like",
"just",
"love",
"know",
"never",
"want",
"time",
"out",
"there",
"make",
"look",
"eye",
"down",
"only",
"think",
"heart",
"back",
"then",
"into",
"about",
"more",
"away",
"still",
"them",
"take",
"thing",
"even",
"through",
"long",
"always",
"world",
"too",
"friend",
"tell",
"try",
"hand",
"thought",
"over",
"here",
"other",
"need",
"smile",
"again",
"much",
"cry",
"been",
"night",
"ever",
"little",
"said",
"end",
"some",
"those",
"around",
"mind",
"people",
"girl",
"leave",
"dream",
"left",
"turn",
"myself",
"give",
"nothing",
"really",
"off",
"before",
"something",
"find",
"walk",
"wish",
"good",
"once",
"place",
"ask",
"stop",
"keep",
"watch",
"seem",
"everything",
"wait",
"got",
"yet",
"made",
"remember",
"start",
"alone",
"run",
"hope",
"maybe",
"believe",
"body",
"hate",
"after",
"close",
"talk",
"stand",
"own",
"each",
"hurt",
"help",
"home",
"god",
"soul",
"new",
"many",
"two",
"inside",
"should",
"true",
"first",
"fear",
"mean",
"better",
"play",
"another",
"gone",
"change",
"use",
"wonder",
"someone",
"hair",
"cold",
"open",
"best",
"any",
"behind",
"happen",
"water",
"dark",
"laugh",
"stay",
"forever",
"name",
"work",
"show",
"sky",
"break",
"came",
"deep",
"door",
"put",
"black",
"together",
"upon",
"happy",
"such",
"great",
"white",
"matter",
"fill",
"past",
"please",
"burn",
"cause",
"enough",
"touch",
"moment",
"soon",
"voice",
"scream",
"anything",
"stare",
"sound",
"red",
"everyone",
"hide",
"kiss",
"truth",
"death",
"beautiful",
"mine",
"blood",
"broken",
"very",
"pass",
"next",
"forget",
"tree",
"wrong",
"air",
"mother",
"understand",
"lip",
"hit",
"wall",
"memory",
"sleep",
"free",
"high",
"realize",
"school",
"might",
"skin",
"sweet",
"perfect",
"blue",
"kill",
"breath",
"dance",
"against",
"fly",
"between",
"grow",
"strong",
"under",
"listen",
"bring",
"sometimes",
"speak",
"pull",
"person",
"become",
"family",
"begin",
"ground",
"real",
"small",
"father",
"sure",
"feet",
"rest",
"young",
"finally",
"land",
"across",
"today",
"different",
"guy",
"line",
"fire",
"reason",
"reach",
"second",
"slowly",
"write",
"eat",
"smell",
"mouth",
"step",
"learn",
"three",
"floor",
"promise",
"breathe",
"darkness",
"push",
"earth",
"guess",
"save",
"song",
"above",
"along",
"both",
"color",
"house",
"almost",
"sorry",
"anymore",
"brother",
"okay",
"dear",
"game",
"fade",
"already",
"apart",
"warm",
"beauty",
"heard",
"notice",
"question",
"shine",
"began",
"piece",
"whole",
"shadow",
"secret",
"street",
"within",
"finger",
"point",
"morning",
"whisper",
"child",
"moon",
"green",
"story",
"glass",
"kid",
"silence",
"since",
"soft",
"yourself",
"empty",
"shall",
"angel",
"answer",
"baby",
"bright",
"dad",
"path",
"worry",
"hour",
"drop",
"follow",
"power",
"war",
"half",
"flow",
"heaven",
"act",
"chance",
"fact",
"least",
"tired",
"children",
"near",
"quite",
"afraid",
"rise",
"sea",
"taste",
"window",
"cover",
"nice",
"trust",
"lot",
"sad",
"cool",
"force",
"peace",
"return",
"blind",
"easy",
"ready",
"roll",
"rose",
"drive",
"held",
"music",
"beneath",
"hang",
"mom",
"paint",
"emotion",
"quiet",
"clear",
"cloud",
"few",
"pretty",
"bird",
"outside",
"paper",
"picture",
"front",
"rock",
"simple",
"anyone",
"meant",
"reality",
"road",
"sense",
"waste",
"bit",
"leaf",
"thank",
"happiness",
"meet",
"men",
"smoke",
"truly",
"decide",
"self",
"age",
"book",
"form",
"alive",
"carry",
"escape",
"damn",
"instead",
"able",
"ice",
"minute",
"throw",
"catch",
"leg",
"ring",
"course",
"goodbye",
"lead",
"poem",
"sick",
"corner",
"desire",
"known",
"problem",
"remind",
"shoulder",
"suppose",
"toward",
"wave",
"drink",
"jump",
"woman",
"pretend",
"sister",
"week",
"human",
"joy",
"crack",
"grey",
"pray",
"surprise",
"dry",
"knee",
"less",
"search",
"bleed",
"caught",
"clean",
"embrace",
"future",
"king",
"son",
"sorrow",
"chest",
"hug",
"remain",
"sat",
"worth",
"blow",
"daddy",
"final",
"parent",
"tight",
"also",
"create",
"lonely",
"safe",
"cross",
"dress",
"evil",
"silent",
"bone",
"fate",
"perhaps",
"anger",
"class",
"scar",
"snow",
"tiny",
"tonight",
"continue",
"control",
"dog",
"edge",
"mirror",
"month",
"suddenly",
"comfort",
"given",
"loud",
"quickly",
"gaze",
"plan",
"rush",
"stone",
"town",
"battle",
"ignore",
"spirit",
"stood",
"stupid",
"yours",
"brown",
"build",
"dust",
"hey",
"kept",
"pay",
"phone",
"twist",
"although",
"ball",
"beyond",
"hidden",
"nose",
"taken",
"fail",
"float",
"pure",
"somehow",
"wash",
"wrap",
"angry",
"cheek",
"creature",
"forgotten",
"heat",
"rip",
"single",
"space",
"special",
"weak",
"whatever",
"yell",
"anyway",
"blame",
"job",
"choose",
"country",
"curse",
"drift",
"echo",
"figure",
"grew",
"laughter",
"neck",
"suffer",
"worse",
"yeah",
"disappear",
"foot",
"forward",
"knife",
"mess",
"somewhere",
"stomach",
"storm",
"beg",
"idea",
"lift",
"offer",
"breeze",
"field",
"five",
"often",
"simply",
"stuck",
"win",
"allow",
"confuse",
"enjoy",
"except",
"flower",
"seek",
"strength",
"calm",
"grin",
"gun",
"heavy",
"hill",
"large",
"ocean",
"shoe",
"sigh",
"straight",
"summer",
"tongue",
"accept",
"crazy",
"everyday",
"exist",
"grass",
"mistake",
"sent",
"shut",
"surround",
"table",
"ache",
"brain",
"destroy",
"heal",
"nature",
"shout",
"sign",
"stain",
"choice",
"doubt",
"glance",
"glow",
"mountain",
"queen",
"stranger",
"throat",
"tomorrow",
"city",
"either",
"fish",
"flame",
"rather",
"shape",
"spin",
"spread",
"ash",
"distance",
"finish",
"image",
"imagine",
"important",
"nobody",
"shatter",
"warmth",
"became",
"feed",
"flesh",
"funny",
"lust",
"shirt",
"trouble",
"yellow",
"attention",
"bare",
"bite",
"money",
"protect",
"amaze",
"appear",
"born",
"choke",
"completely",
"daughter",
"fresh",
"friendship",
"gentle",
"probably",
"six",
"deserve",
"expect",
"grab",
"middle",
"nightmare",
"river",
"thousand",
"weight",
"worst",
"wound",
"barely",
"bottle",
"cream",
"regret",
"relationship",
"stick",
"test",
"crush",
"endless",
"fault",
"itself",
"rule",
"spill",
"art",
"circle",
"join",
"kick",
"mask",
"master",
"passion",
"quick",
"raise",
"smooth",
"unless",
"wander",
"actually",
"broke",
"chair",
"deal",
"favorite",
"gift",
"note",
"number",
"sweat",
"box",
"chill",
"clothes",
"lady",
"mark",
"park",
"poor",
"sadness",
"tie",
"animal",
"belong",
"brush",
"consume",
"dawn",
"forest",
"innocent",
"pen",
"pride",
"stream",
"thick",
"clay",
"complete",
"count",
"draw",
"faith",
"press",
"silver",
"struggle",
"surface",
"taught",
"teach",
"wet",
"bless",
"chase",
"climb",
"enter",
"letter",
"melt",
"metal",
"movie",
"stretch",
"swing",
"vision",
"wife",
"beside",
"crash",
"forgot",
"guide",
"haunt",
"joke",
"knock",
"plant",
"pour",
"prove",
"reveal",
"steal",
"stuff",
"trip",
"wood",
"wrist",
"bother",
"bottom",
"crawl",
"crowd",
"fix",
"forgive",
"frown",
"grace",
"loose",
"lucky",
"party",
"release",
"surely",
"survive",
"teacher",
"gently",
"grip",
"speed",
"suicide",
"travel",
"treat",
"vein",
"written",
"cage",
"chain",
"conversation",
"date",
"enemy",
"however",
"interest",
"million",
"page",
"pink",
"proud",
"sway",
"themselves",
"winter",
"church",
"cruel",
"cup",
"demon",
"experience",
"freedom",
"pair",
"pop",
"purpose",
"respect",
"shoot",
"softly",
"state",
"strange",
"bar",
"birth",
"curl",
"dirt",
"excuse",
"lord",
"lovely",
"monster",
"order",
"pack",
"pants",
"pool",
"scene",
"seven",
"shame",
"slide",
"ugly",
"among",
"blade",
"blonde",
"closet",
"creek",
"deny",
"drug",
"eternity",
"gain",
"grade",
"handle",
"key",
"linger",
"pale",
"prepare",
"swallow",
"swim",
"tremble",
"wheel",
"won",
"cast",
"cigarette",
"claim",
"college",
"direction",
"dirty",
"gather",
"ghost",
"hundred",
"loss",
"lung",
"orange",
"present",
"swear",
"swirl",
"twice",
"wild",
"bitter",
"blanket",
"doctor",
"everywhere",
"flash",
"grown",
"knowledge",
"numb",
"pressure",
"radio",
"repeat",
"ruin",
"spend",
"unknown",
"buy",
"clock",
"devil",
"early",
"false",
"fantasy",
"pound",
"precious",
"refuse",
"sheet",
"teeth",
"welcome",
"add",
"ahead",
"block",
"bury",
"caress",
"content",
"depth",
"despite",
"distant",
"marry",
"purple",
"threw",
"whenever",
"bomb",
"dull",
"easily",
"grasp",
"hospital",
"innocence",
"normal",
"receive",
"reply",
"rhyme",
"shade",
"someday",
"sword",
"toe",
"visit",
"asleep",
"bought",
"center",
"consider",
"flat",
"hero",
"history",
"ink",
"insane",
"muscle",
"mystery",
"pocket",
"reflection",
"shove",
"silently",
"smart",
"soldier",
"spot",
"stress",
"train",
"type",
"view",
"whether",
"bus",
"energy",
"explain",
"holy",
"hunger",
"inch",
"magic",
"mix",
"noise",
"nowhere",
"prayer",
"presence",
"shock",
"snap",
"spider",
"study",
"thunder",
"trail",
"admit",
"agree",
"bag",
"bang",
"bound",
"butterfly",
"cute",
"exactly",
"explode",
"familiar",
"fold",
"further",
"pierce",
"reflect",
"scent",
"selfish",
"sharp",
"sink",
"spring",
"stumble",
"universe",
"weep",
"women",
"wonderful",
"action",
"ancient",
"attempt",
"avoid",
"birthday",
"branch",
"chocolate",
"core",
"depress",
"drunk",
"especially",
"focus",
"fruit",
"honest",
"match",
"palm",
"perfectly",
"pillow",
"pity",
"poison",
"roar",
"shift",
"slightly",
"thump",
"truck",
"tune",
"twenty",
"unable",
"wipe",
"wrote",
"coat",
"constant",
"dinner",
"drove",
"egg",
"eternal",
"flight",
"flood",
"frame",
"freak",
"gasp",
"glad",
"hollow",
"motion",
"peer",
"plastic",
"root",
"screen",
"season",
"sting",
"strike",
"team",
"unlike",
"victim",
"volume",
"warn",
"weird",
"attack",
"await",
"awake",
"built",
"charm",
"crave",
"despair",
"fought",
"grant",
"grief",
"horse",
"limit",
"message",
"ripple",
"sanity",
"scatter",
"serve",
"split",
"string",
"trick",
"annoy",
"blur",
"boat",
"brave",
"clearly",
"cling",
"connect",
"fist",
"forth",
"imagination",
"iron",
"jock",
"judge",
"lesson",
"milk",
"misery",
"nail",
"naked",
"ourselves",
"poet",
"possible",
"princess",
"sail",
"size",
"snake",
"society",
"stroke",
"torture",
"toss",
"trace",
"wise",
"bloom",
"bullet",
"cell",
"check",
"cost",
"darling",
"during",
"footstep",
"fragile",
"hallway",
"hardly",
"horizon",
"invisible",
"journey",
"midnight",
"mud",
"nod",
"pause",
"relax",
"shiver",
"sudden",
"value",
"youth",
"abuse",
"admire",
"blink",
"breast",
"bruise",
"constantly",
"couple",
"creep",
"curve",
"difference",
"dumb",
"emptiness",
"gotta",
"honor",
"plain",
"planet",
"recall",
"rub",
"ship",
"slam",
"soar",
"somebody",
"tightly",
"weather",
"adore",
"approach",
"bond",
"bread",
"burst",
"candle",
"coffee",
"cousin",
"crime",
"desert",
"flutter",
"frozen",
"grand",
"heel",
"hello",
"language",
"level",
"movement",
"pleasure",
"powerful",
"random",
"rhythm",
"settle",
"silly",
"slap",
"sort",
"spoken",
"steel",
"threaten",
"tumble",
"upset",
"aside",
"awkward",
"bee",
"blank",
"board",
"button",
"card",
"carefully",
"complain",
"crap",
"deeply",
"discover",
"drag",
"dread",
"effort",
"entire",
"fairy",
"giant",
"gotten",
"greet",
"illusion",
"jeans",
"leap",
"liquid",
"march",
"mend",
"nervous",
"nine",
"replace",
"rope",
"spine",
"stole",
"terror",
"accident",
"apple",
"balance",
"boom",
"childhood",
"collect",
"demand",
"depression",
"eventually",
"faint",
"glare",
"goal",
"group",
"honey",
"kitchen",
"laid",
"limb",
"machine",
"mere",
"mold",
"murder",
"nerve",
"painful",
"poetry",
"prince",
"rabbit",
"shelter",
"shore",
"shower",
"soothe",
"stair",
"steady",
"sunlight",
"tangle",
"tease",
"treasure",
"uncle",
"begun",
"bliss",
"canvas",
"cheer",
"claw",
"clutch",
"commit",
"crimson",
"crystal",
"delight",
"doll",
"existence",
"express",
"fog",
"football",
"gay",
"goose",
"guard",
"hatred",
"illuminate",
"mass",
"math",
"mourn",
"rich",
"rough",
"skip",
"stir",
"student",
"style",
"support",
"thorn",
"tough",
"yard",
"yearn",
"yesterday",
"advice",
"appreciate",
"autumn",
"bank",
"beam",
"bowl",
"capture",
"carve",
"collapse",
"confusion",
"creation",
"dove",
"feather",
"girlfriend",
"glory",
"government",
"harsh",
"hop",
"inner",
"loser",
"moonlight",
"neighbor",
"neither",
"peach",
"pig",
"praise",
"screw",
"shield",
"shimmer",
"sneak",
"stab",
"subject",
"throughout",
"thrown",
"tower",
"twirl",
"wow",
"army",
"arrive",
"bathroom",
"bump",
"cease",
"cookie",
"couch",
"courage",
"dim",
"guilt",
"howl",
"hum",
"husband",
"insult",
"led",
"lunch",
"mock",
"mostly",
"natural",
"nearly",
"needle",
"nerd",
"peaceful",
"perfection",
"pile",
"price",
"remove",
"roam",
"sanctuary",
"serious",
"shiny",
"shook",
"sob",
"stolen",
"tap",
"vain",
"void",
"warrior",
"wrinkle",
"affection",
"apologize",
"blossom",
"bounce",
"bridge",
"cheap",
"crumble",
"decision",
"descend",
"desperately",
"dig",
"dot",
"flip",
"frighten",
"heartbeat",
"huge",
"lazy",
"lick",
"odd",
"opinion",
"process",
"puzzle",
"quietly",
"retreat",
"score",
"sentence",
"separate",
"situation",
"skill",
"soak",
"square",
"stray",
"taint",
"task",
"tide",
"underneath",
"veil",
"whistle",
"anywhere",
"bedroom",
"bid",
"bloody",
"burden",
"careful",
"compare",
"concern",
"curtain",
"decay",
"defeat",
"describe",
"double",
"dreamer",
"driver",
"dwell",
"evening",
"flare",
"flicker",
"grandma",
"guitar",
"harm",
"horrible",
"hungry",
"indeed",
"lace",
"melody",
"monkey",
"nation",
"object",
"obviously",
"rainbow",
"salt",
"scratch",
"shown",
"shy",
"stage",
"stun",
"third",
"tickle",
"useless",
"weakness",
"worship",
"worthless",
"afternoon",
"beard",
"boyfriend",
"bubble",
"busy",
"certain",
"chin",
"concrete",
"desk",
"diamond",
"doom",
"drawn",
"due",
"felicity",
"freeze",
"frost",
"garden",
"glide",
"harmony",
"hopefully",
"hunt",
"jealous",
"lightning",
"mama",
"mercy",
"peel",
"physical",
"position",
"pulse",
"punch",
"quit",
"rant",
"respond",
"salty",
"sane",
"satisfy",
"savior",
"sheep",
"slept",
"social",
"sport",
"tuck",
"utter",
"valley",
"wolf",
"aim",
"alas",
"alter",
"arrow",
"awaken",
"beaten",
"belief",
"brand",
"ceiling",
"cheese",
"clue",
"confidence",
"connection",
"daily",
"disguise",
"eager",
"erase",
"essence",
"everytime",
"expression",
"fan",
"flag",
"flirt",
"foul",
"fur",
"giggle",
"glorious",
"ignorance",
"law",
"lifeless",
"measure",
"mighty",
"muse",
"north",
"opposite",
"paradise",
"patience",
"patient",
"pencil",
"petal",
"plate",
"ponder",
"possibly",
"practice",
"slice",
"spell",
"stock",
"strife",
"strip",
"suffocate",
"suit",
"tender",
"tool",
"trade",
"velvet",
"verse",
"waist",
"witch",
"aunt",
"bench",
"bold",
"cap",
"certainly",
"click",
"companion",
"creator",
"dart",
"delicate",
"determine",
"dish",
"dragon",
"drama",
"drum",
"dude",
"everybody",
"feast",
"forehead",
"former",
"fright",
"fully",
"gas",
"hook",
"hurl",
"invite",
"juice",
"manage",
"moral",
"possess",
"raw",
"rebel",
"royal",
"scale",
"scary",
"several",
"slight",
"stubborn",
"swell",
"talent",
"tea",
"terrible",
"thread",
"torment",
"trickle",
"usually",
"vast",
"violence",
"weave",
"acid",
"agony",
"ashamed",
"awe",
"belly",
"blend",
"blush",
"character",
"cheat",
"common",
"company",
"coward",
"creak",
"danger",
"deadly",
"defense",
"define",
"depend",
"desperate",
"destination",
"dew",
"duck",
"dusty",
"embarrass",
"engine",
"example",
"explore",
"foe",
"freely",
"frustrate",
"generation",
"glove",
"guilty",
"health",
"hurry",
"idiot",
"impossible",
"inhale",
"jaw",
"kingdom",
"mention",
"mist",
"moan",
"mumble",
"mutter",
"observe",
"ode",
"pathetic",
"pattern",
"pie",
"prefer",
"puff",
"rape",
"rare",
"revenge",
"rude",
"scrape",
"spiral",
"squeeze",
"strain",
"sunset",
"suspend",
"sympathy",
"thigh",
"throne",
"total",
"unseen",
"weapon",
"weary"
]



n = 1626

# Note about US patent no 5892470: Here each word does not represent a given digit.
# Instead, the digit represented by a word is variable, it depends on the previous word.

def mn_encode( message ):
    out = []
    for i in range(len(message)/8):
        word = message[8*i:8*i+8]
        x = int(word, 16)
        w1 = (x%n)
        w2 = ((x/n) + w1)%n
        w3 = ((x/n/n) + w2)%n
        out += [ words[w1], words[w2], words[w3] ]
    return out

def mn_decode( wlist ):
    out = ''
    for i in range(len(wlist)/3):
        word1, word2, word3 = wlist[3*i:3*i+3]
        w1 =  words.index(word1)
        w2 = (words.index(word2))%n
        w3 = (words.index(word3))%n
        x = w1 +n*((w2-w1)%n) +n*n*((w3-w2)%n)
        out += '%08x'%x
    return out


if __name__ == '__main__':
    import sys
    if len( sys.argv ) == 1:
        print 'I need arguments: a hex string to encode, or a list of words to decode'
    elif len( sys.argv ) == 2:
        print ' '.join(mn_encode(sys.argv[1]))
    else:
        print mn_decode(sys.argv[1:])

########NEW FILE########
__FILENAME__ = msqr
# from http://eli.thegreenplace.net/2009/03/07/computing-modular-square-roots-in-python/

def modular_sqrt(a, p):
    """ Find a quadratic residue (mod p) of 'a'. p
    must be an odd prime.
    
    Solve the congruence of the form:
    x^2 = a (mod p)
    And returns x. Note that p - x is also a root.
    
    0 is returned is no square root exists for
    these a and p.
    
    The Tonelli-Shanks algorithm is used (except
    for some simple cases in which the solution
    is known from an identity). This algorithm
    runs in polynomial time (unless the
    generalized Riemann hypothesis is false).
    """
    # Simple cases
    #
    if legendre_symbol(a, p) != 1:
        return 0
    elif a == 0:
        return 0
    elif p == 2:
        return p
    elif p % 4 == 3:
        return pow(a, (p + 1) / 4, p)
    
    # Partition p-1 to s * 2^e for an odd s (i.e.
    # reduce all the powers of 2 from p-1)
    #
    s = p - 1
    e = 0
    while s % 2 == 0:
        s /= 2
        e += 1
        
    # Find some 'n' with a legendre symbol n|p = -1.
    # Shouldn't take long.
    #
    n = 2
    while legendre_symbol(n, p) != -1:
        n += 1
        
    # Here be dragons!
    # Read the paper "Square roots from 1; 24, 51,
    # 10 to Dan Shanks" by Ezra Brown for more
    # information
    #
    
    # x is a guess of the square root that gets better
    # with each iteration.
    # b is the "fudge factor" - by how much we're off
    # with the guess. The invariant x^2 = ab (mod p)
    # is maintained throughout the loop.
    # g is used for successive powers of n to update
    # both a and b
    # r is the exponent - decreases with each update
    #
    x = pow(a, (s + 1) / 2, p)
    b = pow(a, s, p)
    g = pow(n, s, p)
    r = e
    
    while True:
        t = b
        m = 0
        for m in xrange(r):
            if t == 1:
                break
            t = pow(t, 2, p)
            
        if m == 0:
            return x
        
        gs = pow(g, 2 ** (r - m - 1), p)
        g = (gs * gs) % p
        x = (x * gs) % p
        b = (b * g) % p
        r = m
        
def legendre_symbol(a, p):
    """ Compute the Legendre symbol a|p using
    Euler's criterion. p is a prime, a is
    relatively prime to p (if p divides
    a, then a|p = 0)
    
    Returns 1 if a has a square root modulo
    p, -1 otherwise.
    """
    ls = pow(a, (p - 1) / 2, p)
    return -1 if ls == p - 1 else ls

########NEW FILE########
__FILENAME__ = network
import threading, time, Queue, os, sys, shutil, random
from util import user_dir, appdata_dir, print_error, print_msg
from bitcoin import *
import interface
from blockchain import Blockchain

DEFAULT_PORTS = {'t':'50001', 's':'50002', 'h':'8081', 'g':'8082'}

DEFAULT_SERVERS = {
    'ecdsa.org': DEFAULT_PORTS,
    'ecdsa.net': DEFAULT_PORTS,
    'electrum.hachre.de': DEFAULT_PORTS,
    'electrum.novit.ro': DEFAULT_PORTS,
    'electrum.coinwallet.me': DEFAULT_PORTS,
    'cube.l0g.in': DEFAULT_PORTS,
    'bitcoin.epicinet.net': DEFAULT_PORTS,
    'h.1209k.com': DEFAULT_PORTS,
    'electrum.electricnewyear.net': DEFAULT_PORTS,
    'erbium.sytes.net': DEFAULT_PORTS,
    'e2.pdmc.net':DEFAULT_PORTS,
    'electrum.no-ip.org':{'h': '80', 's': '50002', 't': '50001', 'g': '443'},
    'electrum.thwg.org':DEFAULT_PORTS,
    'electrum.stepkrav.pw':DEFAULT_PORTS,
}


def parse_servers(result):
    """ parse servers list into dict format"""
    from version import PROTOCOL_VERSION
    servers = {}
    for item in result:
        host = item[1]
        out = {}
        version = None
        pruning_level = '-'
        if len(item) > 2:
            for v in item[2]:
                if re.match("[stgh]\d*", v):
                    protocol, port = v[0], v[1:]
                    if port == '': port = DEFAULT_PORTS[protocol]
                    out[protocol] = port
                elif re.match("v(.?)+", v):
                    version = v[1:]
                elif re.match("p\d*", v):
                    pruning_level = v[1:]
                if pruning_level == '': pruning_level = '0'
        try: 
            is_recent = float(version)>=float(PROTOCOL_VERSION)
        except Exception:
            is_recent = False

        if out and is_recent:
            out['pruning'] = pruning_level
            servers[host] = out

    return servers



def filter_protocol(servers, p):
    l = []
    for k, protocols in servers.items():
        if p in protocols:
            l.append( ':'.join([k, protocols[p], p]) )
    return l
    

def pick_random_server(p='s'):
    return random.choice( filter_protocol(DEFAULT_SERVERS,p) )

from simple_config import SimpleConfig

class Network(threading.Thread):

    def __init__(self, config = {}):
        threading.Thread.__init__(self)
        self.daemon = True
        self.config = SimpleConfig(config) if type(config) == type({}) else config
        self.lock = threading.Lock()
        self.num_server = 8 if not self.config.get('oneserver') else 0
        self.blockchain = Blockchain(self.config, self)
        self.interfaces = {}
        self.queue = Queue.Queue()
        self.callbacks = {}
        self.protocol = self.config.get('protocol','s')
        self.running = False

        # Server for addresses and transactions
        self.default_server = self.config.get('server')
        if not self.default_server:
            self.default_server = pick_random_server(self.protocol)

        self.irc_servers = [] # returned by interface (list from irc)
        self.pending_servers = set([])
        self.disconnected_servers = set([])
        self.recent_servers = self.config.get('recent_servers',[]) # successful connections

        self.banner = ''
        self.interface = None
        self.proxy = self.config.get('proxy')
        self.heights = {}
        self.merkle_roots = {}
        self.utxo_roots = {}
        self.server_lag = 0

        dir_path = os.path.join( self.config.path, 'certs')
        if not os.path.exists(dir_path):
            os.mkdir(dir_path)

        # default subscriptions
        self.subscriptions = {}
        self.subscriptions[self.on_banner] = [('server.banner',[])]
        self.subscriptions[self.on_peers] = [('server.peers.subscribe',[])]
        self.pending_transactions_for_notifications = []


    def is_connected(self):
        return self.interface and self.interface.is_connected


    def is_up_to_date(self):
        return self.interface.is_up_to_date()


    def main_server(self):
        return self.interface.server


    def send_subscriptions(self):
        for cb, sub in self.subscriptions.items():
            self.interface.send(sub, cb)


    def subscribe(self, messages, callback):
        with self.lock:
            if self.subscriptions.get(callback) is None: 
                self.subscriptions[callback] = []
            for message in messages:
                if message not in self.subscriptions[callback]:
                    self.subscriptions[callback].append(message)

        if self.is_connected():
            self.interface.send( messages, callback )


    def send(self, messages, callback):
        if self.is_connected():
            self.interface.send( messages, callback )
            return True
        else:
            return False


    def register_callback(self, event, callback):
        with self.lock:
            if not self.callbacks.get(event):
                self.callbacks[event] = []
            self.callbacks[event].append(callback)


    def trigger_callback(self, event):
        with self.lock:
            callbacks = self.callbacks.get(event,[])[:]
        if callbacks:
            [callback() for callback in callbacks]


    def random_server(self):
        choice_list = []
        l = filter_protocol(self.get_servers(), self.protocol)
        for s in l:
            if s in self.pending_servers or s in self.disconnected_servers or s in self.interfaces.keys():
                continue
            else:
                choice_list.append(s)
        
        if not choice_list: 
            if not self.interfaces:
                # we are probably offline, retry later
                self.disconnected_servers = set([])
            return
        
        server = random.choice( choice_list )
        return server


    def get_servers(self):
        if self.irc_servers:
            out = self.irc_servers  
        else:
            out = DEFAULT_SERVERS
            for s in self.recent_servers:
                host, port, protocol = s.split(':')
                if host not in out:
                    out[host] = { protocol:port }
        return out

    def start_interface(self, server):
        if server in self.interfaces.keys():
            return
        i = interface.Interface(server, self.config)
        self.pending_servers.add(server)
        i.start(self.queue)
        return i 

    def start_random_interface(self):
        server = self.random_server()
        if server:
            self.start_interface(server)

    def start_interfaces(self):
        self.interface = self.start_interface(self.default_server)

        for i in range(self.num_server):
            self.start_random_interface()
            

    def start(self, wait=False):
        self.start_interfaces()
        threading.Thread.start(self)
        if wait:
            return self.wait_until_connected()

    def wait_until_connected(self):
        "wait until connection status is known"
        if self.config.get('auto_cycle'): 
            # self.random_server() returns None if all servers have been tried
            while not self.is_connected() and self.random_server():
                time.sleep(0.1)
        else:
            self.interface.connect_event.wait()

        return self.interface.is_connected


    def set_parameters(self, host, port, protocol, proxy, auto_connect):

        self.config.set_key('auto_cycle', auto_connect, True)
        self.config.set_key("proxy", proxy, True)
        self.config.set_key("protocol", protocol, True)
        server = ':'.join([ host, port, protocol ])
        self.config.set_key("server", server, True)

        if self.proxy != proxy or self.protocol != protocol:
            self.proxy = proxy
            self.protocol = protocol
            for i in self.interfaces.values(): i.stop()
            if auto_connect:
                #self.interface = None
                return

        if auto_connect:
            if not self.interface.is_connected:
                self.switch_to_random_interface()
            else:
                if self.server_lag > 0:
                    self.stop_interface()
        else:
            self.set_server(server)


    def switch_to_random_interface(self):
        if self.interfaces:
            self.switch_to_interface(random.choice(self.interfaces.values()))

    def switch_to_interface(self, interface):
        assert not self.interface.is_connected
        server = interface.server
        print_error("switching to", server)
        self.interface = interface
        h =  self.heights.get(server)
        if h:
            self.server_lag = self.blockchain.height() - h
        self.config.set_key('server', server, False)
        self.default_server = server
        self.send_subscriptions()
        self.trigger_callback('connected')


    def stop_interface(self):
        self.interface.stop() 


    def set_server(self, server):
        if self.default_server == server and self.interface.is_connected:
            return

        if self.protocol != server.split(':')[2]:
            return

        # stop the interface in order to terminate subscriptions
        if self.interface.is_connected:
            self.stop_interface()

        # notify gui
        self.trigger_callback('disconnecting')
        # start interface
        self.default_server = server
        self.config.set_key("server", server, True)

        if server in self.interfaces.keys():
            self.switch_to_interface( self.interfaces[server] )
        else:
            self.interface = self.start_interface(server)
        

    def add_recent_server(self, i):
        # list is ordered
        s = i.server
        if s in self.recent_servers:
            self.recent_servers.remove(s)
        self.recent_servers.insert(0,s)
        self.recent_servers = self.recent_servers[0:20]
        self.config.set_key('recent_servers', self.recent_servers)


    def new_blockchain_height(self, blockchain_height, i):
        if self.is_connected():
            h = self.heights.get(self.interface.server)
            if h:
                self.server_lag = blockchain_height - h
                if self.server_lag > 1:
                    print_error( "Server is lagging", blockchain_height, h)
                    if self.config.get('auto_cycle'):
                        self.set_server(i.server)
            else:
                print_error('no height for main interface')
        
        self.trigger_callback('updated')


    def run(self):
        self.blockchain.start()

        with self.lock:
            self.running = True

        while self.is_running():
            try:
                i = self.queue.get(timeout = 30 if self.interfaces else 3)
            except Queue.Empty:
                if len(self.interfaces) < self.num_server:
                    self.start_random_interface()
                continue

            if i.server in self.pending_servers:
                self.pending_servers.remove(i.server)

            if i.is_connected:
                #if i.server in self.interfaces: raise
                self.interfaces[i.server] = i
                self.add_recent_server(i)
                i.send([ ('blockchain.headers.subscribe',[])], self.on_header)
                if i == self.interface:
                    print_error('sending subscriptions to', self.interface.server)
                    self.send_subscriptions()
                    self.trigger_callback('connected')
            else:
                self.disconnected_servers.add(i.server)
                if i.server in self.interfaces:
                    self.interfaces.pop(i.server)
                if i.server in self.heights:
                    self.heights.pop(i.server)
                if i == self.interface:
                    #self.interface = None
                    self.trigger_callback('disconnected')

            if not self.interface.is_connected and self.config.get('auto_cycle'):
                self.switch_to_random_interface()


    def on_header(self, i, r):
        result = r.get('result')
        if not result: return
        height = result.get('block_height')
        self.heights[i.server] = height
        self.merkle_roots[i.server] = result.get('merkle_root')
        self.utxo_roots[i.server] = result.get('utxo_root')
        # notify blockchain about the new height
        self.blockchain.queue.put((i,result))

        if i == self.interface:
            self.server_lag = self.blockchain.height() - height
            if self.server_lag > 1 and self.config.get('auto_cycle'):
                print_error( "Server lagging, stopping interface")
                self.stop_interface()

            self.trigger_callback('updated')


    def on_peers(self, i, r):
        if not r: return
        self.irc_servers = parse_servers(r.get('result'))
        self.trigger_callback('peers')

    def on_banner(self, i, r):
        self.banner = r.get('result')
        self.trigger_callback('banner')

    def stop(self):
        with self.lock: self.running = False

    def is_running(self):
        with self.lock: return self.running

    
    def synchronous_get(self, requests, timeout=100000000):
        return self.interface.synchronous_get(requests)


    def get_header(self, tx_height):
        return self.blockchain.read_header(tx_height)

    def get_local_height(self):
        return self.blockchain.height()



    #def retrieve_transaction(self, tx_hash, tx_height=0):
    #    import transaction
    #    r = self.synchronous_get([ ('blockchain.transaction.get',[tx_hash, tx_height]) ])[0]
    #    if r:
    #        return transaction.Transaction(r)





if __name__ == "__main__":
    network = NetworkProxy({})
    network.start()
    print network.get_servers()

    q = Queue.Queue()
    network.send([('blockchain.headers.subscribe',[])], q.put)
    while True:
        r = q.get(timeout=10000)
        print r


########NEW FILE########
__FILENAME__ = paymentrequest
import hashlib
import httplib
import os.path
import re
import sys
import threading
import time
import traceback
import urllib2

try:
    import paymentrequest_pb2
except:
    print "protoc --proto_path=lib/ --python_out=lib/ lib/paymentrequest.proto"
    raise Exception()

import urlparse
import requests
from M2Crypto import X509

from bitcoin import is_valid
import urlparse


import util
import transaction


REQUEST_HEADERS = {'Accept': 'application/bitcoin-paymentrequest', 'User-Agent': 'Electrum'}
ACK_HEADERS = {'Content-Type':'application/bitcoin-payment','Accept':'application/bitcoin-paymentack','User-Agent':'Electrum'}

ca_path = os.path.expanduser("~/.electrum/ca/ca-bundle.crt")
ca_list = {}
try:
    with open(ca_path, 'r') as ca_f:
        c = ""
        for line in ca_f:
            if line == "-----BEGIN CERTIFICATE-----\n":
                c = line
            else:
                c += line
            if line == "-----END CERTIFICATE-----\n":
                x = X509.load_cert_string(c)
                ca_list[x.get_fingerprint()] = x
except Exception:
    print "ERROR: Could not open %s"%ca_path
    print "ca-bundle.crt file should be placed in ~/.electrum/ca/ca-bundle.crt"
    print "Documentation on how to download or create the file here: http://curl.haxx.se/docs/caextract.html"
    print "Payment will continue with manual verification."
    raise Exception()


class PaymentRequest:

    def __init__(self, url):
        self.url = url
        self.outputs = []
        self.error = ""

    def get_amount(self):
        return sum(map(lambda x:x[1], self.outputs))


    def verify(self):
        u = urlparse.urlparse(self.url)
        self.domain = u.netloc

        try:
            connection = httplib.HTTPConnection(u.netloc) if u.scheme == 'http' else httplib.HTTPSConnection(u.netloc)
            connection.request("GET",u.geturl(), headers=REQUEST_HEADERS)
            resp = connection.getresponse()
        except:
            self.error = "cannot read url"
            return

        paymntreq = paymentrequest_pb2.PaymentRequest()
        try:
            r = resp.read()
            paymntreq.ParseFromString(r)
        except:
            self.error = "cannot parse payment request"
            return

        sig = paymntreq.signature
        if not sig:
            self.error = "No signature"
            return 

        cert = paymentrequest_pb2.X509Certificates()
        cert.ParseFromString(paymntreq.pki_data)
        cert_num = len(cert.certificate)

        x509_1 = X509.load_cert_der_string(cert.certificate[0])
        if self.domain != x509_1.get_subject().CN:
            validcert = False
            try:
                SANs = x509_1.get_ext("subjectAltName").get_value().split(",")
                for s in SANs:
                    s = s.strip()
                    if s.startswith("DNS:") and s[4:] == self.domain:
                        validcert = True
                        print "Match SAN DNS"
                    elif s.startswith("IP:") and s[3:] == self.domain:
                        validcert = True
                        print "Match SAN IP"
                    elif s.startswith("email:") and s[6:] == self.domain:
                        validcert = True
                        print "Match SAN email"
            except Exception, e:
                print "ERROR: No SAN data"
            if not validcert:
                ###TODO: check for wildcards
                self.error = "ERROR: Certificate Subject Domain Mismatch and SAN Mismatch"
                return

        x509 = []
        CA_OU = ''

        if cert_num > 1:
            for i in range(cert_num - 1):
                x509.append(X509.load_cert_der_string(cert.certificate[i+1]))
                if x509[i].check_ca() == 0:
                    self.error = "ERROR: Supplied CA Certificate Error"
                    return
            for i in range(cert_num - 1):
                if i == 0:
                    if x509_1.verify(x509[i].get_pubkey()) != 1:
                        self.error = "ERROR: Certificate not Signed by Provided CA Certificate Chain"
                        return
                else:
                    if x509[i-1].verify(x509[i].get_pubkey()) != 1:
                        self.error = "ERROR: CA Certificate not Signed by Provided CA Certificate Chain"
                        return

            supplied_CA_fingerprint = x509[cert_num-2].get_fingerprint()
            supplied_CA_CN = x509[cert_num-2].get_subject().CN
            CA_match = False

            x = ca_list.get(supplied_CA_fingerprint)
            if x:
                CA_OU = x.get_subject().OU
                CA_match = True
                if x.get_subject().CN != supplied_CA_CN:
                    print "ERROR: Trusted CA CN Mismatch; however CA has trusted fingerprint"
                    print "Payment will continue with manual verification."
            else:
                print "ERROR: Supplied CA Not Found in Trusted CA Store."
                print "Payment will continue with manual verification."
        else:
            self.error = "ERROR: CA Certificate Chain Not Provided by Payment Processor"
            return False

        paymntreq.signature = ''
        s = paymntreq.SerializeToString()
        pubkey_1 = x509_1.get_pubkey()

        if paymntreq.pki_type == "x509+sha256":
            pubkey_1.reset_context(md="sha256")
        elif paymntreq.pki_type == "x509+sha1":
            pubkey_1.reset_context(md="sha1")
        else:
            self.error = "ERROR: Unsupported PKI Type for Message Signature"
            return False

        pubkey_1.verify_init()
        pubkey_1.verify_update(s)
        if pubkey_1.verify_final(sig) != 1:
            self.error = "ERROR: Invalid Signature for Payment Request Data"
            return False

        ### SIG Verified

        self.payment_details = pay_det = paymentrequest_pb2.PaymentDetails()
        pay_det.ParseFromString(paymntreq.serialized_payment_details)

        if pay_det.expires and pay_det.expires < int(time.time()):
            self.error = "ERROR: Payment Request has Expired."
            return False

        for o in pay_det.outputs:
            addr = transaction.get_address_from_output_script(o.script)[1]
            self.outputs.append( (addr, o.amount) )

        self.memo = pay_det.memo

        if CA_match:
            print 'Signed By Trusted CA: ', CA_OU

        print "payment url", pay_det.payment_url
        return True



    def send_ack(self, raw_tx, refund_addr):

        pay_det = self.payment_details
        if not pay_det.payment_url:
            return False, "no url"

        paymnt = paymentrequest_pb2.Payment()
        paymnt.merchant_data = pay_det.merchant_data
        paymnt.transactions.append(raw_tx)

        ref_out = paymnt.refund_to.add()
        ref_out.script = transaction.Transaction.pay_script(refund_addr)
        paymnt.memo = "Paid using Electrum"
        pm = paymnt.SerializeToString()

        payurl = urlparse.urlparse(pay_det.payment_url)
        try:
            r = requests.post(payurl.geturl(), data=pm, headers=ACK_HEADERS, verify=ca_path)
        except requests.exceptions.SSLError:
            print "Payment Message/PaymentACK verify Failed"
            try:
                r = requests.post(payurl.geturl(), data=pm, headers=ACK_HEADERS, verify=False)
            except Exception as e:
                print e
                return False, "Payment Message/PaymentACK Failed"

        if r.status_code >= 500:
            return False, r.reason

        try:
            paymntack = paymentrequest_pb2.PaymentACK()
            paymntack.ParseFromString(r.content)
        except Exception:
            return False, "PaymentACK could not be processed. Payment was sent; please manually verify that payment was received."

        print "PaymentACK message received: %s" % paymntack.memo
        return True, paymntack.memo




if __name__ == "__main__":

    try:
        uri = sys.argv[1]
    except:
        print "usage: %s url"%sys.argv[0]
        print "example url: \"bitcoin:mpu3yTLdqA1BgGtFUwkVJmhnU3q5afaFkf?r=https%3A%2F%2Fbitcoincore.org%2F%7Egavin%2Ff.php%3Fh%3D2a828c05b8b80dc440c80a5d58890298&amount=1\""
        sys.exit(1)

    address, amount, label, message, request_url, url = util.parse_url(uri)
    pr = PaymentRequest(request_url)
    if not pr.verify():
        sys.exit(1)

    print 'Payment Request Verified Domain: ', pr.domain
    print 'outputs', pr.outputs
    print 'Payment Memo: ', pr.payment_details.memo

    tx = "blah"
    pr.send_ack(tx, refund_addr = "1vXAXUnGitimzinpXrqDWVU4tyAAQ34RA")


########NEW FILE########
__FILENAME__ = plugins
from util import print_error
import traceback, sys
from util import *
from i18n import _

plugins = []


def init_plugins(self):
    import imp, pkgutil, __builtin__, os
    global plugins

    if __builtin__.use_local_modules:
        fp, pathname, description = imp.find_module('plugins')
        plugin_names = [name for a, name, b in pkgutil.iter_modules([pathname])]
        plugin_names = filter( lambda name: os.path.exists(os.path.join(pathname,name+'.py')), plugin_names)
        imp.load_module('electrum_plugins', fp, pathname, description)
        plugin_modules = map(lambda name: imp.load_source('electrum_plugins.'+name, os.path.join(pathname,name+'.py')), plugin_names)
    else:
        import electrum_plugins
        plugin_names = [name for a, name, b in pkgutil.iter_modules(electrum_plugins.__path__)]
        plugin_modules = [ __import__('electrum_plugins.'+name, fromlist=['electrum_plugins']) for name in plugin_names]

    for name, p in zip(plugin_names, plugin_modules):
        try:
            plugins.append( p.Plugin(self, name) )
        except Exception:
            print_msg(_("Error: cannot initialize plugin"),p)
            traceback.print_exc(file=sys.stdout)



def run_hook(name, *args):
    
    global plugins

    for p in plugins:

        if not p.is_enabled():
            continue

        f = getattr(p, name, None)
        if not callable(f):
            continue

        try:
            f(*args)
        except Exception:
            print_error("Plugin error")
            traceback.print_exc(file=sys.stdout)
            
    return



class BasePlugin:

    def __init__(self, gui, name):
        self.gui = gui
        self.name = name
        self.config = gui.config

    def fullname(self):
        return self.name

    def description(self):
        return 'undefined'

    def requires_settings(self):
        return False

    def toggle(self):
        if self.is_enabled():
            if self.disable():
                self.close()
        else:
            if self.enable():
                self.init()

        return self.is_enabled()

    
    def enable(self):
        self.set_enabled(True)
        return True

    def disable(self):
        self.set_enabled(False)
        return True

    def init(self): pass

    def close(self): pass

    def is_enabled(self):
        return self.is_available() and self.config.get('use_'+self.name) is True

    def is_available(self):
        return True

    def set_enabled(self, enabled):
        self.config.set_key('use_'+self.name, enabled, True)

    def settings_dialog(self):
        pass

########NEW FILE########
__FILENAME__ = pyqrnative
import math

#from PIL import Image, ImageDraw

#QRCode for Python
#
#Ported from the Javascript library by Sam Curren
#
#QRCode for Javascript
#http://d-project.googlecode.com/svn/trunk/misc/qrcode/js/qrcode.js
#
#Copyright (c) 2009 Kazuhiko Arase
#
#URL: http://www.d-project.com/
#
#Licensed under the MIT license:
#   http://www.opensource.org/licenses/mit-license.php
#
# The word "QR Code" is registered trademark of
# DENSO WAVE INCORPORATED
#   http://www.denso-wave.com/qrcode/faqpatent-e.html


class QR8bitByte:

    def __init__(self, data):
        self.mode = QRMode.MODE_8BIT_BYTE
        self.data = data

    def getLength(self):
        return len(self.data)

    def write(self, buffer):
        for i in range(len(self.data)):
            #// not JIS ...
            buffer.put(ord(self.data[i]), 8)
    def __repr__(self):
        return self.data

class QRCode:
    def __init__(self, typeNumber, errorCorrectLevel):
        self.typeNumber = typeNumber
        self.errorCorrectLevel = errorCorrectLevel
        self.modules = None
        self.moduleCount = 0
        self.dataCache = None
        self.dataList = []
    def addData(self, data):
        newData = QR8bitByte(data)
        self.dataList.append(newData)
        self.dataCache = None
    def isDark(self, row, col):
        if (row < 0 or self.moduleCount <= row or col < 0 or self.moduleCount <= col):
            raise Exception("%s,%s - %s" % (row, col, self.moduleCount))
        return self.modules[row][col]
    def getModuleCount(self):
        return self.moduleCount
    def make(self):
        self.makeImpl(False, self.getBestMaskPattern() )
    def makeImpl(self, test, maskPattern):

        self.moduleCount = self.typeNumber * 4 + 17
        self.modules = [None for x in range(self.moduleCount)]

        for row in range(self.moduleCount):

            self.modules[row] = [None for x in range(self.moduleCount)]

            for col in range(self.moduleCount):
                self.modules[row][col] = None #//(col + row) % 3;

        self.setupPositionProbePattern(0, 0)
        self.setupPositionProbePattern(self.moduleCount - 7, 0)
        self.setupPositionProbePattern(0, self.moduleCount - 7)
        self.setupPositionAdjustPattern()
        self.setupTimingPattern()
        self.setupTypeInfo(test, maskPattern)

        if (self.typeNumber >= 7):
            self.setupTypeNumber(test)

        if (self.dataCache == None):
            self.dataCache = QRCode.createData(self.typeNumber, self.errorCorrectLevel, self.dataList)
        self.mapData(self.dataCache, maskPattern)

    def setupPositionProbePattern(self, row, col):

        for r in range(-1, 8):

            if (row + r <= -1 or self.moduleCount <= row + r): continue

            for c in range(-1, 8):

                if (col + c <= -1 or self.moduleCount <= col + c): continue

                if ( (0 <= r and r <= 6 and (c == 0 or c == 6) )
                        or (0 <= c and c <= 6 and (r == 0 or r == 6) )
                        or (2 <= r and r <= 4 and 2 <= c and c <= 4) ):
                    self.modules[row + r][col + c] = True;
                else:
                    self.modules[row + r][col + c] = False;

    def getBestMaskPattern(self):

        minLostPoint = 0
        pattern = 0

        for i in range(8):

            self.makeImpl(True, i);

            lostPoint = QRUtil.getLostPoint(self);

            if (i == 0 or minLostPoint > lostPoint):
                minLostPoint = lostPoint
                pattern = i

        return pattern


    def setupTimingPattern(self):

        for r in range(8, self.moduleCount - 8):
            if (self.modules[r][6] != None):
                continue
            self.modules[r][6] = (r % 2 == 0)

        for c in range(8, self.moduleCount - 8):
            if (self.modules[6][c] != None):
                continue
            self.modules[6][c] = (c % 2 == 0)

    def setupPositionAdjustPattern(self):

        pos = QRUtil.getPatternPosition(self.typeNumber)

        for i in range(len(pos)):

            for j in range(len(pos)):

                row = pos[i]
                col = pos[j]

                if (self.modules[row][col] != None):
                    continue

                for r in range(-2, 3):

                    for c in range(-2, 3):

                        if (r == -2 or r == 2 or c == -2 or c == 2 or (r == 0 and c == 0) ):
                            self.modules[row + r][col + c] = True
                        else:
                            self.modules[row + r][col + c] = False

    def setupTypeNumber(self, test):

        bits = QRUtil.getBCHTypeNumber(self.typeNumber)

        for i in range(18):
            mod = (not test and ( (bits >> i) & 1) == 1)
            self.modules[i // 3][i % 3 + self.moduleCount - 8 - 3] = mod;

        for i in range(18):
            mod = (not test and ( (bits >> i) & 1) == 1)
            self.modules[i % 3 + self.moduleCount - 8 - 3][i // 3] = mod;

    def setupTypeInfo(self, test, maskPattern):

        data = (self.errorCorrectLevel << 3) | maskPattern
        bits = QRUtil.getBCHTypeInfo(data)

        #// vertical
        for i in range(15):

            mod = (not test and ( (bits >> i) & 1) == 1)

            if (i < 6):
                self.modules[i][8] = mod
            elif (i < 8):
                self.modules[i + 1][8] = mod
            else:
                self.modules[self.moduleCount - 15 + i][8] = mod

        #// horizontal
        for i in range(15):

            mod = (not test and ( (bits >> i) & 1) == 1);

            if (i < 8):
                self.modules[8][self.moduleCount - i - 1] = mod
            elif (i < 9):
                self.modules[8][15 - i - 1 + 1] = mod
            else:
                self.modules[8][15 - i - 1] = mod

        #// fixed module
        self.modules[self.moduleCount - 8][8] = (not test)

    def mapData(self, data, maskPattern):

        inc = -1
        row = self.moduleCount - 1
        bitIndex = 7
        byteIndex = 0

        for col in range(self.moduleCount - 1, 0, -2):

            if (col == 6): col-=1

            while (True):

                for c in range(2):

                    if (self.modules[row][col - c] == None):

                        dark = False

                        if (byteIndex < len(data)):
                            dark = ( ( (data[byteIndex] >> bitIndex) & 1) == 1)

                        mask = QRUtil.getMask(maskPattern, row, col - c)

                        if (mask):
                            dark = not dark

                        self.modules[row][col - c] = dark
                        bitIndex-=1

                        if (bitIndex == -1):
                            byteIndex+=1
                            bitIndex = 7

                row += inc

                if (row < 0 or self.moduleCount <= row):
                    row -= inc
                    inc = -inc
                    break
    PAD0 = 0xEC
    PAD1 = 0x11

    @staticmethod
    def createData(typeNumber, errorCorrectLevel, dataList):

        rsBlocks = QRRSBlock.getRSBlocks(typeNumber, errorCorrectLevel)

        buffer = QRBitBuffer();

        for i in range(len(dataList)):
            data = dataList[i]
            buffer.put(data.mode, 4)
            buffer.put(data.getLength(), QRUtil.getLengthInBits(data.mode, typeNumber) )
            data.write(buffer)

        #// calc num max data.
        totalDataCount = 0;
        for i in range(len(rsBlocks)):
            totalDataCount += rsBlocks[i].dataCount

        if (buffer.getLengthInBits() > totalDataCount * 8):
            raise Exception("code length overflow. ("
                + buffer.getLengthInBits()
                + ">"
                +  totalDataCount * 8
                + ")")

        #// end code
        if (buffer.getLengthInBits() + 4 <= totalDataCount * 8):
            buffer.put(0, 4)

        #// padding
        while (buffer.getLengthInBits() % 8 != 0):
            buffer.putBit(False)

        #// padding
        while (True):

            if (buffer.getLengthInBits() >= totalDataCount * 8):
                break
            buffer.put(QRCode.PAD0, 8)

            if (buffer.getLengthInBits() >= totalDataCount * 8):
                break
            buffer.put(QRCode.PAD1, 8)

        return QRCode.createBytes(buffer, rsBlocks)

    @staticmethod
    def createBytes(buffer, rsBlocks):

        offset = 0

        maxDcCount = 0
        maxEcCount = 0

        dcdata = [0 for x in range(len(rsBlocks))]
        ecdata = [0 for x in range(len(rsBlocks))]

        for r in range(len(rsBlocks)):

            dcCount = rsBlocks[r].dataCount
            ecCount = rsBlocks[r].totalCount - dcCount

            maxDcCount = max(maxDcCount, dcCount)
            maxEcCount = max(maxEcCount, ecCount)

            dcdata[r] = [0 for x in range(dcCount)]

            for i in range(len(dcdata[r])):
                dcdata[r][i] = 0xff & buffer.buffer[i + offset]
            offset += dcCount

            rsPoly = QRUtil.getErrorCorrectPolynomial(ecCount)
            rawPoly = QRPolynomial(dcdata[r], rsPoly.getLength() - 1)

            modPoly = rawPoly.mod(rsPoly)
            ecdata[r] = [0 for x in range(rsPoly.getLength()-1)]
            for i in range(len(ecdata[r])):
                modIndex = i + modPoly.getLength() - len(ecdata[r])
                if (modIndex >= 0):
                    ecdata[r][i] = modPoly.get(modIndex)
                else:
                    ecdata[r][i] = 0

        totalCodeCount = 0
        for i in range(len(rsBlocks)):
            totalCodeCount += rsBlocks[i].totalCount

        data = [None for x in range(totalCodeCount)]
        index = 0

        for i in range(maxDcCount):
            for r in range(len(rsBlocks)):
                if (i < len(dcdata[r])):
                    data[index] = dcdata[r][i]
                    index+=1

        for i in range(maxEcCount):
            for r in range(len(rsBlocks)):
                if (i < len(ecdata[r])):
                    data[index] = ecdata[r][i]
                    index+=1

        return data


class QRMode:
    MODE_NUMBER = 1 << 0
    MODE_ALPHA_NUM = 1 << 1
    MODE_8BIT_BYTE = 1 << 2
    MODE_KANJI = 1 << 3

class QRErrorCorrectLevel:
    L = 1
    M = 0
    Q = 3
    H = 2

class QRMaskPattern:
    PATTERN000 = 0
    PATTERN001 = 1
    PATTERN010 = 2
    PATTERN011 = 3
    PATTERN100 = 4
    PATTERN101 = 5
    PATTERN110 = 6
    PATTERN111 = 7

class QRUtil(object):
    PATTERN_POSITION_TABLE = [
        [],
        [6, 18],
        [6, 22],
        [6, 26],
        [6, 30],
        [6, 34],
        [6, 22, 38],
        [6, 24, 42],
        [6, 26, 46],
        [6, 28, 50],
        [6, 30, 54],
        [6, 32, 58],
        [6, 34, 62],
        [6, 26, 46, 66],
        [6, 26, 48, 70],
        [6, 26, 50, 74],
        [6, 30, 54, 78],
        [6, 30, 56, 82],
        [6, 30, 58, 86],
        [6, 34, 62, 90],
        [6, 28, 50, 72, 94],
        [6, 26, 50, 74, 98],
        [6, 30, 54, 78, 102],
        [6, 28, 54, 80, 106],
        [6, 32, 58, 84, 110],
        [6, 30, 58, 86, 114],
        [6, 34, 62, 90, 118],
        [6, 26, 50, 74, 98, 122],
        [6, 30, 54, 78, 102, 126],
        [6, 26, 52, 78, 104, 130],
        [6, 30, 56, 82, 108, 134],
        [6, 34, 60, 86, 112, 138],
        [6, 30, 58, 86, 114, 142],
        [6, 34, 62, 90, 118, 146],
        [6, 30, 54, 78, 102, 126, 150],
        [6, 24, 50, 76, 102, 128, 154],
        [6, 28, 54, 80, 106, 132, 158],
        [6, 32, 58, 84, 110, 136, 162],
        [6, 26, 54, 82, 110, 138, 166],
        [6, 30, 58, 86, 114, 142, 170]
    ]

    G15 = (1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 2) | (1 << 1) | (1 << 0)
    G18 = (1 << 12) | (1 << 11) | (1 << 10) | (1 << 9) | (1 << 8) | (1 << 5) | (1 << 2) | (1 << 0)
    G15_MASK = (1 << 14) | (1 << 12) | (1 << 10) | (1 << 4) | (1 << 1)

    @staticmethod
    def getBCHTypeInfo(data):
        d = data << 10;
        while (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G15) >= 0):
            d ^= (QRUtil.G15 << (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G15) ) )

        return ( (data << 10) | d) ^ QRUtil.G15_MASK
    @staticmethod
    def getBCHTypeNumber(data):
        d = data << 12;
        while (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G18) >= 0):
            d ^= (QRUtil.G18 << (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G18) ) )
        return (data << 12) | d
    @staticmethod
    def getBCHDigit(data):
        digit = 0;
        while (data != 0):
            digit += 1
            data >>= 1
        return digit
    @staticmethod
    def getPatternPosition(typeNumber):
        return QRUtil.PATTERN_POSITION_TABLE[typeNumber - 1]
    @staticmethod
    def getMask(maskPattern, i, j):
        if maskPattern == QRMaskPattern.PATTERN000 : return (i + j) % 2 == 0
        if maskPattern == QRMaskPattern.PATTERN001 : return i % 2 == 0
        if maskPattern == QRMaskPattern.PATTERN010 : return j % 3 == 0
        if maskPattern == QRMaskPattern.PATTERN011 : return (i + j) % 3 == 0
        if maskPattern == QRMaskPattern.PATTERN100 : return (math.floor(i / 2) + math.floor(j / 3) ) % 2 == 0
        if maskPattern == QRMaskPattern.PATTERN101 : return (i * j) % 2 + (i * j) % 3 == 0
        if maskPattern == QRMaskPattern.PATTERN110 : return ( (i * j) % 2 + (i * j) % 3) % 2 == 0
        if maskPattern == QRMaskPattern.PATTERN111 : return ( (i * j) % 3 + (i + j) % 2) % 2 == 0
        raise Exception("bad maskPattern:" + maskPattern);
    @staticmethod
    def getErrorCorrectPolynomial(errorCorrectLength):
        a = QRPolynomial([1], 0);
        for i in range(errorCorrectLength):
            a = a.multiply(QRPolynomial([1, QRMath.gexp(i)], 0) )
        return a
    @staticmethod
    def getLengthInBits(mode, type):

        if 1 <= type and type < 10:

            #// 1 - 9

            if mode == QRMode.MODE_NUMBER     : return 10
            if mode == QRMode.MODE_ALPHA_NUM     : return 9
            if mode == QRMode.MODE_8BIT_BYTE    : return 8
            if mode == QRMode.MODE_KANJI      : return 8
            raise Exception("mode:" + mode)

        elif (type < 27):

            #// 10 - 26

            if mode == QRMode.MODE_NUMBER     : return 12
            if mode == QRMode.MODE_ALPHA_NUM     : return 11
            if mode == QRMode.MODE_8BIT_BYTE    : return 16
            if mode == QRMode.MODE_KANJI      : return 10
            raise Exception("mode:" + mode)

        elif (type < 41):

            #// 27 - 40

            if mode == QRMode.MODE_NUMBER     : return 14
            if mode == QRMode.MODE_ALPHA_NUM    : return 13
            if mode == QRMode.MODE_8BIT_BYTE    : return 16
            if mode == QRMode.MODE_KANJI      : return 12
            raise Exception("mode:" + mode)

        else:
            raise Exception("type:" + type)
    @staticmethod
    def getLostPoint(qrCode):

        moduleCount = qrCode.getModuleCount();

        lostPoint = 0;

        #// LEVEL1

        for row in range(moduleCount):

            for col in range(moduleCount):

                sameCount = 0;
                dark = qrCode.isDark(row, col);

                for r in range(-1, 2):

                    if (row + r < 0 or moduleCount <= row + r):
                        continue

                    for c in range(-1, 2):

                        if (col + c < 0 or moduleCount <= col + c):
                            continue
                        if (r == 0 and c == 0):
                            continue

                        if (dark == qrCode.isDark(row + r, col + c) ):
                            sameCount+=1
                if (sameCount > 5):
                    lostPoint += (3 + sameCount - 5)

        #// LEVEL2

        for row in range(moduleCount - 1):
            for col in range(moduleCount - 1):
                count = 0;
                if (qrCode.isDark(row,     col    ) ): count+=1
                if (qrCode.isDark(row + 1, col    ) ): count+=1
                if (qrCode.isDark(row,     col + 1) ): count+=1
                if (qrCode.isDark(row + 1, col + 1) ): count+=1
                if (count == 0 or count == 4):
                    lostPoint += 3

        #// LEVEL3

        for row in range(moduleCount):
            for col in range(moduleCount - 6):
                if (qrCode.isDark(row, col)
                        and not qrCode.isDark(row, col + 1)
                        and  qrCode.isDark(row, col + 2)
                        and  qrCode.isDark(row, col + 3)
                        and  qrCode.isDark(row, col + 4)
                        and not qrCode.isDark(row, col + 5)
                        and  qrCode.isDark(row, col + 6) ):
                    lostPoint += 40

        for col in range(moduleCount):
            for row in range(moduleCount - 6):
                if (qrCode.isDark(row, col)
                        and not qrCode.isDark(row + 1, col)
                        and  qrCode.isDark(row + 2, col)
                        and  qrCode.isDark(row + 3, col)
                        and  qrCode.isDark(row + 4, col)
                        and not qrCode.isDark(row + 5, col)
                        and  qrCode.isDark(row + 6, col) ):
                    lostPoint += 40

        #// LEVEL4

        darkCount = 0;

        for col in range(moduleCount):
            for row in range(moduleCount):
                if (qrCode.isDark(row, col) ):
                    darkCount+=1

        ratio = abs(100 * darkCount / moduleCount / moduleCount - 50) / 5
        lostPoint += ratio * 10

        return lostPoint

class QRMath:

    @staticmethod
    def glog(n):
        if (n < 1):
            raise Exception("glog(" + n + ")")
        return LOG_TABLE[n];
    @staticmethod
    def gexp(n):
        while n < 0:
            n += 255
        while n >= 256:
            n -= 255
        return EXP_TABLE[n];

EXP_TABLE = [x for x in range(256)]

LOG_TABLE = [x for x in range(256)]

for i in range(8):
    EXP_TABLE[i] = 1 << i;

for i in range(8, 256):
    EXP_TABLE[i] = EXP_TABLE[i - 4] ^ EXP_TABLE[i - 5] ^ EXP_TABLE[i - 6] ^ EXP_TABLE[i - 8]

for i in range(255):
    LOG_TABLE[EXP_TABLE[i] ] = i

class QRPolynomial:

    def __init__(self, num, shift):

        if (len(num) == 0):
            raise Exception(num.length + "/" + shift)

        offset = 0

        while offset < len(num) and num[offset] == 0:
            offset += 1

        self.num = [0 for x in range(len(num)-offset+shift)]
        for i in range(len(num) - offset):
            self.num[i] = num[i + offset]


    def get(self, index):
        return self.num[index]
    def getLength(self):
        return len(self.num)
    def multiply(self, e):
        num = [0 for x in range(self.getLength() + e.getLength() - 1)];

        for i in range(self.getLength()):
            for j in range(e.getLength()):
                num[i + j] ^= QRMath.gexp(QRMath.glog(self.get(i) ) + QRMath.glog(e.get(j) ) )

        return QRPolynomial(num, 0);
    def mod(self, e):

        if (self.getLength() - e.getLength() < 0):
            return self;

        ratio = QRMath.glog(self.get(0) ) - QRMath.glog(e.get(0) )

        num = [0 for x in range(self.getLength())]

        for i in range(self.getLength()):
            num[i] = self.get(i);

        for i in range(e.getLength()):
            num[i] ^= QRMath.gexp(QRMath.glog(e.get(i) ) + ratio)

        # recursive call
        return QRPolynomial(num, 0).mod(e);

class QRRSBlock:

    RS_BLOCK_TABLE = [

        #// L
        #// M
        #// Q
        #// H

        #// 1
        [1, 26, 19],
        [1, 26, 16],
        [1, 26, 13],
        [1, 26, 9],

        #// 2
        [1, 44, 34],
        [1, 44, 28],
        [1, 44, 22],
        [1, 44, 16],

        #// 3
        [1, 70, 55],
        [1, 70, 44],
        [2, 35, 17],
        [2, 35, 13],

        #// 4
        [1, 100, 80],
        [2, 50, 32],
        [2, 50, 24],
        [4, 25, 9],

        #// 5
        [1, 134, 108],
        [2, 67, 43],
        [2, 33, 15, 2, 34, 16],
        [2, 33, 11, 2, 34, 12],

        #// 6
        [2, 86, 68],
        [4, 43, 27],
        [4, 43, 19],
        [4, 43, 15],

        #// 7
        [2, 98, 78],
        [4, 49, 31],
        [2, 32, 14, 4, 33, 15],
        [4, 39, 13, 1, 40, 14],

        #// 8
        [2, 121, 97],
        [2, 60, 38, 2, 61, 39],
        [4, 40, 18, 2, 41, 19],
        [4, 40, 14, 2, 41, 15],

        #// 9
        [2, 146, 116],
        [3, 58, 36, 2, 59, 37],
        [4, 36, 16, 4, 37, 17],
        [4, 36, 12, 4, 37, 13],

        #// 10
        [2, 86, 68, 2, 87, 69],
        [4, 69, 43, 1, 70, 44],
        [6, 43, 19, 2, 44, 20],
        [6, 43, 15, 2, 44, 16],

      # 11
      [4, 101, 81],
      [1, 80, 50, 4, 81, 51],
      [4, 50, 22, 4, 51, 23],
      [3, 36, 12, 8, 37, 13],

      # 12
      [2, 116, 92, 2, 117, 93],
      [6, 58, 36, 2, 59, 37],
      [4, 46, 20, 6, 47, 21],
      [7, 42, 14, 4, 43, 15],

      # 13
      [4, 133, 107],
      [8, 59, 37, 1, 60, 38],
      [8, 44, 20, 4, 45, 21],
      [12, 33, 11, 4, 34, 12],

      # 14
      [3, 145, 115, 1, 146, 116],
      [4, 64, 40, 5, 65, 41],
      [11, 36, 16, 5, 37, 17],
      [11, 36, 12, 5, 37, 13],

      # 15
      [5, 109, 87, 1, 110, 88],
      [5, 65, 41, 5, 66, 42],
      [5, 54, 24, 7, 55, 25],
      [11, 36, 12],

      # 16
      [5, 122, 98, 1, 123, 99],
      [7, 73, 45, 3, 74, 46],
      [15, 43, 19, 2, 44, 20],
      [3, 45, 15, 13, 46, 16],

      # 17
      [1, 135, 107, 5, 136, 108],
      [10, 74, 46, 1, 75, 47],
      [1, 50, 22, 15, 51, 23],
      [2, 42, 14, 17, 43, 15],

      # 18
      [5, 150, 120, 1, 151, 121],
      [9, 69, 43, 4, 70, 44],
      [17, 50, 22, 1, 51, 23],
      [2, 42, 14, 19, 43, 15],

      # 19
      [3, 141, 113, 4, 142, 114],
      [3, 70, 44, 11, 71, 45],
      [17, 47, 21, 4, 48, 22],
      [9, 39, 13, 16, 40, 14],

      # 20
      [3, 135, 107, 5, 136, 108],
      [3, 67, 41, 13, 68, 42],
      [15, 54, 24, 5, 55, 25],
      [15, 43, 15, 10, 44, 16],

      # 21
      [4, 144, 116, 4, 145, 117],
      [17, 68, 42],
      [17, 50, 22, 6, 51, 23],
      [19, 46, 16, 6, 47, 17],

      # 22
      [2, 139, 111, 7, 140, 112],
      [17, 74, 46],
      [7, 54, 24, 16, 55, 25],
      [34, 37, 13],

      # 23
      [4, 151, 121, 5, 152, 122],
      [4, 75, 47, 14, 76, 48],
      [11, 54, 24, 14, 55, 25],
      [16, 45, 15, 14, 46, 16],

      # 24
      [6, 147, 117, 4, 148, 118],
      [6, 73, 45, 14, 74, 46],
      [11, 54, 24, 16, 55, 25],
      [30, 46, 16, 2, 47, 17],

      # 25
      [8, 132, 106, 4, 133, 107],
      [8, 75, 47, 13, 76, 48],
      [7, 54, 24, 22, 55, 25],
      [22, 45, 15, 13, 46, 16],

      # 26
      [10, 142, 114, 2, 143, 115],
      [19, 74, 46, 4, 75, 47],
      [28, 50, 22, 6, 51, 23],
      [33, 46, 16, 4, 47, 17],

      # 27
      [8, 152, 122, 4, 153, 123],
      [22, 73, 45, 3, 74, 46],
      [8, 53, 23, 26, 54, 24],
      [12, 45, 15, 28, 46, 16],

      # 28
      [3, 147, 117, 10, 148, 118],
      [3, 73, 45, 23, 74, 46],
      [4, 54, 24, 31, 55, 25],
      [11, 45, 15, 31, 46, 16],

      # 29
      [7, 146, 116, 7, 147, 117],
      [21, 73, 45, 7, 74, 46],
      [1, 53, 23, 37, 54, 24],
      [19, 45, 15, 26, 46, 16],

      # 30
      [5, 145, 115, 10, 146, 116],
      [19, 75, 47, 10, 76, 48],
      [15, 54, 24, 25, 55, 25],
      [23, 45, 15, 25, 46, 16],

      # 31
      [13, 145, 115, 3, 146, 116],
      [2, 74, 46, 29, 75, 47],
      [42, 54, 24, 1, 55, 25],
      [23, 45, 15, 28, 46, 16],

      # 32
      [17, 145, 115],
      [10, 74, 46, 23, 75, 47],
      [10, 54, 24, 35, 55, 25],
      [19, 45, 15, 35, 46, 16],

      # 33
      [17, 145, 115, 1, 146, 116],
      [14, 74, 46, 21, 75, 47],
      [29, 54, 24, 19, 55, 25],
      [11, 45, 15, 46, 46, 16],

      # 34
      [13, 145, 115, 6, 146, 116],
      [14, 74, 46, 23, 75, 47],
      [44, 54, 24, 7, 55, 25],
      [59, 46, 16, 1, 47, 17],

      # 35
      [12, 151, 121, 7, 152, 122],
      [12, 75, 47, 26, 76, 48],
      [39, 54, 24, 14, 55, 25],
      [22, 45, 15, 41, 46, 16],

      # 36
      [6, 151, 121, 14, 152, 122],
      [6, 75, 47, 34, 76, 48],
      [46, 54, 24, 10, 55, 25],
      [2, 45, 15, 64, 46, 16],

      # 37
      [17, 152, 122, 4, 153, 123],
      [29, 74, 46, 14, 75, 47],
      [49, 54, 24, 10, 55, 25],
      [24, 45, 15, 46, 46, 16],

      # 38
      [4, 152, 122, 18, 153, 123],
      [13, 74, 46, 32, 75, 47],
      [48, 54, 24, 14, 55, 25],
      [42, 45, 15, 32, 46, 16],

      # 39
      [20, 147, 117, 4, 148, 118],
      [40, 75, 47, 7, 76, 48],
      [43, 54, 24, 22, 55, 25],
      [10, 45, 15, 67, 46, 16],

      # 40
      [19, 148, 118, 6, 149, 119],
      [18, 75, 47, 31, 76, 48],
      [34, 54, 24, 34, 55, 25],
      [20, 45, 15, 61, 46, 16]

    ]

    def __init__(self, totalCount, dataCount):
        self.totalCount = totalCount
        self.dataCount = dataCount

    @staticmethod
    def getRSBlocks(typeNumber, errorCorrectLevel):
        rsBlock = QRRSBlock.getRsBlockTable(typeNumber, errorCorrectLevel);
        if rsBlock == None:
            raise Exception("bad rs block @ typeNumber:" + typeNumber + "/errorCorrectLevel:" + errorCorrectLevel)

        length = len(rsBlock) / 3

        list = []

        for i in range(length):

            count = rsBlock[i * 3 + 0]
            totalCount = rsBlock[i * 3 + 1]
            dataCount  = rsBlock[i * 3 + 2]

            for j in range(count):
                list.append(QRRSBlock(totalCount, dataCount))

        return list;

    @staticmethod
    def getRsBlockTable(typeNumber, errorCorrectLevel):
        if errorCorrectLevel == QRErrorCorrectLevel.L:
            return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 0];
        elif errorCorrectLevel == QRErrorCorrectLevel.M:
            return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 1];
        elif errorCorrectLevel ==  QRErrorCorrectLevel.Q:
            return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 2];
        elif errorCorrectLevel ==  QRErrorCorrectLevel.H:
            return QRRSBlock.RS_BLOCK_TABLE[(typeNumber - 1) * 4 + 3];
        else:
            return None;

class QRBitBuffer:
    def __init__(self):
        self.buffer = []
        self.length = 0
    def __repr__(self):
        return ".".join([str(n) for n in self.buffer])
    def get(self, index):
        bufIndex = math.floor(index / 8)
        val = ( (self.buffer[bufIndex] >> (7 - index % 8) ) & 1) == 1
        print "get ", val
        return ( (self.buffer[bufIndex] >> (7 - index % 8) ) & 1) == 1
    def put(self, num, length):
        for i in range(length):
            self.putBit( ( (num >> (length - i - 1) ) & 1) == 1)
    def getLengthInBits(self):
        return self.length
    def putBit(self, bit):
        bufIndex = self.length // 8
        if len(self.buffer) <= bufIndex:
            self.buffer.append(0)
        if bit:
            self.buffer[bufIndex] |= (0x80 >> (self.length % 8) )
        self.length+=1

########NEW FILE########
__FILENAME__ = ripemd
## ripemd.py - pure Python implementation of the RIPEMD-160 algorithm.
## Bjorn Edstrom <be@bjrn.se> 16 december 2007.
##
## Copyrights
## ==========
##
## This code is a derived from an implementation by Markus Friedl which is
## subject to the following license. This Python implementation is not
## subject to any other license.
##
##/*
## * Copyright (c) 2001 Markus Friedl.  All rights reserved.
## *
## * Redistribution and use in source and binary forms, with or without
## * modification, are permitted provided that the following conditions
## * are met:
## * 1. Redistributions of source code must retain the above copyright
## *    notice, this list of conditions and the following disclaimer.
## * 2. Redistributions in binary form must reproduce the above copyright
## *    notice, this list of conditions and the following disclaimer in the
## *    documentation and/or other materials provided with the distribution.
## *
## * THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
## * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
## * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
## * IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
## * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
## * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
## * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
## */
##/*
## * Preneel, Bosselaers, Dobbertin, "The Cryptographic Hash Function RIPEMD-160",
## * RSA Laboratories, CryptoBytes, Volume 3, Number 2, Autumn 1997,
## * ftp://ftp.rsasecurity.com/pub/cryptobytes/crypto3n2.pdf
## */

try:
    import psyco
    psyco.full()
except ImportError:
    pass

#block_size = 1
digest_size = 20
digestsize = 20

class RIPEMD160:
    """Return a new RIPEMD160 object. An optional string argument
    may be provided; if present, this string will be automatically
    hashed."""
    
    def __init__(self, arg=None):
        self.ctx = RMDContext()
        if arg:
            self.update(arg)
        self.dig = None
        
    def update(self, arg):
        """update(arg)"""        
        RMD160Update(self.ctx, arg, len(arg))
        self.dig = None
        
    def digest(self):
        """digest()"""        
        if self.dig:
            return self.dig
        ctx = self.ctx.copy()
        self.dig = RMD160Final(self.ctx)
        self.ctx = ctx
        return self.dig
    
    def hexdigest(self):
        """hexdigest()"""
        dig = self.digest()
        hex_digest = ''
        for d in dig:
            hex_digest += '%02x' % ord(d)
        return hex_digest
    
    def copy(self):
        """copy()"""        
        import copy
        return copy.deepcopy(self)



def new(arg=None):
    """Return a new RIPEMD160 object. An optional string argument
    may be provided; if present, this string will be automatically
    hashed."""    
    return RIPEMD160(arg)



#
# Private.
#

class RMDContext:
    def __init__(self):
        self.state = [0x67452301, 0xEFCDAB89, 0x98BADCFE,
                      0x10325476, 0xC3D2E1F0] # uint32
        self.count = 0 # uint64
        self.buffer = [0]*64 # uchar
    def copy(self):
        ctx = RMDContext()
        ctx.state = self.state[:]
        ctx.count = self.count
        ctx.buffer = self.buffer[:]
        return ctx

K0 = 0x00000000
K1 = 0x5A827999
K2 = 0x6ED9EBA1
K3 = 0x8F1BBCDC
K4 = 0xA953FD4E

KK0 = 0x50A28BE6
KK1 = 0x5C4DD124
KK2 = 0x6D703EF3
KK3 = 0x7A6D76E9
KK4 = 0x00000000

def ROL(n, x):
    return ((x << n) & 0xffffffff) | (x >> (32 - n))

def F0(x, y, z):
    return x ^ y ^ z

def F1(x, y, z):
    return (x & y) | (((~x) % 0x100000000) & z)

def F2(x, y, z):
    return (x | ((~y) % 0x100000000)) ^ z

def F3(x, y, z):
    return (x & z) | (((~z) % 0x100000000) & y)

def F4(x, y, z):
    return x ^ (y | ((~z) % 0x100000000))

def R(a, b, c, d, e, Fj, Kj, sj, rj, X):
    a = ROL(sj, (a + Fj(b, c, d) + X[rj] + Kj) % 0x100000000) + e
    c = ROL(10, c)
    return a % 0x100000000, c

PADDING = [0x80] + [0]*63

import sys
import struct

def RMD160Transform(state, block): #uint32 state[5], uchar block[64]
    x = [0]*16
    if sys.byteorder == 'little':
        x = struct.unpack('<16L', ''.join([chr(x) for x in block[0:64]]))
    else:
        raise "Error!!"
    a = state[0]
    b = state[1]
    c = state[2]
    d = state[3]
    e = state[4]

    #/* Round 1 */
    a, c = R(a, b, c, d, e, F0, K0, 11,  0, x);
    e, b = R(e, a, b, c, d, F0, K0, 14,  1, x);
    d, a = R(d, e, a, b, c, F0, K0, 15,  2, x);
    c, e = R(c, d, e, a, b, F0, K0, 12,  3, x);
    b, d = R(b, c, d, e, a, F0, K0,  5,  4, x);
    a, c = R(a, b, c, d, e, F0, K0,  8,  5, x);
    e, b = R(e, a, b, c, d, F0, K0,  7,  6, x);
    d, a = R(d, e, a, b, c, F0, K0,  9,  7, x);
    c, e = R(c, d, e, a, b, F0, K0, 11,  8, x);
    b, d = R(b, c, d, e, a, F0, K0, 13,  9, x);
    a, c = R(a, b, c, d, e, F0, K0, 14, 10, x);
    e, b = R(e, a, b, c, d, F0, K0, 15, 11, x);
    d, a = R(d, e, a, b, c, F0, K0,  6, 12, x);
    c, e = R(c, d, e, a, b, F0, K0,  7, 13, x);
    b, d = R(b, c, d, e, a, F0, K0,  9, 14, x);
    a, c = R(a, b, c, d, e, F0, K0,  8, 15, x); #/* #15 */
    #/* Round 2 */
    e, b = R(e, a, b, c, d, F1, K1,  7,  7, x);
    d, a = R(d, e, a, b, c, F1, K1,  6,  4, x);
    c, e = R(c, d, e, a, b, F1, K1,  8, 13, x);
    b, d = R(b, c, d, e, a, F1, K1, 13,  1, x);
    a, c = R(a, b, c, d, e, F1, K1, 11, 10, x);
    e, b = R(e, a, b, c, d, F1, K1,  9,  6, x);
    d, a = R(d, e, a, b, c, F1, K1,  7, 15, x);
    c, e = R(c, d, e, a, b, F1, K1, 15,  3, x);
    b, d = R(b, c, d, e, a, F1, K1,  7, 12, x);
    a, c = R(a, b, c, d, e, F1, K1, 12,  0, x);
    e, b = R(e, a, b, c, d, F1, K1, 15,  9, x);
    d, a = R(d, e, a, b, c, F1, K1,  9,  5, x);
    c, e = R(c, d, e, a, b, F1, K1, 11,  2, x);
    b, d = R(b, c, d, e, a, F1, K1,  7, 14, x);
    a, c = R(a, b, c, d, e, F1, K1, 13, 11, x);
    e, b = R(e, a, b, c, d, F1, K1, 12,  8, x); #/* #31 */
    #/* Round 3 */
    d, a = R(d, e, a, b, c, F2, K2, 11,  3, x);
    c, e = R(c, d, e, a, b, F2, K2, 13, 10, x);
    b, d = R(b, c, d, e, a, F2, K2,  6, 14, x);
    a, c = R(a, b, c, d, e, F2, K2,  7,  4, x);
    e, b = R(e, a, b, c, d, F2, K2, 14,  9, x);
    d, a = R(d, e, a, b, c, F2, K2,  9, 15, x);
    c, e = R(c, d, e, a, b, F2, K2, 13,  8, x);
    b, d = R(b, c, d, e, a, F2, K2, 15,  1, x);
    a, c = R(a, b, c, d, e, F2, K2, 14,  2, x);
    e, b = R(e, a, b, c, d, F2, K2,  8,  7, x);
    d, a = R(d, e, a, b, c, F2, K2, 13,  0, x);
    c, e = R(c, d, e, a, b, F2, K2,  6,  6, x);
    b, d = R(b, c, d, e, a, F2, K2,  5, 13, x);
    a, c = R(a, b, c, d, e, F2, K2, 12, 11, x);
    e, b = R(e, a, b, c, d, F2, K2,  7,  5, x);
    d, a = R(d, e, a, b, c, F2, K2,  5, 12, x); #/* #47 */
    #/* Round 4 */
    c, e = R(c, d, e, a, b, F3, K3, 11,  1, x);
    b, d = R(b, c, d, e, a, F3, K3, 12,  9, x);
    a, c = R(a, b, c, d, e, F3, K3, 14, 11, x);
    e, b = R(e, a, b, c, d, F3, K3, 15, 10, x);
    d, a = R(d, e, a, b, c, F3, K3, 14,  0, x);
    c, e = R(c, d, e, a, b, F3, K3, 15,  8, x);
    b, d = R(b, c, d, e, a, F3, K3,  9, 12, x);
    a, c = R(a, b, c, d, e, F3, K3,  8,  4, x);
    e, b = R(e, a, b, c, d, F3, K3,  9, 13, x);
    d, a = R(d, e, a, b, c, F3, K3, 14,  3, x);
    c, e = R(c, d, e, a, b, F3, K3,  5,  7, x);
    b, d = R(b, c, d, e, a, F3, K3,  6, 15, x);
    a, c = R(a, b, c, d, e, F3, K3,  8, 14, x);
    e, b = R(e, a, b, c, d, F3, K3,  6,  5, x);
    d, a = R(d, e, a, b, c, F3, K3,  5,  6, x);
    c, e = R(c, d, e, a, b, F3, K3, 12,  2, x); #/* #63 */
    #/* Round 5 */
    b, d = R(b, c, d, e, a, F4, K4,  9,  4, x);
    a, c = R(a, b, c, d, e, F4, K4, 15,  0, x);
    e, b = R(e, a, b, c, d, F4, K4,  5,  5, x);
    d, a = R(d, e, a, b, c, F4, K4, 11,  9, x);
    c, e = R(c, d, e, a, b, F4, K4,  6,  7, x);
    b, d = R(b, c, d, e, a, F4, K4,  8, 12, x);
    a, c = R(a, b, c, d, e, F4, K4, 13,  2, x);
    e, b = R(e, a, b, c, d, F4, K4, 12, 10, x);
    d, a = R(d, e, a, b, c, F4, K4,  5, 14, x);
    c, e = R(c, d, e, a, b, F4, K4, 12,  1, x);
    b, d = R(b, c, d, e, a, F4, K4, 13,  3, x);
    a, c = R(a, b, c, d, e, F4, K4, 14,  8, x);
    e, b = R(e, a, b, c, d, F4, K4, 11, 11, x);
    d, a = R(d, e, a, b, c, F4, K4,  8,  6, x);
    c, e = R(c, d, e, a, b, F4, K4,  5, 15, x);
    b, d = R(b, c, d, e, a, F4, K4,  6, 13, x); #/* #79 */

    aa = a;
    bb = b;
    cc = c;
    dd = d;
    ee = e;

    a = state[0]
    b = state[1]
    c = state[2]
    d = state[3]
    e = state[4]    

    #/* Parallel round 1 */
    a, c = R(a, b, c, d, e, F4, KK0,  8,  5, x)
    e, b = R(e, a, b, c, d, F4, KK0,  9, 14, x)
    d, a = R(d, e, a, b, c, F4, KK0,  9,  7, x)
    c, e = R(c, d, e, a, b, F4, KK0, 11,  0, x)
    b, d = R(b, c, d, e, a, F4, KK0, 13,  9, x)
    a, c = R(a, b, c, d, e, F4, KK0, 15,  2, x)
    e, b = R(e, a, b, c, d, F4, KK0, 15, 11, x)
    d, a = R(d, e, a, b, c, F4, KK0,  5,  4, x)
    c, e = R(c, d, e, a, b, F4, KK0,  7, 13, x)
    b, d = R(b, c, d, e, a, F4, KK0,  7,  6, x)
    a, c = R(a, b, c, d, e, F4, KK0,  8, 15, x)
    e, b = R(e, a, b, c, d, F4, KK0, 11,  8, x)
    d, a = R(d, e, a, b, c, F4, KK0, 14,  1, x)
    c, e = R(c, d, e, a, b, F4, KK0, 14, 10, x)
    b, d = R(b, c, d, e, a, F4, KK0, 12,  3, x)
    a, c = R(a, b, c, d, e, F4, KK0,  6, 12, x) #/* #15 */
    #/* Parallel round 2 */
    e, b = R(e, a, b, c, d, F3, KK1,  9,  6, x)
    d, a = R(d, e, a, b, c, F3, KK1, 13, 11, x)
    c, e = R(c, d, e, a, b, F3, KK1, 15,  3, x)
    b, d = R(b, c, d, e, a, F3, KK1,  7,  7, x)
    a, c = R(a, b, c, d, e, F3, KK1, 12,  0, x)
    e, b = R(e, a, b, c, d, F3, KK1,  8, 13, x)
    d, a = R(d, e, a, b, c, F3, KK1,  9,  5, x)
    c, e = R(c, d, e, a, b, F3, KK1, 11, 10, x)
    b, d = R(b, c, d, e, a, F3, KK1,  7, 14, x)
    a, c = R(a, b, c, d, e, F3, KK1,  7, 15, x)
    e, b = R(e, a, b, c, d, F3, KK1, 12,  8, x)
    d, a = R(d, e, a, b, c, F3, KK1,  7, 12, x)
    c, e = R(c, d, e, a, b, F3, KK1,  6,  4, x)
    b, d = R(b, c, d, e, a, F3, KK1, 15,  9, x)
    a, c = R(a, b, c, d, e, F3, KK1, 13,  1, x)
    e, b = R(e, a, b, c, d, F3, KK1, 11,  2, x) #/* #31 */
    #/* Parallel round 3 */
    d, a = R(d, e, a, b, c, F2, KK2,  9, 15, x)
    c, e = R(c, d, e, a, b, F2, KK2,  7,  5, x)
    b, d = R(b, c, d, e, a, F2, KK2, 15,  1, x)
    a, c = R(a, b, c, d, e, F2, KK2, 11,  3, x)
    e, b = R(e, a, b, c, d, F2, KK2,  8,  7, x)
    d, a = R(d, e, a, b, c, F2, KK2,  6, 14, x)
    c, e = R(c, d, e, a, b, F2, KK2,  6,  6, x)
    b, d = R(b, c, d, e, a, F2, KK2, 14,  9, x)
    a, c = R(a, b, c, d, e, F2, KK2, 12, 11, x)
    e, b = R(e, a, b, c, d, F2, KK2, 13,  8, x)
    d, a = R(d, e, a, b, c, F2, KK2,  5, 12, x)
    c, e = R(c, d, e, a, b, F2, KK2, 14,  2, x)
    b, d = R(b, c, d, e, a, F2, KK2, 13, 10, x)
    a, c = R(a, b, c, d, e, F2, KK2, 13,  0, x)
    e, b = R(e, a, b, c, d, F2, KK2,  7,  4, x)
    d, a = R(d, e, a, b, c, F2, KK2,  5, 13, x) #/* #47 */
    #/* Parallel round 4 */
    c, e = R(c, d, e, a, b, F1, KK3, 15,  8, x)
    b, d = R(b, c, d, e, a, F1, KK3,  5,  6, x)
    a, c = R(a, b, c, d, e, F1, KK3,  8,  4, x)
    e, b = R(e, a, b, c, d, F1, KK3, 11,  1, x)
    d, a = R(d, e, a, b, c, F1, KK3, 14,  3, x)
    c, e = R(c, d, e, a, b, F1, KK3, 14, 11, x)
    b, d = R(b, c, d, e, a, F1, KK3,  6, 15, x)
    a, c = R(a, b, c, d, e, F1, KK3, 14,  0, x)
    e, b = R(e, a, b, c, d, F1, KK3,  6,  5, x)
    d, a = R(d, e, a, b, c, F1, KK3,  9, 12, x)
    c, e = R(c, d, e, a, b, F1, KK3, 12,  2, x)
    b, d = R(b, c, d, e, a, F1, KK3,  9, 13, x)
    a, c = R(a, b, c, d, e, F1, KK3, 12,  9, x)
    e, b = R(e, a, b, c, d, F1, KK3,  5,  7, x)
    d, a = R(d, e, a, b, c, F1, KK3, 15, 10, x)
    c, e = R(c, d, e, a, b, F1, KK3,  8, 14, x) #/* #63 */
    #/* Parallel round 5 */
    b, d = R(b, c, d, e, a, F0, KK4,  8, 12, x)
    a, c = R(a, b, c, d, e, F0, KK4,  5, 15, x)
    e, b = R(e, a, b, c, d, F0, KK4, 12, 10, x)
    d, a = R(d, e, a, b, c, F0, KK4,  9,  4, x)
    c, e = R(c, d, e, a, b, F0, KK4, 12,  1, x)
    b, d = R(b, c, d, e, a, F0, KK4,  5,  5, x)
    a, c = R(a, b, c, d, e, F0, KK4, 14,  8, x)
    e, b = R(e, a, b, c, d, F0, KK4,  6,  7, x)
    d, a = R(d, e, a, b, c, F0, KK4,  8,  6, x)
    c, e = R(c, d, e, a, b, F0, KK4, 13,  2, x)
    b, d = R(b, c, d, e, a, F0, KK4,  6, 13, x)
    a, c = R(a, b, c, d, e, F0, KK4,  5, 14, x)
    e, b = R(e, a, b, c, d, F0, KK4, 15,  0, x)
    d, a = R(d, e, a, b, c, F0, KK4, 13,  3, x)
    c, e = R(c, d, e, a, b, F0, KK4, 11,  9, x)
    b, d = R(b, c, d, e, a, F0, KK4, 11, 11, x) #/* #79 */

    t = (state[1] + cc + d) % 0x100000000;
    state[1] = (state[2] + dd + e) % 0x100000000;
    state[2] = (state[3] + ee + a) % 0x100000000;
    state[3] = (state[4] + aa + b) % 0x100000000;
    state[4] = (state[0] + bb + c) % 0x100000000;
    state[0] = t % 0x100000000;

    pass


def RMD160Update(ctx, inp, inplen):
    if type(inp) == str:
        inp = [ord(i)&0xff for i in inp]
    
    have = (ctx.count / 8) % 64
    need = 64 - have
    ctx.count += 8 * inplen
    off = 0
    if inplen >= need:
        if have:
            for i in xrange(need):
                ctx.buffer[have+i] = inp[i]
            RMD160Transform(ctx.state, ctx.buffer)
            off = need
            have = 0
        while off + 64 <= inplen:
            RMD160Transform(ctx.state, inp[off:]) #<---
            off += 64
    if off < inplen:
        # memcpy(ctx->buffer + have, input+off, len-off);
        for i in xrange(inplen - off):
            ctx.buffer[have+i] = inp[off+i]

def RMD160Final(ctx):
    size = struct.pack("<Q", ctx.count)
    padlen = 64 - ((ctx.count / 8) % 64)
    if padlen < 1+8:
        padlen += 64
    RMD160Update(ctx, PADDING, padlen-8)
    RMD160Update(ctx, size, 8)
    return struct.pack("<5L", *ctx.state)


assert '37f332f68db77bd9d7edd4969571ad671cf9dd3b' == \
       new('The quick brown fox jumps over the lazy dog').hexdigest()
assert '132072df690933835eb8b6ad0b77e7b6f14acad7' == \
       new('The quick brown fox jumps over the lazy cog').hexdigest()
assert '9c1185a5c5e9fc54612808977ee8f548b2258d31' == \
       new('').hexdigest()

########NEW FILE########
__FILENAME__ = simple_config
import json
import ast
import threading
import os

from util import user_dir, print_error



class SimpleConfig:
    """
The SimpleConfig class is responsible for handling operations involving
configuration files.  The constructor reads and stores the system and 
user configurations from electrum.conf into separate dictionaries within
a SimpleConfig instance then reads the wallet file.
"""
    def __init__(self, options={}):
        self.lock = threading.Lock()

        # system conf, readonly
        self.system_config = {}
        if options.get('portable') is not True:
            self.read_system_config()

        # command-line options
        self.options_config = options

        # init path
        self.init_path()

        # user conf, writeable
        self.user_config = {}
        self.read_user_config()





    def init_path(self):

        # Read electrum path in the command line configuration
        self.path = self.options_config.get('electrum_path')

        # Read electrum path in the system configuration
        if self.path is None:
            self.path = self.system_config.get('electrum_path')

        # If not set, use the user's default data directory.
        if self.path is None:
            self.path = user_dir()

        # Make directory if it does not yet exist.
        if not os.path.exists(self.path):
            os.mkdir(self.path)

        print_error( "electrum directory", self.path)

        # portable wallet: use the same directory for wallet and headers file
        #if options.get('portable'):
        #    self.wallet_config['blockchain_headers_path'] = os.path.dirname(self.path)
            
    def set_key(self, key, value, save = True):
        # find where a setting comes from and save it there
        if self.options_config.get(key) is not None:
            print "Warning: not changing '%s' because it was passed as a command-line option"%key
            return

        elif self.system_config.get(key) is not None:
            if str(self.system_config[key]) != str(value):
                print "Warning: not changing '%s' because it was set in the system configuration"%key

        else:

            with self.lock:
                self.user_config[key] = value
                if save: 
                    self.save_user_config()



    def get(self, key, default=None):

        out = None

        # 1. command-line options always override everything
        if self.options_config.has_key(key) and self.options_config.get(key) is not None:
            out = self.options_config.get(key)

        # 2. user configuration 
        elif self.user_config.has_key(key):
            out = self.user_config.get(key)

        # 2. system configuration
        elif self.system_config.has_key(key):
            out = self.system_config.get(key)

        if out is None and default is not None:
            out = default

        # try to fix the type
        if default is not None and type(out) != type(default):
            import ast
            try:
                out = ast.literal_eval(out)
            except Exception:
                print "type error for '%s': using default value"%key
                out = default

        return out


    def is_modifiable(self, key):
        """Check if the config file is modifiable."""
        if self.options_config.has_key(key):
            return False
        elif self.user_config.has_key(key):
            return True
        elif self.system_config.has_key(key):
            return False
        else:
            return True


    def read_system_config(self):
        """Parse and store the system config settings in electrum.conf into system_config[]."""
        name = '/etc/electrum.conf'
        if os.path.exists(name):
            try:
                import ConfigParser
            except ImportError:
                print "cannot parse electrum.conf. please install ConfigParser"
                return
                
            p = ConfigParser.ConfigParser()
            p.read(name)
            try:
                for k, v in p.items('client'):
                    self.system_config[k] = v
            except ConfigParser.NoSectionError:
                pass


    def read_user_config(self):
        """Parse and store the user config settings in electrum.conf into user_config[]."""
        if not self.path: return

        path = os.path.join(self.path, "config")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = f.read()
            except IOError:
                return
            try:
                d = ast.literal_eval( data )  #parse raw data from reading wallet file
            except Exception:
                raise IOError("Cannot read config file.")

            self.user_config = d


    def save_user_config(self):
        if not self.path: return

        path = os.path.join(self.path, "config")
        s = repr(self.user_config)
        f = open(path,"w")
        f.write( s )
        f.close()
        if self.get('gui') != 'android':
            import stat
            os.chmod(path, stat.S_IREAD | stat.S_IWRITE)

########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.
   
THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

"""

import socket
import struct
import sys

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        self.sendall(("CONNECT " + addr + ":" + str(destport) + " HTTP/1.1\r\n" + "Host: " + destaddr + "\r\n\r\n").encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (type(destpair[0]) != type('')) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

########NEW FILE########
__FILENAME__ = synchronizer
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2014 Thomas Voegtlin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import threading
import Queue
import bitcoin
from util import print_error
from transaction import Transaction


class WalletSynchronizer(threading.Thread):

    def __init__(self, wallet, network):
        threading.Thread.__init__(self)
        self.daemon = True
        self.wallet = wallet
        self.network = network
        self.was_updated = True
        self.running = False
        self.lock = threading.Lock()
        self.queue = Queue.Queue()

    def stop(self):
        with self.lock: self.running = False

    def is_running(self):
        with self.lock: return self.running

    
    def subscribe_to_addresses(self, addresses):
        messages = []
        for addr in addresses:
            messages.append(('blockchain.address.subscribe', [addr]))
        self.network.subscribe( messages, lambda i,r: self.queue.put(r))


    def run(self):
        with self.lock:
            self.running = True

        while self.is_running():

            if not self.network.is_connected():
                self.network.wait_until_connected()
                
            self.run_interface()


    def run_interface(self):

        print_error("synchronizer: connected to", self.network.main_server())

        requested_tx = []
        missing_tx = []
        requested_histories = {}

        # request any missing transactions
        for history in self.wallet.history.values():
            if history == ['*']: continue
            for tx_hash, tx_height in history:
                if self.wallet.transactions.get(tx_hash) is None and (tx_hash, tx_height) not in missing_tx:
                    missing_tx.append( (tx_hash, tx_height) )

        if missing_tx:
            print_error("missing tx", missing_tx)

        # subscriptions
        self.subscribe_to_addresses(self.wallet.addresses(True))

        while self.is_running():
            # 1. create new addresses
            new_addresses = self.wallet.synchronize()

            # request missing addresses
            if new_addresses:
                self.subscribe_to_addresses(new_addresses)

            # request missing transactions
            for tx_hash, tx_height in missing_tx:
                if (tx_hash, tx_height) not in requested_tx:
                    self.network.send([ ('blockchain.transaction.get',[tx_hash, tx_height]) ], lambda i,r: self.queue.put(r))
                    requested_tx.append( (tx_hash, tx_height) )
            missing_tx = []

            # detect if situation has changed
            if self.network.is_up_to_date() and self.queue.empty():
                if not self.wallet.is_up_to_date():
                    self.wallet.set_up_to_date(True)
                    self.was_updated = True
            else:
                if self.wallet.is_up_to_date():
                    self.wallet.set_up_to_date(False)
                    self.was_updated = True

            if self.was_updated:
                self.network.trigger_callback('updated')
                self.was_updated = False

            # 2. get a response
            try:
                r = self.queue.get(block=True, timeout=1)
            except Queue.Empty:
                continue

            # see if it changed
            #if interface != self.network.interface:
            #    break
            
            if not r:
                continue

            # 3. handle response
            method = r['method']
            params = r['params']
            result = r.get('result')
            error = r.get('error')
            if error:
                print "error", r
                continue

            if method == 'blockchain.address.subscribe':
                addr = params[0]
                if self.wallet.get_status(self.wallet.get_history(addr)) != result:
                    if requested_histories.get(addr) is None:
                        self.network.send([('blockchain.address.get_history', [addr])], lambda i,r:self.queue.put(r))
                        requested_histories[addr] = result

            elif method == 'blockchain.address.get_history':
                addr = params[0]
                print_error("receiving history", addr, result)
                if result == ['*']:
                    assert requested_histories.pop(addr) == '*'
                    self.wallet.receive_history_callback(addr, result)
                else:
                    hist = []
                    # check that txids are unique
                    txids = []
                    for item in result:
                        tx_hash = item['tx_hash']
                        if tx_hash not in txids:
                            txids.append(tx_hash)
                            hist.append( (tx_hash, item['height']) )

                    if len(hist) != len(result):
                        raise Exception("error: server sent history with non-unique txid", result)

                    # check that the status corresponds to what was announced
                    rs = requested_histories.pop(addr)
                    if self.wallet.get_status(hist) != rs:
                        raise Exception("error: status mismatch: %s"%addr)
                
                    # store received history
                    self.wallet.receive_history_callback(addr, hist)

                    # request transactions that we don't have 
                    for tx_hash, tx_height in hist:
                        if self.wallet.transactions.get(tx_hash) is None:
                            if (tx_hash, tx_height) not in requested_tx and (tx_hash, tx_height) not in missing_tx:
                                missing_tx.append( (tx_hash, tx_height) )

            elif method == 'blockchain.transaction.get':
                tx_hash = params[0]
                tx_height = params[1]
                assert tx_hash == bitcoin.hash_encode(bitcoin.Hash(result.decode('hex')))
                tx = Transaction(result)
                self.wallet.receive_tx_callback(tx_hash, tx, tx_height)
                self.was_updated = True
                requested_tx.remove( (tx_hash, tx_height) )
                print_error("received tx:", tx_hash, len(tx.raw))

            else:
                print_error("Error: Unknown message:" + method + ", " + repr(params) + ", " + repr(result) )

            if self.was_updated and not requested_tx:
                self.network.trigger_callback('updated')
                # Updated gets called too many times from other places as well; if we use that signal we get the notification three times
                self.network.trigger_callback("new_transaction") 
                self.was_updated = False


########NEW FILE########
__FILENAME__ = transaction
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


# Note: The deserialization code originally comes from ABE.


from bitcoin import *
from util import print_error
import time
import struct

#
# Workalike python implementation of Bitcoin's CDataStream class.
#
import struct
import StringIO
import mmap

class SerializationError(Exception):
    """ Thrown when there's a problem deserializing or serializing """

class BCDataStream(object):
    def __init__(self):
        self.input = None
        self.read_cursor = 0

    def clear(self):
        self.input = None
        self.read_cursor = 0

    def write(self, bytes):  # Initialize with string of bytes
        if self.input is None:
            self.input = bytes
        else:
            self.input += bytes

    def map_file(self, file, start):  # Initialize with bytes from file
        self.input = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        self.read_cursor = start

    def seek_file(self, position):
        self.read_cursor = position
        
    def close_file(self):
        self.input.close()

    def read_string(self):
        # Strings are encoded depending on length:
        # 0 to 252 :  1-byte-length followed by bytes (if any)
        # 253 to 65,535 : byte'253' 2-byte-length followed by bytes
        # 65,536 to 4,294,967,295 : byte '254' 4-byte-length followed by bytes
        # ... and the Bitcoin client is coded to understand:
        # greater than 4,294,967,295 : byte '255' 8-byte-length followed by bytes of string
        # ... but I don't think it actually handles any strings that big.
        if self.input is None:
            raise SerializationError("call write(bytes) before trying to deserialize")

        try:
            length = self.read_compact_size()
        except IndexError:
            raise SerializationError("attempt to read past end of buffer")

        return self.read_bytes(length)

    def write_string(self, string):
        # Length-encoded as with read-string
        self.write_compact_size(len(string))
        self.write(string)

    def read_bytes(self, length):
        try:
            result = self.input[self.read_cursor:self.read_cursor+length]
            self.read_cursor += length
            return result
        except IndexError:
            raise SerializationError("attempt to read past end of buffer")

        return ''

    def read_boolean(self): return self.read_bytes(1)[0] != chr(0)
    def read_int16(self): return self._read_num('<h')
    def read_uint16(self): return self._read_num('<H')
    def read_int32(self): return self._read_num('<i')
    def read_uint32(self): return self._read_num('<I')
    def read_int64(self): return self._read_num('<q')
    def read_uint64(self): return self._read_num('<Q')

    def write_boolean(self, val): return self.write(chr(1) if val else chr(0))
    def write_int16(self, val): return self._write_num('<h', val)
    def write_uint16(self, val): return self._write_num('<H', val)
    def write_int32(self, val): return self._write_num('<i', val)
    def write_uint32(self, val): return self._write_num('<I', val)
    def write_int64(self, val): return self._write_num('<q', val)
    def write_uint64(self, val): return self._write_num('<Q', val)

    def read_compact_size(self):
        size = ord(self.input[self.read_cursor])
        self.read_cursor += 1
        if size == 253:
            size = self._read_num('<H')
        elif size == 254:
            size = self._read_num('<I')
        elif size == 255:
            size = self._read_num('<Q')
        return size

    def write_compact_size(self, size):
        if size < 0:
            raise SerializationError("attempt to write size < 0")
        elif size < 253:
            self.write(chr(size))
        elif size < 2**16:
            self.write('\xfd')
            self._write_num('<H', size)
        elif size < 2**32:
            self.write('\xfe')
            self._write_num('<I', size)
        elif size < 2**64:
            self.write('\xff')
            self._write_num('<Q', size)

    def _read_num(self, format):
        (i,) = struct.unpack_from(format, self.input, self.read_cursor)
        self.read_cursor += struct.calcsize(format)
        return i

    def _write_num(self, format, num):
        s = struct.pack(format, num)
        self.write(s)

#
# enum-like type
# From the Python Cookbook, downloaded from http://code.activestate.com/recipes/67107/
#
import types, string, exceptions

class EnumException(exceptions.Exception):
    pass

class Enumeration:
    def __init__(self, name, enumList):
        self.__doc__ = name
        lookup = { }
        reverseLookup = { }
        i = 0
        uniqueNames = [ ]
        uniqueValues = [ ]
        for x in enumList:
            if type(x) == types.TupleType:
                x, i = x
            if type(x) != types.StringType:
                raise EnumException, "enum name is not a string: " + x
            if type(i) != types.IntType:
                raise EnumException, "enum value is not an integer: " + i
            if x in uniqueNames:
                raise EnumException, "enum name is not unique: " + x
            if i in uniqueValues:
                raise EnumException, "enum value is not unique for " + x
            uniqueNames.append(x)
            uniqueValues.append(i)
            lookup[x] = i
            reverseLookup[i] = x
            i = i + 1
        self.lookup = lookup
        self.reverseLookup = reverseLookup
    def __getattr__(self, attr):
        if not self.lookup.has_key(attr):
            raise AttributeError
        return self.lookup[attr]
    def whatis(self, value):
        return self.reverseLookup[value]


# This function comes from bitcointools, bct-LICENSE.txt.
def long_hex(bytes):
    return bytes.encode('hex_codec')

# This function comes from bitcointools, bct-LICENSE.txt.
def short_hex(bytes):
    t = bytes.encode('hex_codec')
    if len(t) < 11:
        return t
    return t[0:4]+"..."+t[-4:]




def parse_redeemScript(bytes):
    dec = [ x for x in script_GetOp(bytes.decode('hex')) ]

    # 2 of 2
    match = [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_2, opcodes.OP_CHECKMULTISIG ]
    if match_decoded(dec, match):
        pubkeys = [ dec[1][1].encode('hex'), dec[2][1].encode('hex') ]
        return 2, pubkeys

    # 2 of 3
    match = [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG ]
    if match_decoded(dec, match):
        pubkeys = [ dec[1][1].encode('hex'), dec[2][1].encode('hex'), dec[3][1].encode('hex') ]
        return 2, pubkeys



opcodes = Enumeration("Opcodes", [
    ("OP_0", 0), ("OP_PUSHDATA1",76), "OP_PUSHDATA2", "OP_PUSHDATA4", "OP_1NEGATE", "OP_RESERVED",
    "OP_1", "OP_2", "OP_3", "OP_4", "OP_5", "OP_6", "OP_7",
    "OP_8", "OP_9", "OP_10", "OP_11", "OP_12", "OP_13", "OP_14", "OP_15", "OP_16",
    "OP_NOP", "OP_VER", "OP_IF", "OP_NOTIF", "OP_VERIF", "OP_VERNOTIF", "OP_ELSE", "OP_ENDIF", "OP_VERIFY",
    "OP_RETURN", "OP_TOALTSTACK", "OP_FROMALTSTACK", "OP_2DROP", "OP_2DUP", "OP_3DUP", "OP_2OVER", "OP_2ROT", "OP_2SWAP",
    "OP_IFDUP", "OP_DEPTH", "OP_DROP", "OP_DUP", "OP_NIP", "OP_OVER", "OP_PICK", "OP_ROLL", "OP_ROT",
    "OP_SWAP", "OP_TUCK", "OP_CAT", "OP_SUBSTR", "OP_LEFT", "OP_RIGHT", "OP_SIZE", "OP_INVERT", "OP_AND",
    "OP_OR", "OP_XOR", "OP_EQUAL", "OP_EQUALVERIFY", "OP_RESERVED1", "OP_RESERVED2", "OP_1ADD", "OP_1SUB", "OP_2MUL",
    "OP_2DIV", "OP_NEGATE", "OP_ABS", "OP_NOT", "OP_0NOTEQUAL", "OP_ADD", "OP_SUB", "OP_MUL", "OP_DIV",
    "OP_MOD", "OP_LSHIFT", "OP_RSHIFT", "OP_BOOLAND", "OP_BOOLOR",
    "OP_NUMEQUAL", "OP_NUMEQUALVERIFY", "OP_NUMNOTEQUAL", "OP_LESSTHAN",
    "OP_GREATERTHAN", "OP_LESSTHANOREQUAL", "OP_GREATERTHANOREQUAL", "OP_MIN", "OP_MAX",
    "OP_WITHIN", "OP_RIPEMD160", "OP_SHA1", "OP_SHA256", "OP_HASH160",
    "OP_HASH256", "OP_CODESEPARATOR", "OP_CHECKSIG", "OP_CHECKSIGVERIFY", "OP_CHECKMULTISIG",
    "OP_CHECKMULTISIGVERIFY",
    ("OP_SINGLEBYTE_END", 0xF0),
    ("OP_DOUBLEBYTE_BEGIN", 0xF000),
    "OP_PUBKEY", "OP_PUBKEYHASH",
    ("OP_INVALIDOPCODE", 0xFFFF),
])


def script_GetOp(bytes):
    i = 0
    while i < len(bytes):
        vch = None
        opcode = ord(bytes[i])
        i += 1
        if opcode >= opcodes.OP_SINGLEBYTE_END:
            opcode <<= 8
            opcode |= ord(bytes[i])
            i += 1

        if opcode <= opcodes.OP_PUSHDATA4:
            nSize = opcode
            if opcode == opcodes.OP_PUSHDATA1:
                nSize = ord(bytes[i])
                i += 1
            elif opcode == opcodes.OP_PUSHDATA2:
                (nSize,) = struct.unpack_from('<H', bytes, i)
                i += 2
            elif opcode == opcodes.OP_PUSHDATA4:
                (nSize,) = struct.unpack_from('<I', bytes, i)
                i += 4
            vch = bytes[i:i+nSize]
            i += nSize

        yield (opcode, vch, i)


def script_GetOpName(opcode):
    return (opcodes.whatis(opcode)).replace("OP_", "")


def decode_script(bytes):
    result = ''
    for (opcode, vch, i) in script_GetOp(bytes):
        if len(result) > 0: result += " "
        if opcode <= opcodes.OP_PUSHDATA4:
            result += "%d:"%(opcode,)
            result += short_hex(vch)
        else:
            result += script_GetOpName(opcode)
    return result


def match_decoded(decoded, to_match):
    if len(decoded) != len(to_match):
        return False;
    for i in range(len(decoded)):
        if to_match[i] == opcodes.OP_PUSHDATA4 and decoded[i][0] <= opcodes.OP_PUSHDATA4 and decoded[i][0]>0:
            continue  # Opcodes below OP_PUSHDATA4 all just push data onto stack, and are equivalent.
        if to_match[i] != decoded[i][0]:
            return False
    return True

def get_address_from_input_script(bytes):
    try:
        decoded = [ x for x in script_GetOp(bytes) ]
    except Exception:
        # coinbase transactions raise an exception
        print_error("cannot find address in input script", bytes.encode('hex'))
        return [], {}, "(None)"

    # payto_pubkey
    match = [ opcodes.OP_PUSHDATA4 ]
    if match_decoded(decoded, match):
        return None, {}, "(pubkey)"

    # non-generated TxIn transactions push a signature
    # (seventy-something bytes) and then their public key
    # (65 bytes) onto the stack:
    match = [ opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4 ]
    if match_decoded(decoded, match):
        sig = decoded[0][1].encode('hex')
        pubkey = decoded[1][1].encode('hex')
        if sig[-2:] == '01':
            sig = sig[:-2]
            return [pubkey], {pubkey:sig}, public_key_to_bc_address(pubkey.decode('hex'))
        else:
            print_error("cannot find address in input script", bytes.encode('hex'))
            return [], {}, "(None)"


    # p2sh transaction, 2 of n
    match = [ opcodes.OP_0 ]
    while len(match) < len(decoded):
        match.append(opcodes.OP_PUSHDATA4)

    if match_decoded(decoded, match):

        redeemScript = decoded[-1][1]
        num = len(match) - 2
        signatures = map(lambda x:x[1][:-1].encode('hex'), decoded[1:-1])

        dec2 = [ x for x in script_GetOp(redeemScript) ]

        # 2 of 2
        match2 = [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_2, opcodes.OP_CHECKMULTISIG ]
        if match_decoded(dec2, match2):
            pubkeys = [ dec2[1][1].encode('hex'), dec2[2][1].encode('hex') ]
            return pubkeys, signatures, hash_160_to_bc_address(hash_160(redeemScript), 5)
 
        # 2 of 3
        match2 = [ opcodes.OP_2, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_PUSHDATA4, opcodes.OP_3, opcodes.OP_CHECKMULTISIG ]
        if match_decoded(dec2, match2):
            pubkeys = [ dec2[1][1].encode('hex'), dec2[2][1].encode('hex'), dec2[3][1].encode('hex') ]
            return pubkeys, signatures, hash_160_to_bc_address(hash_160(redeemScript), 5)

    print_error("cannot find address in input script", bytes.encode('hex'))
    return [], {}, "(None)"



def get_address_from_output_script(bytes):
    decoded = [ x for x in script_GetOp(bytes) ]

    # The Genesis Block, self-payments, and pay-by-IP-address payments look like:
    # 65 BYTES:... CHECKSIG
    match = [ opcodes.OP_PUSHDATA4, opcodes.OP_CHECKSIG ]
    if match_decoded(decoded, match):
        return True, public_key_to_bc_address(decoded[0][1])

    # Pay-by-Bitcoin-address TxOuts look like:
    # DUP HASH160 20 BYTES:... EQUALVERIFY CHECKSIG
    match = [ opcodes.OP_DUP, opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUALVERIFY, opcodes.OP_CHECKSIG ]
    if match_decoded(decoded, match):
        return False, hash_160_to_bc_address(decoded[2][1])

    # p2sh
    match = [ opcodes.OP_HASH160, opcodes.OP_PUSHDATA4, opcodes.OP_EQUAL ]
    if match_decoded(decoded, match):
        return False, hash_160_to_bc_address(decoded[1][1],5)

    return False, "(None)"


class Transaction:
    
    def __init__(self, raw):
        self.raw = raw
        self.deserialize()
        self.inputs = self.d['inputs']
        self.outputs = self.d['outputs']
        self.outputs = map(lambda x: (x['address'],x['value']), self.outputs)
        self.locktime = self.d['lockTime']

    def __str__(self):
        return self.raw

    @classmethod
    def from_io(klass, inputs, outputs):
        raw = klass.serialize(inputs, outputs, for_sig = None) # for_sig=-1 means do not sign
        self = klass(raw)
        self.inputs = inputs
        self.outputs = outputs
        return self

    @classmethod 
    def sweep(klass, privkeys, network, to_address, fee):
        inputs = []
        for privkey in privkeys:
            pubkey = public_key_from_private_key(privkey)
            address = address_from_private_key(privkey)
            u = network.synchronous_get([ ('blockchain.address.listunspent',[address])])[0]
            pay_script = klass.pay_script(address)
            for item in u:
                item['scriptPubKey'] = pay_script
                item['redeemPubkey'] = pubkey
                item['address'] = address
                item['prevout_hash'] = item['tx_hash']
                item['prevout_n'] = item['tx_pos']
            inputs += u

        if not inputs:
            return

        total = sum( map(lambda x:int(x.get('value')), inputs) ) - fee
        outputs = [(to_address, total)]
        self = klass.from_io(inputs, outputs)
        self.sign({ pubkey:privkey })
        return self

    @classmethod
    def multisig_script(klass, public_keys, num=None):
        n = len(public_keys)
        if num is None: num = n
        # supports only "2 of 2", and "2 of 3" transactions
        assert num <= n and n in [2,3]
    
        if num==2:
            s = '52'
        elif num == 3:
            s = '53'
        else:
            raise
    
        for k in public_keys:
            s += var_int(len(k)/2)
            s += k
        if n==2:
            s += '52'
        elif n==3:
            s += '53'
        else:
            raise
        s += 'ae'

        return s


    @classmethod
    def pay_script(self, addr):
        addrtype, hash_160 = bc_address_to_hash_160(addr)
        if addrtype == 0:
            script = '76a9'                                      # op_dup, op_hash_160
            script += '14'                                       # push 0x14 bytes
            script += hash_160.encode('hex')
            script += '88ac'                                     # op_equalverify, op_checksig
        elif addrtype == 5:
            script = 'a9'                                        # op_hash_160
            script += '14'                                       # push 0x14 bytes
            script += hash_160.encode('hex')
            script += '87'                                       # op_equal
        else:
            raise
        return script


    @classmethod
    def serialize( klass, inputs, outputs, for_sig = None ):

        push_script = lambda x: op_push(len(x)/2) + x
        s  = int_to_hex(1,4)                                         # version
        s += var_int( len(inputs) )                                  # number of inputs
        for i in range(len(inputs)):
            txin = inputs[i]
            s += txin['prevout_hash'].decode('hex')[::-1].encode('hex')   # prev hash
            s += int_to_hex(txin['prevout_n'],4)                          # prev index

            signatures = txin.get('signatures', {})
            if for_sig is None and not signatures:
                script = ''

            elif for_sig is None:
                pubkeys = txin['pubkeys']
                sig_list = ''
                for pubkey in pubkeys:
                    sig = signatures.get(pubkey)
                    if not sig: 
                        continue
                    sig = sig + '01'
                    sig_list += push_script(sig)

                if not txin.get('redeemScript'):
                    script = sig_list
                    script += push_script(pubkeys[0])
                else:
                    script = '00'                                    # op_0
                    script += sig_list
                    redeem_script = klass.multisig_script(pubkeys,2)
                    assert redeem_script == txin.get('redeemScript')
                    script += push_script(redeem_script)

            elif for_sig==i:
                if txin.get('redeemScript'):
                    script = txin['redeemScript']                    # p2sh uses the inner script
                else:
                    script = txin['scriptPubKey']                    # scriptsig
            else:
                script = ''
            s += var_int( len(script)/2 )                            # script length
            s += script
            s += "ffffffff"                                          # sequence

        s += var_int( len(outputs) )                                 # number of outputs
        for output in outputs:
            addr, amount = output
            s += int_to_hex( amount, 8)                              # amount
            script = klass.pay_script(addr)
            s += var_int( len(script)/2 )                           #  script length
            s += script                                             #  script
        s += int_to_hex(0,4)                                        #  lock time
        if for_sig is not None and for_sig != -1:
            s += int_to_hex(1, 4)                                   #  hash type
        return s


    def tx_for_sig(self,i):
        return self.serialize(self.inputs, self.outputs, for_sig = i)


    def hash(self):
        return Hash(self.raw.decode('hex') )[::-1].encode('hex')

    def add_signature(self, i, pubkey, sig):
        txin = self.inputs[i]
        signatures = txin.get("signatures",{})
        signatures[pubkey] = sig
        txin["signatures"] = signatures
        self.inputs[i] = txin
        print_error("adding signature for", pubkey)
        self.raw = self.serialize( self.inputs, self.outputs )


    def is_complete(self):
        for i, txin in enumerate(self.inputs):
            redeem_script = txin.get('redeemScript')
            num, redeem_pubkeys = parse_redeemScript(redeem_script) if redeem_script else (1, [txin.get('redeemPubkey')])
            signatures = txin.get("signatures",{})
            if len(signatures) == num:
                continue
            else:
                return False
        return True



    def sign(self, keypairs):
        print_error("tx.sign(), keypairs:", keypairs)

        for i, txin in enumerate(self.inputs):

            # if the input is multisig, parse redeem script
            redeem_script = txin.get('redeemScript')
            num, redeem_pubkeys = parse_redeemScript(redeem_script) if redeem_script else (1, [txin.get('redeemPubkey')])

            # add pubkeys
            txin["pubkeys"] = redeem_pubkeys
            # get list of already existing signatures
            signatures = txin.get("signatures",{})
            # continue if this txin is complete
            if len(signatures) == num:
                continue

            for_sig = Hash(self.tx_for_sig(i).decode('hex'))
            for pubkey in redeem_pubkeys:
                if pubkey in keypairs.keys():
                    # add signature
                    sec = keypairs[pubkey]
                    pkey = regenerate_key(sec)
                    secexp = pkey.secret
                    private_key = ecdsa.SigningKey.from_secret_exponent( secexp, curve = SECP256k1 )
                    public_key = private_key.get_verifying_key()
                    sig = private_key.sign_digest_deterministic( for_sig, hashfunc=hashlib.sha256, sigencode = ecdsa.util.sigencode_der )
                    assert public_key.verify_digest( sig, for_sig, sigdecode = ecdsa.util.sigdecode_der)
                    self.add_signature(i, pubkey, sig.encode('hex'))


        print_error("is_complete", self.is_complete())
        self.raw = self.serialize( self.inputs, self.outputs )



    def deserialize(self):
        vds = BCDataStream()
        vds.write(self.raw.decode('hex'))
        d = {}
        start = vds.read_cursor
        d['version'] = vds.read_int32()
        n_vin = vds.read_compact_size()
        d['inputs'] = []
        for i in xrange(n_vin):
            d['inputs'].append(self.parse_input(vds))
        n_vout = vds.read_compact_size()
        d['outputs'] = []
        for i in xrange(n_vout):
            d['outputs'].append(self.parse_output(vds, i))
        d['lockTime'] = vds.read_uint32()
        self.d = d
        return self.d
    

    def parse_input(self, vds):
        d = {}
        prevout_hash = hash_encode(vds.read_bytes(32))
        prevout_n = vds.read_uint32()
        scriptSig = vds.read_bytes(vds.read_compact_size())
        sequence = vds.read_uint32()

        if prevout_hash == '00'*32:
            d['is_coinbase'] = True
        else:
            d['is_coinbase'] = False
            d['prevout_hash'] = prevout_hash
            d['prevout_n'] = prevout_n
            d['sequence'] = sequence
            if scriptSig:
                pubkeys, signatures, address = get_address_from_input_script(scriptSig)
            else:
                pubkeys = []
                signatures = {}
                address = None
            d['address'] = address
            d['pubkeys'] = pubkeys
            d['signatures'] = signatures
        return d


    def parse_output(self, vds, i):
        d = {}
        d['value'] = vds.read_int64()
        scriptPubKey = vds.read_bytes(vds.read_compact_size())
        is_pubkey, address = get_address_from_output_script(scriptPubKey)
        d['is_pubkey'] = is_pubkey
        d['address'] = address
        d['scriptPubKey'] = scriptPubKey.encode('hex')
        d['prevout_n'] = i
        return d


    def add_extra_addresses(self, txlist):
        for i in self.inputs:
            if i.get("address") == "(pubkey)":
                prev_tx = txlist.get(i.get('prevout_hash'))
                if prev_tx:
                    address, value = prev_tx.outputs[i.get('prevout_n')]
                    print_error("found pay-to-pubkey address:", address)
                    i["address"] = address


    def has_address(self, addr):
        found = False
        for txin in self.inputs:
            if addr == txin.get('address'): 
                found = True
                break
        for txout in self.outputs:
            if addr == txout[0]:
                found = True
                break
        return found


    def get_value(self, addresses, prevout_values):
        # return the balance for that tx
        is_relevant = False
        is_send = False
        is_pruned = False
        is_partial = False
        v_in = v_out = v_out_mine = 0

        for item in self.inputs:
            addr = item.get('address')
            if addr in addresses:
                is_send = True
                is_relevant = True
                key = item['prevout_hash']  + ':%d'%item['prevout_n']
                value = prevout_values.get( key )
                if value is None:
                    is_pruned = True
                else:
                    v_in += value
            else:
                is_partial = True

        if not is_send: is_partial = False
                    
        for item in self.outputs:
            addr, value = item
            v_out += value
            if addr in addresses:
                v_out_mine += value
                is_relevant = True

        if is_pruned:
            # some inputs are mine:
            fee = None
            if is_send:
                v = v_out_mine - v_out
            else:
                # no input is mine
                v = v_out_mine

        else:
            v = v_out_mine - v_in

            if is_partial:
                # some inputs are mine, but not all
                fee = None
                is_send = v < 0
            else:
                # all inputs are mine
                fee = v_out - v_in

        return is_relevant, is_send, v, fee


    def get_input_info(self):
        keys = ['prevout_hash', 'prevout_n', 'address', 'KeyID', 'scriptPubKey', 'redeemScript', 'redeemPubkey', 'pubkeys', 'signatures', 'is_coinbase']
        info = []
        for i in self.inputs:
            item = {}
            for k in keys:
                v = i.get(k)
                if v is not None:
                    item[k] = v
            info.append(item)
        return info


    def as_dict(self):
        import json
        out = {
            "hex":self.raw,
            "complete":self.is_complete()
            }

        if not self.is_complete():
            input_info = self.get_input_info()
            out['input_info'] = json.dumps(input_info).replace(' ','')

        return out


    def requires_fee(self, verifier):
        # see https://en.bitcoin.it/wiki/Transaction_fees
        threshold = 57600000
        size = len(self.raw)/2
        if size >= 10000: 
            return True

        for o in self.outputs:
            value = o[1]
            if value < 1000000:
                return True
        sum = 0
        for i in self.inputs:
            age = verifier.get_confirmations(i["prevout_hash"])[0]
            sum += i["value"] * age
        priority = sum / size
        print_error(priority, threshold)
        return priority < threshold 



    def add_input_info(self, input_info):
        for i, txin in enumerate(self.inputs):
            item = input_info[i]
            txin['scriptPubKey'] = item['scriptPubKey']
            txin['redeemScript'] = item.get('redeemScript')
            txin['redeemPubkey'] = item.get('redeemPubkey')
            txin['KeyID'] = item.get('KeyID')
            txin['signatures'] = item.get('signatures',{})

########NEW FILE########
__FILENAME__ = util
import os, sys, re, json
import platform
import shutil
from datetime import datetime
is_verbose = False


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        from transaction import Transaction
        if isinstance(obj, Transaction):
            return obj.as_dict()
        return super(MyEncoder, self).default(obj)


def set_verbosity(b):
    global is_verbose
    is_verbose = b


def print_error(*args):
    if not is_verbose: return
    print_stderr(*args)

def print_stderr(*args):
    args = [str(item) for item in args]
    sys.stderr.write(" ".join(args) + "\n")
    sys.stderr.flush()

def print_msg(*args):
    # Stringify args
    args = [str(item) for item in args]
    sys.stdout.write(" ".join(args) + "\n")
    sys.stdout.flush()

def print_json(obj):
    try:
        s = json.dumps(obj, sort_keys = True, indent = 4, cls=MyEncoder)
    except TypeError:
        s = repr(obj)
    sys.stdout.write(s + "\n")
    sys.stdout.flush()

def user_dir():
    if "HOME" in os.environ:
        return os.path.join(os.environ["HOME"], ".electrum")
    elif "APPDATA" in os.environ:
        return os.path.join(os.environ["APPDATA"], "Electrum")
    elif "LOCALAPPDATA" in os.environ:
        return os.path.join(os.environ["LOCALAPPDATA"], "Electrum")
    elif 'ANDROID_DATA' in os.environ:
        return "/sdcard/electrum/"
    else:
        #raise Exception("No home directory found in environment variables.")
        return

def appdata_dir():
    """Find the path to the application data directory; add an electrum folder and return path."""
    if platform.system() == "Windows":
        return os.path.join(os.environ["APPDATA"], "Electrum")
    elif platform.system() == "Linux":
        return os.path.join(sys.prefix, "share", "electrum")
    elif (platform.system() == "Darwin" or
          platform.system() == "DragonFly" or
          platform.system() == "OpenBSD" or
          platform.system() == "FreeBSD" or
	  platform.system() == "NetBSD"):
        return "/Library/Application Support/Electrum"
    else:
        raise Exception("Unknown system")


def get_resource_path(*args):
    return os.path.join(".", *args)


def local_data_dir():
    """Return path to the data folder."""
    assert sys.argv
    prefix_path = os.path.dirname(sys.argv[0])
    local_data = os.path.join(prefix_path, "data")
    return local_data


def format_satoshis(x, is_diff=False, num_zeros = 0, decimal_point = 8, whitespaces=False):
    from decimal import Decimal
    s = Decimal(x)
    sign, digits, exp = s.as_tuple()
    digits = map(str, digits)
    while len(digits) < decimal_point + 1:
        digits.insert(0,'0')
    digits.insert(-decimal_point,'.')
    s = ''.join(digits).rstrip('0')
    if sign:
        s = '-' + s
    elif is_diff:
        s = "+" + s

    p = s.find('.')
    s += "0"*( 1 + num_zeros - ( len(s) - p ))
    if whitespaces:
        s += " "*( 1 + decimal_point - ( len(s) - p ))
        s = " "*( 13 - decimal_point - ( p )) + s
    return s


# Takes a timestamp and returns a string with the approximation of the age
def age(from_date, since_date = None, target_tz=None, include_seconds=False):
    if from_date is None:
        return "Unknown"

    from_date = datetime.fromtimestamp(from_date)
    if since_date is None:
        since_date = datetime.now(target_tz)

    distance_in_time = since_date - from_date
    distance_in_seconds = int(round(abs(distance_in_time.days * 86400 + distance_in_time.seconds)))
    distance_in_minutes = int(round(distance_in_seconds/60))

    if distance_in_minutes <= 1:
        if include_seconds:
            for remainder in [5, 10, 20]:
                if distance_in_seconds < remainder:
                    return "less than %s seconds ago" % remainder
            if distance_in_seconds < 40:
                return "half a minute ago"
            elif distance_in_seconds < 60:
                return "less than a minute ago"
            else:
                return "1 minute ago"
        else:
            if distance_in_minutes == 0:
                return "less than a minute ago"
            else:
                return "1 minute ago"
    elif distance_in_minutes < 45:
        return "%s minutes ago" % distance_in_minutes
    elif distance_in_minutes < 90:
        return "about 1 hour ago"
    elif distance_in_minutes < 1440:
        return "about %d hours ago" % (round(distance_in_minutes / 60.0))
    elif distance_in_minutes < 2880:
        return "1 day ago"
    elif distance_in_minutes < 43220:
        return "%d days ago" % (round(distance_in_minutes / 1440))
    elif distance_in_minutes < 86400:
        return "about 1 month ago"
    elif distance_in_minutes < 525600:
        return "%d months ago" % (round(distance_in_minutes / 43200))
    elif distance_in_minutes < 1051200:
        return "about 1 year ago"
    else:
        return "over %d years ago" % (round(distance_in_minutes / 525600))


# URL decode
#_ud = re.compile('%([0-9a-hA-H]{2})', re.MULTILINE)
#urldecode = lambda x: _ud.sub(lambda m: chr(int(m.group(1), 16)), x)

def parse_url(url):
    import urlparse
    from decimal import Decimal

    u = urlparse.urlparse(url)
    assert u.scheme == 'bitcoin'

    address = u.path
    #assert bitcoin.is_address(address)

    pq = urlparse.parse_qs(u.query)
    
    for k, v in pq.items():
        if len(v)!=1:
            raise Exception('Duplicate Key', k)

    amount = label = message = request_url = ''
    if 'amount' in pq:
        am = pq['amount'][0]
        m = re.match('([0-9\.]+)X([0-9])', am)
        if m:
            k = int(m.group(2)) - 8
            amount = Decimal(m.group(1)) * pow(  Decimal(10) , k)
        else:
            amount = Decimal(am)
    if 'message' in pq:
        message = pq['message'][0]
    if 'label' in pq:
        label = pq['label'][0]
    if 'r' in pq:
        request_url = pq['r'][0]
        
    return address, amount, label, message, request_url, url


# Python bug (http://bugs.python.org/issue1927) causes raw_input
# to be redirected improperly between stdin/stderr on Unix systems
def raw_input(prompt=None):
    if prompt:
        sys.stdout.write(prompt)
    return builtin_raw_input()
import __builtin__
builtin_raw_input = __builtin__.raw_input
__builtin__.raw_input = raw_input

########NEW FILE########
__FILENAME__ = verifier
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@ecdsa.org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import threading, time, Queue, os, sys, shutil
from util import user_dir, appdata_dir, print_error
from bitcoin import *




class TxVerifier(threading.Thread):
    """ Simple Payment Verification """

    def __init__(self, network, storage):
        threading.Thread.__init__(self)
        self.daemon = True
        self.storage = storage
        self.network = network
        self.transactions    = {}                                 # requested verifications (with height sent by the requestor)
        self.verified_tx     = storage.get('verified_tx3',{})      # height, timestamp of verified transactions
        self.merkle_roots    = storage.get('merkle_roots',{})      # hashed by me
        self.lock = threading.Lock()
        self.running = False
        self.queue = Queue.Queue()


    def get_confirmations(self, tx):
        """ return the number of confirmations of a monitored transaction. """
        with self.lock:
            if tx in self.verified_tx:
                height, timestamp, pos = self.verified_tx[tx]
                conf = (self.network.get_local_height() - height + 1)
                if conf <= 0: timestamp = None

            elif tx in self.transactions:
                conf = -1
                timestamp = None

            else:
                conf = 0
                timestamp = None

        return conf, timestamp


    def get_txpos(self, tx_hash):
        "return position, even if the tx is unverified"
        with self.lock:
            x = self.verified_tx.get(tx_hash)
            y = self.transactions.get(tx_hash)
        if x:
            height, timestamp, pos = x
            return height, pos
        elif y:
            return y, 0
        else:
            return 1e12, 0


    def get_height(self, tx_hash):
        with self.lock:
            v = self.verified_tx.get(tx_hash)
        height = v[0] if v else None
        return height


    def add(self, tx_hash, tx_height):
        """ add a transaction to the list of monitored transactions. """
        assert tx_height > 0
        with self.lock:
            if tx_hash not in self.transactions.keys():
                self.transactions[tx_hash] = tx_height

    def stop(self):
        with self.lock: self.running = False

    def is_running(self):
        with self.lock: return self.running

    def run(self):
        with self.lock:
            self.running = True
        requested_merkle = []

        while self.is_running():
            # request missing tx
            for tx_hash, tx_height in self.transactions.items():
                if tx_hash not in self.verified_tx:
                    if self.merkle_roots.get(tx_hash) is None and tx_hash not in requested_merkle:
                        if self.network.send([ ('blockchain.transaction.get_merkle',[tx_hash, tx_height]) ], lambda i,r: self.queue.put(r)):
                            print_error('requesting merkle', tx_hash)
                            requested_merkle.append(tx_hash)

            try:
                r = self.queue.get(timeout=1)
            except Queue.Empty:
                continue

            if not r: continue

            if r.get('error'):
                print_error('Verifier received an error:', r)
                continue

            # 3. handle response
            method = r['method']
            params = r['params']
            result = r['result']

            if method == 'blockchain.transaction.get_merkle':
                tx_hash = params[0]
                self.verify_merkle(tx_hash, result)
                requested_merkle.remove(tx_hash)


    def verify_merkle(self, tx_hash, result):
        tx_height = result.get('block_height')
        pos = result.get('pos')
        self.merkle_roots[tx_hash] = self.hash_merkle_root(result['merkle'], tx_hash, pos)
        header = self.network.get_header(tx_height)
        if not header: return
        assert header.get('merkle_root') == self.merkle_roots[tx_hash]
        # we passed all the tests
        timestamp = header.get('timestamp')
        with self.lock:
            self.verified_tx[tx_hash] = (tx_height, timestamp, pos)
        print_error("verified %s"%tx_hash)
        self.storage.put('verified_tx3', self.verified_tx, True)
        self.network.trigger_callback('updated')


    def hash_merkle_root(self, merkle_s, target_hash, pos):
        h = hash_decode(target_hash)
        for i in range(len(merkle_s)):
            item = merkle_s[i]
            h = Hash( hash_decode(item) + h ) if ((pos >> i) & 1) else Hash( h + hash_decode(item) )
        return hash_encode(h)



    def undo_verifications(self, height):
        with self.lock:
            items = self.verified_tx.items()[:]
        for tx_hash, item in items:
            tx_height, timestamp, pos = item
            if tx_height >= height:
                print_error("redoing", tx_hash)
                with self.lock:
                    self.verified_tx.pop(tx_hash)
                    if tx_hash in self.merkle_roots:
                        self.merkle_roots.pop(tx_hash)

########NEW FILE########
__FILENAME__ = version
ELECTRUM_VERSION = "1.9.8"  # version of the client package
PROTOCOL_VERSION = '0.9'    # protocol version requested
NEW_SEED_VERSION = 7        # bip32 wallets
OLD_SEED_VERSION = 4        # old electrum deterministic generation
SEED_PREFIX      = '01'     # the hash of the mnemonic seed must begin with this

########NEW FILE########
__FILENAME__ = wallet
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import sys
import base64
import os
import re
import hashlib
import copy
import operator
import ast
import threading
import random
import aes
import Queue
import time
import math

from util import print_msg, print_error, format_satoshis
from bitcoin import *
from account import *
from transaction import Transaction
from plugins import run_hook
import bitcoin
from synchronizer import WalletSynchronizer

COINBASE_MATURITY = 100
DUST_THRESHOLD = 5430

# internal ID for imported account
IMPORTED_ACCOUNT = '/x'



from version import *


class WalletStorage:

    def __init__(self, config):
        self.lock = threading.Lock()
        self.config = config
        self.data = {}
        self.file_exists = False
        self.path = self.init_path(config)
        print_error( "wallet path", self.path )
        if self.path:
            self.read(self.path)


    def init_path(self, config):
        """Set the path of the wallet."""

        # command line -w option
        path = config.get('wallet_path')
        if path:
            return path

        # path in config file
        path = config.get('default_wallet_path')
        if path:
            return path

        # default path
        dirpath = os.path.join(config.path, "wallets")
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)

        new_path = os.path.join(config.path, "wallets", "default_wallet")

        # default path in pre 1.9 versions
        old_path = os.path.join(config.path, "electrum.dat")
        if os.path.exists(old_path) and not os.path.exists(new_path):
            os.rename(old_path, new_path)

        return new_path


    def read(self, path):
        """Read the contents of the wallet file."""
        try:
            with open(self.path, "r") as f:
                data = f.read()
        except IOError:
            return
        try:
            d = ast.literal_eval( data )  #parse raw data from reading wallet file
        except Exception:
            raise IOError("Cannot read wallet file.")

        self.data = d
        self.file_exists = True


    def get(self, key, default=None):
        v = self.data.get(key)
        if v is None: 
            v = default
        return v

    def put(self, key, value, save = True):

        with self.lock:
            if value is not None:
                self.data[key] = value
            else:
                self.data.pop(key)
            if save: 
                self.write()

    def write(self):
        s = repr(self.data)
        f = open(self.path,"w")
        f.write( s )
        f.close()
        if 'ANDROID_DATA' not in os.environ:
            import stat
            os.chmod(self.path,stat.S_IREAD | stat.S_IWRITE)



    

        

class Abstract_Wallet:

    def __init__(self, storage):

        self.storage = storage
        self.electrum_version = ELECTRUM_VERSION
        self.gap_limit_for_change = 3 # constant
        # saved fields
        self.seed_version          = storage.get('seed_version', NEW_SEED_VERSION)
        self.gap_limit             = storage.get('gap_limit', 5)
        self.use_change            = storage.get('use_change',True)
        self.use_encryption        = storage.get('use_encryption', False)
        self.seed                  = storage.get('seed', '')               # encrypted
        self.labels                = storage.get('labels', {})
        self.frozen_addresses      = storage.get('frozen_addresses',[])
        self.addressbook           = storage.get('contacts', [])

        self.history               = storage.get('addr_history',{})        # address -> list(txid, height)

        self.fee                   = int(storage.get('fee_per_kb', 10000))

        self.master_public_keys = storage.get('master_public_keys',{})
        self.master_private_keys = storage.get('master_private_keys', {})

        self.next_addresses = storage.get('next_addresses',{})


        # This attribute is set when wallet.start_threads is called.
        self.synchronizer = None

        self.load_accounts()

        self.transactions = {}
        tx_list = self.storage.get('transactions',{})
        for k,v in tx_list.items():
            try:
                tx = Transaction(v)
            except Exception:
                print_msg("Warning: Cannot deserialize transactions. skipping")
                continue

            self.add_extra_addresses(tx)
            self.transactions[k] = tx

        for h,tx in self.transactions.items():
            if not self.check_new_tx(h, tx):
                print_error("removing unreferenced tx", h)
                self.transactions.pop(h)


        # not saved
        self.prevout_values = {}     # my own transaction outputs
        self.spent_outputs = []

        # spv
        self.verifier = None

        # there is a difference between wallet.up_to_date and interface.is_up_to_date()
        # interface.is_up_to_date() returns true when all requests have been answered and processed
        # wallet.up_to_date is true when the wallet is synchronized (stronger requirement)
        
        self.up_to_date = False
        self.lock = threading.Lock()
        self.transaction_lock = threading.Lock()
        self.tx_event = threading.Event()

        for tx_hash, tx in self.transactions.items():
            self.update_tx_outputs(tx_hash)


    def add_extra_addresses(self, tx):
        h = tx.hash()
        # find the address corresponding to pay-to-pubkey inputs
        tx.add_extra_addresses(self.transactions)
        for o in tx.d.get('outputs'):
            if o.get('is_pubkey'):
                for tx2 in self.transactions.values():
                    tx2.add_extra_addresses({h:tx})


    def get_action(self):
        pass

    def load_accounts(self):
        self.accounts = {}
        self.imported_keys = self.storage.get('imported_keys',{})
        if self.imported_keys:
            print_error("cannot load imported keys")

        d = self.storage.get('accounts', {})
        for k, v in d.items():
            if k == 0:
                v['mpk'] = self.storage.get('master_public_key')
                self.accounts[k] = OldAccount(v)
            elif v.get('imported'):
                self.accounts[k] = ImportedAccount(v)
            elif v.get('xpub3'):
                self.accounts[k] = BIP32_Account_2of3(v)
            elif v.get('xpub2'):
                self.accounts[k] = BIP32_Account_2of2(v)
            elif v.get('xpub'):
                self.accounts[k] = BIP32_Account(v)
            elif v.get('pending'):
                self.accounts[k] = PendingAccount(v)
            else:
                print_error("cannot load account", v)


    def synchronize(self):
        pass

    def can_create_accounts(self):
        return False

    def set_up_to_date(self,b):
        with self.lock: self.up_to_date = b

    def is_up_to_date(self):
        with self.lock: return self.up_to_date


    def update(self):
        self.up_to_date = False
        while not self.is_up_to_date(): 
            time.sleep(0.1)

    def is_imported(self, addr):
        account = self.accounts.get(IMPORTED_ACCOUNT)
        if account: 
            return addr in account.get_addresses(0)
        else:
            return False

    def import_key(self, sec, password):
        try:
            pubkey = public_key_from_private_key(sec)
            address = public_key_to_bc_address(pubkey.decode('hex'))
        except Exception:
            raise Exception('Invalid private key')

        if self.is_mine(address):
            raise Exception('Address already in wallet')
        
        if self.accounts.get(IMPORTED_ACCOUNT) is None:
            self.accounts[IMPORTED_ACCOUNT] = ImportedAccount({'imported':{}})
        self.accounts[IMPORTED_ACCOUNT].add(address, pubkey, sec, password)
        self.save_accounts()
        
        if self.synchronizer:
            self.synchronizer.subscribe_to_addresses([address])
        return address
        

    def delete_imported_key(self, addr):
        account = self.accounts[IMPORTED_ACCOUNT]
        account.remove(addr)
        if not account.get_addresses(0):
            self.accounts.pop(IMPORTED_ACCOUNT)
        self.save_accounts()


    def set_label(self, name, text = None):
        changed = False
        old_text = self.labels.get(name)
        if text:
            if old_text != text:
                self.labels[name] = text
                changed = True
        else:
            if old_text:
                self.labels.pop(name)
                changed = True

        if changed:
            self.storage.put('labels', self.labels, True)

        run_hook('set_label', name, text, changed)
        return changed




    def addresses(self, include_change = True, _next=True):
        o = []
        for a in self.accounts.keys():
            o += self.get_account_addresses(a, include_change)

        if _next:
            for addr in self.next_addresses.values():
                if addr not in o:
                    o += [addr]
        return o


    def is_mine(self, address):
        return address in self.addresses(True) 


    def is_change(self, address):
        if not self.is_mine(address): return False
        acct, s = self.get_address_index(address)
        if s is None: return False
        return s[0] == 1


    def get_address_index(self, address):

        for account in self.accounts.keys():
            for for_change in [0,1]:
                addresses = self.accounts[account].get_addresses(for_change)
                for addr in addresses:
                    if address == addr:
                        return account, (for_change, addresses.index(addr))

        for k,v in self.next_addresses.items():
            if v == address:
                return k, (0,0)

        raise Exception("Address not found", address)


    def getpubkeys(self, addr):
        assert is_valid(addr) and self.is_mine(addr)
        account, sequence = self.get_address_index(addr)
        a = self.accounts[account]
        return a.get_pubkeys( sequence )


    def get_private_key(self, address, password):
        if self.is_watching_only():
            return []
        account_id, sequence = self.get_address_index(address)
        return self.accounts[account_id].get_private_key(sequence, self, password)


    def get_public_keys(self, address):
        account_id, sequence = self.get_address_index(address)
        return self.accounts[account_id].get_pubkeys(sequence)


    def add_keypairs_from_wallet(self, tx, keypairs, password):
        for txin in tx.inputs:
            address = txin['address']
            if not self.is_mine(address):
                continue
            private_keys = self.get_private_key(address, password)
            for sec in private_keys:
                pubkey = public_key_from_private_key(sec)
                keypairs[ pubkey ] = sec



    def add_keypairs_from_KeyID(self, tx, keypairs, password):
        # first check the provided password
        seed = self.get_seed(password)

        for txin in tx.inputs:
            keyid = txin.get('KeyID')
            if keyid:
                roots = []
                for s in keyid.split('&'):
                    m = re.match("bip32\((.*),(/\d+/\d+)\)", s)
                    if not m: continue
                    xpub = m.group(1)
                    sequence = m.group(2)
                    root = self.find_root_by_master_key(xpub)
                    if not root: continue
                    sequence = map(lambda x:int(x), sequence.strip('/').split('/'))
                    root = root + '%d'%sequence[0]
                    sequence = sequence[1:]
                    roots.append((root,sequence)) 

                account_id = " & ".join( map(lambda x:x[0], roots) )
                account = self.accounts.get(account_id)
                if not account: continue
                addr = account.get_address(*sequence)
                txin['address'] = addr # fixme: side effect
                pk = self.get_private_key(addr, password)
                for sec in pk:
                    pubkey = public_key_from_private_key(sec)
                    keypairs[pubkey] = sec



    def signrawtransaction(self, tx, input_info, private_keys, password):

        # check that the password is correct
        seed = self.get_seed(password)

        # if input_info is not known, build it using wallet UTXOs
        if not input_info:
            input_info = []
            unspent_coins = self.get_unspent_coins()
            for txin in tx.inputs:
                for item in unspent_coins:
                    if txin['prevout_hash'] == item['prevout_hash'] and txin['prevout_n'] == item['prevout_n']:
                        info = { 'address':item['address'], 'scriptPubKey':item['scriptPubKey'] }
                        self.add_input_info(info)
                        input_info.append(info)
                        break
                else:
                    print_error( "input not in UTXOs" )
                    input_info.append(None)

        # add input_info to the transaction
        print_error("input_info", input_info)
        tx.add_input_info(input_info)

        # build a list of public/private keys
        keypairs = {}

        # add private keys from parameter
        for sec in private_keys:
            pubkey = public_key_from_private_key(sec)
            keypairs[ pubkey ] = sec

        # add private_keys from KeyID
        self.add_keypairs_from_KeyID(tx, keypairs, password)
        # add private keys from wallet
        self.add_keypairs_from_wallet(tx, keypairs, password)
        # sign the transaction
        self.sign_transaction(tx, keypairs, password)


    def sign_message(self, address, message, password):
        keys = self.get_private_key(address, password)
        assert len(keys) == 1
        sec = keys[0]
        key = regenerate_key(sec)
        compressed = is_compressed(sec)
        return key.sign_message(message, compressed, address)



    def decrypt_message(self, pubkey, message, password):
        address = public_key_to_bc_address(pubkey.decode('hex'))
        keys = self.get_private_key(address, password)
        secret = keys[0]
        ec = regenerate_key(secret)
        decrypted = ec.decrypt_message(message)
        return decrypted



    def is_found(self):
        return self.history.values() != [[]] * len(self.history) 


    def add_contact(self, address, label=None):
        self.addressbook.append(address)
        self.storage.put('contacts', self.addressbook, True)
        if label:  
            self.set_label(address, label)


    def delete_contact(self, addr):
        if addr in self.addressbook:
            self.addressbook.remove(addr)
            self.storage.put('addressbook', self.addressbook, True)


    def fill_addressbook(self):
        for tx_hash, tx in self.transactions.items():
            is_relevant, is_send, _, _ = self.get_tx_value(tx)
            if is_send:
                for addr, v in tx.outputs:
                    if not self.is_mine(addr) and addr not in self.addressbook:
                        self.addressbook.append(addr)
        # redo labels
        # self.update_tx_labels()

    def get_num_tx(self, address):
        n = 0 
        for tx in self.transactions.values():
            if address in map(lambda x:x[0], tx.outputs): n += 1
        return n


    def get_address_flags(self, addr):
        flags = "C" if self.is_change(addr) else "I" if addr in self.imported_keys.keys() else "-" 
        flags += "F" if addr in self.frozen_addresses else "-"
        return flags
        

    def get_tx_value(self, tx, account=None):
        domain = self.get_account_addresses(account)
        return tx.get_value(domain, self.prevout_values)

    
    def update_tx_outputs(self, tx_hash):
        tx = self.transactions.get(tx_hash)

        for i, (addr, value) in enumerate(tx.outputs):
            key = tx_hash+ ':%d'%i
            self.prevout_values[key] = value

        for item in tx.inputs:
            if self.is_mine(item.get('address')):
                key = item['prevout_hash'] + ':%d'%item['prevout_n']
                self.spent_outputs.append(key)


    def get_addr_balance(self, address):
        #assert self.is_mine(address)
        h = self.history.get(address,[])
        if h == ['*']: return 0,0
        c = u = 0
        received_coins = []   # list of coins received at address

        for tx_hash, tx_height in h:
            tx = self.transactions.get(tx_hash)
            if not tx: continue

            for i, (addr, value) in enumerate(tx.outputs):
                if addr == address:
                    key = tx_hash + ':%d'%i
                    received_coins.append(key)

        for tx_hash, tx_height in h:
            tx = self.transactions.get(tx_hash)
            if not tx: continue
            v = 0

            for item in tx.inputs:
                addr = item.get('address')
                if addr == address:
                    key = item['prevout_hash']  + ':%d'%item['prevout_n']
                    value = self.prevout_values.get( key )
                    if key in received_coins: 
                        v -= value

            for i, (addr, value) in enumerate(tx.outputs):
                key = tx_hash + ':%d'%i
                if addr == address:
                    v += value

            if tx_height:
                c += v
            else:
                u += v
        return c, u


    def get_account_name(self, k):
        return self.labels.get(k, self.accounts[k].get_name(k))


    def get_account_names(self):
        account_names = {}
        for k in self.accounts.keys():
            account_names[k] = self.get_account_name(k)
        return account_names


    def get_account_addresses(self, a, include_change=True):
        if a is None:
            o = self.addresses(True)
        elif a in self.accounts:
            ac = self.accounts[a]
            o = ac.get_addresses(0)
            if include_change: o += ac.get_addresses(1)
        return o


    def get_account_balance(self, account):
        return self.get_balance(self.get_account_addresses(account))

    def get_frozen_balance(self):
        return self.get_balance(self.frozen_addresses)
        
    def get_balance(self, domain=None):
        if domain is None: domain = self.addresses(True)
        cc = uu = 0
        for addr in domain:
            c, u = self.get_addr_balance(addr)
            cc += c
            uu += u
        return cc, uu


    def get_unspent_coins(self, domain=None):
        coins = []
        if domain is None: domain = self.addresses(True)
        for addr in domain:
            h = self.history.get(addr, [])
            if h == ['*']: continue
            for tx_hash, tx_height in h:
                tx = self.transactions.get(tx_hash)
                if tx is None: raise Exception("Wallet not synchronized")
                is_coinbase = tx.inputs[0].get('prevout_hash') == '0'*64
                for o in tx.d.get('outputs'):
                    output = o.copy()
                    if output.get('address') != addr: continue
                    key = tx_hash + ":%d" % output.get('prevout_n')
                    if key in self.spent_outputs: continue
                    output['prevout_hash'] = tx_hash
                    output['height'] = tx_height
                    output['coinbase'] = is_coinbase
                    coins.append((tx_height, output))

        # sort by age
        if coins:
            coins = sorted(coins)
            if coins[-1][0] != 0:
                while coins[0][0] == 0: 
                    coins = coins[1:] + [ coins[0] ]
        return [x[1] for x in coins]


    def choose_tx_inputs( self, amount, fixed_fee, num_outputs, domain = None ):
        """ todo: minimize tx size """
        total = 0
        fee = self.fee if fixed_fee is None else fixed_fee
        if domain is None:
            domain = self.addresses(True)

        for i in self.frozen_addresses:
            if i in domain: domain.remove(i)

        coins = self.get_unspent_coins(domain)
        inputs = []

        for item in coins:
            if item.get('coinbase') and item.get('height') + COINBASE_MATURITY > self.network.get_local_height():
                continue
            addr = item.get('address')
            v = item.get('value')
            total += v
            inputs.append(item)
            fee = self.estimated_fee(inputs, num_outputs) if fixed_fee is None else fixed_fee
            if total >= amount + fee: break
        else:
            inputs = []

        return inputs, total, fee


    def set_fee(self, fee):
        if self.fee != fee:
            self.fee = fee
            self.storage.put('fee_per_kb', self.fee, True)
        
    def estimated_fee(self, inputs, num_outputs):
        estimated_size =  len(inputs) * 180 + num_outputs * 34    # this assumes non-compressed keys
        fee = self.fee * int(math.ceil(estimated_size/1000.))
        return fee


    def add_tx_change( self, inputs, outputs, amount, fee, total, change_addr=None):
        "add change to a transaction"
        change_amount = total - ( amount + fee )
        if change_amount > DUST_THRESHOLD:
            if not change_addr:

                # send change to one of the accounts involved in the tx
                address = inputs[0].get('address')
                account, _ = self.get_address_index(address)

                if not self.use_change or account == IMPORTED_ACCOUNT:
                    change_addr = inputs[-1]['address']
                else:
                    change_addr = self.accounts[account].get_addresses(1)[-self.gap_limit_for_change]

            # Insert the change output at a random position in the outputs
            posn = random.randint(0, len(outputs))
            outputs[posn:posn] = [( change_addr,  change_amount)]
        return outputs


    def get_history(self, address):
        with self.lock:
            return self.history.get(address)


    def get_status(self, h):
        if not h: return None
        if h == ['*']: return '*'
        status = ''
        for tx_hash, height in h:
            status += tx_hash + ':%d:' % height
        return hashlib.sha256( status ).digest().encode('hex')


    def receive_tx_callback(self, tx_hash, tx, tx_height):

        with self.transaction_lock:
            self.add_extra_addresses(tx)
            if not self.check_new_tx(tx_hash, tx):
                # may happen due to pruning
                print_error("received transaction that is no longer referenced in history", tx_hash)
                return
            self.transactions[tx_hash] = tx
            self.network.pending_transactions_for_notifications.append(tx)
            self.save_transactions()
            if self.verifier and tx_height>0: 
                self.verifier.add(tx_hash, tx_height)
            self.update_tx_outputs(tx_hash)


    def save_transactions(self):
        tx = {}
        for k,v in self.transactions.items():
            tx[k] = str(v)
        self.storage.put('transactions', tx, True)

    def receive_history_callback(self, addr, hist):

        if not self.check_new_history(addr, hist):
            raise Exception("error: received history for %s is not consistent with known transactions"%addr)
            
        with self.lock:
            self.history[addr] = hist
            self.storage.put('addr_history', self.history, True)

        if hist != ['*']:
            for tx_hash, tx_height in hist:
                if tx_height>0:
                    # add it in case it was previously unconfirmed
                    if self.verifier: self.verifier.add(tx_hash, tx_height)


    def get_tx_history(self, account=None):
        if not self.verifier:
            return []

        with self.transaction_lock:
            history = self.transactions.items()
            history.sort(key = lambda x: self.verifier.get_txpos(x[0]))
            result = []
    
            balance = 0
            for tx_hash, tx in history:
                is_relevant, is_mine, v, fee = self.get_tx_value(tx, account)
                if v is not None: balance += v

            c, u = self.get_account_balance(account)

            if balance != c+u:
                result.append( ('', 1000, 0, c+u-balance, None, c+u-balance, None ) )

            balance = c + u - balance
            for tx_hash, tx in history:
                is_relevant, is_mine, value, fee = self.get_tx_value(tx, account)
                if not is_relevant:
                    continue
                if value is not None:
                    balance += value

                conf, timestamp = self.verifier.get_confirmations(tx_hash) if self.verifier else (None, None)
                result.append( (tx_hash, conf, is_mine, value, fee, balance, timestamp) )

        return result


    def get_label(self, tx_hash):
        label = self.labels.get(tx_hash)
        is_default = (label == '') or (label is None)
        if is_default: label = self.get_default_label(tx_hash)
        return label, is_default


    def get_default_label(self, tx_hash):
        tx = self.transactions.get(tx_hash)
        default_label = ''
        if tx:
            is_relevant, is_mine, _, _ = self.get_tx_value(tx)
            if is_mine:
                for o in tx.outputs:
                    o_addr, _ = o
                    if not self.is_mine(o_addr):
                        try:
                            default_label = self.labels[o_addr]
                        except KeyError:
                            default_label = '>' + o_addr
                        break
                else:
                    default_label = '(internal)'
            else:
                for o in tx.outputs:
                    o_addr, _ = o
                    if self.is_mine(o_addr) and not self.is_change(o_addr):
                        break
                else:
                    for o in tx.outputs:
                        o_addr, _ = o
                        if self.is_mine(o_addr):
                            break
                    else:
                        o_addr = None

                if o_addr:
                    dest_label = self.labels.get(o_addr)
                    try:
                        default_label = self.labels[o_addr]
                    except KeyError:
                        default_label = '<' + o_addr

        return default_label


    def make_unsigned_transaction(self, outputs, fee=None, change_addr=None, domain=None ):
        for address, x in outputs:
            assert is_valid(address), "Address " + address + " is invalid!"
        amount = sum( map(lambda x:x[1], outputs) )
        inputs, total, fee = self.choose_tx_inputs( amount, fee, len(outputs), domain )
        if not inputs:
            raise ValueError("Not enough funds")
        for txin in inputs:
            self.add_input_info(txin)
        outputs = self.add_tx_change(inputs, outputs, amount, fee, total, change_addr)
        return Transaction.from_io(inputs, outputs)


    def mktx(self, outputs, password, fee=None, change_addr=None, domain= None ):
        tx = self.make_unsigned_transaction(outputs, fee, change_addr, domain)
        keypairs = {}
        self.add_keypairs_from_wallet(tx, keypairs, password)
        if keypairs:
            self.sign_transaction(tx, keypairs, password)
        return tx


    def add_input_info(self, txin):
        address = txin['address']
        account_id, sequence = self.get_address_index(address)
        account = self.accounts[account_id]
        txin['KeyID'] = account.get_keyID(sequence)
        redeemScript = account.redeem_script(sequence)
        if redeemScript: 
            txin['redeemScript'] = redeemScript
        else:
            txin['redeemPubkey'] = account.get_pubkey(*sequence)


    def sign_transaction(self, tx, keypairs, password):
        tx.sign(keypairs)
        run_hook('sign_transaction', tx, password)


    def sendtx(self, tx):
        # synchronous
        h = self.send_tx(tx)
        self.tx_event.wait()
        return self.receive_tx(h, tx)

    def send_tx(self, tx):
        # asynchronous
        self.tx_event.clear()
        self.network.send([('blockchain.transaction.broadcast', [str(tx)])], self.on_broadcast)
        return tx.hash()

    def on_broadcast(self, i, r):
        self.tx_result = r.get('result')
        self.tx_event.set()

    def receive_tx(self, tx_hash, tx):
        out = self.tx_result 
        if out != tx_hash:
            return False, "error: " + out
        run_hook('receive_tx', tx, self)
        return True, out


    def update_password(self, old_password, new_password):
        if new_password == '': 
            new_password = None

        if self.has_seed():
            decoded = self.get_seed(old_password)
            self.seed = pw_encode( decoded, new_password)
            self.storage.put('seed', self.seed, True)

        imported_account = self.accounts.get(IMPORTED_ACCOUNT)
        if imported_account: 
            imported_account.update_password(old_password, new_password)
            self.save_accounts()

        for k, v in self.master_private_keys.items():
            b = pw_decode(v, old_password)
            c = pw_encode(b, new_password)
            self.master_private_keys[k] = c
        self.storage.put('master_private_keys', self.master_private_keys, True)

        self.use_encryption = (new_password != None)
        self.storage.put('use_encryption', self.use_encryption,True)


    def freeze(self,addr):
        if self.is_mine(addr) and addr not in self.frozen_addresses:
            self.frozen_addresses.append(addr)
            self.storage.put('frozen_addresses', self.frozen_addresses, True)
            return True
        else:
            return False


    def unfreeze(self,addr):
        if self.is_mine(addr) and addr in self.frozen_addresses:
            self.frozen_addresses.remove(addr)
            self.storage.put('frozen_addresses', self.frozen_addresses, True)
            return True
        else:
            return False


    def set_verifier(self, verifier):
        self.verifier = verifier

        # review transactions that are in the history
        for addr, hist in self.history.items():
            if hist == ['*']: continue
            for tx_hash, tx_height in hist:
                if tx_height>0:
                    # add it in case it was previously unconfirmed
                    self.verifier.add(tx_hash, tx_height)

        # if we are on a pruning server, remove unverified transactions
        vr = self.verifier.transactions.keys() + self.verifier.verified_tx.keys()
        for tx_hash in self.transactions.keys():
            if tx_hash not in vr:
                self.transactions.pop(tx_hash)


    def check_new_history(self, addr, hist):
        
        # check that all tx in hist are relevant
        if hist != ['*']:
            for tx_hash, height in hist:
                tx = self.transactions.get(tx_hash)
                if not tx: continue
                if not tx.has_address(addr):
                    return False

        # check that we are not "orphaning" a transaction
        old_hist = self.history.get(addr,[])
        if old_hist == ['*']: return True

        for tx_hash, height in old_hist:
            if tx_hash in map(lambda x:x[0], hist): continue
            found = False
            for _addr, _hist in self.history.items():
                if _addr == addr: continue
                if _hist == ['*']: continue
                _tx_hist = map(lambda x:x[0], _hist)
                if tx_hash in _tx_hist:
                    found = True
                    break

            if not found:
                tx = self.transactions.get(tx_hash)
                # tx might not be there
                if not tx: continue
                
                # already verified?
                if self.verifier.get_height(tx_hash):
                    continue
                # unconfirmed tx
                print_error("new history is orphaning transaction:", tx_hash)
                # check that all outputs are not mine, request histories
                ext_requests = []
                for _addr, _v in tx.outputs:
                    # assert not self.is_mine(_addr)
                    ext_requests.append( ('blockchain.address.get_history', [_addr]) )

                ext_h = self.network.synchronous_get(ext_requests)
                print_error("sync:", ext_requests, ext_h)
                height = None
                for h in ext_h:
                    if h == ['*']: continue
                    for item in h:
                        if item.get('tx_hash') == tx_hash:
                            height = item.get('height')
                if height:
                    print_error("found height for", tx_hash, height)
                    self.verifier.add(tx_hash, height)
                else:
                    print_error("removing orphaned tx from history", tx_hash)
                    self.transactions.pop(tx_hash)

        return True


    def check_new_tx(self, tx_hash, tx):
        # 1 check that tx is referenced in addr_history. 
        addresses = []
        for addr, hist in self.history.items():
            if hist == ['*']:continue
            for txh, height in hist:
                if txh == tx_hash: 
                    addresses.append(addr)

        if not addresses:
            return False

        # 2 check that referencing addresses are in the tx
        for addr in addresses:
            if not tx.has_address(addr):
                return False

        return True


    def start_threads(self, network):
        from verifier import TxVerifier
        self.network = network
        if self.network is not None:
            self.verifier = TxVerifier(self.network, self.storage)
            self.verifier.start()
            self.set_verifier(self.verifier)
            self.synchronizer = WalletSynchronizer(self, network)
            self.synchronizer.start()
        else:
            self.verifier = None
            self.synchronizer =None

    def stop_threads(self):
        if self.network:
            self.verifier.stop()
            self.synchronizer.stop()

    def restore(self, cb):
        pass

    def get_accounts(self):
        return self.accounts

    def save_accounts(self):
        d = {}
        for k, v in self.accounts.items():
            d[k] = v.dump()
        self.storage.put('accounts', d, True)

    def can_import(self):
        return not self.is_watching_only()

    def is_used(self, address):
        h = self.history.get(address,[])
        c, u = self.get_addr_balance(address)
        return len(h), len(h) > 0 and c == -u
    

class Imported_Wallet(Abstract_Wallet):

    def __init__(self, storage):
        Abstract_Wallet.__init__(self, storage)
        a = self.accounts.get(IMPORTED_ACCOUNT)
        if not a:
            self.accounts[IMPORTED_ACCOUNT] = ImportedAccount({'imported':{}})
        self.storage.put('wallet_type', 'imported', True)


    def is_watching_only(self):
        acc = self.accounts[IMPORTED_ACCOUNT]
        n = acc.keypairs.values()
        return n == [(None, None)] * len(n)

    def has_seed(self):
        return False

    def is_deterministic(self):
        return False

    def check_password(self, password):
        self.accounts[IMPORTED_ACCOUNT].get_private_key((0,0), self, password)

    def is_used(self, address):
        h = self.history.get(address,[])
        return len(h), False


class Deterministic_Wallet(Abstract_Wallet):

    def __init__(self, storage):
        Abstract_Wallet.__init__(self, storage)

    def has_seed(self):
        return self.seed != ''

    def is_deterministic(self):
        return True

    def is_watching_only(self):
        return not self.has_seed()

    def add_seed(self, seed, password):
        if self.seed: 
            raise Exception("a seed exists")
        
        self.seed_version, self.seed = self.prepare_seed(seed)
        if password: 
            self.seed = pw_encode( self.seed, password)
            self.use_encryption = True
        else:
            self.use_encryption = False

        self.storage.put('seed', self.seed, True)
        self.storage.put('seed_version', self.seed_version, True)
        self.storage.put('use_encryption', self.use_encryption,True)
        self.create_master_keys(password)

    def get_seed(self, password):
        return pw_decode(self.seed, password)

    def get_mnemonic(self, password):
        return self.get_seed(password)
        
    def change_gap_limit(self, value):
        if value >= self.gap_limit:
            self.gap_limit = value
            self.storage.put('gap_limit', self.gap_limit, True)
            #self.interface.poke('synchronizer')
            return True

        elif value >= self.min_acceptable_gap():
            for key, account in self.accounts.items():
                addresses = account[0]
                k = self.num_unused_trailing_addresses(addresses)
                n = len(addresses) - k + value
                addresses = addresses[0:n]
                self.accounts[key][0] = addresses

            self.gap_limit = value
            self.storage.put('gap_limit', self.gap_limit, True)
            self.save_accounts()
            return True
        else:
            return False

    def num_unused_trailing_addresses(self, addresses):
        k = 0
        for a in addresses[::-1]:
            if self.history.get(a):break
            k = k + 1
        return k

    def min_acceptable_gap(self):
        # fixme: this assumes wallet is synchronized
        n = 0
        nmax = 0

        for account in self.accounts.values():
            addresses = account.get_addresses(0)
            k = self.num_unused_trailing_addresses(addresses)
            for a in addresses[0:-k]:
                if self.history.get(a):
                    n = 0
                else:
                    n += 1
                    if n > nmax: nmax = n
        return nmax + 1


    def address_is_old(self, address):
        age = -1
        h = self.history.get(address, [])
        if h == ['*']:
            return True
        for tx_hash, tx_height in h:
            if tx_height == 0:
                tx_age = 0
            else:
                tx_age = self.network.get_local_height() - tx_height + 1
            if tx_age > age:
                age = tx_age
        return age > 2


    def synchronize_sequence(self, account, for_change):
        limit = self.gap_limit_for_change if for_change else self.gap_limit
        new_addresses = []
        while True:
            addresses = account.get_addresses(for_change)
            if len(addresses) < limit:
                address = account.create_new_address(for_change)
                self.history[address] = []
                new_addresses.append( address )
                continue

            if map( lambda a: self.address_is_old(a), addresses[-limit:] ) == limit*[False]:
                break
            else:
                address = account.create_new_address(for_change)
                self.history[address] = []
                new_addresses.append( address )

        return new_addresses
        

    def check_pending_accounts(self):
        for account_id, addr in self.next_addresses.items():
            if self.address_is_old(addr):
                print_error( "creating account", account_id )
                xpub = self.master_public_keys[account_id]
                account = BIP32_Account({'xpub':xpub})
                self.add_account(account_id, account)
                self.next_addresses.pop(account_id)


    def synchronize_account(self, account):
        new = []
        new += self.synchronize_sequence(account, 0)
        new += self.synchronize_sequence(account, 1)
        return new


    def synchronize(self):
        self.check_pending_accounts()
        new = []
        for account in self.accounts.values():
            if type(account) in [ImportedAccount, PendingAccount]:
                continue
            new += self.synchronize_account(account)
        if new:
            self.save_accounts()
            self.storage.put('addr_history', self.history, True)
        return new


    def restore(self, callback):
        from i18n import _
        def wait_for_wallet():
            self.set_up_to_date(False)
            while not self.is_up_to_date():
                msg = "%s\n%s %d\n%s %.1f"%(
                    _("Please wait..."),
                    _("Addresses generated:"),
                    len(self.addresses(True)), 
                    _("Kilobytes received:"), 
                    self.network.interface.bytes_received/1024.)

                apply(callback, (msg,))
                time.sleep(0.1)

        def wait_for_network():
            while not self.network.is_connected():
                msg = "%s \n" % (_("Connecting..."))
                apply(callback, (msg,))
                time.sleep(0.1)

        # wait until we are connected, because the user might have selected another server
        if self.network:
            wait_for_network()
            wait_for_wallet()
        else:
            self.synchronize()
            
        self.fill_addressbook()


    def create_account(self, name, password):
        i = self.num_accounts()
        account_id = self.account_id(i)
        account = self.make_account(account_id, password)
        self.add_account(account_id, account)
        if name:
            self.set_label(account_id, name)

        # add address of the next account
        _, _ = self.next_account_address(password)


    def add_account(self, account_id, account):
        self.accounts[account_id] = account
        self.save_accounts()



    def account_is_pending(self, k):
        return type(self.accounts.get(k)) == PendingAccount

    def delete_pending_account(self, k):
        assert self.account_is_pending(k)
        self.accounts.pop(k)
        self.save_accounts()

    def create_pending_account(self, name, password):
        account_id, addr = self.next_account_address(password)
        self.set_label(account_id, name)
        self.accounts[account_id] = PendingAccount({'pending':addr})
        self.save_accounts()




class NewWallet(Deterministic_Wallet):

    def __init__(self, storage):
        Deterministic_Wallet.__init__(self, storage)

    def can_create_accounts(self):
        return not self.is_watching_only()

    def get_master_public_key(self):
        return self.master_public_keys["m/"]

    def get_master_public_keys(self):
        out = {}
        for k, account in self.accounts.items():
            name = self.get_account_name(k)
            mpk_text = '\n\n'.join( account.get_master_pubkeys() )
            out[name] = mpk_text
        return out

    def get_master_private_key(self, account, password):
        k = self.master_private_keys.get(account)
        if not k: return
        xpriv = pw_decode( k, password)
        return xpriv

    def check_password(self, password):
        xpriv = self.get_master_private_key( "m/", password )
        xpub = self.master_public_keys["m/"]
        assert deserialize_xkey(xpriv)[3] == deserialize_xkey(xpub)[3]

    def create_watching_only_wallet(self, xpub):
        self.storage.put('seed_version', self.seed_version, True)
        self.add_master_public_key("m/", xpub)
        account = BIP32_Account({'xpub':xpub})
        self.add_account("m/", account)


    def create_accounts(self, password):
        seed = pw_decode(self.seed, password)
        self.create_account('Main account', password)


    def add_master_public_key(self, name, mpk):
        self.master_public_keys[name] = mpk
        self.storage.put('master_public_keys', self.master_public_keys, True)


    def add_master_private_key(self, name, xpriv, password):
        self.master_private_keys[name] = pw_encode(xpriv, password)
        self.storage.put('master_private_keys', self.master_private_keys, True)


    def add_master_keys(self, root, account_id, password):
        x = self.master_private_keys.get(root)
        if x: 
            master_xpriv = pw_decode(x, password )
            xpriv, xpub = bip32_private_derivation(master_xpriv, root, account_id)
            self.add_master_public_key(account_id, xpub)
            self.add_master_private_key(account_id, xpriv, password)
        else:
            master_xpub = self.master_public_keys[root]
            xpub = bip32_public_derivation(master_xpub, root, account_id)
            self.add_master_public_key(account_id, xpub)
        return xpub


    def create_master_keys(self, password):
        xpriv, xpub = bip32_root(mnemonic_to_seed(self.get_seed(password),'').encode('hex'))
        self.add_master_public_key("m/", xpub)
        self.add_master_private_key("m/", xpriv, password)


    def find_root_by_master_key(self, xpub):
        for key, xpub2 in self.master_public_keys.items():
            if key == "m/":continue
            if xpub == xpub2:
                return key


    def num_accounts(self):
        keys = []
        for k, v in self.accounts.items():
            if type(v) != BIP32_Account:
                continue
            keys.append(k)

        i = 0
        while True:
            account_id = self.account_id(i)
            if account_id not in keys: break
            i += 1
        return i


    def next_account_address(self, password):
        i = self.num_accounts()
        account_id = self.account_id(i)

        addr = self.next_addresses.get(account_id)
        if not addr: 
            account = self.make_account(account_id, password)
            addr = account.first_address()
            self.next_addresses[account_id] = addr
            self.storage.put('next_addresses', self.next_addresses)

        return account_id, addr

    def account_id(self, i):
        return "m/%d'"%i

    def make_account(self, account_id, password):
        """Creates and saves the master keys, but does not save the account"""
        xpub = self.add_master_keys("m/", account_id, password)
        account = BIP32_Account({'xpub':xpub})
        return account


    def make_seed(self):
        import mnemonic, ecdsa
        entropy = ecdsa.util.randrange( pow(2,160) )
        nonce = 0
        while True:
            ss = "%040x"%(entropy+nonce)
            s = hashlib.sha256(ss.decode('hex')).digest().encode('hex')
            # we keep only 13 words, that's approximately 139 bits of entropy
            words = mnemonic.mn_encode(s)[0:13] 
            seed = ' '.join(words)
            if is_new_seed(seed):
                break  # this will remove 8 bits of entropy
            nonce += 1
        return seed

    def prepare_seed(self, seed):
        import unicodedata
        return NEW_SEED_VERSION, unicodedata.normalize('NFC', unicode(seed.strip()))



class Wallet_2of2(NewWallet):

    def __init__(self, storage):
        NewWallet.__init__(self, storage)
        self.storage.put('wallet_type', '2of2', True)

    def can_create_accounts(self):
        return False

    def can_import(self):
        return False

    def create_account(self):
        xpub1 = self.master_public_keys.get("m/")
        xpub2 = self.master_public_keys.get("cold/")
        account = BIP32_Account_2of2({'xpub':xpub1, 'xpub2':xpub2})
        self.add_account('m/', account)

    def get_master_public_keys(self):
        xpub1 = self.master_public_keys.get("m/")
        xpub2 = self.master_public_keys.get("cold/")
        return {'hot':xpub1, 'cold':xpub2}

    def get_action(self):
        xpub1 = self.master_public_keys.get("m/")
        xpub2 = self.master_public_keys.get("cold/")
        if xpub1 is None:
            return 'create_2of2_1'
        if xpub2 is None:
            return 'create_2of2_2'



class Wallet_2of3(Wallet_2of2):

    def __init__(self, storage):
        Wallet_2of2.__init__(self, storage)
        self.storage.put('wallet_type', '2of3', True)

    def create_account(self):
        xpub1 = self.master_public_keys.get("m/")
        xpub2 = self.master_public_keys.get("cold/")
        xpub3 = self.master_public_keys.get("remote/")
        account = BIP32_Account_2of3({'xpub':xpub1, 'xpub2':xpub2, 'xpub3':xpub3})
        self.add_account('m/', account)

    def get_master_public_keys(self):
        xpub1 = self.master_public_keys.get("m/")
        xpub2 = self.master_public_keys.get("cold/")
        xpub3 = self.master_public_keys.get("remote/")
        return {'hot':xpub1, 'cold':xpub2, 'remote':xpub3}

    def get_action(self):
        xpub1 = self.master_public_keys.get("m/")
        xpub2 = self.master_public_keys.get("cold/")
        xpub3 = self.master_public_keys.get("remote/")
        # fixme: we use order of creation
        if xpub2 and xpub1 is None:
            return 'create_2fa_2'
        if xpub1 is None:
            return 'create_2of3_1'
        if xpub2 is None or xpub3 is None:
            return 'create_2of3_2'





class OldWallet(Deterministic_Wallet):

    def make_seed(self):
        import mnemonic
        seed = random_seed(128)
        return ' '.join(mnemonic.mn_encode(seed))

    def prepare_seed(self, seed):
        import mnemonic
        # see if seed was entered as hex
        seed = seed.strip()
        try:
            assert seed
            seed.decode('hex')
            return OLD_SEED_VERSION, str(seed)
        except Exception:
            pass

        words = seed.split()
        seed = mnemonic.mn_decode(words)
        if not seed:
            raise Exception("Invalid seed")
            
        return OLD_SEED_VERSION, seed


    def create_master_keys(self, password):
        seed = self.get_seed(password)
        mpk = OldAccount.mpk_from_seed(seed)
        self.storage.put('master_public_key', mpk, True)

    def get_master_public_key(self):
        return self.storage.get("master_public_key")

    def get_master_public_keys(self):
        return {'Main Account':self.get_master_public_key()}

    def create_accounts(self, password):
        mpk = self.storage.get("master_public_key")
        self.create_account(mpk)

    def create_account(self, mpk):
        self.accounts[0] = OldAccount({'mpk':mpk, 0:[], 1:[]})
        self.save_accounts()

    def create_watching_only_wallet(self, mpk):
        self.seed_version = OLD_SEED_VERSION
        self.storage.put('seed_version', self.seed_version, True)
        self.storage.put('master_public_key', mpk, True)
        self.create_account(mpk)

    def get_seed(self, password):
        seed = pw_decode(self.seed, password).encode('utf8')
        return seed

    def check_password(self, password):
        seed = pw_decode(self.seed, password)
        self.accounts[0].check_seed(seed)

    def get_mnemonic(self, password):
        import mnemonic
        s = self.get_seed(password)
        return ' '.join(mnemonic.mn_encode(s))


    def add_keypairs_from_KeyID(self, tx, keypairs, password):
        # first check the provided password
        for txin in tx.inputs:
            keyid = txin.get('KeyID')
            if keyid:
                m = re.match("old\(([0-9a-f]+),(\d+),(\d+)", keyid)
                if not m: continue
                mpk = m.group(1)
                if mpk != self.storage.get('master_public_key'): continue 
                for_change = int(m.group(2))
                num = int(m.group(3))
                account = self.accounts[0]
                addr = account.get_address(for_change, num)
                txin['address'] = addr # fixme: side effect
                pk = account.get_private_key((for_change, num), self, password)
                for sec in pk:
                    pubkey = public_key_from_private_key(sec)
                    keypairs[pubkey] = sec



    def check_pending_accounts(self):
        pass


# former WalletFactory
class Wallet(object):

    def __new__(self, storage):
        config = storage.config
        if config.get('bitkey', False):
            # if user requested support for Bitkey device,
            # import Bitkey driver
            from wallet_bitkey import WalletBitkey
            return WalletBitkey(config)

        if storage.get('wallet_type') == '2of2':
            return Wallet_2of2(storage)

        if storage.get('wallet_type') == '2of3':
            return Wallet_2of3(storage)

        if storage.get('wallet_type') == 'imported':
            return Imported_Wallet(storage)


        if not storage.file_exists:
            seed_version = NEW_SEED_VERSION if config.get('bip32') is True else OLD_SEED_VERSION
        else:
            seed_version = storage.get('seed_version')
            if not seed_version:
                seed_version = OLD_SEED_VERSION if len(storage.get('master_public_key')) == 128 else NEW_SEED_VERSION

        if seed_version == OLD_SEED_VERSION:
            return OldWallet(storage)
        elif seed_version == NEW_SEED_VERSION:
            return NewWallet(storage)
        else:
            msg = "This wallet seed is not supported."
            if seed_version in [5]:
                msg += "\nTo open this wallet, try 'git checkout seed_v%d'"%seed_version
            print msg
            sys.exit(1)



    @classmethod
    def is_seed(self, seed):
        if not seed:
            return False
        elif is_old_seed(seed):
            return True
        elif is_new_seed(seed):
            return True
        else: 
            return False

    @classmethod
    def is_mpk(self, mpk):
        try:
            int(mpk, 16)
            old = True
        except:
            old = False
            
        if old:
            return len(mpk) == 128
        else:
            try:
                deserialize_xkey(mpk)
                return True
            except:
                return False

    @classmethod
    def is_address(self, text):
        if not text:
            return False
        for x in text.split():
            if not bitcoin.is_address(x):
                return False
        return True

    @classmethod
    def is_private_key(self, text):
        if not text:
            return False
        for x in text.split():
            if not bitcoin.is_private_key(x):
                return False
        return True

    @classmethod
    def from_seed(self, seed, storage):
        if is_old_seed(seed):
            klass = OldWallet
        elif is_new_seed(seed):
            klass = NewWallet
        w = klass(storage)
        return w

    @classmethod
    def from_address(self, text, storage):
        w = Imported_Wallet(storage)
        for x in text.split():
            w.accounts[IMPORTED_ACCOUNT].add(x, None, None, None)
        w.save_accounts()
        return w

    @classmethod
    def from_private_key(self, text, storage):
        w = Imported_Wallet(storage)
        for x in text.split():
            w.import_key(x, None)
        return w

    @classmethod
    def from_mpk(self, mpk, storage):

        try:
            int(mpk, 16)
            old = True
        except:
            old = False

        if old:
            w = OldWallet(storage)
            w.seed = ''
            w.create_watching_only_wallet(mpk)
        else:
            w = NewWallet(storage)
            w.create_watching_only_wallet(mpk)

        return w

########NEW FILE########
__FILENAME__ = wallet_bitkey
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os

from wallet import Wallet
#import bitkeylib.bitkey_pb2 as proto

from version import ELECTRUM_VERSION
SEED_VERSION = 4 # Version of bitkey algorithm

class WalletBitkey(Wallet):
    pass

########NEW FILE########
__FILENAME__ = mki18n
#!/usr/bin/python
from StringIO import StringIO
import urllib2, os, zipfile, pycurl

crowdin_identifier = 'electrum'
crowdin_file_name = 'electrum-client/messages.pot'
locale_file_name = 'locale/messages.pot'

if os.path.exists('contrib/crowdin_api_key.txt'):
    crowdin_api_key = open('contrib/crowdin_api_key.txt').read()

    # Generate fresh translation template
    if not os.path.exists('locale'):
      os.mkdir('locale')

    cmd = 'xgettext -s --no-wrap -f app.fil --output=locale/messages.pot'
    print 'Generate template'
    os.system(cmd)

    # Push to Crowdin
    print 'Push to Crowdin'
    url = ('http://api.crowdin.net/api/project/' + crowdin_identifier + '/update-file?key=' + crowdin_api_key)

    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.POST, 1)
    fields = [('files[' + crowdin_file_name + ']', (pycurl.FORM_FILE, locale_file_name))]
    c.setopt(c.HTTPPOST, fields)
    c.perform()

    # Build translations
    print 'Build translations'
    response = urllib2.urlopen('http://api.crowdin.net/api/project/' + crowdin_identifier + '/export?key=' + crowdin_api_key).read()
    print response

# Download & unzip
print 'Download translations'
zfobj = zipfile.ZipFile(StringIO(urllib2.urlopen('http://crowdin.net/download/project/' + crowdin_identifier + '.zip').read()))

print 'Unzip translations'
for name in zfobj.namelist():
    if not name.startswith('electrum-client/locale'):
        continue
    if name.endswith('/'):
        if not os.path.exists(name[16:]):
            os.mkdir(name[16:])
    else:
        output = open(name[16:],'w')
        output.write(zfobj.read(name))
        output.close()

# Convert .po to .mo
print 'Installing'
for lang in os.listdir('./locale'):
    if lang.startswith('messages'):
        continue
    # Check LC_MESSAGES folder
    mo_dir = 'locale/%s/LC_MESSAGES' % lang
    if not os.path.exists(mo_dir):
        os.mkdir(mo_dir)
    cmd = 'msgfmt --output-file="%s/electrum.mo" "locale/%s/electrum.po"' % (mo_dir,lang)
    print 'Installing',lang
    os.system(cmd)

########NEW FILE########
__FILENAME__ = coinbase_buyback
import PyQt4
import sys

import PyQt4.QtCore as QtCore
import base64
import urllib
import re
import time
import os
import httplib
import datetime
import json
import string

from urllib import urlencode

from PyQt4.QtGui import *
from PyQt4.QtCore import *
try:
    from PyQt4.QtWebKit import QWebView
    loaded_qweb = True
except ImportError as e:
    loaded_qweb = False

from electrum import BasePlugin
from electrum.i18n import _, set_language
from electrum.util import user_dir
from electrum.util import appdata_dir
from electrum.util import format_satoshis
from electrum_gui.qt import ElectrumGui

SATOSHIS_PER_BTC = float(100000000)
COINBASE_ENDPOINT = 'https://coinbase.com'
SCOPE = 'buy'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
TOKEN_URI = 'https://coinbase.com/oauth/token'
CLIENT_ID = '0a930a48b5a6ea10fb9f7a9fec3d093a6c9062ef8a7eeab20681274feabdab06'
CLIENT_SECRET = 'f515989e8819f1822b3ac7a7ef7e57f755c9b12aee8f22de6b340a99fd0fd617'
# Expiry is stored in RFC3339 UTC format
EXPIRY_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

class Plugin(BasePlugin):

    def fullname(self): return 'Coinbase BuyBack'

    def description(self): return 'After sending bitcoin, prompt the user with the option to rebuy them via Coinbase.\n\nMarcell Ortutay, 1FNGQvm29tKM7y3niq63RKi7Qbg7oZ3jrB'

    def __init__(self, gui, name):
        BasePlugin.__init__(self, gui, name)
        self._is_available = self._init()

    def _init(self):
        return loaded_qweb

    def is_available(self):
        return self._is_available

    def enable(self):
        return BasePlugin.enable(self)

    def receive_tx(self, tx, wallet):
        domain = wallet.get_account_addresses(None)
        is_relevant, is_send, v, fee = tx.get_value(domain, wallet.prevout_values)
        if isinstance(self.gui, ElectrumGui):
            try:
                web = propose_rebuy_qt(abs(v))
            except OAuth2Exception as e:
                rm_local_oauth_credentials()
        # TODO(ortutay): android flow


def propose_rebuy_qt(amount):
    web = QWebView()
    box = QMessageBox()
    box.setFixedSize(200, 200)

    credentials = read_local_oauth_credentials()
    questionText = _('Rebuy ') + format_satoshis(amount) + _(' BTC?')
    if credentials:
        credentials.refresh()
    if credentials and not credentials.invalid:
        credentials.store_locally()
        totalPrice = get_coinbase_total_price(credentials, amount)
        questionText += _('\n(Price: ') + totalPrice + _(')')

    if not question(box, questionText):
        return

    if credentials:
        do_buy(credentials, amount)
    else:
        do_oauth_flow(web, amount)
    return web

def do_buy(credentials, amount):
    conn = httplib.HTTPSConnection('coinbase.com')
    credentials.authorize(conn)
    params = {
        'qty': float(amount)/SATOSHIS_PER_BTC,
        'agree_btc_amount_varies': False
    }
    resp = conn.auth_request('POST', '/api/v1/buys', urlencode(params), None)

    if resp.status != 200:
        message(_('Error, could not buy bitcoin'))
        return
    content = json.loads(resp.read())
    if content['success']:
        message(_('Success!\n') + content['transfer']['description'])
    else:
        if content['errors']:
            message(_('Error: ') + string.join(content['errors'], '\n'))
        else:
            message(_('Error, could not buy bitcoin'))

def get_coinbase_total_price(credentials, amount):
    conn = httplib.HTTPSConnection('coinbase.com')
    params={'qty': amount/SATOSHIS_PER_BTC}
    conn.request('GET', '/api/v1/prices/buy?' + urlencode(params))
    resp = conn.getresponse()
    if resp.status != 200:
        return 'unavailable'
    content = json.loads(resp.read())
    return '$' + content['total']['amount']

def do_oauth_flow(web, amount):
    # QT expects un-escaped URL
    auth_uri = step1_get_authorize_url()
    web.load(QUrl(auth_uri))
    web.setFixedSize(500, 700)
    web.show()
    web.titleChanged.connect(lambda(title): complete_oauth_flow(title, web, amount) if re.search('^[a-z0-9]+$', title) else False)

def complete_oauth_flow(token, web, amount):
    web.close()
    credentials = step2_exchange(str(token))
    credentials.store_locally()
    do_buy(credentials, amount)

def token_path():
    dir = user_dir() + '/coinbase_buyback'
    if not os.access(dir, os.F_OK):
        os.mkdir(dir)
    return dir + '/token'

def read_local_oauth_credentials():
    if not os.access(token_path(), os.F_OK):
        return None
    f = open(token_path(), 'r')
    data = f.read()
    f.close()
    try:
        credentials = Credentials.from_json(data)
        return credentials
    except Exception as e:
        return None

def rm_local_oauth_credentials():
    os.remove(token_path())

def step1_get_authorize_url():
    return ('https://coinbase.com/oauth/authorize'
            + '?scope=' + SCOPE
            + '&redirect_uri=' + REDIRECT_URI
            + '&response_type=code'
            + '&client_id=' + CLIENT_ID
            + '&access_type=offline')

def step2_exchange(code):
    body = urllib.urlencode({
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE,
        })
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
    }

    conn = httplib.HTTPSConnection('coinbase.com')
    conn.request('POST', TOKEN_URI, body, headers)
    resp = conn.getresponse()
    if resp.status == 200:
        d = json.loads(resp.read())
        access_token = d['access_token']
        refresh_token = d.get('refresh_token', None)
        token_expiry = None
        if 'expires_in' in d:
            token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=int(d['expires_in']))
        return Credentials(access_token, refresh_token, token_expiry)
    else:
        raise OAuth2Exception(content)

class OAuth2Exception(Exception):
    """An error related to OAuth2"""

class Credentials(object):
    def __init__(self, access_token, refresh_token, token_expiry):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        
        # Indicates a failed refresh
        self.invalid = False

    def to_json(self):
        token_expiry = self.token_expiry
        if (token_expiry and isinstance(token_expiry, datetime.datetime)):
            token_expiry = token_expiry.strftime(EXPIRY_FORMAT)
        
        d = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expiry': token_expiry,
        }
        return json.dumps(d)

    def store_locally(self):
        f = open(token_path(), 'w')
        f.write(self.to_json())
        f.close()

    @classmethod
    def from_json(cls, s):
        data = json.loads(s)
        if ('token_expiry' in data
            and not isinstance(data['token_expiry'], datetime.datetime)):
            try:
                data['token_expiry'] = datetime.datetime.strptime(
                    data['token_expiry'], EXPIRY_FORMAT)
            except:
                data['token_expiry'] = None
        retval = Credentials(
            data['access_token'],
            data['refresh_token'],
            data['token_expiry'])
        return retval

    def apply(self, headers):
        headers['Authorization'] = 'Bearer ' + self.access_token

    def authorize(self, conn):
        request_orig = conn.request

        def new_request(method, uri, params, headers):
            if headers == None:
                headers = {}
                self.apply(headers)
            request_orig(method, uri, params, headers)
            resp = conn.getresponse()
            if resp.status == 401:
                # Refresh and try again
                self._refresh(request_orig)
                self.store_locally()
                self.apply(headers)
                request_orig(method, uri, params, headers)
                return conn.getresponse()
            else:
                return resp
        
        conn.auth_request = new_request
        return conn

    def refresh(self):
        try:
            self._refresh()
        except OAuth2Exception as e:
            rm_local_oauth_credentials()
            self.invalid = True
            raise e

    def _refresh(self):
        conn = httplib.HTTPSConnection('coinbase.com')
        body = urllib.urlencode({
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        })
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
        }
        conn.request('POST', TOKEN_URI, body, headers)
        resp = conn.getresponse()
        if resp.status == 200:
            d = json.loads(resp.read())
            self.token_response = d
            self.access_token = d['access_token']
            self.refresh_token = d.get('refresh_token', self.refresh_token)
            if 'expires_in' in d:
                self.token_expiry = datetime.timedelta(
                    seconds=int(d['expires_in'])) + datetime.datetime.utcnow()
        else:
            raise OAuth2Exception('Refresh failed, ' + content)

def message(msg):
    box = QMessageBox()
    box.setFixedSize(200, 200)
    return QMessageBox.information(box, _('Message'), msg)

def question(widget, msg):
    return (QMessageBox.question(
        widget, _('Message'), msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            == QMessageBox.Yes)

def main():
    app = QApplication(sys.argv)
    print sys.argv[1]
    propose_rebuy_qt(int(sys.argv[1]))
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = exchange_rate
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import datetime
import decimal
import httplib
import json
import threading
import time
import re
from decimal import Decimal
from electrum.plugins import BasePlugin
from electrum.i18n import _
from electrum_gui.qt.util import *
from electrum_gui.qt.amountedit import AmountEdit


EXCHANGES = ["BitcoinAverage",
             "BitcoinVenezuela",
             "Bitcurex",
             "Bitmarket",
             "BitPay",
             "Blockchain",
             "BTCChina",
             "CaVirtEx",
             "Coinbase",
             "CoinDesk",
             "LocalBitcoins",
             "Winkdex"]


class Exchanger(threading.Thread):

    def __init__(self, parent):
        threading.Thread.__init__(self)
        self.daemon = True
        self.parent = parent
        self.quote_currencies = None
        self.lock = threading.Lock()
        self.query_rates = threading.Event()
        self.use_exchange = self.parent.config.get('use_exchange', "Blockchain")
        self.parent.exchanges = EXCHANGES
        self.parent.currencies = ["EUR","GBP","USD","PLN"]
        self.parent.win.emit(SIGNAL("refresh_exchanges_combo()"))
        self.parent.win.emit(SIGNAL("refresh_currencies_combo()"))
        self.is_running = False

    def get_json(self, site, get_string):
        try:
            connection = httplib.HTTPSConnection(site)
            connection.request("GET", get_string)
        except Exception:
            raise
        resp = connection.getresponse()
        if resp.reason == httplib.responses[httplib.NOT_FOUND]:
            raise
        try:
            json_resp = json.loads(resp.read())
        except Exception:
            raise
        return json_resp


    def exchange(self, btc_amount, quote_currency):
        with self.lock:
            if self.quote_currencies is None:
                return None
            quote_currencies = self.quote_currencies.copy()
        if quote_currency not in quote_currencies:
            return None
        if self.use_exchange == "CoinDesk":
            try:
                resp_rate = self.get_json('api.coindesk.com', "/v1/bpi/currentprice/" + str(quote_currency) + ".json")
            except Exception:
                return
            return btc_amount * decimal.Decimal(str(resp_rate["bpi"][str(quote_currency)]["rate_float"]))
        return btc_amount * decimal.Decimal(str(quote_currencies[quote_currency]))

    def stop(self):
        self.is_running = False

    def update_rate(self):
        self.use_exchange = self.parent.config.get('use_exchange', "Blockchain")
        update_rates = {
            "BitcoinAverage": self.update_ba,
            "BitcoinVenezuela": self.update_bv,
            "Bitcurex": self.update_bx,
            "Bitmarket": self.update_bm,
            "BitPay": self.update_bp,
            "Blockchain": self.update_bc,
            "BTCChina": self.update_CNY,
            "CaVirtEx": self.update_cv,
            "CoinDesk": self.update_cd,
            "Coinbase": self.update_cb,
            "LocalBitcoins": self.update_lb,
            "Winkdex": self.update_wd,
        }
        try:
            update_rates[self.use_exchange]()
        except KeyError:
            return

    def run(self):
        self.is_running = True
        while self.is_running:
            self.query_rates.clear()
            self.update_rate()
            self.query_rates.wait(150)


    def update_cd(self):
        try:
            resp_currencies = self.get_json('api.coindesk.com', "/v1/bpi/supported-currencies.json")
        except Exception:
            return

        quote_currencies = {}
        for cur in resp_currencies:
            quote_currencies[str(cur["currency"])] = 0.0
        with self.lock:
            self.quote_currencies = quote_currencies
        self.parent.set_currencies(quote_currencies)

    def update_wd(self):
        try:
            winkresp = self.get_json('winkdex.com', "/static/data/0_600_288.json")
            ####could need nonce value in GET, no Docs available
        except Exception:
            return
        quote_currencies = {"USD": 0.0}
        ####get y of highest x in "prices"
        lenprices = len(winkresp["prices"])
        usdprice = winkresp["prices"][lenprices-1]["y"]
        try:
            quote_currencies["USD"] = decimal.Decimal(str(usdprice))
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)

    def update_cv(self):
        try:
            jsonresp = self.get_json('www.cavirtex.com', "/api/CAD/ticker.json")
        except Exception:
            return
        quote_currencies = {"CAD": 0.0}
        cadprice = jsonresp["last"]
        try:
            quote_currencies["CAD"] = decimal.Decimal(str(cadprice))
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)

    def update_bm(self):
        try:
            jsonresp = self.get_json('www.bitmarket.pl', "/json/BTCPLN/ticker.json")
        except Exception:
            return
        quote_currencies = {"PLN": 0.0}
        pln_price = jsonresp["last"]
        try:
            quote_currencies["PLN"] = decimal.Decimal(str(pln_price))
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)

    def update_bx(self):
        try:
            jsonresp = self.get_json('pln.bitcurex.com', "/data/ticker.json")
        except Exception:
            return
        quote_currencies = {"PLN": 0.0}
        pln_price = jsonresp["last"]
        try:
            quote_currencies["PLN"] = decimal.Decimal(str(pln_price))
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)

    def update_CNY(self):
        try:
            jsonresp = self.get_json('data.btcchina.com', "/data/ticker")
        except Exception:
            return
        quote_currencies = {"CNY": 0.0}
        cnyprice = jsonresp["ticker"]["last"]
        try:
            quote_currencies["CNY"] = decimal.Decimal(str(cnyprice))
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)

    def update_bp(self):
        try:
            jsonresp = self.get_json('bitpay.com', "/api/rates")
        except Exception:
            return
        quote_currencies = {}
        try:
            for r in jsonresp:
                quote_currencies[str(r["code"])] = decimal.Decimal(r["rate"])
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)

    def update_cb(self):
        try:
            jsonresp = self.get_json('coinbase.com', "/api/v1/currencies/exchange_rates")
        except Exception:
            return

        quote_currencies = {}
        try:
            for r in jsonresp:
                if r[:7] == "btc_to_":
                    quote_currencies[r[7:].upper()] = self._lookup_rate_cb(jsonresp, r)
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)


    def update_bc(self):
        try:
            jsonresp = self.get_json('blockchain.info', "/ticker")
        except Exception:
            return
        quote_currencies = {}
        try:
            for r in jsonresp:
                quote_currencies[r] = self._lookup_rate(jsonresp, r)
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)
        # print "updating exchange rate", self.quote_currencies["USD"]

    def update_lb(self):
        try:
            jsonresp = self.get_json('localbitcoins.com', "/bitcoinaverage/ticker-all-currencies/")
        except Exception:
            return
        quote_currencies = {}
        try:
            for r in jsonresp:
                quote_currencies[r] = self._lookup_rate_lb(jsonresp, r)
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)


    def update_bv(self):
        try:
            jsonresp = self.get_json('api.bitcoinvenezuela.com', "/")
        except Exception:
            return
        quote_currencies = {}
        try:
            for r in jsonresp["BTC"]:
                quote_currencies[r] = Decimal(jsonresp["BTC"][r])
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)


    def update_ba(self):
        try:
            jsonresp = self.get_json('api.bitcoinaverage.com', "/ticker/global/all")
        except Exception:
            return
        quote_currencies = {}
        try:
            for r in jsonresp:
                if not r == "timestamp":
                    quote_currencies[r] = self._lookup_rate_ba(jsonresp, r)
            with self.lock:
                self.quote_currencies = quote_currencies
        except KeyError:
            pass
        self.parent.set_currencies(quote_currencies)


    def get_currencies(self):
        return [] if self.quote_currencies == None else sorted(self.quote_currencies.keys())

    def _lookup_rate(self, response, quote_id):
        return decimal.Decimal(str(response[str(quote_id)]["15m"]))
    def _lookup_rate_cb(self, response, quote_id):
        return decimal.Decimal(str(response[str(quote_id)]))
    def _lookup_rate_ba(self, response, quote_id):
        return decimal.Decimal(response[str(quote_id)]["last"])
    def _lookup_rate_lb(self, response, quote_id):
        return decimal.Decimal(response[str(quote_id)]["rates"]["last"])


class Plugin(BasePlugin):

    def fullname(self):
        return "Exchange rates"

    def description(self):
        return """exchange rates, retrieved from blockchain.info, CoinDesk, or Coinbase"""


    def __init__(self,a,b):
        BasePlugin.__init__(self,a,b)
        self.currencies = [self.config.get('currency', "EUR")]
        self.exchanges = [self.config.get('use_exchange', "Blockchain")]

    def init(self):
        self.win = self.gui.main_window
        self.win.connect(self.win, SIGNAL("refresh_currencies()"), self.win.update_status)
        self.btc_rate = Decimal("0.0")
        # Do price discovery
        self.exchanger = Exchanger(self)
        self.exchanger.start()
        self.gui.exchanger = self.exchanger #

    def set_currencies(self, currency_options):
        self.currencies = sorted(currency_options)
        self.win.emit(SIGNAL("refresh_currencies()"))
        self.win.emit(SIGNAL("refresh_currencies_combo()"))

    def get_fiat_balance_text(self, btc_balance, r):
        # return balance as: 1.23 USD
        r[0] = self.create_fiat_balance_text(Decimal(btc_balance) / 100000000)

    def get_fiat_price_text(self, r):
        # return BTC price as: 123.45 USD
        r[0] = self.create_fiat_balance_text(1)
        quote = r[0]
        if quote:
            r[0] = "%s"%quote

    def get_fiat_status_text(self, btc_balance, r2):
        # return status as:   (1.23 USD)    1 BTC~123.45 USD
        text = ""
        r = {}
        self.get_fiat_price_text(r)
        quote = r.get(0)
        if quote:
            price_text = "1 BTC~%s"%quote
            fiat_currency = quote[-3:]
            btc_price = self.btc_rate
            fiat_balance = Decimal(btc_price) * (Decimal(btc_balance)/100000000)
            balance_text = "(%.2f %s)" % (fiat_balance,fiat_currency)
            text = "  " + balance_text + "     " + price_text + " "
        r2[0] = text

    def create_fiat_balance_text(self, btc_balance):
        quote_currency = self.config.get("currency", "EUR")
        self.exchanger.use_exchange = self.config.get("use_exchange", "Blockchain")
        cur_rate = self.exchanger.exchange(Decimal("1.0"), quote_currency)
        if cur_rate is None:
            quote_text = ""
        else:
            quote_balance = btc_balance * Decimal(cur_rate)
            self.btc_rate = cur_rate
            quote_text = "%.2f %s" % (quote_balance, quote_currency)
        return quote_text

    def load_wallet(self, wallet):
        self.wallet = wallet
        tx_list = {}
        for item in self.wallet.get_tx_history(self.wallet.storage.get("current_account", None)):
            tx_hash, conf, is_mine, value, fee, balance, timestamp = item
            tx_list[tx_hash] = {'value': value, 'timestamp': timestamp, 'balance': balance}

        self.tx_list = tx_list


    def requires_settings(self):
        return True


    def toggle(self):
        out = BasePlugin.toggle(self)
        self.win.update_status()
        self.win.tabs.removeTab(1)
        new_send_tab = self.gui.main_window.create_send_tab()
        self.win.tabs.insertTab(1, new_send_tab, _('Send'))
        return out


    def close(self):
        self.exchanger.stop()

    def history_tab_update(self):
        if self.config.get('history_rates', 'unchecked') == "checked":
            cur_exchange = self.config.get('use_exchange', "Blockchain")
            try:
                tx_list = self.tx_list
            except Exception:
                return

            try:
                mintimestr = datetime.datetime.fromtimestamp(int(min(tx_list.items(), key=lambda x: x[1]['timestamp'])[1]['timestamp'])).strftime('%Y-%m-%d')
            except Exception:
                return
            maxtimestr = datetime.datetime.now().strftime('%Y-%m-%d')

            if cur_exchange == "CoinDesk":
                try:
                    resp_hist = self.exchanger.get_json('api.coindesk.com', "/v1/bpi/historical/close.json?start=" + mintimestr + "&end=" + maxtimestr)
                except Exception:
                    return
            elif cur_exchange == "Winkdex":
                try:
                    resp_hist = self.exchanger.get_json('winkdex.com', "/static/data/0_86400_730.json")['prices']
                except Exception:
                    return
            elif cur_exchange == "BitcoinVenezuela":
                cur_currency = self.config.get('currency', "EUR")
                if cur_currency == "VEF":
                    try:
                        resp_hist = self.exchanger.get_json('api.bitcoinvenezuela.com', "/historical/index.php?coin=BTC")['VEF_BTC']
                    except Exception:
                        return
                elif cur_currency == "ARS":
                    try:
                        resp_hist = self.exchanger.get_json('api.bitcoinvenezuela.com', "/historical/index.php?coin=BTC")['ARS_BTC']
                    except Exception:
                        return
                else:
                    return

            self.gui.main_window.is_edit = True
            self.gui.main_window.history_list.setColumnCount(6)
            self.gui.main_window.history_list.setHeaderLabels( [ '', _('Date'), _('Description') , _('Amount'), _('Balance'), _('Fiat Amount')] )
            root = self.gui.main_window.history_list.invisibleRootItem()
            childcount = root.childCount()
            for i in range(childcount):
                item = root.child(i)
                try:
                    tx_info = tx_list[str(item.data(0, Qt.UserRole).toPyObject())]
                except Exception:
                    newtx = self.wallet.get_tx_history()
                    v = newtx[[x[0] for x in newtx].index(str(item.data(0, Qt.UserRole).toPyObject()))][3]

                    tx_info = {'timestamp':int(time.time()), 'value': v }
                    pass
                tx_time = int(tx_info['timestamp'])
                if cur_exchange == "CoinDesk":
                    tx_time_str = datetime.datetime.fromtimestamp(tx_time).strftime('%Y-%m-%d')
                    try:
                        tx_USD_val = "%.2f %s" % (Decimal(str(tx_info['value'])) / 100000000 * Decimal(resp_hist['bpi'][tx_time_str]), "USD")
                    except KeyError:
                        tx_USD_val = "%.2f %s" % (self.btc_rate * Decimal(str(tx_info['value']))/100000000 , "USD")
                elif cur_exchange == "Winkdex":
                    tx_time_str = int(tx_time) - (int(tx_time) % (60 * 60 * 24))
                    try:
                        tx_rate = resp_hist[[x['x'] for x in resp_hist].index(tx_time_str)]['y']
                        tx_USD_val = "%.2f %s" % (Decimal(tx_info['value']) / 100000000 * Decimal(tx_rate), "USD")
                    except ValueError:
                        tx_USD_val = "%.2f %s" % (self.btc_rate * Decimal(tx_info['value'])/100000000 , "USD")
                elif cur_exchange == "BitcoinVenezuela":
                    tx_time_str = datetime.datetime.fromtimestamp(tx_time).strftime('%Y-%m-%d')
                    try:
                        num = resp_hist[tx_time_str].replace(',','')
                        tx_BTCVEN_val = "%.2f %s" % (Decimal(str(tx_info['value'])) / 100000000 * Decimal(num), cur_currency)
                    except KeyError:
                        tx_BTCVEN_val = _("No data")

                if cur_exchange == "CoinDesk" or cur_exchange == "Winkdex":
                    item.setText(5, tx_USD_val)
                elif cur_exchange == "BitcoinVenezuela":
                    item.setText(5, tx_BTCVEN_val)
                if Decimal(str(tx_info['value'])) < 0:
                    item.setForeground(5, QBrush(QColor("#BC1E1E")))

            for i, width in enumerate(self.gui.main_window.column_widths['history']):
                self.gui.main_window.history_list.setColumnWidth(i, width)
            self.gui.main_window.history_list.setColumnWidth(4, 140)
            self.gui.main_window.history_list.setColumnWidth(5, 120)
            self.gui.main_window.is_edit = False


    def settings_widget(self, window):
        return EnterButton(_('Settings'), self.settings_dialog)

    def settings_dialog(self):
        d = QDialog()
        d.setWindowTitle("Settings")
        layout = QGridLayout(d)
        layout.addWidget(QLabel(_('Exchange rate API: ')), 0, 0)
        layout.addWidget(QLabel(_('Currency: ')), 1, 0)
        layout.addWidget(QLabel(_('History Rates: ')), 2, 0)
        combo = QComboBox()
        combo_ex = QComboBox()
        hist_checkbox = QCheckBox()
        hist_checkbox.setEnabled(False)
        if self.config.get('history_rates', 'unchecked') == 'unchecked':
            hist_checkbox.setChecked(False)
        else:
            hist_checkbox.setChecked(True)
        ok_button = QPushButton(_("OK"))

        def on_change(x):
            try:
                cur_request = str(self.currencies[x])
            except Exception:
                return
            if cur_request != self.config.get('currency', "EUR"):
                self.config.set_key('currency', cur_request, True)
                cur_exchange = self.config.get('use_exchange', "Blockchain")
                if cur_request == "USD" and (cur_exchange == "CoinDesk" or cur_exchange == "Winkdex"):
                    hist_checkbox.setEnabled(True)
                elif cur_request == "VEF" and (cur_exchange == "BitcoinVenezuela"):
                    hist_checkbox.setEnabled(True)
                elif cur_request == "ARS" and (cur_exchange == "BitcoinVenezuela"):
                    hist_checkbox.setEnabled(True)
                else:
                    hist_checkbox.setChecked(False)
                    hist_checkbox.setEnabled(False)
                self.win.update_status()
                try:
                    self.fiat_button
                except:
                    pass
                else:
                    self.fiat_button.setText(cur_request)

        def disable_check():
            hist_checkbox.setChecked(False)
            hist_checkbox.setEnabled(False)

        def on_change_ex(x):
            cur_request = str(self.exchanges[x])
            if cur_request != self.config.get('use_exchange', "Blockchain"):
                self.config.set_key('use_exchange', cur_request, True)
                self.currencies = []
                combo.clear()
                self.exchanger.query_rates.set()
                cur_currency = self.config.get('currency', "EUR")
                if cur_request == "CoinDesk" or cur_request == "Winkdex":
                    if cur_currency == "USD":
                        hist_checkbox.setEnabled(True)
                    else:
                        disable_check()
                elif cur_request == "BitcoinVenezuela":
                    if cur_currency == "VEF" or cur_currency == "ARS":
                        hist_checkbox.setEnabled(True)
                    else:
                        disable_check()
                else:
                    disable_check()
                set_currencies(combo)
                self.win.update_status()

        def on_change_hist(checked):
            if checked:
                self.config.set_key('history_rates', 'checked')
                self.history_tab_update()
            else:
                self.config.set_key('history_rates', 'unchecked')
                self.gui.main_window.history_list.setHeaderLabels( [ '', _('Date'), _('Description') , _('Amount'), _('Balance')] )
                self.gui.main_window.history_list.setColumnCount(5)
                for i,width in enumerate(self.gui.main_window.column_widths['history']):
                    self.gui.main_window.history_list.setColumnWidth(i, width)

        def set_hist_check(hist_checkbox):
            cur_exchange = self.config.get('use_exchange', "Blockchain")
            if cur_exchange == "CoinDesk" or cur_exchange == "Winkdex":
                hist_checkbox.setEnabled(True)
            elif cur_exchange == "BitcoinVenezuela":
                hist_checkbox.setEnabled(True)
            else:
                hist_checkbox.setEnabled(False)

        def set_currencies(combo):
            current_currency = self.config.get('currency', "EUR")
            try:
                combo.clear()
            except Exception:
                return
            combo.addItems(self.currencies)
            try:
                index = self.currencies.index(current_currency)
            except Exception:
                index = 0
            combo.setCurrentIndex(index)

        def set_exchanges(combo_ex):
            try:
                combo_ex.clear()
            except Exception:
                return
            combo_ex.addItems(self.exchanges)
            try:
                index = self.exchanges.index(self.config.get('use_exchange', "Blockchain"))
            except Exception:
                index = 0
            combo_ex.setCurrentIndex(index)

        def ok_clicked():
            d.accept();

        set_exchanges(combo_ex)
        set_currencies(combo)
        set_hist_check(hist_checkbox)
        combo.currentIndexChanged.connect(on_change)
        combo_ex.currentIndexChanged.connect(on_change_ex)
        hist_checkbox.stateChanged.connect(on_change_hist)
        combo.connect(self.win, SIGNAL('refresh_currencies_combo()'), lambda: set_currencies(combo))
        combo_ex.connect(d, SIGNAL('refresh_exchanges_combo()'), lambda: set_exchanges(combo_ex))
        ok_button.clicked.connect(lambda: ok_clicked())
        layout.addWidget(combo,1,1)
        layout.addWidget(combo_ex,0,1)
        layout.addWidget(hist_checkbox,2,1)
        layout.addWidget(ok_button,3,1)

        if d.exec_():
            return True
        else:
            return False

    def fiat_unit(self):
        quote_currency = self.config.get("currency", "???")
        return quote_currency

    def fiat_dialog(self):
        if not self.config.get('use_exchange_rate'):
          self.gui.main_window.show_message(_("To use this feature, first enable the exchange rate plugin."))
          return

        if not self.gui.main_window.network.is_connected():
          self.gui.main_window.show_message(_("To use this feature, you must have a network connection."))
          return

        quote_currency = self.fiat_unit()

        d = QDialog(self.gui.main_window)
        d.setWindowTitle("Fiat")
        vbox = QVBoxLayout(d)
        text = "Amount to Send in " + quote_currency
        vbox.addWidget(QLabel(_(text)+':'))

        grid = QGridLayout()
        fiat_e = AmountEdit(self.fiat_unit)
        grid.addWidget(fiat_e, 1, 0)

        r = {}
        self.get_fiat_price_text(r)
        quote = r.get(0)
        if quote:
          text = "1 BTC~%s"%quote
          grid.addWidget(QLabel(_(text)), 4, 0, 3, 0)
        else:
            self.gui.main_window.show_message(_("Exchange rate not available.  Please check your network connection."))
            return

        vbox.addLayout(grid)
        vbox.addLayout(ok_cancel_buttons(d))

        if not d.exec_():
            return

        fiat = str(fiat_e.text())

        if str(fiat) == "" or str(fiat) == ".":
            fiat = "0"

        quote = quote[:-4]
        btcamount = Decimal(fiat) / Decimal(quote)
        if str(self.gui.main_window.base_unit()) == "mBTC":
            btcamount = btcamount * 1000
        quote = "%.8f"%btcamount
        self.gui.main_window.amount_e.setText( quote )

    def exchange_rate_button(self, grid):
        quote_currency = self.config.get("currency", "EUR")
        self.fiat_button = EnterButton(_(quote_currency), self.fiat_dialog)
        grid.addWidget(self.fiat_button, 4, 3, Qt.AlignHCenter)

########NEW FILE########
__FILENAME__ = labels
from electrum.util import print_error

import httplib, urllib
import socket
import hashlib
import json
from urlparse import urlparse, parse_qs
try:
    import PyQt4
except Exception:
    sys.exit("Error: Could not import PyQt4 on Linux systems, you may try 'sudo apt-get install python-qt4'")

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui
import aes
import base64
from electrum import bmp, pyqrnative
from electrum.plugins import BasePlugin
from electrum.i18n import _

from electrum_gui.qt import HelpButton, EnterButton

class Plugin(BasePlugin):

    def fullname(self):
        return _('Label Sync')

    def description(self):
        return '%s\n\n%s%s%s' % (_("This plugin can sync your labels across multiple Electrum installs by using a remote database to save your data. Labels, transactions and addresses are all sent and stored encrypted on the remote server. This code might increase the load of your wallet with a few microseconds as it will sync labels on each startup."), _("To get started visit"), " http://labelectrum.herokuapp.com/ ", _(" to sign up for an account."))

    def version(self):
        return "0.2.1"

    def encode(self, message):
        encrypted = aes.encryptData(self.encode_password, unicode(message))
        encoded_message = base64.b64encode(encrypted)

        return encoded_message

    def decode(self, message):
        decoded_message = aes.decryptData(self.encode_password, base64.b64decode(unicode(message)) )

        return decoded_message


    def init(self):
        self.target_host = 'labelectrum.herokuapp.com'
        self.window = self.gui.main_window

    def load_wallet(self, wallet):
        self.wallet = wallet
        if self.wallet.get_master_public_key():
            mpk = self.wallet.get_master_public_key()
        else:
            mpk = self.wallet.master_public_keys["m/0'/"][1]
        self.encode_password = hashlib.sha1(mpk).digest().encode('hex')[:32]
        self.wallet_id = hashlib.sha256(mpk).digest().encode('hex')

        addresses = [] 
        for account in self.wallet.accounts.values():
            for address in account.get_addresses(0):
                addresses.append(address)

        self.addresses = addresses

        if self.auth_token():
            # If there is an auth token we can try to actually start syncing
            self.full_pull()

    def auth_token(self):
        return self.config.get("plugin_label_api_key")

    def is_available(self):
        return True

    def requires_settings(self):
        return True

    def set_label(self, item,label, changed):
        if not changed:
            return 
        try:
            bundle = {"label": {"external_id": self.encode(item), "text": self.encode(label)}}
            params = json.dumps(bundle)
            connection = httplib.HTTPConnection(self.target_host)
            connection.request("POST", ("/api/wallets/%s/labels.json?auth_token=%s" % (self.wallet_id, self.auth_token())), params, {'Content-Type': 'application/json'})

            response = connection.getresponse()
            if response.reason == httplib.responses[httplib.NOT_FOUND]:
                return
            response = json.loads(response.read())
        except socket.gaierror as e:
            print_error('Error connecting to service: %s ' %  e)
            return False

    def settings_widget(self, window):
        return EnterButton(_('Settings'), self.settings_dialog)

    def settings_dialog(self):
        def check_for_api_key(api_key):
            if api_key and len(api_key) > 12:
              self.config.set_key("plugin_label_api_key", str(self.auth_token_edit.text()))
              self.upload.setEnabled(True)
              self.download.setEnabled(True)
              self.accept.setEnabled(True)
            else:
              self.upload.setEnabled(False)
              self.download.setEnabled(False)
              self.accept.setEnabled(False)

        d = QDialog()
        layout = QGridLayout(d)
        layout.addWidget(QLabel("API Key: "),0,0)

        self.auth_token_edit = QLineEdit(self.auth_token())
        self.auth_token_edit.textChanged.connect(check_for_api_key)

        layout.addWidget(QLabel("Label sync options: "),2,0)
        layout.addWidget(self.auth_token_edit, 0,1,1,2)

        decrypt_key_text =  QLineEdit(self.encode_password)
        decrypt_key_text.setReadOnly(True)
        layout.addWidget(decrypt_key_text, 1,1)
        layout.addWidget(QLabel("Decryption key: "),1,0)
        layout.addWidget(HelpButton("This key can be used on the LabElectrum website to decrypt your data in case you want to review it online."),1,2)

        self.upload = QPushButton("Force upload")
        self.upload.clicked.connect(self.full_push)
        layout.addWidget(self.upload, 2,1)

        self.download = QPushButton("Force download")
        self.download.clicked.connect(lambda: self.full_pull(True))
        layout.addWidget(self.download, 2,2)

        c = QPushButton(_("Cancel"))
        c.clicked.connect(d.reject)

        self.accept = QPushButton(_("Done"))
        self.accept.clicked.connect(d.accept)

        layout.addWidget(c,3,1)
        layout.addWidget(self.accept,3,2)

        check_for_api_key(self.auth_token())

        if d.exec_():
          return True
        else:
          return False

    def enable(self):
        if not self.auth_token(): # First run, throw plugin settings in your face
            self.init()
            self.load_wallet(self.gui.main_window.wallet)
            if self.settings_dialog():
                self.set_enabled(True)
                return True
            else:
                self.set_enabled(False)
                return False

        self.set_enabled(True)
        return True


    def full_push(self):
        if self.do_full_push():
            QMessageBox.information(None, _("Labels uploaded"), _("Your labels have been uploaded."))

    def full_pull(self, force = False):
        if self.do_full_pull(force) and force:
            QMessageBox.information(None, _("Labels synchronized"), _("Your labels have been synchronized."))
            self.window.update_history_tab()
            self.window.update_completions()
            self.window.update_receive_tab()
            self.window.update_contacts_tab()

    def do_full_push(self):
        try:
            bundle = {"labels": {}}
            for key, value in self.wallet.labels.iteritems():
                encoded = self.encode(key)
                bundle["labels"][encoded] = self.encode(value)

            params = json.dumps(bundle)
            connection = httplib.HTTPConnection(self.target_host)
            connection.request("POST", ("/api/wallets/%s/labels/batch.json?auth_token=%s" % (self.wallet_id, self.auth_token())), params, {'Content-Type': 'application/json'})

            response = connection.getresponse()
            if response.reason == httplib.responses[httplib.NOT_FOUND]:
                return
            try:
                response = json.loads(response.read())
            except ValueError as e:
                return False

            if "error" in response:
                QMessageBox.warning(None, _("Error"),_("Could not sync labels: %s" % response["error"]))
                return False

            return True
        except socket.gaierror as e:
            print_error('Error connecting to service: %s ' %  e)
            return False

    def do_full_pull(self, force = False):
        try:
            connection = httplib.HTTPConnection(self.target_host)
            connection.request("GET", ("/api/wallets/%s/labels.json?auth_token=%s" % (self.wallet_id, self.auth_token())),"", {'Content-Type': 'application/json'})
            response = connection.getresponse()
            if response.reason == httplib.responses[httplib.NOT_FOUND]:
                return
            try:
                response = json.loads(response.read())
            except ValueError as e:
                return False

            if "error" in response:
                QMessageBox.warning(None, _("Error"),_("Could not sync labels: %s" % response["error"]))
                return False

            for label in response:
                 decoded_key = self.decode(label["external_id"]) 
                 decoded_label = self.decode(label["text"]) 
                 if force or not self.wallet.labels.get(decoded_key):
                     self.wallet.labels[decoded_key] = decoded_label 
            return True
        except socket.gaierror as e:
            print_error('Error connecting to service: %s ' %  e)
            return False

########NEW FILE########
__FILENAME__ = pointofsale
import re
import platform
from decimal import Decimal
from urllib import quote

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import PyQt4.QtCore as QtCore
import PyQt4.QtGui as QtGui

from electrum_gui.qt.qrcodewidget import QRCodeWidget

from electrum import bmp, pyqrnative, BasePlugin
from electrum.i18n import _


if platform.system() == 'Windows':
    MONOSPACE_FONT = 'Lucida Console'
elif platform.system() == 'Darwin':
    MONOSPACE_FONT = 'Monaco'
else:
    MONOSPACE_FONT = 'monospace'

column_index = 4

class QR_Window(QWidget):

    def __init__(self, exchanger):
        QWidget.__init__(self)
        self.exchanger = exchanger
        self.setWindowTitle('Electrum - '+_('Invoice'))
        self.setMinimumSize(800, 250)
        self.address = ''
        self.label = ''
        self.amount = 0
        self.setFocusPolicy(QtCore.Qt.NoFocus)

        main_box = QHBoxLayout()
        
        self.qrw = QRCodeWidget()
        main_box.addWidget(self.qrw, 1)

        vbox = QVBoxLayout()
        main_box.addLayout(vbox)

        self.address_label = QLabel("")
        #self.address_label.setFont(QFont(MONOSPACE_FONT))
        vbox.addWidget(self.address_label)

        self.label_label = QLabel("")
        vbox.addWidget(self.label_label)

        self.amount_label = QLabel("")
        vbox.addWidget(self.amount_label)

        vbox.addStretch(1)
        self.setLayout(main_box)


    def set_content(self, addr, label, amount, currency):
        self.address = addr
        address_text = "<span style='font-size: 18pt'>%s</span>" % addr if addr else ""
        self.address_label.setText(address_text)

        if currency == 'BTC': currency = None
        amount_text = ''
        if amount:
            if currency:
                try:
                    self.amount = Decimal(amount) / self.exchanger.exchange(1, currency) if currency else amount
                except Exception:
                    self.amount = None
            else:
                self.amount = Decimal(amount)
            self.amount = self.amount.quantize(Decimal('1.0000'))

            if currency:
                amount_text += "<span style='font-size: 18pt'>%s %s</span><br/>" % (amount, currency)
            amount_text += "<span style='font-size: 21pt'>%s</span> <span style='font-size: 16pt'>BTC</span> " % str(self.amount) 
        else:
            self.amount = None
            
        self.amount_label.setText(amount_text)

        self.label = label
        label_text = "<span style='font-size: 21pt'>%s</span>" % label if label else ""
        self.label_label.setText(label_text)

        msg = 'bitcoin:'+self.address
        if self.amount is not None:
            msg += '?amount=%s'%(str( self.amount))
            if self.label is not None:
                encoded_label = quote(self.label)
                msg += '&label=%s'%(encoded_label)
        elif self.label is not None:
            encoded_label = quote(self.label)
            msg += '?label=%s'%(encoded_label)
            
        self.qrw.set_addr( msg )




class Plugin(BasePlugin):

    def fullname(self):
        return 'Point of Sale'

    def description(self):
        return _('Show QR code window and amounts requested for each address. Add menu item to request amount.')+_(' Note: This requires the exchange rate plugin to be installed.')

    def init(self):
        self.window = self.gui.main_window
        self.wallet = self.window.wallet

        self.qr_window = None
        self.merchant_name = self.config.get('merchant_name', 'Invoice')

        self.window.expert_mode = True
        self.window.receive_list.setColumnCount(5)
        self.window.receive_list.setHeaderLabels([ _('Address'), _('Label'), _('Balance'), _('Tx'), _('Request')])
        self.requested_amounts = {}
        self.toggle_QR_window(True)

    def enable(self):
        if not self.config.get('use_exchange_rate'):
            self.gui.main_window.show_message("Please enable exchange rates first!")
            return False

        return BasePlugin.enable(self)


    def load_wallet(self, wallet):
        self.wallet = wallet
        self.requested_amounts = self.wallet.storage.get('requested_amounts',{}) 

    def close(self):
        self.window.receive_list.setHeaderLabels([ _('Address'), _('Label'), _('Balance'), _('Tx')])
        self.window.receive_list.setColumnCount(4)
        for i,width in enumerate(self.window.column_widths['receive']):
            self.window.receive_list.setColumnWidth(i, width)
        self.toggle_QR_window(False)
    

    def close_main_window(self):
        if self.qr_window: 
            self.qr_window.close()
            self.qr_window = None

    
    def timer_actions(self):
        if self.qr_window:
            self.qr_window.qrw.update_qr()


    def toggle_QR_window(self, show):
        if show and not self.qr_window:
            self.qr_window = QR_Window(self.gui.exchanger)
            self.qr_window.setVisible(True)
            self.qr_window_geometry = self.qr_window.geometry()
            item = self.window.receive_list.currentItem()
            if item:
                address = str(item.text(1))
                label = self.wallet.labels.get(address)
                amount, currency = self.requested_amounts.get(address, (None, None))
                self.qr_window.set_content( address, label, amount, currency )

        elif show and self.qr_window and not self.qr_window.isVisible():
            self.qr_window.setVisible(True)
            self.qr_window.setGeometry(self.qr_window_geometry)

        elif not show and self.qr_window and self.qr_window.isVisible():
            self.qr_window_geometry = self.qr_window.geometry()
            self.qr_window.setVisible(False)


    
    def update_receive_item(self, address, item):
        try:
            amount, currency = self.requested_amounts.get(address, (None, None))
        except Exception:
            print "cannot get requested amount", address, self.requested_amounts.get(address)
            amount, currency = None, None
            self.requested_amounts.pop(address)

        amount_str = amount + (' ' + currency if currency else '') if amount is not None  else ''
        item.setData(column_index,0,amount_str)


    
    def current_item_changed(self, a):
        if not self.wallet: 
            return
        if a is not None and self.qr_window and self.qr_window.isVisible():
            address = str(a.text(0))
            label = self.wallet.labels.get(address)
            try:
                amount, currency = self.requested_amounts.get(address, (None, None))
            except Exception:
                amount, currency = None, None
            self.qr_window.set_content( address, label, amount, currency )


    
    def item_changed(self, item, column):
        if column != column_index:
            return
        address = str( item.text(0) )
        text = str( item.text(column) )
        try:
            seq = self.wallet.get_address_index(address)
            index = seq[1][1]
        except Exception:
            print "cannot get index"
            return

        text = text.strip().upper()
        #print text
        m = re.match('^(\d*(|\.\d*))\s*(|BTC|EUR|USD|GBP|CNY|JPY|RUB|BRL)$', text)
        if m and m.group(1) and m.group(1)!='.':
            amount = m.group(1)
            currency = m.group(3)
            if not currency:
                currency = 'BTC'
            else:
                currency = currency.upper()
                    
            self.requested_amounts[address] = (amount, currency)
            self.wallet.storage.put('requested_amounts', self.requested_amounts, True)

            label = self.wallet.labels.get(address)
            if label is None:
                label = self.merchant_name + ' - %04d'%(index+1)
                self.wallet.labels[address] = label

            if self.qr_window:
                self.qr_window.set_content( address, label, amount, currency )

        else:
            item.setText(column,'')
            if address in self.requested_amounts:
                self.requested_amounts.pop(address)
            
        self.window.update_receive_item(self.window.receive_list.currentItem())




    def edit_amount(self):
        l = self.window.receive_list
        item = l.currentItem()
        item.setFlags(Qt.ItemIsEditable|Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
        l.editItem( item, column_index )
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)

    
    def receive_menu(self, menu, addr):
        menu.addAction(_("Request amount"), self.edit_amount)
        menu.addAction(_("Show Invoice"), lambda: self.toggle_QR_window(True))



########NEW FILE########
__FILENAME__ = qrscanner
from electrum.util import print_error
from urlparse import urlparse, parse_qs
from PyQt4.QtGui import QPushButton, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox
from PyQt4.QtCore import Qt

from electrum.i18n import _
import re
import os
from electrum import Transaction
from electrum.bitcoin import MIN_RELAY_TX_FEE, is_valid
from electrum_gui.qt.qrcodewidget import QRCodeWidget
from electrum import bmp
from electrum_gui.qt import HelpButton, EnterButton
import json

try:
    import zbar
except ImportError:
    zbar = None

from electrum import BasePlugin
class Plugin(BasePlugin):

    def fullname(self): return 'QR scans'

    def description(self): return "QR Scans.\nInstall the zbar package (http://zbar.sourceforge.net/download.html) to enable this plugin"

    def __init__(self, gui, name):
        BasePlugin.__init__(self, gui, name)
        self._is_available = self._init()

    def _init(self):
        if not zbar:
            return False
        try:
            proc = zbar.Processor()
            proc.init(video_device=self.video_device())
        except zbar.SystemError:
            # Cannot open video device
            pass
            #return False

        return True

    def load_wallet(self, wallet):
        b = QPushButton(_("Scan QR code"))
        b.clicked.connect(self.fill_from_qr)
        self.send_tab_grid.addWidget(b, 1, 5)
        b2 = QPushButton(_("Scan TxQR"))
        b2.clicked.connect(self.read_raw_qr)
        
        if not wallet.seed:
            b3 = QPushButton(_("Show unsigned TxQR"))
            b3.clicked.connect(self.show_raw_qr)
            self.send_tab_grid.addWidget(b3, 7, 1)
            self.send_tab_grid.addWidget(b2, 7, 2)
        else:
            self.send_tab_grid.addWidget(b2, 7, 1)

    def is_available(self):
        return self._is_available

    def create_send_tab(self, grid):
        self.send_tab_grid = grid

    def scan_qr(self):
        proc = zbar.Processor()
        try:
            proc.init(video_device=self.video_device())
        except zbar.SystemError, e:
            QMessageBox.warning(self.gui.main_window, _('Error'), _(e), _('OK'))
            return

        proc.visible = True

        while True:
            try:
                proc.process_one()
            except Exception:
                # User closed the preview window
                return {}

            for r in proc.results:
                if str(r.type) != 'QRCODE':
                    continue
                return r.data
        
    def show_raw_qr(self):
        r = unicode( self.gui.main_window.payto_e.text() )
        r = r.strip()

        # label or alias, with address in brackets
        m = re.match('(.*?)\s*\<([1-9A-HJ-NP-Za-km-z]{26,})\>', r)
        to_address = m.group(2) if m else r

        if not is_valid(to_address):
            QMessageBox.warning(self.gui.main_window, _('Error'), _('Invalid Bitcoin Address') + ':\n' + to_address, _('OK'))
            return

        try:
            amount = self.gui.main_window.read_amount(unicode( self.gui.main_window.amount_e.text()))
        except Exception:
            QMessageBox.warning(self.gui.main_window, _('Error'), _('Invalid Amount'), _('OK'))
            return
        try:
            fee = self.gui.main_window.read_amount(unicode( self.gui.main_window.fee_e.text()))
        except Exception:
            QMessageBox.warning(self.gui.main_window, _('Error'), _('Invalid Fee'), _('OK'))
            return

        try:
            tx = self.gui.main_window.wallet.mktx( [(to_address, amount)], None, fee)
        except Exception as e:
            self.gui.main_window.show_message(str(e))
            return

        if tx.requires_fee(self.gui.main_window.wallet.verifier) and fee < MIN_RELAY_TX_FEE:
            QMessageBox.warning(self.gui.main_window, _('Error'), _("This transaction requires a higher fee, or it will not be propagated by the network."), _('OK'))
            return

        try:
            out = {
            "hex" : tx.hash(),
            "complete" : "false"
            }
    
            input_info = []

        except Exception as e:
            self.gui.main_window.show_message(str(e))

        try:
            json_text = json.dumps(tx.as_dict()).replace(' ', '')
            self.show_tx_qrcode(json_text, 'Unsigned Transaction')
        except Exception as e:
            self.gui.main_window.show_message(str(e))

    def show_tx_qrcode(self, data, title):
        if not data: return
        d = QDialog(self.gui.main_window)
        d.setModal(1)
        d.setWindowTitle(title)
        d.setMinimumSize(250, 525)
        vbox = QVBoxLayout()
        qrw = QRCodeWidget(data)
        vbox.addWidget(qrw, 0)
        hbox = QHBoxLayout()
        hbox.addStretch(1)

        def print_qr(self):
            filename = "qrcode.bmp"
            electrum_gui.bmp.save_qrcode(qrw.qr, filename)
            QMessageBox.information(None, _('Message'), _("QR code saved to file") + " " + filename, _('OK'))

        b = QPushButton(_("Save"))
        hbox.addWidget(b)
        b.clicked.connect(print_qr)

        b = QPushButton(_("Close"))
        hbox.addWidget(b)
        b.clicked.connect(d.accept)
        b.setDefault(True)

        vbox.addLayout(hbox, 1)
        d.setLayout(vbox)
        d.exec_()

    def read_raw_qr(self):
        qrcode = self.scan_qr()
        if qrcode:
            tx = self.gui.main_window.tx_from_text(qrcode)
            if tx:
                self.create_transaction_details_window(tx)

    def create_transaction_details_window(self, tx):            
        dialog = QDialog(self.gui.main_window)
        dialog.setMinimumWidth(500)
        dialog.setWindowTitle(_('Process Offline transaction'))
        dialog.setModal(1)

        l = QGridLayout()
        dialog.setLayout(l)

        l.addWidget(QLabel(_("Transaction status:")), 3,0)
        l.addWidget(QLabel(_("Actions")), 4,0)

        if tx.is_complete == False:
            l.addWidget(QLabel(_("Unsigned")), 3,1)
            if self.gui.main_window.wallet.seed :
                b = QPushButton("Sign transaction")
                b.clicked.connect(lambda: self.sign_raw_transaction(tx, tx.inputs, dialog))
                l.addWidget(b, 4, 1)
            else:
                l.addWidget(QLabel(_("Wallet is de-seeded, can't sign.")), 4,1)
        else:
            l.addWidget(QLabel(_("Signed")), 3,1)
            b = QPushButton("Broadcast transaction")
            def broadcast(tx):
                result, result_message = self.gui.main_window.wallet.sendtx( tx )
                if result:
                    self.gui.main_window.show_message(_("Transaction successfully sent:")+' %s' % (result_message))
                    if dialog:
                        dialog.done(0)
                else:
                    self.gui.main_window.show_message(_("There was a problem sending your transaction:") + '\n %s' % (result_message))
            b.clicked.connect(lambda: broadcast( tx ))
            l.addWidget(b,4,1)
    
        closeButton = QPushButton(_("Close"))
        closeButton.clicked.connect(lambda: dialog.done(0))
        l.addWidget(closeButton, 4,2)

        dialog.exec_()

    def do_protect(self, func, args):
        if self.gui.main_window.wallet.use_encryption:
            password = self.gui.main_window.password_dialog()
            if not password:
                return
        else:
            password = None
            
        if args != (False,):
            args = (self,) + args + (password,)
        else:
            args = (self,password)
        apply( func, args)

    def protected(func):
        return lambda s, *args: s.do_protect(func, args)

    @protected
    def sign_raw_transaction(self, tx, input_info, dialog ="", password = ""):
        try:
            self.gui.main_window.wallet.signrawtransaction(tx, input_info, [], password)
            txtext = json.dumps(tx.as_dict()).replace(' ', '')
            self.show_tx_qrcode(txtext, 'Signed Transaction')
        except Exception as e:
            self.gui.main_window.show_message(str(e))


    def fill_from_qr(self):
        qrcode = parse_uri(self.scan_qr())
        if not qrcode:
            return

        if 'address' in qrcode:
            self.gui.main_window.payto_e.setText(qrcode['address'])
        if 'amount' in qrcode:
            self.gui.main_window.amount_e.setText(str(qrcode['amount']))
        if 'label' in qrcode:
            self.gui.main_window.message_e.setText(qrcode['label'])
        if 'message' in qrcode:
            self.gui.main_window.message_e.setText("%s (%s)" % (self.gui.main_window.message_e.text(), qrcode['message']))
                
    def video_device(self):
        device = self.config.get("video_device", "default")
        if device == 'default':
            device = ''
        return device

    def requires_settings(self):
        return True

    def settings_widget(self, window):
        return EnterButton(_('Settings'), self.settings_dialog)
    
    def _find_system_cameras(self):
        device_root = "/sys/class/video4linux"
        devices = {} # Name -> device
        if os.path.exists(device_root):
            for device in os.listdir(device_root):
                name = open(os.path.join(device_root, device, 'name')).read()
                devices[name] = os.path.join("/dev",device)
        return devices

    def settings_dialog(self):
        system_cameras = self._find_system_cameras()

        d = QDialog()
        layout = QGridLayout(d)
        layout.addWidget(QLabel("Choose a video device:"),0,0)

        # Create a combo box with the available video devices:
        combo = QComboBox()

        # on change trigger for video device selection, makes the
        # manual device selection only appear when needed:
        def on_change(x):
            combo_text = str(combo.itemText(x))
            combo_data = combo.itemData(x)
            if combo_text == "Manually specify a device":
                custom_device_label.setVisible(True)
                self.video_device_edit.setVisible(True)
                if self.config.get("video_device") == "default":
                    self.video_device_edit.setText("")
                else:
                    self.video_device_edit.setText(self.config.get("video_device"))
            else:
                custom_device_label.setVisible(False)
                self.video_device_edit.setVisible(False)
                self.video_device_edit.setText(combo_data.toString())

        # on save trigger for the video device selection window,
        # stores the chosen video device on close.
        def on_save():
            device = str(self.video_device_edit.text())
            self.config.set_key("video_device", device)
            d.accept()

        custom_device_label = QLabel("Video device: ")
        custom_device_label.setVisible(False)
        layout.addWidget(custom_device_label,1,0)
        self.video_device_edit = QLineEdit()
        self.video_device_edit.setVisible(False)
        layout.addWidget(self.video_device_edit, 1,1,2,2)
        combo.currentIndexChanged.connect(on_change)

        combo.addItem("Default","default")
        for camera, device in system_cameras.items():
            combo.addItem(camera, device)
        combo.addItem("Manually specify a device",self.config.get("video_device"))

        # Populate the previously chosen device:
        index = combo.findData(self.config.get("video_device"))
        combo.setCurrentIndex(index)

        layout.addWidget(combo,0,1)

        self.accept = QPushButton(_("Done"))
        self.accept.clicked.connect(on_save)
        layout.addWidget(self.accept,4,2)

        if d.exec_():
          return True
        else:
          return False



def parse_uri(uri):
    if ':' not in uri:
        # It's just an address (not BIP21)
        return {'address': uri}

    if '//' not in uri:
        # Workaround for urlparse, it don't handle bitcoin: URI properly
        uri = uri.replace(':', '://')
        
    uri = urlparse(uri)
    result = {'address': uri.netloc} 
    
    if uri.query.startswith('?'):
        params = parse_qs(uri.query[1:])
    else:
        params = parse_qs(uri.query)    

    for k,v in params.items():
        if k in ('amount', 'label', 'message'):
            result[k] = v[0]
        
    return result    





if __name__ == '__main__':
    # Run some tests
    
    assert(parse_uri('1Marek48fwU7mugmSe186do2QpUkBnpzSN') ==
           {'address': '1Marek48fwU7mugmSe186do2QpUkBnpzSN'})

    assert(parse_uri('bitcoin://1Marek48fwU7mugmSe186do2QpUkBnpzSN') ==
           {'address': '1Marek48fwU7mugmSe186do2QpUkBnpzSN'})
    
    assert(parse_uri('bitcoin:1Marek48fwU7mugmSe186do2QpUkBnpzSN') ==
           {'address': '1Marek48fwU7mugmSe186do2QpUkBnpzSN'})
    
    assert(parse_uri('bitcoin:1Marek48fwU7mugmSe186do2QpUkBnpzSN?amount=10') ==
           {'amount': '10', 'address': '1Marek48fwU7mugmSe186do2QpUkBnpzSN'})
    
    assert(parse_uri('bitcoin:1Marek48fwU7mugmSe186do2QpUkBnpzSN?amount=10&label=slush&message=Small%20tip%20to%20slush') ==
           {'amount': '10', 'label': 'slush', 'message': 'Small tip to slush', 'address': '1Marek48fwU7mugmSe186do2QpUkBnpzSN'})
    
    

########NEW FILE########
__FILENAME__ = virtualkeyboard
from PyQt4.QtGui import *
from electrum import BasePlugin
from electrum.i18n import _

class Plugin(BasePlugin):


    def fullname(self):
        return 'Virtual Keyboard'

    def description(self):
        return '%s\n%s' % (_("Add an optional virtual keyboard to the password dialog."), _("Warning: do not use this if it makes you pick a weaker password."))

    def init(self):
        self.vkb = None
        self.vkb_index = 0


    def password_dialog(self, pw, grid, pos):
        vkb_button = QPushButton(_("+"))
        vkb_button.setFixedWidth(20)
        vkb_button.clicked.connect(lambda: self.toggle_vkb(grid, pw))
        grid.addWidget(vkb_button, pos, 2)
        self.kb_pos = 2


    def toggle_vkb(self, grid, pw):
        if self.vkb: grid.removeItem(self.vkb)
        self.vkb = self.virtual_keyboard(self.vkb_index, pw)
        grid.addLayout(self.vkb, self.kb_pos, 0, 1, 3)
        self.vkb_index += 1


    def virtual_keyboard(self, i, pw):
        import random
        i = i%3
        if i == 0:
            chars = 'abcdefghijklmnopqrstuvwxyz '
        elif i == 1:
            chars = 'ABCDEFGHIJKLMNOPQRTSUVWXYZ '
        elif i == 2:
            chars = '1234567890!?.,;:/%&()[]{}+-'
            
        n = len(chars)
        s = []
        for i in xrange(n):
            while True:
                k = random.randint(0,n-1)
                if k not in s:
                    s.append(k)
                    break

        def add_target(t):
            return lambda: pw.setText(str( pw.text() ) + t)
            
        vbox = QVBoxLayout()
        grid = QGridLayout()
        grid.setSpacing(2)
        for i in range(n):
            l_button = QPushButton(chars[s[i]])
            l_button.setFixedWidth(25)
            l_button.setFixedHeight(25)
            l_button.clicked.connect(add_target(chars[s[i]]) )
            grid.addWidget(l_button, i/6, i%6)

        vbox.addLayout(grid)

        return vbox


########NEW FILE########
__FILENAME__ = merchant
#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


import time, thread, sys, socket, os
import urllib2,json
import Queue
import sqlite3
from electrum import Wallet, WalletStorage, SimpleConfig, Network, set_verbosity
set_verbosity(False)

import ConfigParser
config = ConfigParser.ConfigParser()
config.read("merchant.conf")

my_password = config.get('main','password')
my_host = config.get('main','host')
my_port = config.getint('main','port')

database = config.get('sqlite3','database')

received_url = config.get('callback','received')
expired_url = config.get('callback','expired')
cb_password = config.get('callback','password')

wallet_path = config.get('electrum','wallet_path')
master_public_key = config.get('electrum','mpk')
master_chain = config.get('electrum','chain')


pending_requests = {}

num = 0

def check_create_table(conn):
    global num
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='electrum_payments';")
    data = c.fetchall()
    if not data: 
        c.execute("""CREATE TABLE electrum_payments (address VARCHAR(40), amount FLOAT, confirmations INT(8), received_at TIMESTAMP, expires_at TIMESTAMP, paid INT(1), processed INT(1));""")
        conn.commit()

    c.execute("SELECT Count(address) FROM 'electrum_payments'")
    num = c.fetchone()[0]
    print "num rows", num



# this process detects when addresses have received payments
def on_wallet_update():
    for addr, v in pending_requests.items():
        h = wallet.history.get(addr, [])
        requested_amount = v.get('requested')
        requested_confs  = v.get('confirmations')
        value = 0
        for tx_hash, tx_height in h:
            tx = wallet.transactions.get(tx_hash)
            if not tx: continue
            if wallet.verifier.get_confirmations(tx_hash) < requested_confs: continue
            for o in tx.outputs:
                o_address, o_value = o
                if o_address == addr:
                    value += o_value

        s = (value)/1.e8
        print "balance for %s:"%addr, s, requested_amount
        if s>= requested_amount: 
            print "payment accepted", addr
            out_queue.put( ('payment', addr))


stopping = False

def do_stop(password):
    global stopping
    if password != my_password:
        return "wrong password"
    stopping = True
    return "ok"

def process_request(amount, confirmations, expires_in, password):
    global num

    if password != my_password:
        return "wrong password"

    try:
        amount = float(amount)
        confirmations = int(confirmations)
        expires_in = float(expires_in)
    except Exception:
        return "incorrect parameters"

    account = wallet.accounts["m/0'/0"]
    addr = account.get_address(0, num)
    num += 1

    out_queue.put( ('request', (addr, amount, confirmations, expires_in) ))
    return addr



def server_thread(conn):
    from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
    server = SimpleJSONRPCServer(( my_host, my_port))
    server.register_function(process_request, 'request')
    server.register_function(do_stop, 'stop')
    server.serve_forever()
    




def send_command(cmd, params):
    import jsonrpclib
    server = jsonrpclib.Server('http://%s:%d'%(my_host, my_port))
    try:
        if cmd == 'request':
            out = server.request(*params)
        elif cmd == 'stop':
            out = server.stop(*params)
        else:
            out = "unknown command"
    except socket.error:
        print "Server not running"
        return 1

    print out
    return 0


if __name__ == '__main__':

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        params = sys.argv[2:] + [my_password]
        ret = send_command(cmd, params)
        sys.exit(ret)

    conn = sqlite3.connect(database);
    # create table if needed
    check_create_table(conn)

    # init network
    config = SimpleConfig({'wallet_path':wallet_path})
    network = Network(config)
    network.start(wait=True)

    # create watching_only wallet
    storage = WalletStorage(config)
    wallet = Wallet(storage)
    if not storage.file_exists:
        wallet.seed = ''
        wallet.create_watching_only_wallet(master_public_key,master_chain)

    wallet.synchronize = lambda: None # prevent address creation by the wallet
    wallet.start_threads(network)
    network.register_callback('updated', on_wallet_update)
    
    out_queue = Queue.Queue()
    thread.start_new_thread(server_thread, (conn,))

    while not stopping:
        cur = conn.cursor()

        # read pending requests from table
        cur.execute("SELECT address, amount, confirmations FROM electrum_payments WHERE paid IS NULL;")
        data = cur.fetchall()

        # add pending requests to the wallet
        for item in data: 
            addr, amount, confirmations = item
            if addr in pending_requests: 
                continue
            else:
                with wallet.lock:
                    print "subscribing to %s"%addr
                    pending_requests[addr] = {'requested':float(amount), 'confirmations':int(confirmations)}
                    wallet.synchronizer.subscribe_to_addresses([addr])
                    wallet.up_to_date = False

        try:
            cmd, params = out_queue.get(True, 10)
        except Queue.Empty:
            cmd = ''

        if cmd == 'payment':
            addr = params
            # set paid=1 for received payments
            print "received payment from", addr
            cur.execute("update electrum_payments set paid=1 where address='%s'"%addr)

        elif cmd == 'request':
            # add a new request to the table.
            addr, amount, confs, minutes = params
            sql = "INSERT INTO electrum_payments (address, amount, confirmations, received_at, expires_at, paid, processed)"\
                + " VALUES ('%s', %f, %d, datetime('now'), datetime('now', '+%d Minutes'), NULL, NULL);"%(addr, amount, confs, minutes)
            print sql
            cur.execute(sql)

        # set paid=0 for expired requests 
        cur.execute("""UPDATE electrum_payments set paid=0 WHERE expires_at < CURRENT_TIMESTAMP and paid is NULL;""")

        # do callback for addresses that received payment or expired
        cur.execute("""SELECT oid, address, paid from electrum_payments WHERE paid is not NULL and processed is NULL;""")
        data = cur.fetchall()
        for item in data:
            oid, address, paid = item
            paid = bool(paid)
            headers = {'content-type':'application/json'}
            data_json = { 'address':address, 'password':cb_password, 'paid':paid }
            data_json = json.dumps(data_json)
            url = received_url if paid else expired_url
            req = urllib2.Request(url, data_json, headers)
            try:
                response_stream = urllib2.urlopen(req)
                print 'Got Response for %s' % address
                cur.execute("UPDATE electrum_payments SET processed=1 WHERE oid=%d;"%(oid))
            except urllib2.HTTPError:
                print "cannot do callback", data_json
            except ValueError, e:
                print e
                print "cannot do callback", data_json
        
        conn.commit()

    conn.close()
    print "Done"


########NEW FILE########
