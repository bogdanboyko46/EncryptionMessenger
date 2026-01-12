# Important to note, for vast majority of code "messages" arent actually referring to actual typed messages
# It refers to the bytes sent between clients & relay_server, these messages for most part contain 
# socket & a map of instructions

import socket
import threading
import queue
import tkinter as tk
import client_encryption
import encryption_helper
from tkinter import ttk
from protocol import send_message, recv_message
from tkinter import font
from client_obj import Client

state = {

    "RUNNING": True,
    "IN_ROOM": False,
    "USER": None, 

<<<<<<< HEAD
    "ROOM": {
        "ROOM_NAME": None,
        "ADMIN_FLAG": False,

        "JOIN_REJECT": False,
        "CREATE_REJECT": False,

        "OWNER": False,

        "ROTATE_FLAG": False,
=======
    "ROOM_ACTION_ERROR": {
        "JOIN_REJECT": False,
        "CREATE_REJECT": False,
>>>>>>> origin/main
    },
}

inbox = queue.Queue()   # messages from server (dicts)
outbox = queue.Queue()  # messages to be sent to relay server (dicts)
local = queue.Queue() # information that is needed within individual functions

# ALL THREAD FUNCTIONS 
def recieving_thread(s):
    while state["RUNNING"]:
            
        msg = recv_message(s)
        # in the case of a null msg sent to socket
        
        if msg is None:
            print("MESSAGE IS NONE!")
            print("Disconnected from server.")
            state["RUNNING"] = False
            s.close()
            break
        
        print(f"RECIEVING {msg}")
        inbox.put(msg)

def _wait_outbound():
    while state["RUNNING"]:
        try:
            contents = outbox.get(timeout=.25)
            return contents
        except queue.Empty:
            pass

def outbox_thread(s):
    while state["RUNNING"]:

        # waits for contents patiently
        contents = _wait_outbound()

        # invalid contents if condition passes; either null or contains nothing
        if contents is None or not contents:
            continue
<<<<<<< HEAD
        
        # print(f"SENDING {contents}")
=======

        print(f"SENDING {contents}")
>>>>>>> origin/main
        # else, we send the contents to the relay server
        send_message(s, contents)

def process_inbox(s):
    # .get() will freeze the gui, we need a try except

    while state["RUNNING"]:
        try:
            # inbound logic - checks to see if inbox queue is empty
            msg = inbox.get(timeout=.25)

            # gets the type of the message
            mType = msg.get("TYPE")

            print(f"PROCESSING MSG {msg}")
            match mType:
                
                # message type that indicates a logic error
                case "ERROR":
                    
                    error_message = msg.get("MESSAGE")

                    print(f"[Error]: {error_message}")
                    state["RUNNING"] = False
                    s.close()

                # message type that disconnected a user from a room, user now needs room reassignment
                case "REJOIN":
                    
                    # drain anything from current inbox
                    try:
                        inbox.get(timeout=0.25)
                    except queue.Empty:
                        pass

                    # unassign user flags
                    state["IN_ROOM"] = False
                    state["ROOM"]["ROOM_NAME"] = None
                    
                    # PRINT SERVER MESSAGE TO USER - PROVIDE CHAT_ROOMS
                    local.put(msg)

                    print("REJOINING!!!!!")
                    # All rejoin handling is done within the chat room scene class

                # inbound messages coming from other users in the assigned room / from broadcast
                case "SEND" | "BROADCAST" | "REGISTRATION" | "RELOAD" | "ADMIN" | "ROTATE" | "OWNER":
                    
                    # process it in the local queue to print messages from users / print broadcast messages
                    # when registered, make info like chat_rooms and server message accessible by local queue
                    local.put(msg)
                
                case "JOIN_REJECT" | "CREATE_REJECT":
                    # set error flag to true
                    
<<<<<<< HEAD
                    state["ROOM"][mType] = True
                    local.put(msg)

                case "CONNECTED":
                    
                    room = msg.get("CHAT_ROOM")

                    state["IN_ROOM"] = True
                    state["ROOM"]["ROOM_NAME"] = room.get_chat_room_name()
                    
                case "ROOM_KEY_WRAP":
                    state["ROOM"]["ROTATE_FLAG"] = True
                    
=======
                    state["ROOM_ACTION_ERROR"][mType] = True
>>>>>>> origin/main
                    local.put(msg)

        except queue.Empty:
            pass
        
def poll_registration(expected_type):
    stash = []

    while True:
        try:
            msg = local.get_nowait()
        except queue.Empty:
            # retry
            continue
            
        msg_type = msg.get("TYPE")

        print(f"type is {msg_type}")
        if msg_type == expected_type:
            for other in stash:
                local.put(other)
            return msg

        # set aside the msg we cannot accept
        stash.append(msg)
        
class ChatGUI(tk.Tk):
<<<<<<< HEAD

    def __init__(self):
        super().__init__()

        self._theme()
         # generate necessary client crypto obj
        self.client_crypto = client_encryption.ClientCrypto()

=======
    def __init__(self):
        super().__init__()
        
>>>>>>> origin/main
        self.title("Chat Room Messenger")
        self.geometry("975x550")

        # Container that holds all scenes
        container = ttk.Frame(self, padding=0)
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        # Create and register scenes
        self.frames = {}
        for SceneClass in (UsernameScene, ConnectedScene, CreateRoomScene, JoinRoomScene, RoomScene):
            frame = SceneClass(parent=container, app=self)
            self.frames[SceneClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Start at username scene
        self.show("UsernameScene")

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        print("Shutting down client...")
 
        state["RUNNING"] = False

        try:
            outbox.put({"TYPE": "DISCONNECT"})
        except Exception:
            pass
            
        self.destroy()

    def show(self, scene_name: str):
        """Raise (show) a scene by name."""
        frame = self.frames[scene_name]
        frame.on_show()
        frame.tkraise()
    
    def rejoin(self):
        frame = self.frames["ConnectedScene"]

        # reload chat rooms
        outbox.put({"TYPE": "RELOAD"})

        frame.welcome_label.config(text=f"Welcome to the chat room server, {state['USER']}!")
        returned_message = poll_registration("RELOAD") or {}

        chat_rooms = returned_message.get("CHAT_ROOMS") or {}

        for w in frame.content_frame.winfo_children():
            w.destroy()

        frame.chat_rooms = chat_rooms
        frame.room_logic()
        frame.tkraise()

    def _theme(self):
        style = ttk.Style(self)

        # Use a theme that is configurable (default themes are often ugly + limited)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass  # fallback to whatever exists

        # --- Palette (modern, not grayscale) ---
        BG        = "#0B1220"  # window background (deep navy)
        SURFACE   = "#111A2E"  # cards/panels
        SURFACE_2 = "#16223A"  # inputs / slightly raised
        TEXT      = "#E6EAF2"  # primary text
        MUTED     = "#A8B0C3"  # secondary text
        ACCENT    = "#4F7DFF"  # primary action
        ACCENT_2  = "#2FE4AB"  # secondary highlight
        DANGER    = "#FF5C7A"  # errors

        self.configure(bg=BG)

        style.configure(".", font=("Segoe UI", 11))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure("Title.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 12))
        style.configure("Danger.TLabel", background=BG, foreground=DANGER)

        # Buttons
        style.configure(
            "TButton",
            padding=(14, 10),
            background=SURFACE_2,
            foreground=TEXT,
            borderwidth=0,
            focusthickness=0
        )
        style.map(
            "TButton",
            background=[("active", "#1B2A4A"), ("pressed", "#0E1630"), ("disabled", "#0E1630")],
            foreground=[("disabled", "#66708A")]
        )

        # Primary button (use by setting style="Primary.TButton")
        style.configure(
            "Primary.TButton",
            padding=(16, 11),
            background=ACCENT,
            foreground="white",
            borderwidth=0
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#3E6FFF"), ("pressed", "#2E58DA"), ("disabled", "#1D2C5A")],
            foreground=[("disabled", "#B9C3DD")]
        )

     # reload button
        style.configure(
            "Icon.TButton",
            padding=(10, 8),
            background=SURFACE,
            foreground=TEXT
        )
        style.map(
            "Icon.TButton",
            background=[("active", "#1B2A4A"), ("pressed", "#0E1630")]
        )

        # Entries
        style.configure(
            "TEntry",
            padding=(10, 8),
            fieldbackground=SURFACE_2,
            foreground=TEXT,
            borderwidth=0,
            relief="flat",
            insertcolor=TEXT
        )

        style.map(
            "TEntry",
            fieldbackground=[("focus", SURFACE_2), ("active", SURFACE_2)],
            foreground=[("focus", TEXT), ("active", TEXT)]
        )

        # Scrollbar
        style.configure("Vertical.TScrollbar", background=SURFACE, troughcolor=BG, bordercolor=BG, arrowcolor=MUTED)

        self.option_add("*Text.background", SURFACE)
        self.option_add("*Text.foreground", TEXT)
        self.option_add("*Text.insertBackground", TEXT)
        self.option_add("*Text.selectBackground", ACCENT)
        self.option_add("*Text.selectForeground", "white")

        self.option_add("*Listbox.background", SURFACE)
        self.option_add("*Listbox.foreground", TEXT)
        self.option_add("*Listbox.selectBackground", ACCENT)
        self.option_add("*Listbox.selectForeground", "white")
        self.option_add("*Listbox.highlightThickness", 0)
        self.option_add("*Listbox.borderWidth", 0)

        # Make ttk backgrounds consistent
        style.configure("TLabelframe", background=BG, foreground=TEXT)
        style.configure("TLabelframe.Label", background=BG, foreground=MUTED)

        style.configure("Red.TLabel", background=BG, foreground=DANGER)

        style.configure("Card.TLabel", background=SURFACE, foreground=TEXT)
        style.configure("CardMuted.TLabel", background=SURFACE, foreground=MUTED)
        style.configure("CardTitle.TLabel", background=SURFACE, foreground=TEXT, font=("Segoe UI", 20, "bold"))
        style.configure("CardSubtitle.TLabel", background=SURFACE, foreground=MUTED, font=("Segoe UI", 12))

class UsernameScene(ttk.Frame):
    def __init__(self, parent, app: ChatGUI):
        super().__init__(parent)
        self.app = app

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        outer = ttk.Frame(self)
        outer.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        card = ttk.Frame(outer, style="Card.TFrame")
        card.grid(row=0, column=0, sticky="n", pady=(40, 0))
        card.columnconfigure(0, weight=1)

        # Give the card internal padding by placing an inner frame
        inner = ttk.Frame(card, style="Card.TFrame")
        inner.grid(row=0, column=0, sticky="nsew", padx=26, pady=22)
        inner.columnconfigure(0, weight=1)
        
        title = ttk.Label(inner, text="Chat Room Messenger", style="CardTitle.TLabel")
        title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        subtitle = ttk.Label(
            inner,
            text="Enter a display name to connect securely.",
            style="CardSubtitle.TLabel"
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(0, 18))

        # Field label
        field_label = ttk.Label(inner, text="Display name", style="CardMuted.TLabel")
        field_label.grid(row=2, column=0, sticky="w", pady=(0, 6))

        # Hint line
        hint = ttk.Label(inner, text="Tip: Press Enter to continue.", style="CardMuted.TLabel")
        hint.grid(row=4, column=0, sticky="w", pady=(14, 0))

        # Input row: entry + button
        row = ttk.Frame(inner, style="Card.TFrame")
        row.grid(row=3, column=0, sticky="ew")
        row.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(row, width=26, font=("Segoe UI", 13))
        self.entry.grid(row=0, column=0, sticky="ew", ipady=6)
        self.entry.bind("<Return>", self.on_submit)

        enter_btn = ttk.Button(row, text="Continue", style="Primary.TButton", command=self.on_submit)
        enter_btn.grid(row=0, column=1, padx=(12, 0), ipadx=10, ipady=2)


    def on_show(self):
        self.entry.delete(0, "end")
        self.entry.focus_set()

    def on_submit(self, event=None):
        name = self.entry.get().strip()
        if not name:
            return  # do nothing on empty input

        state["USER"] = name
        self.app.show("ConnectedScene")


class ConnectedScene(ttk.Frame):
    def __init__(self, parent, app: ChatGUI):
        super().__init__(parent)
        self.app = app

        # Layout: top welcome, middle content
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        self.welcome_label = ttk.Label(self, text="", font=("Arial", 20))
        self.welcome_label.grid(row=0, column=0, pady=(40, 18), padx=20, sticky="n")

        # This content_frame will be rebuilt depending on chat_rooms empty/non-empty
        self.content_frame = ttk.Frame(self)
        self.content_frame.grid(row=1, column=0, sticky="n")
        self.content_frame.columnconfigure(0, weight=1)

        reload_font = font.Font(family="Arial", size=20, weight="bold")

        reload_btn = ttk.Button(
        self,
        text="⟳",
        command=self.app.rejoin
            )
            
        reload_btn.configure(style="Icon.TButton")

        style = ttk.Style()
        style.configure("Reload.TButton", font=reload_font)

        reload_btn.place(relx=1.0, rely=0.0, x=-12, y=12, anchor="ne")

    def on_show(self):
<<<<<<< HEAD

        outbox.put({
            "TYPE": "PUBKEYS",
            "NAME": state["USER"],
            "SIGN_PUB": encryption_helper.sign_pub_bytes(self.app.client_crypto.sign_pub),
            "DH_PUB": encryption_helper.dh_pub_bytes(self.app.client_crypto.dh_pub),
            })
=======
        # create client obj
        outbox.put({"NAME": state["USER"]})
>>>>>>> origin/main
        
        self.welcome_label.config(text="Connecting...")
        for w in self.content_frame.winfo_children():
            w.destroy()
        self.after(400, self._prepare_scene)

    def _prepare_scene(self):

        returned_message = poll_registration("REGISTRATION") or {}

        self.chat_rooms = returned_message.get("CHAT_ROOMS") or {}
        welcome_message = returned_message.get("MESSAGE") or "Connected."

        self.welcome_label.config(text=welcome_message)

        for w in self.content_frame.winfo_children():
            w.destroy()

        self.room_logic()


    def room_logic(self):
        # room logic
        if self.chat_rooms:
            prompt = ttk.Label(
                self.content_frame,
                text="Would you like to create or join a room?",
                font=("Arial", 14),
            )


            prompt.grid(row=0, column=0, pady=(10, 18))

            # Two equal-size buttons adjacent
            btn_row = ttk.Frame(self.content_frame)
            btn_row.grid(row=1, column=0)

            # Make both columns expand equally
            btn_row.columnconfigure(0, weight=1, uniform="btns")
            btn_row.columnconfigure(1, weight=1, uniform="btns")

            create_btn = ttk.Button(btn_row, text="Create", command=self.go_create)
            join_btn = ttk.Button(btn_row, text="Join", command=self.go_join)

            create_btn.grid(row=0, column=0, padx=(0, 10), ipadx=30, ipady=8, sticky="ew")
            join_btn.grid(row=0, column=1, padx=(10, 0), ipadx=30, ipady=8, sticky="ew")

        else:
            prompt = ttk.Label(
                self.content_frame,
                text="There are no rooms on the server, please create one!",
                font=("Arial", 14),
            )
            prompt.grid(row=0, column=0, pady=(10, 18))

            # Single centered Create button
            create_btn = ttk.Button(self.content_frame, text="Create", command=self.go_create)
            create_btn.grid(row=1, column=0, ipadx=40, ipady=10)


    def go_create(self):
        # clear any past error msgs if any
        self.app.frames["CreateRoomScene"].error_label.config(text="")

        self.app.show("CreateRoomScene")

    def go_join(self):
        # clear any past error msgs if any
        self.app.frames["JoinRoomScene"].error_label.config(text="")

        self.app.show("JoinRoomScene")

class CreateRoomScene(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        
        self.app = app

        self.columnconfigure(0, weight=1)

        title = ttk.Label(self, text="Create a Room", font=("Arial", 20))
        title.grid(row=0, column=0, pady=(40, 20))

        form = ttk.Frame(self)
        form.grid(row=1, column=0)

        ttk.Label(form, text="Room name:").grid(row=0, column=0, sticky="e", padx=(0, 10))
        self.room_entry = ttk.Entry(form, width=25)
        self.room_entry.grid(row=0, column=1)

        ttk.Label(form, text="Password (optional):").grid(row=1, column=0, sticky="e", padx=(0, 10))
        self.pass_entry = ttk.Entry(form, width=25, show="*")
        self.pass_entry.grid(row=1, column=1)

        buttons = ttk.Frame(self)
        buttons.grid(row=2, column=0, pady=20)

        create_btn = ttk.Button(buttons, text="Create", command=self.create_room)
        create_btn.grid(row=0, column=0, padx=10)

        cancel_btn = ttk.Button(buttons, text="Cancel", command=self.go_back)
        cancel_btn.grid(row=0, column=1, padx=10)

        self.error_label = ttk.Label(self, text="", font=("Arial", 12))
        self.error_label.grid(row=3, column=0, pady=(6, 6))

        style = ttk.Style()
        style.configure("Red.TLabel", foreground="red")
        self.error_label.configure(style="Red.TLabel")

    def on_show(self):
        """
        Called every time this scene becomes visible.
        Reset inputs and prepare UI state.
        """
        # Clear previous input
        self.room_entry.delete(0, "end")
        self.pass_entry.delete(0, "end")
        
        # Focus the room name field
        self.room_entry.focus_set()

    def create_room(self):
        
        # clear error msg when user tries to create a room again
        self.error_label.config(text="")
        room_name = self.room_entry.get()
        password = self.pass_entry.get()

        if not room_name:
            msg = "You must enter a room name!"
            self.error_label.config(text=msg)
            self.on_show()
            return

        if not password:
            password = None

        # SEND MESSAGE TO SERVER
        outbox.put({
            "TYPE": "CREATE_ROOM",
            "ROOM_NAME": room_name,
            "PASSWORD": password
        })
        
        # wait 5ms after sending message out, wait until IN_ROOM state is True
        self.after(5, self.wait_for_room_connect)
        
    def wait_for_room_connect(self):
        if state["IN_ROOM"]:
            # if the in room state becomes true, then we can confirm that the room creation was successful
<<<<<<< HEAD
            state["ROOM"]["ADMIN_FLAG"] = True
            state["ROOM"]["OWNER"] = True
            
            self.app.show("RoomScene")

        elif state["ROOM"]["CREATE_REJECT"]:
=======
            self.app.frame.get("RoomScene")._is_admin = True
            self.app.show("RoomScene")

        elif state["ROOM_ACTION_ERROR"]["CREATE_REJECT"]:
>>>>>>> origin/main
            
            contents = poll_registration("CREATE_REJECT") or {}
            msg = contents.get("MESSAGE") or "Error"
            self.error_label.config(text=msg)

            # set error flag back to false
<<<<<<< HEAD
            state["ROOM"]["CREATE_REJECT"] = False
=======
            state["ROOM_ACTION_ERROR"]["CREATE_REJECT"] = False
>>>>>>> origin/main
            self.on_show()

        else:
            self.after(5, self.wait_for_room_connect)
            
    def go_back(self):
        self.error_label.config(text="")
        self.app.rejoin()


class JoinRoomScene(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.columnconfigure(0, weight=1)

        title = ttk.Label(self, text="Join a Room", font=("Arial", 20))
        title.grid(row=0, column=0, pady=(40, 10))

        subtitle = ttk.Label(self, text="Select a room and enter password if required.", font=("Arial", 12))
        subtitle.grid(row=1, column=0, pady=(0, 20))

        content = ttk.Frame(self)
        content.grid(row=2, column=0)

        # Room list (left)
        left = ttk.Frame(content)
        left.grid(row=0, column=0, padx=(0, 30), sticky="n")

        ttk.Label(left, text="Available rooms:").grid(row=0, column=0, sticky="w")

        self.rooms_list = tk.Listbox(left, height=10, width=28, exportselection=False)
        self.rooms_list.grid(row=1, column=0, pady=(8, 0))
        self.rooms_list.configure(font=("Segoe UI", 11), height=12)
        self.rooms_list.bind("<<ListboxSelect>>", self.on_room_select)
        self.rooms_list.bind("<Double-Button-1>", lambda e: self.on_join())
        
        # Details + password (right)
        right = ttk.Frame(content)
        right.grid(row=0, column=1, sticky="n")

        self.details_label = ttk.Label(right, text="Select a room to see details.", font=("Arial", 11))
        self.details_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        ttk.Label(right, text="Password (if needed):").grid(row=1, column=0, sticky="w")
        self.pass_entry = ttk.Entry(right, width=28, font=("Arial", 12), show="*")
        self.pass_entry.grid(row=2, column=0, pady=(8, 0))
        self.pass_entry.bind("<Return>", lambda e: self.on_join())

        self.error_label = ttk.Label(self, text="", foreground="red")
        self.error_label.grid(row=3, column=0, pady=(10, 0), sticky="w")

        btn_row = ttk.Frame(self)
        btn_row.grid(row=3, column=0, pady=20)

        self.join_btn = ttk.Button(btn_row, text="Join", command=self.on_join)
        self.join_btn.grid(row=0, column=0, padx=10, ipadx=20, ipady=6)

        back_btn = ttk.Button(btn_row, text="Back", command=lambda: self.app.rejoin())
        back_btn.grid(row=0, column=1, padx=10, ipadx=20, ipady=6)

        # Internal selection state
        self.selected_room = None
        self.selected_requires_pw = False

    def on_show(self):
        # clear any past error messages
        self.error_label.config(text="")

        # Rebuild room list from app.chat_rooms
        self.pass_entry.delete(0, "end")
        self.details_label.config(text="Select a room to see details.")
        self.selected_room = None
        self.selected_requires_pw = False

        self.rooms_list.delete(0, "end")

        # perform reload operation
        outbox.put({"TYPE": "RELOAD"})
        chat_room_info = poll_registration("RELOAD") or {}
        self.rooms = chat_room_info.get("CHAT_ROOMS") or {}

        for room_name in self.rooms.keys():
            self.rooms_list.insert("end", room_name)

        if not self.rooms:
            self.error_label.config(text="No rooms available to join.")
            self.join_btn.config(state="disabled")

            # no rooms available, rejoin!
            self.app.rejoin()
        else:
            self.join_btn.config(state="normal")

    def on_room_select(self, event=None):
        print("543")
        idxs = self.rooms_list.curselection()
        if not idxs:
            return

        room_name = self.rooms_list.get(idxs[0])
        self.selected_room = room_name

        info = self.rooms.get(room_name)
        # in case of failure to retrieve chat room corresponding chat room obj
        if info is None:
            return 
        
        owner = info.get_owner()
        users = info.list_users()
        has_pw = info.has_password
        self.selected_requires_pw = has_pw

        self.details_label.config(
            text=f"Room: {room_name}\nOwner: {owner}\nUsers: {len(users)}\nPassword: {'Yes' if has_pw else 'No'}"
        )

        # If no password, clear it and focus join button; otherwise focus password entry
        print("565")
        self.pass_entry.delete(0, "end")
        if has_pw:
            self.pass_entry.focus_set()
        else:
            self.join_btn.focus_set()

    def on_join(self):
        print("ON JOIN!")
        if not self.selected_room:
            self.error_label.config(text="Select a room first.")
            return

        password = self.pass_entry.get().strip() or None

        if self.selected_requires_pw and not password:
            self.error_label.config(text="This room requires a password.")
            return

        outbox.put({
            "TYPE": "JOIN_ROOM",
            "ROOM_NAME": self.selected_room,
            "PASSWORD": password
        })

        # wait 5s after sending message out, wait until IN_ROOM state is True
        self.after(5, self.wait_for_room_connect)
        
    def wait_for_room_connect(self):

        if state["IN_ROOM"]:
            print("IN ROOM!")
            # if the in room state becomes true, then we can confirm that the room creation was successful
<<<<<<< HEAD
            print("IN ROOM!!!!")
            self.app.show("RoomScene") # runs when room key wrap type is reached - block something

        elif state["ROOM"]["JOIN_REJECT"]:
=======
            self.app.show("RoomScene")
>>>>>>> origin/main
            
        elif state["ROOM_ACTION_ERROR"]["JOIN_REJECT"]:
            
            print("ROOM ERROR JOIN REJECT!")

            contents = poll_registration("JOIN_REJECT") or {}
            msg = contents.get("MESSAGE") or "Error"
            self.error_label.config(text=msg)

            # set error flag back to false
<<<<<<< HEAD
            state["ROOM"]["JOIN_REJECT"] = False
=======
            state["ROOM_ACTION_ERROR"]["JOIN_REJECT"] = False
>>>>>>> origin/main
            self.on_room_select()

        else:
            print("LOOP")
            self.after(5, self.wait_for_room_connect)
        
class RoomScene(ttk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.chat_rooms = {} 
        self.secure_ready = False

        # Polling
        self._polling = False
        self._poll_job = None
        self._is_admin = False

        # Root grid: header row removed in favor of left header inside body
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)  # body
        self.rowconfigure(1, weight=0)  # input

        self.body = ttk.Frame(self)
        self.body.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 10))

        self.body.columnconfigure(0, weight=3) # left
        self.body.columnconfigure(1, weight=2) # right
        self.body.rowconfigure(0, weight=0) # left header row
        self.body.rowconfigure(1, weight=1) # main row

        left_header = ttk.Frame(self.body)
        left_header.grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.room_label = ttk.Label(left_header, text="", font=("Arial", 14))
        self.user_label = ttk.Label(left_header, text="", font=("Arial", 14))
        self.room_label.grid(row=0, column=0, sticky="w")
        self.user_label.grid(row=0, column=1, sticky="w", padx=(25, 0))

        self.chat_container = ttk.Frame(self.body)
        self.chat_container.grid(row=1, column=0, sticky="nsew")
        self.chat_container.columnconfigure(0, weight=1)
        self.chat_container.rowconfigure(0, weight=1)

        self.chat_text = tk.Text(self.chat_container, wrap="word", state="disabled")
        self.chat_text.grid(row=0, column=0, sticky="nsew")

        self.chat_text.configure(
        bg="#111A2E",
        fg="#E6EAF2",
        insertbackground="#E6EAF2",
        relief="flat",
        padx=12,
        pady=10,
        font=("Segoe UI", 11)
        )

        scroll = ttk.Scrollbar(self.chat_container, orient="vertical", command=self.chat_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.chat_text.configure(yscrollcommand=scroll.set)
        
        self.admin_container = ttk.Frame(self.body)
        self.admin_container.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(20, 0))
        self.admin_container.columnconfigure(0, weight=1)
        self.admin_container.rowconfigure(0, weight=1)

        self.admin_stack = ttk.Frame(self.admin_container)
        self.admin_stack.grid(row=0, column=0, sticky="nsew")
        self.admin_stack.columnconfigure(0, weight=1)
        self.admin_stack.rowconfigure(0, weight=1)

        self._build_admin_main_view()
        self._build_admin_tools_view()

        # Start on main view
        self._show_admin_main_view()

        # initially set to false
        self.room_state = client_encryption.RoomCryptoState(False)

        input_frame = ttk.Frame(self)
        input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 20))
        input_frame.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(input_frame)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", self.on_send)

        self.send_btn = ttk.Button(input_frame, text="Send", command=self.on_send)
        self.send_btn.grid(row=0, column=1, padx=(10, 0))

        # Start in normal mode until on_show() runs
        self._set_admin_mode()


    def _build_admin_main_view(self):
        self.admin_main = ttk.Frame(self.admin_stack)
        self.admin_main.grid(row=0, column=0, sticky="nsew")
        self.admin_main.columnconfigure(0, weight=1)

        # Spacer weights to center the title and space buttons evenly
        self.admin_main.rowconfigure(0, weight=3)  # top spacer
        self.admin_main.rowconfigure(1, weight=0)  # title
        self.admin_main.rowconfigure(2, weight=1)  # spacer
        self.admin_main.rowconfigure(3, weight=0)  # button 1
        self.admin_main.rowconfigure(4, weight=1)  # spacer (equal-ish)
        self.admin_main.rowconfigure(5, weight=0)  # button 2
        self.admin_main.rowconfigure(6, weight=3)  # bottom spacer

        title = ttk.Label(self.admin_main, text="Admin Panel", font=("Arial", 18))
        title.grid(row=1, column=0, pady=(0, 20))

        self.admin_tools_btn = ttk.Button(
            self.admin_main, text="Admin Tools", command=self._show_admin_tools_view
        )
        self.admin_tools_btn.grid(row=3, column=0, ipadx=30, ipady=12)

        self.leave_btn = ttk.Button(self.admin_main, text="Leave", command=self._leave_room)
        self.leave_btn.grid(row=5, column=0, ipadx=30, ipady=12)

    def _build_admin_tools_view(self):
        """Right pane tools: embedded list + actions + back."""
        self.admin_tools = ttk.Frame(self.admin_stack)
        self.admin_tools.grid(row=0, column=0, sticky="nsew")
        self.admin_tools.columnconfigure(0, weight=1)
        self.admin_tools.rowconfigure(2, weight=1)

        hdr = ttk.Label(self.admin_tools, text="Please select a user(s):", font=("Arial", 16))
        hdr.grid(row=0, column=0, sticky="w", pady=(10, 10))

        self._admin_list = tk.Listbox(self.admin_tools, selectmode="extended")
        self._admin_list.grid(row=2, column=0, sticky="nsew")
        self._admin_list.configure(font=("Segoe UI", 11), height=12)

        footer = ttk.Frame(self.admin_tools)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 10))
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)
        footer.columnconfigure(2, weight=1)
        footer.columnconfigure(3, weight=1)

        ttk.Button(footer, text="Kick", command=lambda: self._admin_action("remove")).grid(row=0, column=0, padx=5, sticky="ew")
        ttk.Button(footer, text="Ban", command=lambda: self._admin_action("ban")).grid(row=0, column=1, padx=5, sticky="ew")

        ttk.Button(footer, text="Make Admin", command=lambda: self._admin_action("makeadmin")).grid(row=0, column=2, padx=5, sticky="ew")
        ttk.Button(footer, text="Back", command=self._show_admin_main_view).grid(row=0, column=3, padx=5, sticky="ew")

    def _show_admin_main_view(self):
        self.admin_main.tkraise()

    def _show_admin_tools_view(self):
        # Ask server to refresh chat_rooms
        outbox.put({"TYPE": "RELOAD"})

        self._refresh_admin_list_from_chat_rooms()
        self.admin_tools.tkraise()

    def _set_admin_mode(self):
        """
        If admin: show right panel; chat stays in left column only.
        If not admin: hide right panel and let chat span across both columns.
        """
        if self._is_admin:
            self.admin_container.grid()  # show
            self.chat_container.grid_configure(columnspan=1)
        else:
            self.admin_container.grid_remove()  # hide
            self.chat_container.grid_configure(columnspan=2)


    def on_show(self):
        room = state["ROOM"]["ROOM_NAME"] or ""
        user = state["USER"] or ""
        self.room_label.config(text=f"Room: {room}")
        self.user_label.config(text=f"User: {user}")

