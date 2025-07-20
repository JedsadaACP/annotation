import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
import argparse
import logging
import os
import json
from datetime import datetime
import copy
import pandas as pd
from PIL import Image, ImageTk
from collections import Counter

# Setup logging
logger = logging.getLogger('DataIntegritySuite')
logger.setLevel(logging.INFO)

# File handler
fh = logging.FileHandler('log.txt')
fh_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh.setFormatter(fh_formatter)
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler()
ch_formatter = logging.Formatter('%(levelname)s: %(message)s')
ch.setFormatter(ch_formatter)
logger.addHandler(ch)

DEFAULT_CONFIG = {
    "sheet_name": "Sheet1",
    "provinces": [
        "Bangkok", "Nonthaburi", "Pathum Thani", "Samut Prakan",
        "Chiang Mai", "Phuket", "Chonburi", "Nakhon Ratchasima", "Songkhla"
    ],
    "column_mapping": {
        "container_number_original": "OriginalContainerNo",
        "container_number_corrected": "CorrectedContainerNo",
        "license_plate_original": "OriginalLicensePlate",
        "license_plate_corrected": "CorrectedLicensePlate",
        "province_original": "OriginalProvince",
        "province_corrected": "CorrectedProvince",
        "image_paths": ["ImagePath1", "ImagePath2", "ImagePath3", "ImagePath4"]
    }
}

# --- Global Constants ---

# Font Families
DEFAULT_FONT_FAMILY = "Segoe UI"
DATA_FONT_FAMILY = "Consolas" # For data, code-like text
THAI_FONT_FAMILY = "Leelawadee UI" # For Thai text, specified in SRS. Fallback: "Tahoma"
# It's often better to use a single font that supports all needed characters if possible,
# e.g., "Leelawadee UI" or "Tahoma" for fields that might mix Thai and alphanumeric.
# For this exercise, we'll try to apply them as specifically as possible.

# Font Sizes
FONT_SIZE_NORMAL = 10
FONT_SIZE_SMALL = 8
FONT_SIZE_LARGE = 12
FONT_SIZE_BUTTON = 10

# Complete Font Tuples
GENERAL_LABEL_FONT = (DEFAULT_FONT_FAMILY, FONT_SIZE_NORMAL)
DATA_LABEL_FONT = (DATA_FONT_FAMILY, FONT_SIZE_NORMAL) # For labels of data fields if needed for alignment
DATA_VALUE_FONT = (DATA_FONT_FAMILY, FONT_SIZE_NORMAL) # For displaying original data values
DATA_ENTRY_FONT = (DATA_FONT_FAMILY, FONT_SIZE_NORMAL) # For user entry of data (non-Thai)
PROVINCE_FONT = (THAI_FONT_FAMILY, FONT_SIZE_NORMAL)   # For province entry and display
BUTTON_FONT = (DEFAULT_FONT_FAMILY, FONT_SIZE_BUTTON, "bold")
ACTION_BUTTON_FONT = (DEFAULT_FONT_FAMILY, FONT_SIZE_SMALL)
STATUS_BAR_FONT = (DEFAULT_FONT_FAMILY, FONT_SIZE_NORMAL)
REPORT_TEXT_FONT = (DATA_FONT_FAMILY, FONT_SIZE_NORMAL) # For the content of the session report
AUTOCOMPLETE_LISTBOX_FONT = PROVINCE_FONT # Should match the province entry field

# Theme Colors
THEME_BACKGROUND = "#2E2E2E"         # Main window background
THEME_COMPONENT_BG = "#3c3c3c"       # Background for frames, buttons, listboxes
THEME_TEXT_COLOR = "#FFFFFF"           # General text color
THEME_ENTRY_FIELD_BG = "#4A4A4A"     # Background for Entry widgets (slightly different from component_bg)
THEME_ENTRY_TEXT_COLOR = "#FFFFFF"     # Text color for Entry widgets
THEME_ENTRY_INSERT_COLOR = "#FFFFFF" # Cursor color in Entry widgets
THEME_SELECT_BG = "#0078D7"          # Background for selected items in listboxes/autocomplete
THEME_SELECT_FG = "#FFFFFF"          # Text color for selected items
THEME_BUTTON_FG = "#FFFFFF"          # Text color for buttons (can be same as THEME_TEXT_COLOR)
THEME_LABELFRAME_FG = "#FFFFFF"      # Text color for LabelFrame titles


class SessionReportDialog(tk.Toplevel):
    def __init__(self, master, report_text, input_filename_base):
        super().__init__(master)
        self.master = master
        self.report_text = report_text
        self.input_filename_base = input_filename_base # Store base name for default save name

        self.title("Session Summary Report")
        self.configure(bg=THEME_BACKGROUND)
        self.protocol("WM_DELETE_WINDOW", self._on_close_button)


        # Make modal
        self.transient(master)
        self.grab_set()

        # Main frame for content
        main_frame = ttk.Frame(self, style="App.TFrame", padding=(10,10,10,10))
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Text widget for report
        self.report_text_widget = tk.Text(main_frame, wrap=tk.WORD,
                                          font=REPORT_TEXT_FONT,
                                          bg=THEME_COMPONENT_BG,
                                          fg=THEME_TEXT_COLOR,
                                          insertbackground=THEME_TEXT_COLOR, # Cursor color
                                          borderwidth=1, relief=tk.SUNKEN,
                                          padx=5, pady=5)
        self.report_text_widget.insert(tk.END, self.report_text)
        self.report_text_widget.config(state=tk.DISABLED) # Read-only
        self.report_text_widget.pack(expand=True, fill=tk.BOTH, pady=(0,10))

        # Frame for buttons
        button_frame = ttk.Frame(main_frame, style="App.TFrame")
        button_frame.pack(fill=tk.X)

        # Add some space to the right of "Save Report" button by using a spacer frame or packing options
        spacer = ttk.Frame(button_frame, width=10, style="App.TFrame") # Adjust width as needed
        spacer.pack(side=tk.RIGHT)

        close_button = ttk.Button(button_frame, text="Close", command=self._on_close_button, style="Nav.TButton")
        close_button.pack(side=tk.RIGHT)

        save_button = ttk.Button(button_frame, text="Save Report to File...", command=self.save_report_to_file, style="Nav.TButton")
        save_button.pack(side=tk.RIGHT, padx=(0,5)) # padx to space it from Close button

        # Positioning and making it blocking
        self.update_idletasks() # Ensure window elements are created for accurate sizing
        # Center on master
        master_x = master.winfo_x()
        master_y = master.winfo_y()
        master_width = master.winfo_width()
        master_height = master.winfo_height()

        # Reasonable default size for report dialog
        dialog_width = 600
        dialog_height = 400

        # Ensure it doesn't exceed master's dimensions significantly
        dialog_width = min(dialog_width, master_width - 20)
        dialog_height = min(dialog_height, master_height - 20)


        x_offset = (master_width - dialog_width) // 2 + master_x
        y_offset = (master_height - dialog_height) // 2 + master_y

        self.geometry(f"{dialog_width}x{dialog_height}+{x_offset}+{y_offset}")

        logger.info("SessionReportDialog opened.")
        self.wait_window() # Make it blocking

    def _on_close_button(self):
        logger.info("SessionReportDialog closed by user.")
        self.destroy()

    def save_report_to_file(self):
        base_name_part = os.path.splitext(self.input_filename_base)[0]
        default_filename = f"{base_name_part}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Save Session Report As...",
            initialfile=default_filename,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(self.report_text)
                logger.info(f"Session report saved to: {filepath}")
                messagebox.showinfo("Report Saved", f"Report saved successfully to:\n{filepath}", parent=self)
            except (IOError, OSError) as e:
                logger.error(f"Error saving session report to {filepath}: {e}", exc_info=True)
                messagebox.showerror("Save Error", f"Failed to save report: {e}", parent=self)
        else:
            logger.info("User cancelled saving session report.")


