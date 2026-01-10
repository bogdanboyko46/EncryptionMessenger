# Important to note, for vast majority of code "messages" arent actually referring to actual typed messages
# It refers to the bytes sent between clients & relay_server, these messages for most part contain 
# socket & a map of instructions

import socket
import threading
import queue
import tkinter as tk
import client_encryption
from tkinter import ttk
from protocol import send_message, recv_message
from tkinter import font


state = {
    "RUNNING": True,
    "IN_ROOM": False,
    "USER": None, 

    "ROOM": {
        "ROOM_NAME": None,
        "ADMIN_FLAG": False,

        "JOIN_REJECT": False,
        "CREATE_REJECT": False,

        "OWNER": False
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
        
        print(f"SENDING {contents}")
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

            if not state["ROOM"]:
                break

            match mType:
                
                case "CONNECTED":

                    # we are connected!
                    state["IN_ROOM"] = True

                    state["ROOM"]["ROOM_NAME"] = msg.get("ROOM_NAME")

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

                    # All rejoin handling is done within the chat room scene class

                # inbound messages coming from other users in the assigned room / from broadcast
                case "RECEIVE" | "BROADCAST" | "REGISTRATION" | "RELOAD" | "ADMIN":
                    
                    # process it in the local queue to print messages from users / print broadcast messages
                    # when registered, make info like chat_rooms and server message accessible by local queue
                    local.put(msg)
                
                case "JOIN_REJECT" | "CREATE_REJECT":
                    # set error flag to true
                    
                    state["ROOM"][mType] = True
                    local.put(msg)

        except queue.Empty:
            pass
        

def poll_registration(expected_type):
    stash = []

    while True:
        try:
            msg = local.get(timeout=.25)
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
    """
    Scene-based Tkinter app:
      - UsernameScene
      - ConnectedScene (branches based on chat_rooms)
      - CreateRoomScene (placeholder)
      - JoinRoomScene (placeholder)
      - RoomScene
    """

    def __init__(self):
        super().__init__()

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


class UsernameScene(ttk.Frame):
    def __init__(self, parent, app: ChatGUI):
        super().__init__(parent)
        self.app = app

        # Center row
        wrap = ttk.Frame(self)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        prompt = ttk.Label(wrap, text="Hello! Please enter your name:", font=("Arial", 20))
        prompt.grid(row=0, column=0, padx=(0, 12), sticky="e")

        self.entry = ttk.Entry(wrap, width=22, font=("Arial", 16))
        self.entry.grid(row=0, column=1, sticky="w")

        # Enter submits
        self.entry.bind("<Return>", self.on_submit)

        hint = ttk.Label(self, text="Press Enter to continue.", font=("Arial", 11))
        hint.place(relx=0.5, rely=0.5, anchor="n", y=40)

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
            
        reload_btn.configure(style="Reload.TButton")

        style = ttk.Style()
        style.configure("Reload.TButton", font=reload_font)

        reload_btn.place(relx=1.0, rely=0.0, x=-12, y=12, anchor="ne")

    def on_show(self):
        outbox.put({"NAME": state["USER"]})
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
            state["ROOM"]["ADMIN_FLAG"] = True
            state["ROOM"]["OWNER"] = True

            self.app.show("RoomScene")

        elif state["ROOM"]["CREATE_REJECT"]:
            
            contents = poll_registration("CREATE_REJECT") or {}
            msg = contents.get("MESSAGE") or "Error"
            self.error_label.config(text=msg)

            # set error flag back to false
            state["ROOM"]["CREATE_REJECT"] = False
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
        self.pass_entry.delete(0, "end")
        if has_pw:
            self.pass_entry.focus_set()
        else:
            self.join_btn.focus_set()

    def on_join(self):
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
            # if the in room state becomes true, then we can confirm that the room creation was successful
            self.app.show("RoomScene")

        elif state["ROOM"]["JOIN_REJECT"]:
            
            contents = poll_registration("JOIN_REJECT") or {}
            msg = contents.get("MESSAGE") or "Error"
            self.error_label.config(text=msg)

            # set error flag back to false
            state["ROOM"]["JOIN_REJECT"] = False
            self.on_room_select()

        else:
            self.after(5, self.wait_for_room_connect)
        
class RoomScene(ttk.Frame):
    """
    Admin mode UI requirements implemented:
      - Chat/messages ONLY in left half
      - Room + User labels adjacent, left-aligned above chat box
      - Right half contains "Admin Panel" centered
      - "Admin Tools" and "Leave" buttons evenly spaced under the title
      - Admin tools is NOT a new window; it is embedded in the right half
    """

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.chat_rooms = {} 

        # Polling
        self._polling = False
        self._poll_job = None

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
        self._set_admin_mode(False)


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

        btn_row = ttk.Frame(self.admin_tools)
        btn_row.grid(row=3, column=0, sticky="e", pady=(10, 10))

        ttk.Button(btn_row, text="Kick", command=lambda: self._admin_action("remove")).grid(row=0, column=0, padx=5)
        ttk.Button(btn_row, text="Ban", command=lambda: self._admin_action("ban")).grid(row=0, column=1, padx=5)
        ttk.Button(btn_row, text="Make Admin", command=lambda: self._admin_action("makeadmin")).grid(row=0, column=2, padx=5)

        ttk.Button(self.admin_tools, text="Back", command=self._show_admin_main_view).grid(
            row=4, column=0, sticky="w", pady=(0, 10)
        )

    def _show_admin_main_view(self):
        self.admin_main.tkraise()

    def _show_admin_tools_view(self):
        # Ask server to refresh chat_rooms
        outbox.put({"TYPE": "RELOAD"})

        self._refresh_admin_list_from_chat_rooms()
        self.admin_tools.tkraise()

    def _set_admin_mode(self, is_admin):
        """
        If admin: show right panel; chat stays in left column only.
        If not admin: hide right panel and let chat span across both columns.
        """
        if is_admin:
            self.admin_container.grid()  # show
            self.chat_container.grid_configure(columnspan=1)
        else:
            self.admin_container.grid_remove()  # hide
            self.chat_container.grid_configure(columnspan=2)


    def on_show(self):
        """Call this when the app shows this frame."""

        room = state["ROOM"]["ROOM_NAME"] or ""
        user = state["USER"] or ""
        self.room_label.config(text=f"Room: {room}")
        self.user_label.config(text=f"User: {user}")
        
        # create room crypto and ins as creator if user created the room
        self.room_state = client_encryption.RoomCryptoState(state["ROOM"]["OWNER"])

        if state["ROOM"]["OWNER"]:
            self.room_state.ins_as_creator()
        else:
            self.room_state.ins_as_joiner()

        self._set_input_enabled(state["IN_ROOM"])
        self._set_admin_mode(state["ROOM"]["ADMIN_FLAG"])

        if not self._polling:
            self._polling = True
            self.entry.focus_set()
            self._schedule_poll()

    def on_hide(self):
        """Call this when leaving the scene to stop polling cleanly."""
        self._polling = False
        if self._poll_job is not None:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

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
        if not state.get("IN_ROOM"):
            return

        msg = self.entry.get().strip()
        if not msg:
            return

        self.entry.delete(0, "end")

        self._append_chat(f"You: {msg}")

        msgtype = "COMMAND" if msg[0] == "!" else "SEND"

        if state["ROOM"]["ADMIN_FLAG"] and msg == "!leave":
            self._leave_room()
            return
        
        outbox.put({"TYPE": msgtype, "MESSAGE": msg})

    def _refresh_admin_list_from_chat_rooms(self):
        room_name = state["ROOM"]["ROOM_NAME"]
        if not room_name:
            return

        chat_room = self.chat_rooms.get(room_name)
        if not chat_room:
            return

        users = chat_room.admins
        admins = chat_room.admins
        me = state.get("USER")

        self._admin_list.delete(0, "end")

        for u in users:
            if u == me or u in admins:
                continue

            #  mark admins
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
        outbox.put({"TYPE": "COMMAND", "MESSAGE": "!leave"})
        state["ROOM"]["ADMIN_FLAG"] = False
        state["ROOM"]["OWNER"] = False
        self._set_input_enabled(False)
        self._set_admin_mode(False)
        # return to connected scene

    def _poll_inbox(self):
        if not self._polling or not state.get("RUNNING"):
            return
        
        try:
            msg = local.get(timeout=.01)
        except queue.Empty:
            self._schedule_poll()
            return

        if not msg:
            state["RUNNING"] = False
            self._append_chat("[SERVER] Disconnected.")
            self._set_input_enabled(False)
            self._polling = False
            return

        mtype = msg.get("TYPE")
        
        if mtype == "RECEIVE":
            frm = msg.get("FROM", "?")
            text = msg.get("MESSAGE", "")
            self._append_chat(f"{frm}: {text}")

        elif mtype == "BROADCAST":
            text = msg.get("MESSAGE", "")
            self._append_chat(f"[BROADCAST] {text}")

        elif mtype == "REJOIN":
            text = msg.get("MESSAGE", "")
            self._append_chat(f"[BROADCAST] {text}")
            self._set_input_enabled(False)
            self._polling = False
            state["ROOM"]["ADMIN_FLAG"] = False
            self.app.rejoin()
            return

        elif mtype == "ADMIN":
            # promote current user to admin
            print("ADMIN FLAG ENABLED")
            state["ROOM"]["ADMIN_FLAG"] = True
            self._set_admin_mode(True)

        elif mtype == "RELOAD":
            self.chat_rooms = msg.get("CHAT_ROOMS") or self.chat_rooms

            # After updating chat_rooms, refresh embedded admin list
            self.chat_room = self.chat_rooms.get(state["ROOM"]["ROOM_NAME"])
            self._refresh_admin_list_from_chat_rooms()

        self._schedule_poll()


def main():
    # Create a TCP/IP socket, connect to the VPS IP address & port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("72.62.81.113", 5000))
     
    rec_thread = threading.Thread(target = recieving_thread, args=(s,))
    outbx_thread = threading.Thread(target = outbox_thread, args=(s,))
    process_inbox_thread = threading.Thread(target = process_inbox, args=(s,))

    rec_thread.start()
    outbx_thread.start()
    process_inbox_thread.start()
    
    # generate necessary client crypto obj
    client_crypto = client_encryption.ClientCrypto()
    
    app = ChatGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