<<<<<<< HEAD
        self.room_state = client_encryption.RoomCryptoState(state["ROOM"]["OWNER"])

        if self.room_state.is_owner:

            self.secure_ready = True
            self.room_state.ins_as_creator()
        else:
            self.secure_ready = False
            self._append_chat("[YOU]: Establishing room key...")

        # disable send until secure
        self._set_input_enabled(self.secure_ready)
        self._set_admin_mode(state["ROOM"]["ADMIN_FLAG"])
=======
        self._set_input_enabled(bool(state.get("IN_ROOM")))
        self._set_admin_mode()
>>>>>>> origin/main

        if not self._polling:
            self._polling = True
            self.entry.focus_set()
            self._schedule_poll()

<<<<<<< HEAD
=======
    def on_hide(self):
        self._polling = False
        if self._poll_job is not None:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

>>>>>>> origin/main
    def _schedule_poll(self):
        self._poll_job = self.after(10, self._poll_inbox)

    def _set_input_enabled(self, enabled: bool):
        self.entry.configure(state=("normal" if enabled else "disabled"))
        self.send_btn.configure(state=("normal" if enabled else "disabled"))

    def _append_chat(self, line: str):
        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", line + "\n")
        self.chat_text.see("end")
        self.chat_text.configure(state="disabled")


    def on_send(self, event=None):

        if not state.get("IN_ROOM") or self.room_state.epoch is None:
            return

        msg = self.entry.get().strip()
        if not msg:
            return

        self.entry.delete(0, "end")

        # discard msgs until secure
        if not self.secure_ready:
            return

        # Now safe to send
        self._append_chat(f"You: {msg}")
        msgtype = "COMMAND" if msg[0] == "!" else "SEND"

        if state["ROOM"]["ADMIN_FLAG"] and msg == "!leave":
            self._leave_room()
            return
        
        # do not encrypt the message if its a command
        if msgtype == "COMMAND":
            outbox.put({"TYPE": "COMMAND", "MESSAGE": msg})
            return
        
        # encrypt message
        secure_send = encryption_helper.encrypt_room_msg(
            self.app.client_crypto.sign_priv,
            self.room_state.room_key,
            self.room_state.epoch,
            self.room_state.send_ctr,
            msg,
            state["USER"],
            msgtype,
        )

        self.room_state.send_ctr += 1
        outbox.put(secure_send)

    def _refresh_admin_list_from_chat_rooms(self):
        room_name = state["ROOM"]["ROOM_NAME"]
        if not room_name:
            return

        chat_room = self.chat_rooms.get(room_name)
        if not chat_room:
            return

        users = chat_room.members
        admins = chat_room.admins
        me = state.get("USER")

        self._admin_list.delete(0, "end")

        for u in users:
            if u == me or u in admins:
                continue
            
            # no actions can be performed on an admin
            self._admin_list.insert("end", u)

    def _get_selected_users(self):
        idxs = self._admin_list.curselection()
        return [self._admin_list.get(i) for i in idxs]

    def _admin_action(self, action_type: str):
        users = self._get_selected_users()
        if not users:
            self._append_chat("[ADMIN] No user selected.")
            return

        # You are using command messages; keep that pattern:
        for user in users:
            outbox.put({"TYPE": "COMMAND", "MESSAGE": f"!{action_type} {user}"})

        self._append_chat(f"[ADMIN] Sent {action_type} for: {', '.join(users)}")

    def _leave_room(self):
        
        # do not encrypt leave message
        outbox.put({"TYPE": "COMMAND", "MESSAGE": "!leave"})