class AutocompleteEntry(ttk.Entry):
    def __init__(self, master, *args, **kwargs):
        self.completion_list = kwargs.pop('completion_list', [])
        self.textvariable = kwargs.pop('textvariable', tk.StringVar())
        kwargs['textvariable'] = self.textvariable # Ensure parent uses this var

        super().__init__(master, *args, **kwargs)

        self.popup_window = tk.Toplevel(self)
        self.popup_window.overrideredirect(True)
        # Make transient to the main app window (master's master, assuming master is a frame in app)
        # This requires master to be part of the main app window hierarchy
        main_app_window = self.winfo_toplevel()
        if main_app_window != self: # Check it's not the main window itself if AutocompleteEntry is on main
             self.popup_window.transient(main_app_window)


        self.listbox = tk.Listbox(self.popup_window,
                                  font=AUTOCOMPLETE_LISTBOX_FONT,
                                  bg=THEME_COMPONENT_BG,
                                  fg=THEME_TEXT_COLOR,
                                  selectbackground=THEME_SELECT_BG,
                                  selectforeground=THEME_TEXT_COLOR,
                                  borderwidth=0,
                                  highlightthickness=0,
                                  exportselection=False) # Important for multiple AutocompleteEntry widgets
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.popup_window.withdraw()

        self.bind("<KeyRelease>", self.on_key_release)
        self.bind("<Down>", self.focus_listbox_first_item)
        self.bind("<Return>", self.on_entry_return)
        self.bind("<Escape>", self.hide_popup)
        # Using focusout to hide popup needs care to allow clicking on listbox
        self.bind("<FocusOut>", self.on_focus_out)

        self.listbox.bind("<<ListboxSelect>>", self.on_select_suggestion_from_listbox_event)
        self.listbox.bind("<Return>", self.on_select_suggestion_from_listbox_event)
        self.listbox.bind("<Escape>", self.hide_popup)

    def on_key_release(self, event):
        current_text = self.textvariable.get()
        if not current_text:
            self.hide_popup()
            return

        matches = [item for item in self.completion_list if item.lower().startswith(current_text.lower())]

        if matches:
            self.listbox.delete(0, tk.END)
            for item in matches:
                self.listbox.insert(tk.END, item)
            self.position_popup()
            if not self.popup_window.winfo_viewable():
                 self.popup_window.deiconify()
            self.popup_window.lift()
            # Autoselect first item if desired, but let user navigate with Down key
            # self.listbox.selection_set(0)
        else:
            self.hide_popup()

    def position_popup(self):
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        width = self.winfo_width()

        # Calculate listbox height (e.g., max 10 items, or fit content)
        listbox_height = min(10, self.listbox.size()) * 20 # Approx item height
        if listbox_height == 0: listbox_height = 20 # Min height for one item

        self.popup_window.geometry(f'{width}x{listbox_height}+{x}+{y}')

    def hide_popup(self, event=None):
        self.popup_window.withdraw()
        return "break" # Stop propagation for Escape if it was an event

    def on_select_suggestion(self, selected_value):
        self.textvariable.set(selected_value)
        self.hide_popup()
        self.focus_set() # Return focus to entry
        self.icursor(tk.END) # Move cursor to end

    def on_select_suggestion_from_listbox_event(self, event):
        if not self.listbox.curselection():
            return "break" # Nothing selected
        selected_index = self.listbox.curselection()[0]
        selected_value = self.listbox.get(selected_index)
        self.on_select_suggestion(selected_value)
        return "break" # Selection handled

    def on_entry_return(self, event):
        if self.popup_window.winfo_viewable() and self.listbox.curselection():
            self.on_select_suggestion_from_listbox_event(event)
            return "break" # Prevent global Enter key action (save/next)
        # If popup not visible or no selection, let the event propagate for global handler
        return

    def focus_listbox_first_item(self, event):
        if self.popup_window.winfo_viewable() and self.listbox.size() > 0:
            self.listbox.focus_set()
            self.listbox.selection_set(0)
            self.listbox.activate(0)
            return "break" # Prevent default Down key behavior in Entry
        return

    def on_focus_out(self, event=None):
        # Delay hiding to allow click on listbox to register
        self.after(150, self._check_focus_and_hide_popup)

    def _check_focus_and_hide_popup(self):
        # Check if focus is still within the entry, its popup, or the listbox
        focused_widget = self.focus_get()
        if focused_widget != self and \
           focused_widget != self.popup_window and \
           focused_widget != self.listbox:
            # Check if focused_widget is a child of popup_window (e.g. scrollbar)
            if hasattr(focused_widget, 'winfo_parent'):
                parent_of_focused = focused_widget.winfo_parent()
                if parent_of_focused != str(self.popup_window): # Compare string representations of Toplevel paths
                    self.hide_popup()
            else: # If no parent, it's not part of popup
                self.hide_popup()
        elif focused_widget is None: # Lost focus to nothing (e.g. window deactivation)
            self.hide_popup()


class EditConfigurationWindow(tk.Toplevel):
    def __init__(self, master, current_config):
        super().__init__(master)
        self.master = master
        self.protocol("WM_DELETE_WINDOW", self._on_cancel) # Handle window close button
        self.title("Edit Configuration")
        self.configure(bg="#2E2E2E") # Dark theme background

        # Make modal
        self.transient(master)
        self.grab_set()

        self.editable_config = copy.deepcopy(current_config)
        self.entry_widgets = {} # To store entry fields for easy access

        # UI Elements
        main_frame = ttk.Frame(self, padding="10 10 10 10", style="Dark.TFrame") # Style for frame
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Styling for ttk widgets
        style = ttk.Style(self)
        # Using "App." prefix for styles specific to this dialog if needed, or use global VerificationApp styles
        style.configure("App.TFrame", background=THEME_BACKGROUND) # Matches VerificationApp's app_frame
        style.configure("Dialog.TLabel", background=THEME_BACKGROUND, foreground=THEME_TEXT_COLOR, font=GENERAL_LABEL_FONT)
        style.configure("Dialog.TEntry",
                        font=DATA_ENTRY_FONT,
                        fieldbackground=THEME_ENTRY_FIELD_BG,
                        foreground=THEME_ENTRY_TEXT_COLOR,
                        insertbackground=THEME_ENTRY_INSERT_COLOR)
        style.configure("Dialog.TButton", font=BUTTON_FONT, background=THEME_COMPONENT_BG, foreground=THEME_BUTTON_FG)
        style.map("Dialog.TButton", background=[('active', THEME_ENTRY_FIELD_BG)]) # Slightly lighter for active
        style.configure("Dialog.TLabelFrame", background=THEME_BACKGROUND, foreground=THEME_LABELFRAME_FG, font=GENERAL_LABEL_FONT)
        style.configure("Dialog.TLabelFrame.Label", background=THEME_BACKGROUND, foreground=THEME_LABELFRAME_FG, font=GENERAL_LABEL_FONT)


        # Sheet Name
        ttk.Label(main_frame, text="Sheet Name:", style="Dialog.TLabel").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.entry_widgets["sheet_name"] = ttk.Entry(main_frame, width=50, style="Dialog.TEntry")
        self.entry_widgets["sheet_name"].insert(0, self.editable_config.get("sheet_name", ""))
        self.entry_widgets["sheet_name"].grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        # Provinces
        ttk.Label(main_frame, text="Provinces (comma-separated):", style="Dialog.TLabel").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        # For provinces entry, using THAI_FONT_FAMILY could be beneficial if direct input of Thai is expected here
        self.entry_widgets["provinces"] = ttk.Entry(main_frame, width=50, style="Dialog.TEntry", font=PROVINCE_FONT)
        self.entry_widgets["provinces"].insert(0, ", ".join(self.editable_config.get("provinces", [])))
        self.entry_widgets["provinces"].grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)

        # Column Mapping
        map_frame = ttk.LabelFrame(main_frame, text="Column Mapping", style="Dialog.TLabelFrame", padding="10 10 10 10")
        map_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        map_frame.columnconfigure(1, weight=1) # Allow entry widgets to expand

        self.entry_widgets["column_mapping"] = {}
        row_idx = 0
        for key, value in self.editable_config.get("column_mapping", {}).items():
            ttk.Label(map_frame, text=f"{key}:", style="Dialog.TLabel").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(map_frame, width=40, style="Dialog.TEntry")
            if isinstance(value, list):
                entry.insert(0, ", ".join(value))
            else:
                entry.insert(0, str(value))
            entry.grid(row=row_idx, column=1, sticky=tk.EW, padx=5, pady=2)
            self.entry_widgets["column_mapping"][key] = entry
            row_idx += 1

        # Buttons Frame
        buttons_frame = ttk.Frame(main_frame, style="App.TFrame") # Use App.TFrame for consistency if bg is THEME_BACKGROUND
        buttons_frame.grid(row=3, column=0, columnspan=2, pady=10)

        save_button = ttk.Button(buttons_frame, text="Save", command=self._on_save, style="Dialog.TButton")
        save_button.pack(side=tk.LEFT, padx=5)
        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=self._on_cancel, style="Dialog.TButton")
        cancel_button.pack(side=tk.LEFT, padx=5)

        main_frame.columnconfigure(1, weight=1) # Allow entry column to expand

        logger.info("EditConfigurationWindow opened.")
        self.master.eval(f'tk::PlaceWindow {str(self)} center') # Center window
        self.wait_window() # Wait for window to be closed before returning control to master

    def _on_save(self):
        logger.info("Attempting to save configuration.")
        # Retrieve values and update editable_config
        self.editable_config["sheet_name"] = self.entry_widgets["sheet_name"].get()

        provinces_str = self.entry_widgets["provinces"].get()
        self.editable_config["provinces"] = [p.strip() for p in provinces_str.split(',') if p.strip()]

        for key, entry_widget in self.entry_widgets["column_mapping"].items():
            value_str = entry_widget.get()
            # Check original type to decide if it should be a list
            if isinstance(DEFAULT_CONFIG["column_mapping"].get(key), list):
                 self.editable_config["column_mapping"][key] = [v.strip() for v in value_str.split(',') if v.strip()]
            else:
                self.editable_config["column_mapping"][key] = value_str

        try:
            with open("config.json", 'w') as f:
                json.dump(self.editable_config, f, indent=4)

            self.master.config = copy.deepcopy(self.editable_config) # Update main app's config
            logger.info("Configuration saved successfully to config.json and updated in main app.")
            messagebox.showinfo("Success", "Configuration saved successfully.", parent=self)
            self.destroy()
        except (IOError, OSError) as e:
            logger.error(f"Error saving configuration to config.json: {e}")
            messagebox.showerror("Save Error", f"Failed to save configuration: {e}", parent=self)

    def _on_cancel(self):
        logger.info("Configuration editing cancelled.")
        self.destroy()

