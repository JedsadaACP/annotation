import tkinter as tk
from tkinter import font as tkFont
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import pandas as pd
import os
import argparse

# --- 1. CONFIGURATION ---
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

# --- 2. THE MAIN APPLICATION CLASS ---
class VerificationApp(tk.Tk):
    def __init__(self, excel_path):
        super().__init__()

        self.title("Manual Verification Helper v3.0 (Portable & Enhanced)")
        self.geometry("1366x768")
        self.configure(bg="#2E2E2E")

        self.input_file_path = excel_path
        self.base_dir = os.path.dirname(os.path.abspath(excel_path))
        self.output_file_path = self.generate_output_filename(excel_path)

        self.df = None
        self.load_data()

        if self.df is None:
            self.destroy()
            return

        self.total_records = len(self.df)
        self.current_index = self.find_first_unprocessed_row()
        self.corrections = self.load_existing_corrections()

        self.setup_styles()
        self.create_widgets()
        self.load_record(self.current_index)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def generate_output_filename(self, input_path):
        name, ext = os.path.splitext(input_path)
        if name.endswith("_corrected"):
            return input_path
        return f"{name}_corrected{ext}"

    def load_data(self):
        print("DEBUG: Entered load_data()")
        file_to_load = self.input_file_path
        use_resume_file = False # Initialize to default
        if os.path.exists(self.output_file_path):
            print(f"DEBUG: Found potential resume file: {self.output_file_path}")
            print("DEBUG: About to ask to resume via messagebox.")
            # The result of askyesno directly determines if we change file_to_load and set use_resume_file
            resume_response = messagebox.askyesno("Resume Session",
                                   f"Found previous work in '{os.path.basename(self.output_file_path)}'.\n\nDo you want to resume from where you left off?")
            print(f"DEBUG: messagebox.askyesno result: {resume_response}")
            if resume_response: # True if user clicks "Yes"
                file_to_load = self.output_file_path
                use_resume_file = True
            # If user clicks "No", file_to_load remains self.input_file_path and use_resume_file remains False

        try:
            print(f"DEBUG: Attempting to load Excel file: {file_to_load}")
            dtype_map = {col: str for col in COLUMN_NAMES.values()}
            self.df = pd.read_excel(file_to_load, dtype=dtype_map)
            print(f"DEBUG: Successfully loaded {file_to_load}. DataFrame shape: {self.df.shape}")
            self.df.columns = self.df.columns.str.strip()

            if not use_resume_file:
                 for col_type in ['corrected_container', 'corrected_license_plate', 'corrected_province']:
                    col_name = COLUMN_NAMES[col_type]
                    if col_name not in self.df.columns:
                        self.df[col_name] = ""

            self.df = self.df.fillna('')
            print("DEBUG: Exiting load_data() successfully")

        except FileNotFoundError:
            print(f"DEBUG: Exception in load_data: FileNotFoundError - Input file not found:\n{file_to_load}")
            messagebox.showerror("Error", f"Input file not found:\n{file_to_load}")
            self.df = None
        except Exception as e:
            print(f"DEBUG: Exception in load_data: {type(e).__name__} - {e}")
            messagebox.showerror("Error", f"Could not read Excel file. Error:\n{e}")
            self.df = None

    def find_first_unprocessed_row(self):
        print("DEBUG: Entered find_first_unprocessed_row()")
        corr_cols = [
            COLUMN_NAMES['corrected_container'],
            COLUMN_NAMES['corrected_license_plate'],
            COLUMN_NAMES['corrected_province']
        ]
        # Ensure columns exist before trying to filter on them
        for col in corr_cols:
            if col not in self.df.columns:
                # If a correction column is missing entirely, it implies no records are processed for it.
                # This could happen if loading an original file that never had these columns.
                # The load_data method tries to add them if not use_resume_file.
                # If they are still missing, it's safer to start from 0.
                print(f"DEBUG: Exiting find_first_unprocessed_row(), returning index: 0 (missing column: {col})")
                return 0

        print(f"DEBUG: Columns checked. DataFrame shape: {self.df.shape}")
        # Proceed only if all expected correction columns are present
        unprocessed_conditions = []
        for col in corr_cols:
            unprocessed_conditions.append(self.df[col] == '')

        if not unprocessed_conditions: # Should not happen if corr_cols is not empty
            return 0

        # Combine conditions using logical AND
        combined_condition = unprocessed_conditions[0]
        for cond in unprocessed_conditions[1:]:
            combined_condition &= cond

        unprocessed = self.df[combined_condition]

        if not unprocessed.empty:
            index_value = unprocessed.index[0]
            print(f"DEBUG: Exiting find_first_unprocessed_row(), returning index: {index_value}")
            return index_value
        print(f"DEBUG: Exiting find_first_unprocessed_row(), returning index: 0 (no unprocessed records or empty df)")
        return 0 # Default to 0 if all records are processed or if df is empty

    def load_existing_corrections(self):
        print("DEBUG: Entered load_existing_corrections()")
        corrections = {}
        # Define keys for correction data to check if they exist in the DataFrame
        correction_keys_to_check = [
            COLUMN_NAMES['corrected_container'],
            COLUMN_NAMES['corrected_license_plate'],
            COLUMN_NAMES['corrected_province']
        ]

        for index, row in self.df.iterrows():
            # Ensure all correction columns exist in the row before trying to access them
            # This guards against errors if the DataFrame schema is unexpected
            if not all(key in row for key in correction_keys_to_check):
                # If essential correction columns are missing, skip this row for corrections loading
                # or handle as an error/default state. For now, skipping.
                continue

            correction_data = {
                'container': row.get(COLUMN_NAMES['corrected_container'], ''),
                'license_plate': row.get(COLUMN_NAMES['corrected_license_plate'], ''),
                'province': row.get(COLUMN_NAMES['corrected_province'], '')
            }
            if any(val for val in correction_data.values() if val): # Check if any value is non-empty
                 corrections[index] = correction_data
        print(f"DEBUG: Finished iterating rows for corrections. Number of corrections loaded: {len(corrections)}")
        print("DEBUG: Exiting load_existing_corrections()")
        return corrections

    def setup_styles(self):
        self.header_font = tkFont.Font(family="Segoe UI", size=16, weight="bold")
        self.label_font = tkFont.Font(family="Segoe UI", size=11)
        self.data_font = tkFont.Font(family="Segoe UI", size=12, weight="bold")
        self.entry_font = tkFont.Font(family="Consolas", size=12)
        self.button_font = tkFont.Font(family="Segoe UI", size=11, weight="bold")
        self.small_font = tkFont.Font(family="Segoe UI", size=9)
        self.copy_btn_font = tkFont.Font(family="Segoe UI", size=11)

    def create_widgets(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.progress_label = tk.Label(self, text="", font=self.header_font, fg="white", bg="#2E2E2E", pady=10)
        self.progress_label.grid(row=0, column=0, sticky="ew")
        content_frame = tk.Frame(self, bg="#2E2E2E")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content_frame.grid_columnconfigure(1, weight=1) # Allow image frame to expand
        data_frame = tk.Frame(content_frame, bg="#2E2E2E", width=400) # Fixed width for data
        data_frame.grid(row=0, column=0, sticky="ns", padx=(0, 20))
        data_frame.grid_propagate(False) # Prevent data_frame from shrinking/growing with content
        image_frame = tk.Frame(content_frame, bg="#2E2E2E")
        image_frame.grid(row=0, column=1, sticky="nsew")

        self.create_data_section(data_frame)
        self.create_image_section(image_frame)
        self.create_navigation_section()

    def create_data_section(self, parent):
        self.data_labels = {}
        self.entry_boxes = {}
        fields = ["container", "license_plate", "province"]
        field_titles = ["Container Number", "License Plate Number", "License Plate Province"]

        for i, (field, title) in enumerate(zip(fields, field_titles)):
            frame = tk.Frame(parent, bg="#3c3c3c", bd=1, relief=tk.SOLID)
            frame.pack(fill=tk.X, pady=10, anchor="n") # Use pack for vertical layout

            tk.Label(frame, text=f"Original {title}:", font=self.label_font, fg="#B0B0B0", bg="#3c3c3c").pack(anchor="w", padx=10, pady=(5,0))

            original_frame = tk.Frame(frame, bg="#3c3c3c")
            original_frame.pack(fill=tk.X, padx=10, pady=(0, 5)) # Reduced bottom padding
            data_label = tk.Label(original_frame, text="N/A", font=self.data_font, fg="white", bg="#3c3c3c", wraplength=320, justify=tk.LEFT) # Adjusted wraplength
            data_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.data_labels[field] = data_label

            copy_button = tk.Button(original_frame, text="📋", font=self.copy_btn_font, command=lambda f=field: self.copy_to_entry(f), relief=tk.FLAT, bg="#3c3c3c", fg="white", activebackground="#555555", width=2)
            copy_button.pack(side=tk.RIGHT, padx=(0,5)) # Align to right, add padding

            tk.Label(frame, text=f"Enter Correction:", font=self.label_font, fg="#B0B0B0", bg="#3c3c3c").pack(anchor="w", padx=10, pady=(5,0))
            entry = tk.Entry(frame, font=self.entry_font, bg="#2E2E2E", fg="white", insertbackground="white", relief=tk.FLAT, width=38) # Adjusted width
            entry.pack(anchor="w", padx=10, pady=(0,10), ipady=4)
            self.entry_boxes[field] = entry

        quick_fill_frame = tk.Frame(parent, bg="#3c3c3c", bd=1, relief=tk.SOLID)
        quick_fill_frame.pack(fill=tk.X, pady=5, anchor="n")
        btn_style = {'font': self.small_font, 'relief': tk.FLAT, 'fg': 'white', 'activebackground': '#555', 'pady': 2, 'padx':5}
        tk.Label(quick_fill_frame, text="Quick Actions:", font=self.label_font, fg="#B0B0B0", bg="#3c3c3c").pack(side=tk.LEFT, padx=10)
        tk.Button(quick_fill_frame, text="Mark Illegible (-)", bg="#795548", command=lambda: self.quick_fill('-'), **btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(quick_fill_frame, text="Mark Missing (--)", bg="#f44336", command=lambda: self.quick_fill('--'), **btn_style).pack(side=tk.LEFT, padx=3)

    def copy_to_entry(self, field):
        original_text = self.data_labels[field].cget("text")
        if original_text != "N/A" and original_text: # Ensure not empty
            self.entry_boxes[field].delete(0, tk.END)
            self.entry_boxes[field].insert(0, original_text)

    def quick_fill(self, symbol):
        # Only fill license plate and province with quick fill for now
        if 'license_plate' in self.entry_boxes:
            self.entry_boxes['license_plate'].delete(0, tk.END)
            self.entry_boxes['license_plate'].insert(0, symbol)
        if 'province' in self.entry_boxes:
            self.entry_boxes['province'].delete(0, tk.END)
            self.entry_boxes['province'].insert(0, symbol)
        # Optionally, fill container too or make it selective
        # self.entry_boxes['container'].delete(0, tk.END)
        # self.entry_boxes['container'].insert(0, symbol)


    def create_image_section(self, parent):
        self.image_labels = {}
        image_keys = ["top_img", "left_img", "right_img", "plate_img"]
        for i, key in enumerate(image_keys):
            row, col = divmod(i, 2)
            frame = tk.Frame(parent, bg="#2E2E2E", bd=1, relief=tk.SOLID) # Added border for clarity
            frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            parent.grid_rowconfigure(row, weight=1)
            parent.grid_columnconfigure(col, weight=1)
            img_label = tk.Label(frame, bg="#2E2E2E") # Darker background for image area
            img_label.pack(fill=tk.BOTH, expand=True)
            self.image_labels[key] = img_label

    def create_navigation_section(self):
        nav_frame = tk.Frame(self, bg="#2E2E2E", pady=10)
        nav_frame.grid(row=2, column=0, sticky="ew", padx=20)

        self.back_button = tk.Button(nav_frame, text="<< Go Back", command=self.prev_record_event, bg="#555555", font=self.button_font, fg="white", relief=tk.FLAT, padx=10, pady=5)
        self.back_button.pack(side=tk.LEFT, padx=(0,10))

        goto_frame = tk.Frame(nav_frame, bg="#2E2E2E")
        goto_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, anchor="center") # Center the goto section

        tk.Label(goto_frame, text="Go to Record:", font=self.small_font, fg="#B0B0B0", bg="#2E2E2E").pack(side=tk.LEFT, padx=(0, 5))
        self.goto_entry = tk.Entry(goto_frame, font=self.entry_font, bg="#4F4F4F", fg="white", relief=tk.FLAT, width=8, justify='center')
        self.goto_entry.pack(side=tk.LEFT, ipady=2)
        self.goto_entry.bind('<Return>', self.goto_record_event)
        goto_button = tk.Button(goto_frame, text="Go", command=self.goto_record_event, bg="#4A90E2", font=self.button_font, fg="white", relief=tk.FLAT, padx=10, pady=5)
        goto_button.pack(side=tk.LEFT, padx=5)

        right_nav_frame = tk.Frame(nav_frame, bg="#2E2E2E") # Frame to hold next button and label
        right_nav_frame.pack(side=tk.RIGHT, padx=(10,0))
        self.next_button = tk.Button(right_nav_frame, text="Save and Next >>", command=self.next_record_event, bg="#4CAF50", font=self.button_font, fg="white", relief=tk.FLAT, padx=10, pady=5)
        self.next_button.pack(side=tk.LEFT)
        tk.Label(right_nav_frame, text="(Press Enter)", font=self.small_font, fg="#B0B0B0", bg="#2E2E2E").pack(side=tk.LEFT, padx=(5,0))

        self.bind('<Return>', self.next_record_event) # Global Enter key binding
        print("DEBUG: Global <Return> key bound to self.next_record_event")

    def load_record(self, index_to_load):
        if not (0 <= index_to_load < self.total_records):
            # print(f"Attempted to load invalid index: {index_to_load}")
            return

        self.current_index = index_to_load
        self.progress_label.config(text=f"Record {self.current_index + 1} / {self.total_records}")

        record = self.df.iloc[self.current_index]

        self.data_labels['container'].config(text=record.get(COLUMN_NAMES['container'], 'N/A') or 'N/A')
        self.data_labels['license_plate'].config(text=record.get(COLUMN_NAMES['license_plate'], 'N/A') or 'N/A')
        self.data_labels['province'].config(text=record.get(COLUMN_NAMES['province'], 'N/A') or 'N/A')

        saved_correction = self.corrections.get(self.current_index, {})

        self.entry_boxes['container'].delete(0, tk.END)
        self.entry_boxes['container'].insert(0, saved_correction.get('container', ''))

        # --- MODIFIED LOGIC FOR LICENSE PLATE AND PROVINCE ---
        plate_image_path_from_excel = record.get(COLUMN_NAMES['plate_img'])
        plate_image_exists = False
        if plate_image_path_from_excel and not pd.isna(plate_image_path_from_excel) and str(plate_image_path_from_excel).strip():
            plate_image_full_path = os.path.join(self.base_dir, str(plate_image_path_from_excel).strip())
            if os.path.exists(plate_image_full_path):
                plate_image_exists = True

        current_lp_correction = saved_correction.get('license_plate', '')
        self.entry_boxes['license_plate'].delete(0, tk.END)
        if not plate_image_exists and not current_lp_correction:
            self.entry_boxes['license_plate'].insert(0, "--")
        else:
            self.entry_boxes['license_plate'].insert(0, current_lp_correction)

        current_prov_correction = saved_correction.get('province', '')
        self.entry_boxes['province'].delete(0, tk.END)
        if not plate_image_exists and not current_prov_correction:
            self.entry_boxes['province'].insert(0, "--")
        else:
            self.entry_boxes['province'].insert(0, current_prov_correction)
        # --- END OF MODIFIED LOGIC ---

        for key, label in self.image_labels.items():
            path_from_excel = record.get(COLUMN_NAMES[key])
            self.display_image(label, path_from_excel)

        self.back_button.config(state=tk.NORMAL if self.current_index > 0 else tk.DISABLED)
        self.next_button.config(text="Save and Next >>" if self.current_index < self.total_records - 1 else "Save and Finish")

        if 'container' in self.entry_boxes: # Ensure focus target exists
            self.entry_boxes['container'].focus_set()
            print(f"DEBUG: Focus set to container entry. Current focus: {self.focus_get()}")

        print(f"DEBUG: State of 'container' entry box: {self.entry_boxes['container'].cget('state')}")
        print(f"DEBUG: State of 'license_plate' entry box: {self.entry_boxes['license_plate'].cget('state')}")
        print(f"DEBUG: State of 'province' entry box: {self.entry_boxes['province'].cget('state')}")

    def save_current_record(self):
        print("DEBUG: Entered save_current_record")
        if self.current_index is None or not (0 <= self.current_index < self.total_records):
            print("DEBUG: Exiting save_current_record (invalid index or no record)")
            return # No valid record to save

        self.corrections[self.current_index] = {
            'container': self.entry_boxes['container'].get(),
            'license_plate': self.entry_boxes['license_plate'].get(),
            'province': self.entry_boxes['province'].get()
        }
        print(f"DEBUG: Corrections updated for index {self.current_index}: {self.corrections[self.current_index]}")
        print("DEBUG: Exiting save_current_record")

    def next_record_event(self, event=None):
        print(f"DEBUG: next_record_event triggered. Event: {event}")
        print("DEBUG: next_record_event calling self.save_current_record()")
        self.save_current_record()
        print("DEBUG: next_record_event returned from self.save_current_record()")
        if self.current_index + 1 < self.total_records:
            print(f"DEBUG: next_record_event attempting to load record index {self.current_index + 1}")
            self.load_record(self.current_index + 1)
        else:
            # If on the last record, ask_confirmation should ideally be False if "Save and Finish" implies auto-save.
            # However, current on_closing always asks if True by default.
            # For "Save and Finish", we want to save and exit without re-asking.
            print("DEBUG: next_record_event calling self.on_closing for last record")
            self.on_closing(ask_confirmation=False)
        print("DEBUG: Exiting next_record_event")


    def prev_record_event(self):
        if self.current_index > 0:
            self.save_current_record() # Save before moving
            self.load_record(self.current_index - 1)

    def goto_record_event(self, event=None):
        try:
            target_record_str = self.goto_entry.get()
            if not target_record_str: # Handle empty input
                messagebox.showwarning("Invalid Input", "Please enter a record number.")
                return
            target_record = int(target_record_str)
            target_index = target_record - 1
            if 0 <= target_index < self.total_records:
                self.save_current_record() # Save before jumping
                self.load_record(target_index)
            else:
                messagebox.showwarning("Invalid Record", f"Please enter a number between 1 and {self.total_records}.")
        except ValueError: # Catch if int() conversion fails
            messagebox.showwarning("Invalid Input", "Please enter a valid number.")
        finally:
            self.goto_entry.delete(0, tk.END)

    def display_image(self, label, path_from_excel):
        target_width, target_height = label.master.winfo_width() -10, label.master.winfo_height() -10 # Use label frame size
        if target_width < 50 or target_height < 50 : # Fallback if frame size not determined yet
            target_width, target_height = 450,300


        full_path = None
        try:
            img_to_display = None
            if not path_from_excel or pd.isna(path_from_excel) or not str(path_from_excel).strip():
                img_to_display = self.create_placeholder_image("No Path in Excel", target_width, target_height)
            else:
                full_path = os.path.join(self.base_dir, str(path_from_excel).strip())
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    try:
                        img = Image.open(full_path)
                        img.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                        img_to_display = img
                    except IOError: # Catch errors like "cannot identify image file"
                         img_to_display = self.create_placeholder_image(f"Cannot open image:\n{os.path.basename(full_path)}", target_width, target_height)
                else:
                    img_to_display = self.create_placeholder_image(f"Image Not Found:\n{os.path.basename(full_path)}", target_width, target_height)

        except Exception as e:
            # print(f"Unexpected error displaying image '{full_path}': {e}")
            error_text = "Error Loading Image"
            if full_path:
                error_text += f":\n{os.path.basename(full_path)}"
            img_to_display = self.create_placeholder_image(error_text, target_width, target_height)

        if img_to_display:
            tk_img = ImageTk.PhotoImage(img_to_display)
            label.config(image=tk_img, width=target_width, height=target_height) # Set size for label
            label.image = tk_img # Keep a reference!
        else: # Should not happen if logic is correct, but as a fallback:
            placeholder = self.create_placeholder_image("Fallback Error", target_width, target_height)
            tk_img = ImageTk.PhotoImage(placeholder)
            label.config(image=tk_img, width=target_width, height=target_height)
            label.image = tk_img


    def create_placeholder_image(self, text, width, height):
        img = Image.new('RGB', (int(width), int(height)), color="#303030") # Darker placeholder
        draw = ImageDraw.Draw(img)
        try:
            font_size = max(12, int(min(width, height) / 10)) # Dynamic font size
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        lines = []
        max_chars_per_line = int(width / (font_size * 0.5)) # Estimate

        # Improved text wrapping
        for paragraph in text.split('\n'): # Handle explicit newlines
            words = paragraph.split(' ')
            current_line = ""
            for word in words:
                if draw.textbbox((0,0), current_line + word, font=font)[2] <= width - 20: # Check width
                    current_line += (" " + word if current_line else word)
                else:
                    if current_line: lines.append(current_line)
                    current_line = word
            if current_line: lines.append(current_line) # Add last line of paragraph

        total_text_height = sum(draw.textbbox((0,0), line, font=font)[3] - draw.textbbox((0,0), line, font=font)[1] for line in lines)
        y_text = (height - total_text_height) / 2

        for line in lines:
            line_bbox = draw.textbbox((0,0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            line_height = line_bbox[3] - line_bbox[1]
            pos = ((width - line_width) / 2, y_text)
            draw.text(pos, line, fill="white", font=font, anchor="lt") # Left-top anchor
            y_text += line_height + 2 # spacing
        return img

    def on_closing(self, ask_confirmation=True):
        if ask_confirmation:
            if not messagebox.askyesno("Quit", "Do you want to save your work before quitting?"):
                self.destroy() # Destroy window without saving if user says no to saving
                return
        # If ask_confirmation is False, or if user said Yes to saving:
        self.save_and_exit()


    def save_and_exit(self):
        self.save_current_record() # Ensure last record is saved

        # Apply all corrections from self.corrections to self.df
        if self.df is not None and not self.df.empty:
            for index, correction_data in self.corrections.items():
                if index in self.df.index: # Check if index is valid
                    self.df.loc[index, COLUMN_NAMES['corrected_container']] = correction_data['container']
                    self.df.loc[index, COLUMN_NAMES['corrected_license_plate']] = correction_data['license_plate']
                    self.df.loc[index, COLUMN_NAMES['corrected_province']] = correction_data['province']

            try:
                # Make sure output_file_path is absolute or correctly relative
                abs_output_path = os.path.abspath(self.output_file_path)
                self.df.to_excel(abs_output_path, index=False)
                messagebox.showinfo("Save Successful", f"Work saved to:\n{abs_output_path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save the file to '{abs_output_path}'. Error:\n{e}")
        else:
            messagebox.showwarning("Save Warning", "No data to save or DataFrame is not loaded.")

        self.destroy()

# --- 3. SCRIPT EXECUTION ---
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Manual Verification Helper v3.0 (Portable & Enhanced)")
    # Make input_excel optional to allow testing without command line args if needed
    parser.add_argument("input_excel", nargs='?', default=None, help="Path to the input Excel file. If not provided, a demo mode or file dialog could be initiated (not implemented).")
    args = parser.parse_args()

    if args.input_excel is None:
        # Fallback or error if no input file is provided
        # For now, let's try to ask the user for a file if not given
        from tkinter import filedialog
        input_excel_path = filedialog.askopenfilename(
            title="Select Input Excel File",
            filetypes=(("Excel files", "*.xlsx *.xls"), ("All files", "*.*"))
        )
        if not input_excel_path:
            # print("No input file selected. Exiting.")
            messagebox.showerror("Error", "No input Excel file selected. Application will now close.")
            exit() # Exit if no file chosen from dialog
    else:
        input_excel_path = args.input_excel
        if not os.path.exists(input_excel_path):
            messagebox.showerror("Error", f"Input file not found:\n{input_excel_path}\nApplication will now close.")
            exit()


    app = VerificationApp(input_excel_path)
    app.mainloop()
