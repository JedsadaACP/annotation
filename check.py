import tkinter as tk
from tkinter import ttk # For Treeview later
from tkinter import font as tkFont
from tkinter import messagebox
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw, ImageFont
import pandas as pd
import os
import argparse
import re # Added for potential regex use in LP analysis

# Define COLUMN_NAMES dictionary
COLUMN_NAMES = {
    "container": "container_number",
    "corrected_container": "corrected_container_number",
    "license_plate": "license_plate_number",
    "corrected_license_plate": "corrected_license_plate_number",
    "province": "license_plate_province",
    "corrected_province": "corrected_license_plate_province",
    "top_img": "top_camera_image_file",
    "left_img": "left_camera_image_file",
    "right_img": "right_camera_image_file",
    "plate_img": "license_plate_image_file"
}

# Implement basic Tkinter Application Class AnalysisApp
class AnalysisApp(tk.Tk):
    def __init__(self, input_excel_path=None):
        super().__init__()
        self.title("Data Quality Check Tool (check.py)")
        self.geometry("1200x800") # Or other suitable size
        self.configure(bg="#F0F0F0") # A light theme might be better for a check tool

        self.input_file_path = input_excel_path
        self.base_dir = None # Will be set when file is loaded
        self.df = None
        self.flagged_records = [] # To store results from checks
        self.treeview_sort_column = None
        self.treeview_sort_reverse = False

        self.setup_styles()
        self.create_widgets()

        if self.input_file_path:
            # Optionally auto-load if path is given via CLI, or require button press
            print(f"DEBUG: File path provided via CLI: {self.input_file_path}")
            # self.load_data_and_run_checks() # Decide if auto-load or not

    def setup_styles(self):
        self.header_font = tkFont.Font(family="Segoe UI", size=14, weight="bold")
        self.label_font = tkFont.Font(family="Segoe UI", size=10)
        self.button_font = tkFont.Font(family="Segoe UI", size=10, weight="bold")
        # Add more styles as needed

    def create_widgets(self):
        # Top frame for controls
        controls_frame = tk.Frame(self, pady=10, bg="#F0F0F0")
        controls_frame.pack(fill=tk.X)

        self.load_button = tk.Button(controls_frame, text="Load Data File & Run Checks", font=self.button_font, command=self.load_data_and_run_checks)
        self.load_button.pack(side=tk.LEFT, padx=10)

        self.file_label = tk.Label(controls_frame, text="No file loaded.", font=self.label_font, bg="#F0F0F0")
        self.file_label.pack(side=tk.LEFT, padx=10)

        # Placeholder for results and image display (to be detailed in later steps)
        # Example: Results list
        results_list_frame = tk.Frame(self, bg="#F0F0F0")
        results_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Remove placeholder label if any
        for widget in results_list_frame.winfo_children():
            widget.destroy()

        columns = ("index", "field", "original_value", "value", "reason") # New: added "original_value"
        self.results_treeview = ttk.Treeview(results_list_frame, columns=columns, show="headings")

        # Define headings
        self.results_treeview.heading("index", text="Record Index", command=lambda: self.sort_treeview_column("index", False))
        self.results_treeview.heading("field", text="Flagged Field", command=lambda: self.sort_treeview_column("field", False))
        self.results_treeview.heading("original_value", text="Original Value", command=lambda: self.sort_treeview_column("original_value", False)) # New Column
        self.results_treeview.heading("value", text="Corrected Value", command=lambda: self.sort_treeview_column("value", False)) # Text changed for clarity
        self.results_treeview.heading("reason", text="Reason for Flag", command=lambda: self.sort_treeview_column("reason", False))

        # Configure column widths (adjust as needed)
        self.results_treeview.column("index", width=80, anchor=tk.W)
        self.results_treeview.column("field", width=150, anchor=tk.W)
        self.results_treeview.column("original_value", width=200, anchor=tk.W) # New Column
        self.results_treeview.column("value", width=200, anchor=tk.W) # Renamed "Field Value" to "Corrected Value"
        self.results_treeview.column("reason", width=300, anchor=tk.W)

        # Add a vertical scrollbar
        vsb = ttk.Scrollbar(results_list_frame, orient="vertical", command=self.results_treeview.yview)
        self.results_treeview.configure(yscrollcommand=vsb.set)

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind selection event (will be used in the next step for image display)
        self.results_treeview.bind("<<TreeviewSelect>>", self.on_flagged_record_select)

        # Example: Image display area
        self.image_display_frame = tk.Frame(self, bg="#D0D0D0", height=300) # Give it a distinct bg for now
        self.image_display_frame.pack(fill=tk.X, padx=10, pady=5)

        # Clear placeholder if any
        for widget in self.image_display_frame.winfo_children():
            widget.destroy()

        self.image_display_frame.grid_columnconfigure((0, 1), weight=1) # 2 columns
        self.image_display_frame.grid_rowconfigure((0, 1), weight=1)    # 2 rows (if showing 4 images)

        self.image_display_labels = {}
        image_keys_to_display = { # Key: (grid_row, grid_col, descriptive_text)
            "plate_img": (0, 0, "License Plate Image"),
            "top_img": (0, 1, "Top Camera Image"),
            "left_img": (1, 0, "Left Camera Image"),
            "right_img": (1, 1, "Right Camera Image"),
        }

        for key, (r, c, text) in image_keys_to_display.items():
            img_frame = tk.Frame(self.image_display_frame, bd=1, relief=tk.SUNKEN, bg="#E0E0E0")
            img_frame.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)

            desc_label = tk.Label(img_frame, text=text, font=("Segoe UI", 9, "italic"), bg="#E0E0E0")
            desc_label.pack(pady=(2,0))

            img_label = tk.Label(img_frame, bg="#2E2E2E") # Similar to main app's image label bg
            img_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.image_display_labels[key] = img_label


    def load_data_and_run_checks(self):
        file_path_to_load = self.input_file_path

        if not file_path_to_load: # If not provided via CLI, or if user clicks button again
            file_path_to_load = filedialog.askopenfilename(
                title="Select Corrected Excel File",
                filetypes=(("Excel files", "*.xlsx"), ("All files", "*.*"))
            )

        if not file_path_to_load:
            messagebox.showwarning("No File", "No data file selected.")
            return

        try:
            print(f"DEBUG: Attempting to load Excel file: {file_path_to_load}")
            # Assuming all columns should be read as string initially to avoid type issues with corrected data
            self.df = pd.read_excel(file_path_to_load, dtype=str)
            self.df = self.df.fillna('') # Fill NaN with empty strings for consistency
            self.base_dir = os.path.dirname(os.path.abspath(file_path_to_load))
            self.file_label.config(text=f"Loaded: {os.path.basename(file_path_to_load)} ({len(self.df)} records)")
            print(f"DEBUG: Successfully loaded {file_path_to_load}. DataFrame shape: {self.df.shape}")
            messagebox.showinfo("Load Successful", f"Successfully loaded {len(self.df)} records from {os.path.basename(file_path_to_load)}.")

            # Placeholder for calling check functions
            self.run_all_statistical_checks()
        except FileNotFoundError:
            print(f"DEBUG: File not found: {file_path_to_load}")
            messagebox.showerror("Error", f"Input file not found:\n{file_path_to_load}")
            self.df = None
        except Exception as e:
            print(f"DEBUG: Error loading Excel file: {type(e).__name__} - {e}")
            messagebox.showerror("Error", f"Could not read Excel file. Error:\n{e}")
            self.df = None

        # Update UI based on loaded data (e.g., clear old results)
        # This will be expanded when checks are implemented.
        # For now, if df is None, perhaps disable check buttons etc.

    # Placeholder for statistical check runner
    def load_thai_provinces(self, filepath="thai_provinces.txt"):
        print(f"DEBUG: Attempting to load Thai provinces from {filepath}")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                provinces = [line.strip() for line in f if line.strip()]
            print(f"DEBUG: Loaded {len(provinces)} Thai provinces.")
            return set(provinces) # Use a set for efficient lookup
        except FileNotFoundError:
            print(f"DEBUG: Thai provinces file not found: {filepath}")
            messagebox.showwarning("File Missing", f"Thai province list file '{filepath}' not found. Province checks will be limited.")
            return set() # Return empty set if file not found

    def province_analysis(self, df):
        print("DEBUG: Running province analysis...")
        flagged = []
        if COLUMN_NAMES['corrected_province'] not in df.columns:
            print(f"DEBUG: Missing column for province analysis: {COLUMN_NAMES['corrected_province']}")
            return flagged

        thai_provinces_set = self.load_thai_provinces()

        # Frequency analysis (can be printed or stored if needed later)
        province_counts = df[COLUMN_NAMES['corrected_province']].value_counts()
        print("DEBUG: Province Frequencies:\n", province_counts.to_string())

        for index, row in df.iterrows():
            province = str(row[COLUMN_NAMES['corrected_province']]).strip()
            original_province = str(row.get(COLUMN_NAMES['province'], 'N/A')).strip() # Get original
            if province and province not in thai_provinces_set and province not in ['-', '--']: # Ignore placeholders
                flagged.append({
                    'index': index,
                    'field': COLUMN_NAMES['corrected_province'],
                    'original_value': original_province, # ADDED
                    'value': province, # This is the corrected value
                    'reason': 'Not in standard Thai province list (or is foreign/misspelled)'
                })
        print(f"DEBUG: Province analysis flagged {len(flagged)} records.")
        return flagged

    def license_plate_analysis(self, df):
        print("DEBUG: Running license plate analysis...")
        flagged = []
        if COLUMN_NAMES['corrected_license_plate'] not in df.columns:
            print(f"DEBUG: Missing column for LP analysis: {COLUMN_NAMES['corrected_license_plate']}")
            return flagged

        # Configuration for LP checks (can be moved to class attributes or settings)
        MIN_LP_LENGTH = 3
        MAX_LP_LENGTH = 10 # Adjust as needed
        # Example: Allow alphanumeric, Thai consonants/vowels (very basic set for demo)
        # A more comprehensive regex for Thai LPs would be much better.
        # For now, let's assume basic alphanumeric + common Thai for simplicity of this step.
        # This regex allows English A-Z, a-z, 0-9, and a wide range of Thai characters.
        # It does NOT include spaces or special symbols like '-' or ','.
        # If LPs can have spaces or hyphens, this needs adjustment or pre-cleaning.
        LP_ALLOWED_CHARS_REGEX = r'^[a-zA-Z0-9ก-๛]+$' # Basic Latin alphanumeric + Thai range

        for index, row in df.iterrows():
            lp = str(row[COLUMN_NAMES['corrected_license_plate']]).strip()
            original_lp = str(row.get(COLUMN_NAMES['license_plate'], 'N/A')).strip() # Get original
            if not lp or lp in ['-', '--']: # Skip empty or placeholders
                continue

            # Length check
            if not (MIN_LP_LENGTH <= len(lp) <= MAX_LP_LENGTH):
                flagged.append({
                    'index': index,
                    'field': COLUMN_NAMES['corrected_license_plate'],
                    'original_value': original_lp, # ADDED
                    'value': lp, # Corrected value
                    'reason': f'Invalid length (expected {MIN_LP_LENGTH}-{MAX_LP_LENGTH})'
                })
                continue # Don't check chars if length is already wrong for this example

            # Character set check (simplified)
            # For a real app, this regex would need to be very robust or use specific LP format rules.
            # The current regex is very broad for Thai.
            # import re # Make sure re is imported at the top of check.py
            # if not re.match(LP_ALLOWED_CHARS_REGEX, lp):
            #     flagged.append({
            #         'index': index,
            #         'field': COLUMN_NAMES['corrected_license_plate'],
            #         'value': lp,
            #         'reason': 'Contains disallowed characters'
            #     })
            # For simplicity of this step, let's assume a simpler check:
            # only check if it's purely alphanumeric (English) for demo, easier to test.
            # User can refine this logic.
            if not lp.isalnum(): # Simplified check for non-alphanumeric (English)
                # This will flag Thai LPs if not handled by a proper regex.
                # For now, this helps test the flagging mechanism.
                # A more robust solution would involve a proper regex for valid LP characters (Thai + Eng + numbers)
                pass # Commenting out the simple isalnum check to avoid flagging all Thai LPs with it.
                     # Proper regex should be part of a dedicated LP validation step.
                     # For now, we focus on length and consistency.

        print(f"DEBUG: License plate analysis (length check) flagged {len(flagged)} records.")
        return flagged

    def consistency_analysis(self, df):
        print("DEBUG: Running consistency analysis...")
        flagged = []
        if COLUMN_NAMES['corrected_license_plate'] not in df.columns or \
           COLUMN_NAMES['corrected_province'] not in df.columns:
            print("DEBUG: Missing columns for consistency analysis.")
            return flagged

        for index, row in df.iterrows():
            lp = str(row[COLUMN_NAMES['corrected_license_plate']]).strip()
            prov = str(row[COLUMN_NAMES['corrected_province']]).strip()
            original_lp = str(row.get(COLUMN_NAMES['license_plate'], 'N/A')).strip()
            original_prov = str(row.get(COLUMN_NAMES['province'], 'N/A')).strip()

            is_lp_placeholder = lp in ['-', '--']
            is_prov_placeholder = prov in ['-', '--']
            # is_lp_empty_or_placeholder = not lp or is_lp_placeholder # original, can simplify
            # is_prov_empty_or_placeholder = not prov or is_prov_placeholder # original, can simplify

            # Case 1: LP is a placeholder, but province is a specific value (not empty and not a placeholder)
            if is_lp_placeholder and prov and not is_prov_placeholder:
                flagged.append({
                    'index': index,
                    'field': 'LP/Province Consistency',
                    'original_value': f"Orig LP: {original_lp}, Orig Prov: {original_prov}", # ADDED/MODIFIED
                    'value': f'Corr LP: {lp}, Corr Prov: {prov}', # Corrected values
                    'reason': 'LP is placeholder but Province is specific value'
                })
            # Case 2: Province is a placeholder, but LP is a specific value (not empty and not a placeholder)
            elif is_prov_placeholder and lp and not is_lp_placeholder:
                flagged.append({
                    'index': index,
                    'field': 'LP/Province Consistency',
                    'original_value': f"Orig LP: {original_lp}, Orig Prov: {original_prov}", # ADDED/MODIFIED
                    'value': f'Corr LP: {lp}, Corr Prov: {prov}', # Corrected values
                    'reason': 'Province is placeholder but LP is specific value'
                })
        print(f"DEBUG: Consistency analysis flagged {len(flagged)} records.")
        return flagged

    def run_all_statistical_checks(self):
        if self.df is None:
            messagebox.showwarning("No Data", "No data loaded to analyze.")
            return

        print("DEBUG: Running all statistical checks...")
        self.flagged_records = [] # Clear previous results

        # Call individual check functions here and aggregate results
        self.flagged_records.extend(self.province_analysis(self.df))
        self.flagged_records.extend(self.license_plate_analysis(self.df)) # Primarily length for now
        self.flagged_records.extend(self.consistency_analysis(self.df))

        print(f"DEBUG: Total flagged records: {len(self.flagged_records)}")
        if not self.flagged_records:
            messagebox.showinfo("Checks Complete", "No anomalies found by current checks.")
        else:
            messagebox.showinfo("Checks Complete", f"{len(self.flagged_records)} potential anomalies found. See console for DEBUG details for now.")

        # Placeholder: Update the GUI list for flagged records (next step)
        self.update_flagged_records_list()

        # For now, print aggregated results to console
        # if self.flagged_records:
        #     print("--- Aggregated Flagged Records ---")
        #     for record in self.flagged_records:
        #         print(f"  Index: {record['index']}, Field: {record['field']}, Value: '{record['value']}', Reason: {record['reason']}")
        #     print("---------------------------------")

    def update_flagged_records_list(self):
        # Clear existing items in the treeview
        for item in self.results_treeview.get_children():
            self.results_treeview.delete(item)

        if not self.flagged_records:
            # Optionally, display a message in the treeview or a label if no records are flagged
            # For now, it will just be empty.
            print("DEBUG: No flagged records to display in Treeview.")
            return

        print(f"DEBUG: Updating Treeview with {len(self.flagged_records)} flagged records.")
        for record_info in self.flagged_records:
            # Ensure all keys are present, provide default if not, though check functions should be consistent
            idx = record_info.get('index', 'N/A')
            field = record_info.get('field', 'N/A')
            original_value = str(record_info.get('original_value', 'N/A')) # Get original_value
            value = str(record_info.get('value', 'N/A')) # Ensure value is string for display
            reason = record_info.get('reason', 'N/A')
            self.results_treeview.insert("", tk.END, values=(idx, field, original_value, value, reason))

    def sort_treeview_column(self, col_name, reverse):
        # Check if this column was the last one sorted
        if self.treeview_sort_column == col_name:
            # If yes, toggle the reverse flag
            current_reverse_state = not self.treeview_sort_reverse
        else:
            # If a new column, sort ascending by default
            current_reverse_state = False

        self.treeview_sort_column = col_name # Store the current sort column
        self.treeview_sort_reverse = current_reverse_state # Store the current sort direction

        # Get data from treeview rows. l is a list of tuples (value, item_id)
        # The values are (idx, field, value, reason) -> now (idx, field, original_value, value, reason)
        # We need to map col_name to the index in these tuples
        col_map = {"index": 0, "field": 1, "original_value": 2, "value": 3, "reason": 4} # New map
        col_index = col_map.get(col_name)

        if col_index is None:
            print(f"DEBUG: Invalid column name for sorting: {col_name}")
            return

        # Get all items with their values
        l = [(self.results_treeview.set(k, col_index), k) for k in self.results_treeview.get_children('')]

        # Data type consideration for sorting
        try:
            # Attempt to sort numerically if 'index' column, else as string (case-insensitive)
            if col_name == "index":
                l.sort(key=lambda t: int(t[0]), reverse=current_reverse_state)
            else:
                l.sort(key=lambda t: str(t[0]).lower(), reverse=current_reverse_state)
        except ValueError:
            # Fallback to string sort if int conversion fails for 'index'
            l.sort(key=lambda t: str(t[0]).lower(), reverse=current_reverse_state)

        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            self.results_treeview.move(k, '', index)

        # Update the heading to show sort direction (optional, using an arrow)
        # This requires a bit more logic to clear previous arrows
        for c_id in self.results_treeview["columns"]:
            current_text = self.results_treeview.heading(c_id, "text")
            # Remove old arrows
            current_text = current_text.replace(" ▲", "").replace(" ▼", "")
            if c_id == col_name:
                arrow = " ▲" if not current_reverse_state else " ▼" # Up or Down arrow
                self.results_treeview.heading(c_id, text=current_text + arrow)
            else:
                self.results_treeview.heading(c_id, text=current_text) # Reset others

    def on_flagged_record_select(self, event):
        selection = self.results_treeview.selection()
        if not selection:
            return

        item = selection[0] # Get the first selected item
        record_values = self.results_treeview.item(item, "values")

        try:
            record_index = int(record_values[0]) # Assuming 'Record Index' is the first value
            print(f"DEBUG: Selected flagged record with original index: {record_index}")
        except (IndexError, ValueError) as e:
            print(f"DEBUG: Could not get valid record index from Treeview: {record_values}. Error: {e}")
            return

        if self.df is None or not (0 <= record_index < len(self.df)):
            print(f"DEBUG: DataFrame not loaded or invalid record index: {record_index}")
            # Clear image panels if record is invalid
            for key in self.image_display_labels:
                self._display_single_image(self.image_display_labels[key], None) # Display placeholder
            return

        record_data = self.df.iloc[record_index]

        # Display images
        for key, img_label_widget in self.image_display_labels.items():
            image_path_from_df = record_data.get(COLUMN_NAMES.get(key)) # Use .get(key) on COLUMN_NAMES too
            self._display_single_image(img_label_widget, image_path_from_df)

    def _display_single_image(self, image_label_widget, path_from_df):
        # Determine target size from the widget, if possible, else use default
        try:
            # Ensure widget is updated to get correct dimensions
            image_label_widget.update_idletasks()
            target_width = image_label_widget.winfo_width() - 10
            target_height = image_label_widget.winfo_height() - 10
        except tk.TclError: # Widget might not be mapped yet
            target_width, target_height = 200, 150 # Default/fallback size

        if target_width < 20 or target_height < 20: # Min size
            target_width, target_height = 200, 150

        full_path = None
        img_to_display = None

        try:
            if not path_from_df or pd.isna(path_from_df) or not str(path_from_df).strip():
                img_to_display = self._create_placeholder_image("No Path Provided", target_width, target_height)
            else:
                if not self.base_dir:
                    print("DEBUG: base_dir not set. Cannot resolve relative image paths.")
                    img_to_display = self._create_placeholder_image("Error: Base Directory Not Set", target_width, target_height)
                else:
                    full_path = os.path.join(self.base_dir, str(path_from_df).strip())
                    if os.path.exists(full_path) and os.path.isfile(full_path):
                        try:
                            img = Image.open(full_path)
                            img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                            img_to_display = img
                        except IOError:
                            img_to_display = self._create_placeholder_image(f"Cannot open image:\n{os.path.basename(full_path)}", target_width, target_height)
                    else:
                        img_to_display = self._create_placeholder_image(f"Image Not Found:\n{os.path.basename(full_path)}", target_width, target_height)
        except Exception as e:
            print(f"DEBUG: Unexpected error in _display_single_image for path '{path_from_df}': {type(e).__name__} - {e}")
            error_text = "Error Loading Image"
            if path_from_df and isinstance(path_from_df, str): # Check if path_from_df is a string
                error_text += f":\n{os.path.basename(str(path_from_df))}"
            img_to_display = self._create_placeholder_image(error_text, target_width, target_height)

        if img_to_display:
            tk_img = ImageTk.PhotoImage(img_to_display)
            image_label_widget.config(image=tk_img, width=target_width, height=target_height)
            image_label_widget.image = tk_img # Keep a reference!
        else: # Fallback
            placeholder = self._create_placeholder_image("Display Error", target_width, target_height)
            tk_img = ImageTk.PhotoImage(placeholder)
            image_label_widget.config(image=tk_img, width=target_width, height=target_height)
            image_label_widget.image = tk_img

    def _create_placeholder_image(self, text, width, height):
        # Ensure width and height are positive integers
        width = max(1, int(width))
        height = max(1, int(height))
        img = Image.new('RGB', (width, height), color="#404040") # Slightly different placeholder color
        draw = ImageDraw.Draw(img)
        try:
            font_size = max(10, int(min(width, height) / 8))
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        lines = []
        for paragraph in text.split('\n'):
            words = paragraph.split(' ')
            current_line = ""
            for word in words:
                if draw.textbbox((0,0), current_line + word, font=font)[2] <= width - 10: # 10px padding
                    current_line += (" " + word if current_line else word)
                else:
                    if current_line: lines.append(current_line)
                    current_line = word
            if current_line: lines.append(current_line)

        line_heights = [draw.textbbox((0,0), line, font=font)[3] - draw.textbbox((0,0), line, font=font)[1] for line in lines]
        total_text_height = sum(line_heights) + max(0, (len(lines) - 1) * 2)
        y_text = (height - total_text_height) / 2

        for i, line in enumerate(lines):
            line_bbox = draw.textbbox((0,0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            pos = ((width - line_width) / 2, y_text)
            draw.text(pos, line, fill="white", font=font, anchor="lt")
            y_text += line_heights[i] + 2
        return img

# Implement if __name__ == '__main__': block with argparse
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Data Quality Check Tool for Labeled Excel Files.")
    parser.add_argument("input_excel", nargs='?', default=None,
                        help="Path to the corrected Excel file to be analyzed.")
    args = parser.parse_args()

    app = AnalysisApp(args.input_excel)
    app.mainloop()
