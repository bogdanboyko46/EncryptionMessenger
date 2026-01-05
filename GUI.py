# Important to note, for vast majority of code "messages" arent actually referring to actual typed messages
# It refers to the bytes sent between clients & relay_server, these messages for most part contain 
# socket & a map of instructions

import time
import socket
import threading
import queue
import tkinter as tk
from tkinter import ttk
from protocol import send_message, recv_message

state = {
    "RUNNING": True,
    "IN_ROOM": False,
    "ROOM": None,
    "USER": None, 
    "CHAT_ROOMS": None,
}

inbox = queue.Queue()   # messages from server (dicts)
outbox = queue.Queue()  # messages to be sent to relay server (dicts)
local = queue.Queue() # information that is needed within individual functions

# ALL THREAD FUNCTIONS 
def recieving_thread(s):
    while state["RUNNING"]:
            
        msg = recv_message(s)
        # in the case of a null msg sent to socket
        
        print(f"THE RECEIEVED MESSAGE IS {msg}")
        if msg is None:
            print("Disconnected from server.")
            state["RUNNING"] = False
            s.close()
            break
        
        inbox.put(msg)

def _wait_outbound():
    try:
        contents = outbox.get(timeout=1)
        if contents:
            return contents
    except queue.Empty:
        return _wait_outbound()

def outbox_thread(s):
    while state["RUNNING"]:

        # waits for contents patiently
        contents = _wait_outbound()

        # invalid contents if condition passes; either null or contains nothing
        if contents is None or not contents:
            continue

        # else, we send the contents to the relay server
        send_message(s, contents)

def process_inbox(s):
    # .get() will freeze the gui, we need a try except

    while state["RUNNING"]:
        try:
            # inbound logic - checks to see if inbox queue is empty
            msg = inbox.get(timeout=0.1)

            # gets the type of the message
            mType = msg.get("TYPE")

            match mType:
                
                case "CONNECTED":

                    # we are connected!
                    state["IN_ROOM"] = True
                    state["ROOM"] = msg.get("ROOM_NAME")
                    state["CHAT_ROOMS"] = msg.get("CHAT_ROOMS")

                # message type that indicates a logic error
                case "ERROR":
                    
                    error_message = msg.get("MESSAGE")

                    print(f"[Error]: {error_message}")
                    state["RUNNING"] = False

                # message type that disconnected a user from a room, user now needs room reassignment
                case "REJOIN":
                    
                    # drain anything from current inbox
                    try:
                        inbox.get(timeout=0.1)
                    except queue.Empty:
                        pass

                    # unassign user flags
                    state["IN_ROOM"] = False
                    state["ROOM"] = None
                    state["CHAT_ROOMS"] = msg.get("CHAT_ROOMS")
                    
                    # PRINT SERVER MESSAGE TO USER - PROVIDE CHAT_ROOMS
                    local.put(msg)

                    # All rejoin handling is done within the chat room scene class

                # inbound messages coming from other users in the assigned room / from broadcast
                case "RECEIVE" | "BROADCAST" | "REGISTRATION":
                    
                    print("RECEIEVED A MESSAGE INSIDE THE PROCESS INBOX THREAD! ",msg)
                    # process it in the local queue to print messages from users / print broadcast messages
                    # when registered, make info like chat_rooms and server message accessible by local queue
                    local.put(msg)
                
        except queue.Empty:
            pass
        
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
        self.geometry("900x550")

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

    def show(self, scene_name: str):
        """Raise (show) a scene by name."""
        frame = self.frames[scene_name]
        frame.on_show()
        frame.tkraise()
    
    def rejoin(self):
        print("REJOINING!")
        frame = self.frames["ConnectedScene"]

        frame.welcome_label.config(text="Connecting...")
        for w in frame.content_frame.winfo_children():
            w.destroy()

        frame.welcome_label.config(text=f"Welcome to the VPS server, {state["USER"]}")

        for w in frame.content_frame.winfo_children():
            w.destroy()

        frame.room_logic()


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
            return  # strict: do nothing on empty input

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

    def on_show(self):
        outbox.put({"NAME": state["USER"]})
        self.welcome_label.config(text="Connecting...")
        for w in self.content_frame.winfo_children():
            w.destroy()
        self.after(100, self._poll_registration)

    def _poll_registration(self):
        try:
            returned_message = local.get(timeout=0.1)
        except queue.Empty:
            self.after(5, self._poll_registration)
            return
        
        state["CHAT_ROOMS"] = returned_message.get("CHAT_ROOMS") or {}
        welcome_message = returned_message.get("MESSAGE") or "Connected."

        self.welcome_label.config(text=welcome_message)

        for w in self.content_frame.winfo_children():
            w.destroy()

        self.room_logic()


    def room_logic(self):
        # room logic
        if state["CHAT_ROOMS"]:
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
        self.app.show("CreateRoomScene")

    def go_join(self):
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
    
        room_name = self.room_entry.get()
        password = self.pass_entry.get()

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
            self.app.show("RoomScene")
        else:
            self.after(5, self.wait_for_room_connect)

    def go_back(self):
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
        # Rebuild room list from app.chat_rooms
        self.error_label.config(text="")
        self.pass_entry.delete(0, "end")
        self.details_label.config(text="Select a room to see details.")
        self.selected_room = None
        self.selected_requires_pw = False

        self.rooms_list.delete(0, "end")
        rooms = state["CHAT_ROOMS"] or {}

        for room_name in rooms.keys():
            self.rooms_list.insert("end", room_name)

        if not rooms:
            self.error_label.config(text="No rooms available to join.")
            self.join_btn.config(state="disabled")
        else:
            self.join_btn.config(state="normal")

    def on_room_select(self, event=None):
        idxs = self.rooms_list.curselection()
        if not idxs:
            return

        room_name = self.rooms_list.get(idxs[0])
        self.selected_room = room_name

        info = state["CHAT_ROOMS"].get(room_name)
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
        self.error_label.config(text="")

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
            self.app.show("RoomScene")
        else:
            self.after(5, self.wait_for_room_connect)
        