<<<<<<< HEAD
        state["ROOM"]["ADMIN_FLAG"] = False
        state["ROOM"]["OWNER"] = False
=======
        self._is_admin = False
>>>>>>> origin/main
        self._set_input_enabled(False)
        self._set_admin_mode()
        # return to connected scene

    def handle_decrypt(self, msg):
        if msg["EPOCH"] != self.room_state.epoch:
            print(f"SENDER EPOCH: {msg["EPOCH"]} - YOUR EPOCH: {self.room_state.epoch}")
            self._schedule_poll()
            return
        
        decrypted_msg = encryption_helper.decrypt_room_message(
                self.room_state.room_key,
                msg,
                self.room_state.recv_ctr,
            )
        
        self._append_chat(f"{msg["FROM"]}: {decrypted_msg}")
        
    def _poll_inbox(self):
        if not self._polling or not state.get("RUNNING"):
            return

        try:
            msg = local.get_nowait()
        except queue.Empty:
            self._schedule_poll()
            return

        mtype = msg.get("TYPE")

        # check for room key flag
        if state["ROOM"]["ROTATE_FLAG"]:
             
            self.secure_ready = False

            if mtype not in ("ROOM_KEY_WRAP", "SEND"):
                # DISCARD IF SEND MESSAGE, -> OUTDATED
                local.put(msg)
            
            elif mtype == "ROOM_KEY_WRAP":

                # Process ROOM_KEY_WRAP
                result = encryption_helper.receiver_handle_key_wrap(
                    msg,
                    self.app.client_crypto.dh_priv
                    )
                self.room_state.ins_as_joiner()

                self.room_state.set_room_key(result["ROOM_KEY"])
                self.room_state.epoch = result["EPOCH"]
                self.room_state.send_ctr = 0
                self.room_state.recv_ctr.clear()

                self.secure_ready = True

                self._set_input_enabled(True)

                state["ROOM"]["ROTATE_FLAG"] = False
                self._append_chat("[PYOU]: Established new room key!")

            self._schedule_poll()
            return

        if mtype == "SEND": # receiving type SEND message
            # encrypted
            self.handle_decrypt(msg)

        elif mtype == "BROADCAST":
            # not encrypted
            self._append_chat(f"[BROADCAST] {msg.get("MESSAGE")}")

        elif mtype == "REJOIN":
            # not encrypted
            text = msg.get("MESSAGE", "")
            self._append_chat(f"[BROADCAST] {text}")
            self._set_input_enabled(False)
            self._polling = False