class VerificationApp(tk.Tk):
    def __init__(self, excel_file_path):
        super().__init__()
        self.input_excel_path = excel_file_path # Store the input excel path
        logger.info(f"Application trying to start with Excel file: {self.input_excel_path}")

        self.config = None
        self.load_configuration("config.json")

        if not self.config:
            logger.error("Configuration not loaded. Application cannot continue.")
            # Messagebox already shown by load_configuration or create_default_config if they lead to self.config being None
            self.destroy()
            return # Stop further initialization

        # Data and Session related initializations
        self.df = None
        self.corrections = {} # To store unsaved corrections for the current record, if needed later
        self.session_stats = {
            'records_processed': 0, # Number of records where 'Save' or 'Skip' was hit
            'corrections_made': 0,  # Number of records where a correction was made and saved
            'start_time': datetime.now()
        }
        self.current_record_index = 0
        self.output_excel_path = None # Will be set by determine_output_path
        self.correction_entries = {} # For data panel entries {key: {'var': StringVar, 'entry': ttk.Entry}}
        self.image_labels = [] # For image grid labels
        self.loaded_images = [] # To prevent garbage collection of PhotoImage objects
        self.processed_in_session_indices = set() # For session_stats

        self.title("Data Integrity Suite v1.0")
        self.geometry("1200x800")
        self.configure(bg="#2E2E2E") # Main window background

        # --- Main UI Structure ---
        # Top frame for overall layout, allows status bar to be at bottom easily
        app_frame = ttk.Frame(self, style="App.TFrame") # Style already configured by the time this runs
        app_frame.pack(fill=tk.BOTH, expand=True)

        # --- Centralized Style Configuration ---
        style = ttk.Style(self)
        style.theme_use('clam') # Using a theme that allows more customization

        # General Frame Style (used by app_frame)
        style.configure("App.TFrame", background=THEME_BACKGROUND)

        # Dark Panel Style (for data_panel_frame, image_grid_frame, and internal frames)
        style.configure("DarkPanel.TFrame", background=THEME_COMPONENT_BG)

        # Labels for field names in Data Panel
        style.configure("DataLabel.TLabel", background=THEME_COMPONENT_BG, foreground=THEME_TEXT_COLOR, font=GENERAL_LABEL_FONT)

        # Labels for displaying original (read-only) data values
        style.configure("DataValue.TLabel", background=THEME_COMPONENT_BG, foreground=THEME_TEXT_COLOR, font=DATA_VALUE_FONT)

        # Entry widgets for corrected data
        style.configure("DataEntry.TEntry",
                        font=DATA_ENTRY_FONT, # Default to Consolas for general data
                        fieldbackground=THEME_ENTRY_FIELD_BG,
                        foreground=THEME_ENTRY_TEXT_COLOR,
                        insertbackground=THEME_ENTRY_INSERT_COLOR, # Cursor color
                        borderwidth=1, relief=tk.FLAT) # Subtle border

        # Specific style for Province Entry if it needs THAI_FONT_FAMILY and others don't
        style.configure("Province.DataEntry.TEntry",
                        font=PROVINCE_FONT,
                        fieldbackground=THEME_ENTRY_FIELD_BG,
                        foreground=THEME_ENTRY_TEXT_COLOR,
                        insertbackground=THEME_ENTRY_INSERT_COLOR,
                        borderwidth=1, relief=tk.FLAT)

        # Labels for Image Grid (placeholders or error messages)
        style.configure("ImageGrid.TLabel", background=THEME_COMPONENT_BG, foreground=THEME_TEXT_COLOR, anchor=tk.CENTER, font=GENERAL_LABEL_FONT)

        # Navigation and Action Buttons (used in Data Panel and Dialogs)
        style.configure("Nav.TButton", font=BUTTON_FONT, background=THEME_COMPONENT_BG, foreground=THEME_BUTTON_FG)
        style.map("Nav.TButton", background=[('active', THEME_ENTRY_FIELD_BG)]) # Slightly lighter when active/pressed

        style.configure("Action.TButton", font=ACTION_BUTTON_FONT, background=THEME_ENTRY_FIELD_BG, foreground=THEME_BUTTON_FG)
        style.map("Action.TButton", background=[('active', THEME_SELECT_BG)])

        # Status Bar Label
        style.configure("TStatusbar", background=THEME_COMPONENT_BG, foreground=THEME_TEXT_COLOR, font=STATUS_BAR_FONT) # Example name
        # For ttk.Label used as status bar:
        style.configure("Status.TLabel", background=THEME_COMPONENT_BG, foreground=THEME_TEXT_COLOR, font=STATUS_BAR_FONT, anchor=tk.W, padding=(2,2,2,2))
        self.status_bar_style_name = "Status.TLabel" # To apply to status_bar later if it's a ttk.Label

        # Configure ttk.LabelFrame
        style.configure("Dark.TLabelFrame", background=THEME_COMPONENT_BG, relief=tk.GROOVE) # Main frame bg
        style.configure("Dark.TLabelFrame.Label",
                        background=THEME_COMPONENT_BG, # Label part bg
                        foreground=THEME_LABELFRAME_FG,
                        font=GENERAL_LABEL_FONT)


        # Main content frame (holds data panel and image grid)
        main_content_frame = ttk.Frame(app_frame, style="App.TFrame")
        main_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Data Panel
        self.data_panel_frame = ttk.Frame(main_content_frame, width=450, style="DarkPanel.TFrame")
        self.data_panel_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5), pady=0)
        self.data_panel_frame.pack_propagate(False) # Prevent resizing to fit content initially

        # Right Image Grid
        self.image_grid_frame = ttk.Frame(main_content_frame, style="DarkPanel.TFrame")
        self.image_grid_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=0)

        # Setup 2x2 grid for images
        for i in range(2):
            self.image_grid_frame.rowconfigure(i, weight=1)
            self.image_grid_frame.columnconfigure(i, weight=1)

        for i in range(4):
            img_label = ttk.Label(self.image_grid_frame, text=f"Image {i+1}", style="ImageGrid.TLabel")
            img_label.grid(row=i//2, column=i%2, sticky=tk.NSEW, padx=2, pady=2)
            self.image_labels.append(img_label)

        # Navigation Buttons Frame (Below Data Panel for now)
        nav_frame = ttk.Frame(self.data_panel_frame, style="DarkPanel.TFrame") # Add it to data panel
        nav_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        self.prev_button = ttk.Button(nav_frame, text="Previous (Left)", command=self.prev_record, style="Nav.TButton")
        self.prev_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.suggest_button = ttk.Button(nav_frame, text="Suggest Corrections", command=self.on_suggest_corrections_click, style="Nav.TButton")
        self.suggest_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.next_button = ttk.Button(nav_frame, text="Next (Right)", command=self.next_record, style="Nav.TButton")
        self.next_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2) # Changed from tk.RIGHT to tk.LEFT to keep order

        # Menu Bar
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Settings Menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Edit Configuration", command=self.edit_configuration)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        # Analysis Menu
        analysis_menu = tk.Menu(menubar, tearoff=0)
        analysis_menu.add_command(label="Show Statistics", command=self.show_statistics)
        menubar.add_cascade(label="Analysis", menu=analysis_menu)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)
        menubar.add_cascade(label="Help", menu=help_menu)

        # Status Bar
        # Ensure status_bar is created before trying to apply style if it's a ttk.Label
        self.status_bar = ttk.Label(app_frame, text="Loading...", style=self.status_bar_style_name, relief=tk.SUNKEN) # Use app_frame
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0), padx=0)

        logger.info("Base VerificationApp UI initialized. Proceeding to load data.")
        self.load_data() # Load data after config and basic UI setup

        if self.df is None: # If data loading failed and led to df being None
            logger.error("Data not loaded properly. Application cannot continue.")
            # Appropriate error messages should have been shown by load_data()
            # Ensure window closes if it's still open
            if self.winfo_exists():
                 self.destroy()
            return

        logger.info("VerificationApp UI structure initialized.")

        # Load initial record UI
        if self.df is not None and not self.df.empty:
            self.load_current_record_ui()
        elif self.df is not None and self.df.empty: # Excel loaded but no data
            self.populate_data_panel() # To show "No data" or similar
            self.display_images() # Clear images
            self.update_status_bar()
        else: # df is None (loading failed)
            # Handled by __init__ exit logic
            pass

        self.bind("<Configure>", self.on_window_resize) # For image resizing
        # Bind arrow keys for navigation (example)
        self.bind_all('<Left>', self.prev_record) # bind_all to catch even if focus is on an entry
        self.bind_all('<Right>', self.next_record)
        self.bind_all('<Return>', self.on_enter_key) # Enter key for save and next

        # Add focus to the main app window so it can catch key presses initially
        self.focus_set()


    def on_window_resize(self, event=None):
        # Basic resize handling: redraw images as their container size might have changed.
        # Check if image_grid_frame exists and is visible
        if hasattr(self, 'image_grid_frame') and self.image_grid_frame.winfo_ismapped():
            # Debounce or add more checks later if performance is an issue
            self.display_images()

    def populate_data_panel(self):
        # Clear previous entries/labels
        for widget in self.data_panel_frame.winfo_children():
            # Don't destroy the nav_frame which is now part of data_panel_frame
            if widget.winfo_class() != "TFrame":
                 # Check if it's the nav_frame by checking for a known button if more TFrames are added
                is_nav_frame = False
                if hasattr(widget, 'winfo_children'):
                    for child_w in widget.winfo_children():
                        if isinstance(child_w, ttk.Button) and "Previous" in child_w.cget("text"):
                            is_nav_frame = True
                            break
                if not is_nav_frame:
                    widget.destroy()

        self.correction_entries.clear() # Clear dict of entry widgets and their StringVars

        if self.df is None or self.df.empty or self.current_record_index < 0 :
            # Handle current_record_index >= len(self.df) separately for "All records processed"
            if self.df is not None and self.current_record_index >= len(self.df):
                 msg = "All records processed."
            else:
                 msg = "No data to display."
            if self.df is not None and not self.df.empty and self.current_record_index >= len(self.df):
                msg = "All records processed."

            no_data_label = ttk.Label(self.data_panel_frame, text=msg, style="DataLabel.TLabel", font=("Segoe UI", 12, "italic"))
            no_data_label.pack(padx=10, pady=20, anchor=tk.CENTER)
            return # Do not proceed to populate fields

        # Ensure nav_frame is at the bottom by repacking if necessary (it should exist)
        nav_frame_found = None
        for child in self.data_panel_frame.winfo_children():
             if hasattr(child, 'prev_button'): # Assuming this identifies the nav_frame
                nav_frame_found = child
                break
        if nav_frame_found:
            nav_frame_found.pack_forget()


        # Create a content frame within data_panel_frame to hold the data fields.
        content_fields_frame = ttk.Frame(self.data_panel_frame, style="DarkPanel.TFrame")
        content_fields_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Re-pack nav_frame at the bottom after content_fields_frame
        if nav_frame_found:
            nav_frame_found.pack(side=tk.BOTTOM, fill=tk.X, pady=10)


        try:
            record = self.df.iloc[self.current_record_index]
        except IndexError: # Should be caught by earlier checks, but as safeguard
            logger.warning(f"populate_data_panel: current_record_index {self.current_record_index} is out of bounds for DataFrame length {len(self.df)}.")
            ttk.Label(content_fields_frame, text="Error: Record index out of bounds.", style="DataLabel.TLabel").pack(padx=10, pady=10)
            return

        row_num = 0
        field_display_order = [
            "container_number_original", "container_number_corrected",
            "license_plate_original", "license_plate_corrected",
            "province_original", "province_corrected"
        ]

        for key in field_display_order:
            if key not in self.config["column_mapping"]:
                continue

            actual_col_name = self.config["column_mapping"][key]

            # Make display name more readable
            display_key_name = key.replace("_", " ").title()

            field_frame = ttk.Frame(content_fields_frame, style="DarkPanel.TFrame")
            field_frame.grid(row=row_num, column=0, columnspan=2, sticky=tk.EW, pady=(0, 2))
            field_frame.columnconfigure(1, weight=1) # Label for name
            if key.endswith("_corrected"): # Entry + buttons
                 field_frame.columnconfigure(2, weight=0) # Buttons frame


            lbl = ttk.Label(field_frame, text=f"{display_key_name}:", style="DataLabel.TLabel")
            lbl.grid(row=0, column=0, sticky=tk.NW, pady=(0,0))

            if key.endswith("_corrected"):
                # Determine original value for "Copy" button
                original_key_name = key.replace("_corrected", "_original")
                original_df_col_name = self.config["column_mapping"].get(original_key_name)
                original_value = record.get(original_df_col_name, "") if original_df_col_name else ""

                # Check self.corrections first, then df
                current_value_in_df = record.get(actual_col_name, "")
                field_value = self.corrections.get(self.current_record_index, {}).get(key, current_value_in_df)

                string_var = tk.StringVar(value=str(field_value))
                string_var.trace_add('write', lambda name, index, mode, fk=key, sv=string_var: self._update_correction(fk, sv.get()))

                entry_style_key = "DataEntry.TEntry"
                if key == "province_corrected":
                    entry_style_key = "Province.DataEntry.TEntry" # Use specific style for province
                    entry_widget = AutocompleteEntry(field_frame,
                                                     textvariable=string_var,
                                                     completion_list=self.config.get('provinces', []),
                                                     style=entry_style_key,
                                                     font=PROVINCE_FONT, # Explicitly set font here for AutocompleteEntry
                                                     width=25)
                else:
                    entry_widget = ttk.Entry(field_frame, textvariable=string_var, style=entry_style_key, width=25)

                entry_widget.grid(row=0, column=1, sticky=tk.EW, pady=(0,0), padx=(5,0))
                self.correction_entries[key] = {'var': string_var, 'entry': entry_widget}

                # Action buttons frame
                actions_frame = ttk.Frame(field_frame, style="DarkPanel.TFrame")
                actions_frame.grid(row=0, column=2, sticky=tk.EW, padx=(3,0))

                copy_btn = ttk.Button(actions_frame, text="Copy", style="Action.TButton", width=5,
                                      command=lambda sv=string_var, ov=original_value: sv.set(str(ov)))
                copy_btn.pack(side=tk.LEFT, padx=(0,2))

                dash_btn = ttk.Button(actions_frame, text="-", style="Action.TButton", width=2,
                                      command=lambda sv=string_var: sv.set("-"))
                dash_btn.pack(side=tk.LEFT, padx=(0,2))

                double_dash_btn = ttk.Button(actions_frame, text="--", style="Action.TButton", width=2,
                                             command=lambda sv=string_var: sv.set("--"))
                double_dash_btn.pack(side=tk.LEFT)

            else: # original value (read-only)
                value_from_df = record.get(actual_col_name, "N/A")
                # For original province value, use PROVINCE_FONT. Other original data uses DATA_VALUE_FONT.
                display_font = PROVINCE_FONT if key == "province_original" else DATA_VALUE_FONT
                val_label = ttk.Label(field_frame, text=str(value_from_df), style="DataValue.TLabel", font=display_font, wraplength=280)
                val_label.grid(row=0, column=1, sticky=tk.EW, pady=(0,0), padx=(5,0))
            row_num += 1

        logger.debug(f"Data panel populated for record {self.current_record_index}.")


    def _update_correction(self, field_key, new_value):
        if self.df is None or self.current_record_index < 0 or self.current_record_index >= len(self.df):
            logger.warning(f"_update_correction called with invalid index or df: {self.current_record_index}")
            return

        if self.current_record_index not in self.corrections:
            self.corrections[self.current_record_index] = {}

        # Get original value from DataFrame for comparison
        df_col_name = self.config['column_mapping'].get(field_key)
        original_df_value = ""
        if df_col_name and df_col_name in self.df.columns:
            original_df_value = str(self.df.loc[self.current_record_index, df_col_name])

        # Check if this change is a "meaningful" correction
        # A correction is made if the new value is different from what's in the DataFrame for that corrected field
        # And we haven't already counted this record as having a correction *for this specific change action* (this is tricky)
        # Simplification: if value changes from what's in DF, it's a correction.
        # If it changes back to what's in DF, it's no longer a correction for that field.
        # session_stats['corrections_made'] should reflect number of *records* with at least one *net* correction.

        # Store the new value
        self.corrections[self.current_record_index][field_key] = new_value
        logger.debug(f"Correction updated for record {self.current_record_index}, field {field_key}: {new_value}")

        # Mark record as processed in this session
        is_newly_processed = self.current_record_index not in self.processed_in_session_indices
        self.processed_in_session_indices.add(self.current_record_index)
        if is_newly_processed: # Only update 'records_processed' if it's the first interaction with this record in the session
            self.session_stats['records_processed'] = len(self.processed_in_session_indices)

        # For 'corrections_made', this is simpler: count records that have *any* deviation in `self.corrections` from `self.df`
        # This needs to be re-evaluated across all fields for the record when calculating stats, or managed carefully.
        # For now, let's assume any _update_correction implies a desire to change, and Enter/Save confirms it.
        # The 'corrections_made' stat will be more accurately updated when saving.

        self.update_status_bar()


    def save_current_record_changes(self):
        if self.df is None or self.current_record_index < 0 or self.current_record_index >= len(self.df):
            logger.warning(f"save_current_record_changes: No data or invalid index {self.current_record_index}.")
            return False # Indicate save did not happen

        if self.current_record_index in self.corrections:
            record_corrections = self.corrections[self.current_record_index]
            made_change_to_df = False
            for field_key, new_value in record_corrections.items():
                df_column_name = self.config['column_mapping'].get(field_key)
                if df_column_name:
                    # Compare with current DF value before updating to see if it's a real change
                    if str(self.df.loc[self.current_record_index, df_column_name]) != str(new_value):
                        self.df.loc[self.current_record_index, df_column_name] = new_value
                        made_change_to_df = True
                        logger.info(f"Record {self.current_record_index}: Applied change for {field_key} ('{df_column_name}') to DataFrame: '{new_value}'")
                else:
                    logger.warning(f"Could not find DataFrame column for field_key {field_key} in config.")

            if made_change_to_df:
                # This is a good place to manage the 'corrections_made' stat accurately for the record.
                # If not already counted as a corrected record in this session based on another mechanism.
                # For now, assume `on_enter_key` or a dedicated save button updates this.
                # Let's refine this: if we made a change to DF here, this record is now "corrected".
                # We need a set of indices for records corrected in this session.
                # self.corrected_in_session_indices.add(self.current_record_index)
                # self.session_stats['corrections_made'] = len(self.corrected_in_session_indices)
                # This part is complex to get right with stats, deferring precise 'corrections_made' count to save-to-file.
                pass
            return made_change_to_df
        return False


    def on_enter_key(self, event=None):
        logger.debug(f"<Return> key pressed on record {self.current_record_index}")
        if self.df is None or self.current_record_index < 0 or self.current_record_index >= len(self.df):
            logger.warning("Enter key: No data or invalid index.")
            # If it's the "end of records" state, maybe trigger file save/summary here
            if self.df is not None and self.current_record_index >= len(self.df):
                 logger.info("Enter pressed at end of records. Future: trigger save/summary.")
                 # Potentially call a self.finalize_session() method here
            return

        self.save_current_record_changes()

        # Mark as processed
        self.processed_in_session_indices.add(self.current_record_index)
        self.session_stats['records_processed'] = len(self.processed_in_session_indices)

        # TODO: More sophisticated 'corrections_made' logic needed here or upon final save.
        # For now, if save_current_record_changes returned true, it means a value different from DF was in corrections.
        # This might be a good spot to increment 'corrections_made' if it's the first time this record is confirmed with changes.
        # However, what if user corrects, then corrects back to original, then hits Enter?
        # Let's assume 'corrections_made' counts records that have at least one changed field *at the time of saving to Excel*.
        # So, this counter will be updated more accurately later.

        self.update_status_bar() # Reflect processed count
        self.next_record()


    def save_data_to_excel(self):
        logger.info("Attempting to save data to Excel...")
        if self.df is None:
            logger.warning("No data (DataFrame) to save.")
            messagebox.showwarning("No Data", "There is no data to save.", parent=self)
            return False

        # Ensure current record's changes are in self.df
        if self.current_record_index >= 0 and self.current_record_index < len(self.df) :
             self.save_current_record_changes()
        else: # Handle case where current_record_index might be at len(self.df) (end of records)
            # if there were corrections for an index that's now out of bounds (e.g. last record deleted),
            # this part might need more robust handling. For now, assume save_current_record_changes handles its bounds.
            pass


        if not self.output_excel_path:
            logger.error("Output Excel path is not defined. Cannot save.")
            messagebox.showerror("Save Error", "Output file path is not defined. Cannot save data.", parent=self)
            return False

        try:
            # To preserve other sheets, we need to read the original workbook if it exists,
            # or if the output file is different from the input file.
            # If output_excel_path is same as input_excel_path, this logic ensures we're updating it.

            sheets_data = {}
            if os.path.exists(self.input_excel_path):
                try:
                    xls = pd.ExcelFile(self.input_excel_path, engine='openpyxl')
                    for sheet_name in xls.sheet_names:
                        if sheet_name != self.config['sheet_name']:
                            sheets_data[sheet_name] = pd.read_excel(xls, sheet_name=sheet_name)
                    xls.close() # Close the file explicitly
                except Exception as e: # Broad exception for issues reading original file
                    logger.error(f"Error reading sheets from original file {self.input_excel_path}: {e}", exc_info=True)
                    # Decide if this is critical. For now, proceed to save only our sheet.
                    # messagebox.showwarning("Save Warning", f"Could not read other sheets from original file: {e}\nOnly the active sheet will be saved.", parent=self)

            with pd.ExcelWriter(self.output_excel_path, engine='openpyxl') as writer:
                # Write the main DataFrame
                self.df.to_excel(writer, sheet_name=self.config['sheet_name'], index=False)
                logger.info(f"Data for sheet '{self.config['sheet_name']}' written to Excel writer.")

                # Write back other sheets
                for sheet_name, df_sheet in sheets_data.items():
                    df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info(f"Preserved sheet '{sheet_name}' written to Excel writer.")

            logger.info(f"Data successfully saved to {self.output_excel_path}")
            messagebox.showinfo("Save Successful", f"Data saved to:\n{self.output_excel_path}", parent=self)
            return True

        except PermissionError:
            logger.error(f"Permission denied when trying to save to {self.output_excel_path}. File might be open.", exc_info=True)
            messagebox.showerror("Save Error", f"Cannot save to '{os.path.basename(self.output_excel_path)}'.\nPermission denied. Please ensure the file is not open elsewhere.", parent=self)
            return False
        except Exception as e: # Catch other potential errors during save
            logger.error(f"An error occurred while saving data to {self.output_excel_path}: {e}", exc_info=True)
            messagebox.showerror("Save Error", f"An error occurred while saving data:\n{e}", parent=self)
            return False

    def generate_session_report_text(self):
        logger.info("Generating session report text...")
        end_time = datetime.now()
        duration = end_time - self.session_stats['start_time']

        # Format duration (HH:MM:SS)
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        formatted_duration = f"{hours:02}:{minutes:02}:{seconds:02}"

        records_processed_in_session = len(self.processed_in_session_indices)

        # Calculate actual corrections made in this session for the report
        actual_corrections_count = 0
        if self.df is not None:
            for record_idx in self.processed_in_session_indices:
                if record_idx >= len(self.df): continue # Skip if index out of bounds (e.g. record deleted)

                original_values = {}
                corrected_values = {}
                has_difference_for_this_record = False

                for map_key, df_col_name in self.config["column_mapping"].items():
                    if map_key.endswith("_original"):
                        original_values[map_key.replace("_original", "")] = self.df.loc[record_idx, df_col_name]
                    elif map_key.endswith("_corrected"):
                        corrected_values[map_key.replace("_corrected", "")] = self.df.loc[record_idx, df_col_name]

                for base_key in original_values:
                    # Compare only if both original and corrected versions are mapped
                    if base_key in corrected_values:
                        # Ensure comparison handles various types (e.g. NaN, empty strings) consistently
                        # self.df is loaded with dtype=str and fillna('') so comparison should be fine
                        if str(original_values[base_key]) != str(corrected_values[base_key]):
                            has_difference_for_this_record = True
                            break

                if has_difference_for_this_record:
                    actual_corrections_count += 1

        self.session_stats['corrections_made'] = actual_corrections_count # Update stat for status bar consistency if needed now

        report_lines = [
            "Session Summary Report",
            "----------------------",
            f"Input File: {os.path.basename(self.input_excel_path) if self.input_excel_path else 'N/A'}",
            f"Output File: {os.path.basename(self.output_excel_path) if self.output_excel_path else 'N/A'}",
            f"Session Start Time: {self.session_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"Session End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Session Duration: {formatted_duration}",
            "",
            f"Records Processed in Session: {records_processed_in_session}",
            f"Total Records in File: {len(self.df) if self.df is not None else 'N/A'}",
            f"Records with Corrections Made in Session: {actual_corrections_count}"
        ]

        report_lines.append("\n" + "="*30 + "\n")

        # Add detailed statistics
        analyzer = StatisticsAnalyzer(self.df.copy(), self.config)
        stats_text = analyzer.analyze()
        report_lines.append(stats_text)

        report_text = "\n".join(report_lines)
        logger.info("Session report text generated.")
        logger.info(f"\n{report_text}") # Log the report itself
        return report_text


    def on_suggest_corrections_click(self):
        logger.info("'Suggest Corrections' button clicked.")
        if self.df is None or self.current_record_index < 0 or self.current_record_index >= len(self.df):
            messagebox.showwarning("No Record", "Please load data and select a valid record before suggesting corrections.", parent=self)
            return
        self.run_ocr_and_suggest()

    def run_ocr_and_suggest(self):
        logger.info(f"Starting OCR simulation for record index: {self.current_record_index}")

        # --- IMPORTANT: Placeholder for Actual OCR ---
        logger.warning("This is a SIMULATED OCR process. No actual image processing or Tesseract OCR is being performed.")
        logger.warning("Actual OCR implementation would require: image loading, preprocessing (cropping, binarization), "
                       "Tesseract/other OCR engine calls, and intelligent parsing of results (e.g., using regex).")
        # --- End of Placeholder Warning ---

        # Simulate fetching original values to base suggestions on them slightly
        record = self.df.iloc[self.current_record_index]
        simulated_ocr_results = {}

        # Container Number
        original_container_key = "container_number_original"
        corrected_container_key = "container_number_corrected"
        if original_container_key in self.config["column_mapping"] and corrected_container_key in self.config["column_mapping"]:
            original_container_val = record.get(self.config["column_mapping"][original_container_key], "CONT")
            simulated_ocr_results[corrected_container_key] = f"{original_container_val[:4]}_OCR{datetime.now().second:02d}"

        # License Plate
        original_lp_key = "license_plate_original"
        corrected_lp_key = "license_plate_corrected"
        if original_lp_key in self.config["column_mapping"] and corrected_lp_key in self.config["column_mapping"]:
            original_lp_val = record.get(self.config["column_mapping"][original_lp_key], "PLATE")
            simulated_ocr_results[corrected_lp_key] = f"{original_lp_val[:3]}_OCR{datetime.now().microsecond % 1000:03d}"

        # Province - pick a valid one, maybe cycle through them or pick first
        corrected_prov_key = "province_corrected"
        if corrected_prov_key in self.config["column_mapping"]:
            provinces = self.config.get('provinces', ["(OCR PROVINCE)"])
            if provinces:
                # Simple way to vary suggestion: cycle based on record index
                simulated_ocr_results[corrected_prov_key] = provinces[self.current_record_index % len(provinces)]
            else:
                simulated_ocr_results[corrected_prov_key] = "OCR_PROV_ERR"

        logger.info(f"Simulated OCR results: {simulated_ocr_results}")

        # Populate correction fields with simulated results
        for field_key, suggested_value in simulated_ocr_results.items():
            if field_key in self.correction_entries:
                entry_info = self.correction_entries[field_key]
                if 'var' in entry_info: # Check if 'var' (StringVar) exists
                    entry_info['var'].set(suggested_value)
                    # This should trigger _update_correction via the trace
                else:
                    logger.warning(f"StringVar not found for entry field: {field_key}")
            else:
                logger.warning(f"Entry field not found in self.correction_entries for key: {field_key}")

        messagebox.showinfo("OCR Simulation",
                            "Simulated OCR complete.\nSuggestions have been populated. Please review them.",
                            parent=self)
        logger.info("Simulated OCR suggestions applied to UI fields.")


    def display_images(self):
        self.loaded_images.clear() # Clear previously loaded PhotoImage objects

        if self.df is None or self.df.empty or self.current_record_index < 0 or self.current_record_index >= len(self.df) or not hasattr(self, 'image_grid_frame'):
            for i in range(4): # Clear all image labels
                if i < len(self.image_labels):
                    self.image_labels[i].config(image=None, text=f"Image {i+1}\n(No data or index out of bounds)")
                    self.image_labels[i].image = None
            return

        try:
            record = self.df.iloc[self.current_record_index]
        except IndexError:
            logger.warning(f"display_images: current_record_index {self.current_record_index} is out of bounds.")
            for i in range(4):
                if i < len(self.image_labels):
                    self.image_labels[i].config(image=None, text=f"Image {i+1}\n(Record not found)")
                    self.image_labels[i].image = None
            return

        image_path_cols = self.config['column_mapping'].get('image_paths', [])
        base_dir = os.path.dirname(self.input_excel_path)

        # Get current dimensions of an image cell
        # Ensure image_grid_frame has positive width/height before calculating cell dimensions
        self.image_grid_frame.update_idletasks() # Ensure dimensions are current
        cell_width = self.image_grid_frame.winfo_width() // 2 - 10 # Account for padding/margins
        cell_height = self.image_grid_frame.winfo_height() // 2 - 10

        if cell_width <=0 or cell_height <=0 :
            logger.warning("Image grid frame has zero or negative dimensions, cannot display images.")
            # Fallback: set placeholder text
            for i in range(4):
                 if i < len(self.image_labels):
                    self.image_labels[i].config(image=None, text=f"Image {i+1}\n(Grid size error)")
                    self.image_labels[i].image = None
            return


        for i in range(4):
            img_label = self.image_labels[i]
            if i < len(image_path_cols):
                relative_path = record.get(image_path_cols[i], "")
                if relative_path and isinstance(relative_path, str) and relative_path.strip() != "":
                    full_path = os.path.join(base_dir, relative_path.strip())
                    try:
                        img = Image.open(full_path)

                        # Resize logic (aspect ratio preserving)
                        img_aspect = img.width / img.height
                        cell_aspect = cell_width / cell_height

                        if img_aspect > cell_aspect: # Image is wider than cell, fit to width
                            new_width = cell_width
                            new_height = int(new_width / img_aspect)
                        else: # Image is taller than cell (or same aspect), fit to height
                            new_height = cell_height
                            new_width = int(new_height * img_aspect)

                        if new_width > 0 and new_height > 0:
                           resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                           photo_img = ImageTk.PhotoImage(resized_img)
                           img_label.config(image=photo_img, text="")
                           img_label.image = photo_img # Keep reference!
                           self.loaded_images.append(photo_img)
                        else: # Calculated new_width/height is zero or negative
                            img_label.config(image=None, text=f"Image {i+1}\n(Resize error)")
                            img_label.image = None
                            logger.warning(f"Image {full_path} resulted in zero/negative resize dimensions ({new_width}x{new_height}).")

                    except FileNotFoundError:
                        img_label.config(image=None, text=f"Image {i+1}\n(File not found:\n{os.path.basename(full_path)})")
                        img_label.image = None
                        logger.warning(f"Image file not found: {full_path}")
                    except Exception as e:
                        img_label.config(image=None, text=f"Image {i+1}\n(Error loading)")
                        img_label.image = None
                        logger.error(f"Error loading image {full_path}: {e}", exc_info=True)
                else: # Empty path in cell
                    img_label.config(image=None, text=f"Image {i+1}\n(No path)")
                    img_label.image = None
            else: # Not enough image_path columns configured for this label
                img_label.config(image=None, text=f"Image {i+1}\n(Not configured)")
                img_label.image = None
        logger.debug(f"Images displayed for record {self.current_record_index}.")

    def load_current_record_ui(self):
        if self.df is None or self.df.empty:
            logger.info("load_current_record_ui: No DataFrame or empty DataFrame.")
            self.populate_data_panel() # Will show "No data" or "All records processed"
            self.display_images()      # Will clear images
            self.update_status_bar()
            return

        if self.current_record_index < 0:
            self.current_record_index = 0
        if self.current_record_index >= len(self.df):
            # This state means all records are processed or index is past the end
            self.current_record_index = len(self.df) # Standardize to len(df) for "end" state
            logger.info("load_current_record_ui: Attempting to load UI at or beyond end of records.")
            self.populate_data_panel() # Shows "All records processed"
            self.display_images()      # Clears images
            self.update_status_bar()
            # Disable next button, enable prev if appropriate
            self.next_button.config(state=tk.DISABLED)
            self.prev_button.config(state=tk.NORMAL if len(self.df) > 0 else tk.DISABLED)
            return

        logger.info(f"Loading UI for record index: {self.current_record_index}")
        self.populate_data_panel()
        self.display_images() # Call this after panel, as panel might affect available space if not careful with packing
        self.update_status_bar()

        # Set focus to the first correction entry
        first_correction_key = "container_number_corrected" # Example, make more robust if key order changes
        if self.correction_entries.get(first_correction_key):
            self.correction_entries[first_correction_key].focus_set()

        # Update button states
        self.prev_button.config(state=tk.NORMAL if self.current_record_index > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if self.current_record_index < len(self.df) -1 else tk.DISABLED)
        if self.current_record_index >= len(self.df) -1 : # If on last record
             self.next_button.config(state=tk.DISABLED)


    def next_record(self, event=None): # event=None for button clicks
        logger.debug(f"Next record called. Current index: {self.current_record_index}, DF length: {len(self.df) if self.df is not None else 'N/A'}")
        if self.df is None or self.df.empty:
            logger.warning("Next record: No data loaded.")
            return

        self.save_current_record_changes() # Save changes before navigating

        if self.current_record_index < len(self.df) - 1:
            self.current_record_index += 1
            self.load_current_record_ui()
        elif self.current_record_index == len(self.df) - 1: # Already on the last record
            self.current_record_index = len(self.df) # Move to "end" state
            self.load_current_record_ui() # This will show "All records processed"
            logger.info("Reached end of records.")
            messagebox.showinfo("End of Data", "You have reached the last record.", parent=self)
        else: # current_record_index is already >= len(self.df), should be handled by load_current_record_ui
             logger.info("Already at or past end of records. No next action.")


    def prev_record(self, event=None): # event=None for button clicks
        logger.debug(f"Previous record called. Current index: {self.current_record_index}")
        if self.df is None or self.df.empty:
            logger.warning("Previous record: No data loaded.")
            return

        self.save_current_record_changes() # Save changes before navigating

        if self.current_record_index == len(self.df): # If currently in "end" state
            self.current_record_index = len(self.df) - 1 # Go to the last actual record
            self.load_current_record_ui()
        elif self.current_record_index > 0:
            self.current_record_index -= 1
            self.load_current_record_ui()
        else: # Already at the first record or invalid index
            logger.info("Already at the first record.")
            messagebox.showinfo("Start of Data", "You are at the first record.", parent=self)


    def update_status_bar(self):
        if self.df is not None and not self.df.empty:
            # current_record_index is 0-based, display as 1-based
            display_record_num = self.current_record_index + 1
            if self.current_record_index >= len(self.df) : # If past the last record
                display_record_num = len(self.df)

            status_text = f"Record {display_record_num} / {len(self.df)} | Processed: {self.session_stats['records_processed']} | Corrections: {self.session_stats['corrections_made']}"
            if self.current_record_index >= len(self.df): # If in "end" state
                 status_text = f"End of records ({len(self.df)} total) | Processed: {self.session_stats['records_processed']} | Corrections: {self.session_stats['corrections_made']}"
            self.status_bar.config(text=status_text)
        elif self.df is not None and self.df.empty:
            self.status_bar.config(text="Excel file loaded but is empty or selected sheet is empty.")
        else: # self.df is None
            self.status_bar.config(text="No data loaded or data loading failed.")


    def determine_output_path(self):
        if not self.input_excel_path:
            logger.error("Input Excel path is not set. Cannot determine output path.")
            # This case should ideally be prevented by checks in __main__ or __init__
            messagebox.showerror("Error", "Input Excel path is missing.", parent=self)
            self.output_excel_path = None
            return
        try:
            directory, filename = os.path.split(self.input_excel_path)
            name_part, ext_part = os.path.splitext(filename)
            self.output_excel_path = os.path.join(directory, f"{name_part}_corrected{ext_part}")
            logger.info(f"Determined output Excel path: {self.output_excel_path}")
        except Exception as e:
            logger.error(f"Error determining output path: {e}")
            messagebox.showerror("Error", f"Could not determine output file path: {e}", parent=self)
            self.output_excel_path = None


    def load_data(self):
        logger.info("Starting data loading process...")
        self.determine_output_path() # Sets self.output_excel_path

        if not self.output_excel_path: # If output path determination failed
            logger.error("Output Excel path could not be determined. Halting data load.")
            self.df = None # Ensure df is None to signal failure
            self.update_status_bar()
            return # Exit load_data

        file_to_load = self.input_excel_path
        resuming_session = False

        if os.path.exists(self.output_excel_path):
            logger.info(f"Partially corrected file found: {self.output_excel_path}")
            if messagebox.askyesno("Resume Session?",
                                   f"A partially corrected file '{os.path.basename(self.output_excel_path)}' exists.\nDo you want to resume from it?",
                                   parent=self): # Ensure parent is set for modal behavior
                file_to_load = self.output_excel_path
                resuming_session = True
                logger.info(f"User chose to resume session from: {file_to_load}")
            else:
                logger.info(f"User chose not to resume. Starting fresh from: {self.input_excel_path}. Previous corrections might be overwritten on save.")

        try:
            logger.info(f"Attempting to load Excel file: {file_to_load} using sheet: {self.config['sheet_name']}")
            self.df = pd.read_excel(file_to_load, sheet_name=self.config['sheet_name'], engine='openpyxl', dtype=str) # Load all as string initially
            self.df = self.df.fillna('') # Replace NaN with empty strings for consistency
            logger.info(f"Successfully loaded {len(self.df)} records from {file_to_load}.")

            if self.df.empty:
                logger.warning(f"Loaded Excel file {file_to_load} (sheet: {self.config['sheet_name']}) is empty.")
                # update_status_bar will show "Excel file loaded but is empty..."
                # No need to exit, but further operations might be limited.

            # Verify required columns from column_mapping actually exist in the loaded DataFrame
            # These are the source columns that the tool expects to read data from.
            critical_source_cols_missing = []
            for map_key, config_col_name in self.config["column_mapping"].items():
                if not map_key.endswith("_corrected"): # These are original data columns or image path lists
                    if isinstance(config_col_name, list): # e.g. image_paths
                        for img_col in config_col_name:
                            if img_col not in self.df.columns:
                                critical_source_cols_missing.append(img_col)
                    elif config_col_name not in self.df.columns: # single column name
                         critical_source_cols_missing.append(config_col_name)

            if critical_source_cols_missing:
                unique_missing_cols = sorted(list(set(critical_source_cols_missing)))
                logger.error(f"Missing required source columns in the Excel file: {unique_missing_cols}")
                messagebox.showerror("Data Error", f"The Excel file ('{os.path.basename(file_to_load)}') is missing required source columns defined in config: {', '.join(unique_missing_cols)}.\nPlease check the file or 'column_mapping' in the configuration.", parent=self)
                self.df = None
                self.update_status_bar()
                return

            # Initialize _corrected columns if they don't exist (common when loading original, or if config changed)
            for map_key, actual_col_name in self.config["column_mapping"].items():
                if map_key.endswith("_corrected"):
                    if actual_col_name not in self.df.columns:
                        logger.info(f"Initializing missing corrected column: {actual_col_name} with empty strings.")
                        self.df[actual_col_name] = '' # Initialize with empty string for consistency with fillna('')

            # Find first unprocessed row for resuming_session or set to 0
            self.current_record_index = 0
            if resuming_session and not self.df.empty:
                # Get names of columns that store corrections
                corrected_column_target_names = [
                    self.config["column_mapping"][k]
                    for k in self.config["column_mapping"] if k.endswith("_corrected")
                ]
                # Ensure these columns actually exist in the DataFrame before checking them
                existing_corrected_cols = [name for name in corrected_column_target_names if name in self.df.columns]

                if existing_corrected_cols:
                    all_processed = True
                    for i, row in self.df.iterrows():
                        is_row_processed = False # Assume not processed
                        for col_name in existing_corrected_cols:
                            # A row is considered processed if *any* of its corrected fields has content.
                            if str(row[col_name]).strip() != '':
                                is_row_processed = True
                                break
                        if not is_row_processed:
                            self.current_record_index = i
                            all_processed = False
                            break
                    if all_processed: # If loop completed and all rows were processed
                         self.current_record_index = len(self.df) # Position after last record, indicating completion
                    logger.info(f"Resuming session. Starting at index {self.current_record_index} (0-based).")
                else: # No corrected columns found in DF, cannot determine progress
                    logger.warning("Resuming session, but no corrected columns (as defined in config) found in the loaded data. Starting at index 0.")
            elif not self.df.empty: # New session or non-empty DataFrame
                 logger.info("New session or not resuming. Starting at index 0.")

            # If index is beyond data (e.g. all records processed), set to last record or appropriate state
            if not self.df.empty and self.current_record_index >= len(self.df):
                logger.info(f"All {len(self.df)} records seem processed. Current index set to end.")
                # UI should handle this state (e.g. display last record or "all done" message)
                self.current_record_index = len(self.df) # Or len(self.df) -1 to show last if desired. len(self.df) is good for "add new" or "done".
            elif self.df.empty:
                 self.current_record_index = 0 # No records to process

        except FileNotFoundError:
            logger.error(f"Excel file not found: {file_to_load}")
            messagebox.showerror("File Not Found", f"The Excel file was not found: {file_to_load}", parent=self)
            self.df = None
        except KeyError as e:
            logger.error(f"Sheet name error: {e}. Configured sheet: {self.config['sheet_name']}")
            messagebox.showerror("Sheet Not Found", f"Sheet '{self.config['sheet_name']}' not found in '{os.path.basename(file_to_load)}'.\nPlease check the file or configuration.", parent=self)
            self.df = None
        except ValueError as e:
             logger.error(f"Error reading Excel file {file_to_load} (ValueError): {e}", exc_info=True)
             messagebox.showerror("Excel Read Error", f"Could not read the Excel file '{os.path.basename(file_to_load)}'. It might be corrupted, not a valid Excel format, or an issue with data types.\nDetails: {e}", parent=self)
             self.df = None
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading Excel file {file_to_load}: {e}", exc_info=True)
            messagebox.showerror("Load Error", f"An unexpected error occurred while loading data from '{os.path.basename(file_to_load)}':\n{e}", parent=self)
            self.df = None

        self.update_status_bar() # Update status bar based on outcome


    def load_configuration(self, config_path="config.json"):
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Configuration loaded successfully from {config_path}")
        except FileNotFoundError:
            logger.warning(f"Configuration file {config_path} not found.")
            self.create_default_config(config_path)
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Configuration loaded successfully after creation: {config_path}")
            except FileNotFoundError: # Should not happen if creation was successful and user agreed
                logger.error(f"Failed to load config file {config_path} even after attempting creation.")
                self.config = None # Ensure config is None
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from {config_path} after creation: {e}")
                messagebox.showerror("Configuration Error", f"Error parsing newly created {config_path}. Please check its format or delete it to recreate.")
                self.config = None # Ensure config is None
            except Exception as e:
                logger.error(f"Unexpected error loading {config_path} after creation: {e}")
                messagebox.showerror("Configuration Error", f"An unexpected error occurred while loading {config_path} after creation.")
                self.config = None # Ensure config is None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {config_path}: {e}")
            messagebox.showerror("Configuration Error", f"Error parsing {config_path}. Please check its format.")
            self.config = None # Ensure config is None
            # Decide if to exit or use defaults. For now, set to None and let __init__ handle exit.
        except OSError as e:
            logger.error(f"OS error reading {config_path}: {e}")
            messagebox.showerror("File Error", f"Error reading configuration file {config_path}: {e}\nApplication will exit.")
            self.config = None # Ensure config is None
            # self.destroy() called from __init__ if self.config is None

    def create_default_config(self, config_path="config.json"):
        logger.info(f"Attempting to create default configuration file at {config_path}")
        if messagebox.askyesno("Create Default Configuration?",
                               f"Configuration file '{config_path}' not found.\nDo you want to create a default configuration file?"):
            try:
                with open(config_path, 'w') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
                logger.info(f"Default configuration file created at {config_path}")
                messagebox.showinfo("Configuration Created",
                                    f"Default configuration file '{config_path}' created.\nPlease review and edit it if necessary.")
            except OSError as e:
                logger.error(f"Error creating default configuration file {config_path}: {e}")
                messagebox.showerror("File Creation Error", f"Could not create default configuration file: {e}\nApplication cannot proceed.")
                # No self.config yet, and this path leads to self.config remaining None
        else:
            logger.warning("User declined to create a default configuration file.")
            messagebox.showwarning("Configuration Missing", "Application cannot proceed without a configuration file. Exiting.")
            # No self.config yet, and this path leads to self.config remaining None

    def edit_configuration(self):
        logger.info("Edit Configuration clicked.")
        if not self.config:
            logger.error("Cannot edit configuration: No configuration loaded.")
            messagebox.showerror("Error", "Configuration is not loaded. Cannot open edit window.")
            return
        # Pass self (VerificationApp instance) as master, and its config
        EditConfigurationWindow(self, self.config)
        # The EditConfigurationWindow will call self.master.config = ... on save

    def show_about(self):
        logger.info("Show About clicked")
        messagebox.showinfo("About", "Data Integrity Suite v1.0\n\nDeveloped by [Your Name/Organization]")

    def show_user_guide(self):
        logger.info("Show User Guide clicked")
        messagebox.showinfo("User Guide", "User Guide clicked (placeholder).")

    def show_statistics(self):
        logger.info("Show Statistics clicked.")
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "There is no data to analyze.", parent=self)
            return

        analyzer = StatisticsAnalyzer(self.df.copy(), self.config)
        report_text = analyzer.analyze()
        StatisticsDialog(self, report_text)

    def quit(self):
        logger.info("Quit action initiated.")
        # Prompt to save changes
        # result can be "yes", "no", or None (if window is closed with 'x')
        if self.df is not None and (self.corrections or self.processed_in_session_indices): # Check if there's anything to potentially save
            msg_result = messagebox.askyesnocancel("Save Changes?",
                                                 "Do you want to save your changes before exiting?",
                                                 parent=self)
            if msg_result is True: # Yes
                logger.info("User chose to save changes before exiting.")
                save_success = self.save_data_to_excel()
                if not save_success:
                    # Ask if user still wants to exit if save failed
                    if not messagebox.askyesno("Save Failed", "Could not save data. Exit anyway?", parent=self):
                        logger.info("User chose not to exit after save failed.")
                        return # Do not exit
                # If save successful, or if save failed but user chose to exit anyway:
                # If save successful or if save failed but user chose to exit anyway:
                report_text = self.generate_session_report_text() # Generate report text
                logger.info("Session report generated on exit.")
                # Display the report in a modal dialog
                SessionReportDialog(self, report_text, os.path.basename(self.input_excel_path or "session"))
                # The quit sequence pauses here until SessionReportDialog is closed.
            elif msg_result is False: # No
                logger.info("User chose not to save changes.")
                # Still generate and show report if work was done
                if self.processed_in_session_indices:
                    report_text = self.generate_session_report_text()
                    logger.info("Session report generated on exit (no save).")
                    SessionReportDialog(self, report_text, os.path.basename(self.input_excel_path or "session"))
            else: # Cancel (msg_result is None)
                logger.info("User cancelled exit.")
                return # Do not exit

        logger.info("Proceeding to destroy main window.")
        self.destroy() # Calls the overridden destroy

    # Ensure quit is called if the window is destroyed prematurely
    def destroy(self):
        logger.info("Application window destroyed.")
        super().destroy()