import queue
import tkinter as tk
from tkinter import ttk

# Assumes these exist globally (like your client):
# state = {"RUNNING": True, "IN_ROOM": False, "ROOM": None, "USER": None}
# inbox = queue.Queue()   # messages from server
# outbox = queue.Queue()  # messages to server


class RoomScene(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # header
        self.rowconfigure(1, weight=1)  # chat area
        self.rowconfigure(2, weight=0)  # input area

        # Header
        self.header = ttk.Label(self, text="", font=("Arial", 18))
        self.header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="n")

        # Chat display (Text + scrollbar)
        chat_frame = ttk.Frame(self)
        chat_frame.grid(row=1, column=0, sticky="nsew", padx=20)
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_text = tk.Text(chat_frame, wrap="word", state="disabled")
        self.chat_text.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(chat_frame, orient="vertical", command=self.chat_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.chat_text.configure(yscrollcommand=scroll.set)

        # Input row
        input_frame = ttk.Frame(self)
        input_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 20))
        input_frame.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(input_frame)
        self.entry.grid(row=0, column=0, sticky="ew")
        self.entry.bind("<Return>", self.on_send)

        self.send_btn = ttk.Button(input_frame, text="Send", command=self.on_send)
        self.send_btn.grid(row=0, column=1, padx=(10, 0))

        # Internal flag for polling loop
        self._polling = False

    def on_show(self):
        """
        Called by app.show("RoomScene").
        Start polling inbox safely and refresh UI.
        """
        room = state.get("ROOM") or ""
        user = state.get("USER") or ""
        self.header.config(text=f"Room: {room}    |    User: {user}")

        # Enable input only if actually in room
        self._set_input_enabled(bool(state.get("IN_ROOM")))

        # Start polling loop once per time you enter this scene
        self._polling = True
        self.entry.focus_set()
        self.after(5, self._poll_inbox)

    def on_hide(self):
        """
        Optional: call this when leaving the scene to stop polling.
        """
        self._polling = False

    def _set_input_enabled(self, enabled: bool):
        self.entry.configure(state=("normal" if enabled else "disabled"))
        self.send_btn.configure(state=("normal" if enabled else "disabled"))

    def _append_chat(self, line: str):
        self.chat_text.configure(state="normal")
        self.chat_text.insert("end", line + "\n")
        self.chat_text.see("end")
        self.chat_text.configure(state="disabled")

    def on_send(self, event=None):
        """
        Outbound messages must be event-driven (do NOT use a thread here).
        """
        if not state.get("IN_ROOM"):
            return

        msg = self.entry.get().strip()
        if not msg:
            return

        self.entry.delete(0, "end")

        # show your own message locally
        self._append_chat(f"You: {msg}")

        outbox.put({"TYPE": "SEND", "MESSAGE": msg})

    def _poll_inbox(self):
        """
        Poll inbox without blocking
        """
        if not self._polling or not state.get("RUNNING"):
            return

        # Drain multiple messages per tick to stay responsive under load
        for _ in range(10):
            try:
                msg = local.get(timeout=0.1)
            except queue.Empty:
                break

            if not msg:
                # Treat empty/None as disconnect signal
                state["RUNNING"] = False
                self._append_chat("[SERVER] Disconnected.")
                self._set_input_enabled(False)
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
                self._append_chat(f"[BROADCAST]: {text}")

                self._set_input_enabled(False)
                self._polling = False

                self.app.rejoin()

                # rejoin server

        # schedule next poll
        self.after(5, self._poll_inbox)


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

    app = ChatGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