<<<<<<< HEAD
            state["ROOM"]["ADMIN_FLAG"] = False
=======
            self._is_admin = False
>>>>>>> origin/main
            self.app.rejoin()
            return

        elif mtype == "ADMIN":
<<<<<<< HEAD
            # not encrypted
            state["ROOM"]["ADMIN_FLAG"] = True
            self._set_admin_mode(True)
=======
            # promote current user to admin
            self._is_admin = True
            self._set_admin_mode()
>>>>>>> origin/main

        elif mtype == "RELOAD":
            # not encrypted
            self.chat_rooms = msg.get("CHAT_ROOMS") or self.chat_rooms
            self.chat_room = self.chat_rooms.get(state["ROOM"]["ROOM_NAME"])
            self._refresh_admin_list_from_chat_rooms()

        elif mtype == "OWNER":
            # not encrypted
            self.room_state.is_owner = True
            self.room_state.rotate_key()
            state["ROOM"]["OWNER"] = True

        elif self.room_state.is_owner:
            
            # JOIN was replaced with ROTATE - will be called once someone joins, leaves, or rotates owner
            if mtype == "ROTATE":
                
                self.room_state.epoch = self.room_state.epoch + 1 if self.room_state.epoch else 0
                self.room_state.send_ctr = 0
                self.room_state.recv_ctr.clear()

                new_room_key, wraps = encryption_helper.rotate_room_key(
                    state["USER"],
                    self.app.client_crypto.sign_priv,
                    msg.get("PUBKEY_DIR"),
                    msg.get("CHAT_ROOM"),
                    self.room_state.epoch,
                )
            
                self.room_state.set_room_key(new_room_key)
 
                # send wrapped room key to everyone else
                for wrap in wraps:
                    outbox.put(wrap)

                if msg["JOIN"]:
                    # send broadcast join message to relay server
                    outbox.put({"TYPE": "BROADCAST", "MESSAGE": f"Welcome to the chat room, {msg["USER"]}"})

        self._schedule_poll()

def main():
    # Create a TCP/IP socket, connect to the VPS IP address
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("72.62.81.113", 5000))
     
    rec_thread = threading.Thread(target = recieving_thread, args=(s,))
    outbx_thread = threading.Thread(target = outbox_thread, args=(s,))
    process_inbox_thread = threading.Thread(target = process_inbox, args=(s,))

    rec_thread.start()
    outbx_thread.start()
    process_inbox_thread.start()
    
    app = ChatGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
