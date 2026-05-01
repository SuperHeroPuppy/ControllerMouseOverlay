import tkinter as tk

from core.controller_constants import ACTION_DEFINITIONS, ACTION_KEYS, COLORS, INPUT_LABELS, SUPPORTED_INPUTS, WINDOWS_REMAP_OPTIONS


def build_page(self, parent):
    frame = tk.Frame(parent, bg=COLORS["bg"])

    grid_card = tk.Frame(frame, bg=COLORS["panel"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    grid_card.pack(side="left", fill="both", expand=True, padx=(0, 10))

    tk.Label(grid_card, text="Input Grid", bg=COLORS["panel"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(grid_card, text="Each controller input is a card. Click one to edit its action.", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 12))

    self.mapping_grid_frame = tk.Frame(grid_card, bg=COLORS["panel"])
    self.mapping_grid_frame.pack(fill="both", expand=True)
    self.build_mapping_grid()

    editor = tk.Frame(frame, bg=COLORS["card"], padx=18, pady=16, highlightthickness=1, highlightbackground=COLORS["border"])
    editor.pack(side="left", fill="both", expand=True)

    tk.Label(editor, text="Mapping Editor", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 13)).pack(anchor="w")
    tk.Label(editor, text="Everything here is saved instantly. Pick a controller input, then assign its action.", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=360, justify="left").pack(anchor="w", pady=(4, 12))

    self.selected_input_label = tk.Label(editor, text="", bg=COLORS["card"], fg=COLORS["accent"], font=("Segoe UI Semibold", 11))
    self.selected_input_label.pack(anchor="w")

    self.selected_action_label = tk.Label(editor, text="", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10))
    self.selected_action_label.pack(anchor="w", pady=(6, 12))

    list_frame = tk.Frame(editor, bg=COLORS["card"])
    list_frame.pack(fill="both", expand=True)

    self.action_listbox = tk.Listbox(
        list_frame,
        height=16,
        bg=COLORS["panel_alt"],
        fg=COLORS["text"],
        selectbackground=COLORS["accent_alt"],
        selectforeground=COLORS["text"],
        bd=0,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        activestyle="none",
        font=("Segoe UI", 10),
        exportselection=False,
    )
    self.action_listbox.pack(side="left", fill="both", expand=True)
    self.action_list_scrollbar = self.create_themed_scrollbar(list_frame, self.action_listbox.yview)
    self.action_list_scrollbar.pack(side="right", fill="y", padx=(8, 0))
    self.action_listbox.configure(yscrollcommand=self.action_list_scrollbar.set)
    for action_key in ACTION_KEYS:
        self.action_listbox.insert("end", ACTION_DEFINITIONS[action_key][0])
    self.action_listbox.bind("<<ListboxSelect>>", self.on_action_list_select)
    self.action_listbox.bind("<MouseWheel>", self.on_action_list_mousewheel)
    self.action_listbox.bind("<Button-4>", self.on_action_list_mousewheel)
    self.action_listbox.bind("<Button-5>", self.on_action_list_mousewheel)

    self.action_description_label = tk.Label(
        editor,
        text="",
        bg=COLORS["card"],
        fg=COLORS["muted"],
        font=("Segoe UI", 10),
        wraplength=360,
        justify="left",
    )
    self.action_description_label.pack(anchor="w", pady=(12, 0))

    remap_header = tk.Frame(editor, bg=COLORS["card"])
    remap_header.pack(fill="x", pady=(14, 6))
    tk.Label(remap_header, text="Windows Remap Output", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI Semibold", 10)).pack(side="left")
    self.remap_value_label = tk.Label(remap_header, text="", bg=COLORS["card"], fg=COLORS["accent"], font=("Segoe UI", 10))
    self.remap_value_label.pack(side="right")

    remap_list_frame = tk.Frame(editor, bg=COLORS["card"])
    remap_list_frame.pack(fill="both", expand=True)

    self.remap_listbox = tk.Listbox(
        remap_list_frame,
        height=10,
        bg=COLORS["panel_alt"],
        fg=COLORS["text"],
        selectbackground=COLORS["accent_alt"],
        selectforeground=COLORS["text"],
        bd=0,
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        activestyle="none",
        font=("Segoe UI", 10),
        exportselection=False,
    )
    self.remap_listbox.pack(side="left", fill="both", expand=True)
    self.remap_list_scrollbar = self.create_themed_scrollbar(remap_list_frame, self.remap_listbox.yview)
    self.remap_list_scrollbar.pack(side="right", fill="y", padx=(8, 0))
    self.remap_listbox.configure(yscrollcommand=self.remap_list_scrollbar.set)
    for remap_name in WINDOWS_REMAP_OPTIONS:
        self.remap_listbox.insert("end", remap_name)
    self.remap_listbox.bind("<<ListboxSelect>>", self.on_remap_list_select)
    self.remap_listbox.bind("<MouseWheel>", self.on_remap_list_mousewheel)
    self.remap_listbox.bind("<Button-4>", self.on_remap_list_mousewheel)
    self.remap_listbox.bind("<Button-5>", self.on_remap_list_mousewheel)

    listen_row = tk.Frame(editor, bg=COLORS["card"])
    listen_row.pack(fill="x", pady=(16, 0))

    self.listen_button = tk.Button(
        listen_row,
        text="Pick Next Pressed Input",
        command=self.start_input_listen,
        relief="flat",
        bd=0,
        padx=16,
        pady=10,
        bg=COLORS["card_alt"],
        fg=COLORS["text"],
        activebackground=COLORS["card_alt"],
        activeforeground=COLORS["text"],
        font=("Segoe UI Semibold", 10),
        cursor="hand2",
    )
    self.listen_button.pack(side="left")

    self.listen_status_label = tk.Label(listen_row, text="", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10))
    self.listen_status_label.pack(side="left", padx=(12, 0))

    return frame


def build_grid(self):
    for child in self.mapping_grid_frame.winfo_children():
        child.destroy()
    self.mapping_grid_buttons = {}

    for column in range(3):
        self.mapping_grid_frame.grid_columnconfigure(column, weight=1)

    for index, input_name in enumerate(SUPPORTED_INPUTS):
        card = tk.Button(
            self.mapping_grid_frame,
            command=lambda chosen=input_name: self.select_input(chosen),
            relief="flat",
            bd=0,
            padx=12,
            pady=12,
            cursor="hand2",
            justify="left",
            anchor="w",
            wraplength=180,
            font=("Segoe UI", 10),
        )
        card.grid(row=index // 3, column=index % 3, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.mapping_grid_buttons[input_name] = card


def refresh_editor(self):
    input_name = self.selected_input
    action = self.settings["input_actions"][input_name]
    action_index = ACTION_KEYS.index(action)
    self.selected_input_label.config(text=f"{INPUT_LABELS[input_name]} selected")
    self.selected_action_label.config(text=f"Assigned action: {self.describe_action(input_name)}")
    self.action_description_label.config(text=self.describe_action_detail(input_name))
    self.action_listbox.selection_clear(0, "end")
    self.action_listbox.selection_set(action_index)
    self.action_listbox.see(action_index)
    remap_name = self.settings["input_remaps"][input_name]
    remap_index = list(WINDOWS_REMAP_OPTIONS.keys()).index(remap_name)
    self.remap_value_label.config(text=remap_name)
    self.remap_listbox.selection_clear(0, "end")
    self.remap_listbox.selection_set(remap_index)
    self.remap_listbox.see(remap_index)
    remap_active = action == "windows_remap"
    remap_bg = COLORS["panel_alt"] if remap_active else COLORS["card"]
    remap_fg = COLORS["text"] if remap_active else COLORS["muted"]
    self.remap_listbox.config(state="normal" if remap_active else "disabled", disabledforeground=COLORS["muted"])
    self.remap_value_label.config(fg=COLORS["accent"] if remap_active else COLORS["muted"])
    self.remap_listbox.config(bg=remap_bg, fg=remap_fg)
    self.listen_button.config(
        text="Waiting For Input..." if self.listening_for_input else "Pick Next Pressed Input",
        bg=COLORS["accent_alt"] if self.listening_for_input else COLORS["card_alt"],
        activebackground=COLORS["accent_alt"] if self.listening_for_input else COLORS["card_alt"],
    )


def refresh_grid(self):
    for input_name, button in self.mapping_grid_buttons.items():
        selected = input_name == self.selected_input
        action_name = self.describe_action(input_name)
        button.config(
            text=f"{INPUT_LABELS[input_name]}\n{action_name}",
            bg=COLORS["accent_alt"] if selected else COLORS["card"],
            fg=COLORS["text"],
            activebackground=COLORS["accent_alt"] if selected else COLORS["card_alt"],
            activeforeground=COLORS["text"],
        )