class StatisticsAnalyzer:
    def __init__(self, df, config):
        self.df = df
        self.config = config

    def analyze(self):
        """
        Analyzes the DataFrame to find the distribution of corrected data.
        """
        if self.df is None or self.df.empty:
            return "No data to analyze."

        report = []
        report.append("Correction Statistics Report")
        report.append("=" * 30)

        column_mapping = self.config.get("column_mapping", {})
        correction_fields = [k.replace('_corrected', '') for k in column_mapping if k.endswith('_corrected')]

        total_records = len(self.df)
        report.append(f"Total Records Analyzed: {total_records}")
        report.append("-" * 30)

        for field in correction_fields:
            original_col = column_mapping.get(f"{field}_original")
            corrected_col = column_mapping.get(f"{field}_corrected")

            if not all([original_col, corrected_col, original_col in self.df.columns, corrected_col in self.df.columns]):
                report.append(f"\nSkipping field '{field}': Missing or invalid column mapping.")
                continue

            # Ensure columns are treated as strings for comparison
            self.df[original_col] = self.df[original_col].astype(str).fillna('')
            self.df[corrected_col] = self.df[corrected_col].astype(str).fillna('')

            # Identify records with corrections
            corrected_mask = self.df[original_col] != self.df[corrected_col]
            corrected_df = self.df[corrected_mask]
            num_corrections = len(corrected_df)

            percentage_corrected = (num_corrections / total_records) * 100 if total_records > 0 else 0

            report.append(f"\nAnalysis for field: '{field.replace('_', ' ').title()}'")
            report.append(f"  - Total Corrections: {num_corrections} ({percentage_corrected:.2f}%)")

            if num_corrections > 0:
                # Distribution of corrected values
                value_counts = Counter(corrected_df[corrected_col])
                report.append("  - Distribution of Corrected Values:")
                for value, count in value_counts.most_common(10): # Show top 10
                    report.append(f"    - '{value}': {count} times")
                if len(value_counts) > 10:
                    report.append("    - ... (and other values)")

                # Common changes (Original -> Corrected)
                changes = corrected_df.groupby([original_col, corrected_col]).size().reset_index(name='counts')
                changes = changes.sort_values('counts', ascending=False)
                report.append("  - Most Common Changes (Original -> Corrected):")
                for _, row in changes.head(5).iterrows(): # Show top 5 changes
                    report.append(f"    - From '{row[original_col]}' to '{row[corrected_col]}': {row['counts']} times")
                if len(changes) > 5:
                    report.append("    - ... (and other changes)")

        return "\n".join(report)

class StatisticsDialog(tk.Toplevel):
    def __init__(self, master, analysis_text):
        super().__init__(master)
        self.title("Correction Statistics")
        self.geometry("600x400")
        self.configure(bg="#f0f0f0")

        self.transient(master)
        self.grab_set()

        main_frame = tk.Frame(self, bg="#f0f0f0")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        text_area = tk.Text(main_frame, wrap=tk.WORD, bg="white", font=("Courier New", 10))
        text_area.insert(tk.END, analysis_text)
        text_area.config(state=tk.DISABLED)

        scrollbar = tk.Scrollbar(main_frame, command=text_area.yview)
        text_area['yscrollcommand'] = scrollbar.set

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_area.pack(expand=True, fill=tk.BOTH)

        close_button = tk.Button(self, text="Close", command=self.destroy)
        close_button.pack(pady=5)

        self.wait_window()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Data Integrity Suite v1.0")
    parser.add_argument("excel_file", help="Path to the input Excel file.")
    args = parser.parse_args()

    logger.info("Application starting command-line processing...")

    # Check if the excel file exists
    excel_file_path = args.excel_file
    if not os.path.exists(excel_file_path):
        logger.error(f"Error: Excel file not found at {excel_file_path}")
        # Fallback: Ask user to select a file if not provided or not found
        # This initial Tk() is for the file dialog if needed before main app window
        root_fd = tk.Tk()
        root_fd.withdraw() # Hide the main window
        messagebox.showerror("File Not Found", f"The specified Excel file was not found: {excel_file_path}\nPlease select the Excel file.")
        selected_path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=(("Excel files", "*.xlsx *.xls"), ("All files", "*.*"))
        )
        if not selected_path:
            logger.info("No file selected by user. Exiting application.")
            root_fd.destroy()
            exit() # Exit if no file is chosen
        else:
            excel_file_path = selected_path
        root_fd.destroy() # Clean up the temporary root window

    logger.info("Proceeding to initialize VerificationApp.")
    app = VerificationApp(excel_file_path=excel_file_path)

    # Only run mainloop if app was initialized (i.e. self.config is not None and __init__ didn't return early)
    if app.winfo_exists(): # Check if the main window was created and not destroyed
        app.mainloop()
        logger.info("Application finished.")
    else:
        logger.info("Application did not start due to initialization issues (e.g. config error).")
