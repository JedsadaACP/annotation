# Main script for data verification
import pandas as pd
from PIL import Image
import pytesseract
import re # For cleaning and license plate normalization
import os
from tqdm import tqdm
import concurrent.futures
import multiprocessing # To get cpu_count
import argparse

# Placeholder for Tesseract command path if needed, can be configured by user
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract' # Example for Linux
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Example for Windows

def load_excel_data(file_path: str) -> pd.DataFrame | None:
    """Loads data from an Excel file into a pandas DataFrame."""
    try:
        df = pd.read_excel(file_path)
        print(f"Successfully loaded Excel file: {file_path}")
        return df
    except FileNotFoundError:
        print(f"Error: Excel file not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error loading Excel file {file_path}: {e}")
        return None

def perform_ocr(image_path: str, lang: str = 'eng') -> str | None:
    """Performs OCR on an image and returns the extracted text."""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=lang)
        # print(f"OCR successful for {image_path} with lang {lang}. Text: '{text[:50]}...'") # Optional: for verbose logging
        return text.strip()
    except FileNotFoundError:
        # This case will be handled by checking os.path.exists before calling perform_ocr
        # print(f"Error: Image file not found at {image_path}")
        return None # Should be caught by pre-check
    except pytesseract.TesseractNotFoundError:
        print("Error: Tesseract is not installed or not found in your PATH.")
        print("Please install Tesseract OCR and ensure it's added to your system's PATH.")
        # This is a critical error, might need to halt execution or alert user more strongly.
        # For now, we'll let it propagate or be handled by the main loop.
        raise
    except Exception as e:
        print(f"Error during OCR for image {image_path}: {e}")
        return "" # Return empty string for other OCR errors (e.g., unreadable image by Tesseract)

def clean_text(text: str) -> str:
    """Cleans text by removing common unwanted characters like spaces and hyphens."""
    if not isinstance(text, str):
        return ""
    # Remove spaces, hyphens, and common OCR noise.
    # This can be expanded based on observed OCR output.
    cleaned_text = re.sub(r'[\s\-_]', '', text)
    return cleaned_text.upper() # Standardize to uppercase for comparison

def normalize_license_plate_number(text: str) -> str:
    """
    Normalizes extracted text to a standard license plate number format.
    Converts hyphens to commas, removes extra spaces, and converts to uppercase.
    Example: '740-699' becomes '740,699'. ' 74 - 699 ' becomes '74,699'.
    """
    if not isinstance(text, str):
        return ""

    # Convert to uppercase first for consistent processing
    processed_text = text.upper()
    # Replace hyphens with commas
    processed_text = processed_text.replace('-', ',')

    # Remove spaces around commas and ensure single comma.
    # This regex removes spaces around commas and reduces multiple commas to one.
    processed_text = re.sub(r'\s*,\s*', ',', processed_text)
    processed_text = re.sub(r',+', ',', processed_text) # Ensure single comma if multiple resulted

    # Remove all other spaces (e.g. within number blocks if any like "123 45")
    # This might be too aggressive if internal spaces in number blocks are possible and significant.
    # The examples "740,699" and "74,699" suggest numbers are contiguous.
    # So, removing all remaining spaces from parts might be okay.
    parts = processed_text.split(',')
    parts = [re.sub(r'\s+', '', part) for part in parts]
    final_text = ','.join(parts)

    return final_text.strip() # Final strip just in case

def extract_license_plate_province(text: str, thai_provinces: list = None) -> str:
    """
    Extracts province name from OCR text.
    This is a placeholder. Actual implementation might need a list of Thai provinces
    or more sophisticated NLP techniques if province is mixed with other text.
    For now, it assumes the province might be part of a larger text block and tries basic cleaning.
    The 'tha+eng' OCR should help in direct extraction if formatted well on the plate.
    """
    if not isinstance(text, str):
        return ""

    # Basic cleaning: remove digits, spaces, hyphens, and convert to uppercase.
    # This is a very naive approach. A better method would be to use a predefined list
    # of provinces and find the best match, or use NLP if text is complex.
    # For now, we assume the OCR for province is relatively clean.
    cleaned_province = re.sub(r'[\d\s\-]', '', text) # Remove digits, spaces, hyphens

    # If a list of known provinces is provided, try to find a match
    # This is a more robust approach but requires a list of provinces.
    if thai_provinces:
        # Simple matching (case-insensitive, space-insensitive)
        # This is a basic example; more sophisticated matching might be needed
        normalized_text = clean_text(text) # Use general clean_text for matching
        for province in thai_provinces:
            if clean_text(province) in normalized_text:
                return province
        # If no direct match, return the cleaned text as a fallback
        # This might not be ideal if there's a lot of noise.
        return cleaned_province.upper()

    return cleaned_province.upper() # Fallback to basic cleaned text

# Example usage (will be removed or commented out later):
# if __name__ == '__main__':
#     # Test load_excel_data (requires a dummy_test.xlsx file)
#     # df_test = load_excel_data('dummy_test.xlsx')
#     # if df_test is not None:
#     #     print(df_test.head())

#     # Test clean_text
#     print(f"Cleaned 'AB CD-123': {clean_text('AB CD-123')}")
#     print(f"Cleaned '  กรุงเทพมหานคร  ': {clean_text('  กรุงเทพมหานคร  ')}")

#     # Test normalize_license_plate_number
#     print(f"Normalized LP 'BC-1234': {normalize_license_plate_number('BC-1234')}")
#     print(f"Normalized LP '1กข 5678': {normalize_license_plate_number('1กข 5678')}")

#     # Test extract_license_plate_province (basic)
#     print(f"Extracted Province 'กรุงเทพมหานคร 123': {extract_license_plate_province('กรุงเทพมหานคร 123')}")
#     # Test with a hypothetical list of provinces
#     # sample_provinces = ["กรุงเทพมหานคร", "ชลบุรี", "เชียงใหม่"]
#     # print(f"Extracted Province 'Vehicle Plate Chiang Mai NB': {extract_license_plate_province('Vehicle Plate Chiang Mai NB', sample_provinces)}")
#     # print(f"Extracted Province 'รถสวย ชลบุรี': {extract_license_plate_province('รถสวย ชลบุรี', sample_provinces)}")


#     # Test perform_ocr (requires an image file, e.g., 'test_image.png' and Tesseract installed)
#     # Create a dummy image file for testing if you don't have one
#     # from PIL import Image, ImageDraw, ImageFont
#     # try:
#     #     img = Image.new('RGB', (400, 100), color = (255, 255, 255))
#     #     d = ImageDraw.Draw(img)
#     #     # Specify a font file that supports Thai characters if testing Thai OCR
#     #     # font = ImageFont.truetype("arial.ttf", 30) # Example, use a Thai font for Thai text
#     #     d.text((10,10), "HELLO WORLD 123", fill=(0,0,0)) #, font=font
#     #     img.save("test_ocr_image.png")
#     #     print(f"OCR from test_ocr_image.png: {perform_ocr('test_ocr_image.png', lang='eng')}")
#     # except ImportError:
#     #     print("Pillow is not installed. Skipping dummy image creation for OCR test.")
#     # except pytesseract.TesseractNotFoundError:
#     #     print("Tesseract not found. Skipping OCR test.")
#     # except Exception as e:
#     #     print(f"Error creating dummy image or running OCR test: {e}")

def process_row_wrapper(args):
    """
    Wrapper function to process a single row.
    Takes a tuple of arguments: (index, row_data, config)
    row_data should be a pandas Series or a dictionary.
    config should be a dictionary containing column names and other necessary parameters.
    Returns a dictionary with index and the corrected values.
    """
    index, row_data, config = args

    # Unpack config
    container_number_col = config['container_number_col']
    license_plate_number_col = config['license_plate_number_col']
    license_plate_province_col = config['license_plate_province_col']
    # New specific container image columns
    # left_camera_image_file_col = config['left_camera_image_file_col'] # Will be used in next step
    # right_camera_image_file_col = config['right_camera_image_file_col'] # Will be used in next step
    # top_camera_image_file_col = config['top_camera_image_file_col'] # Will be used in next step
    license_plate_image_file_col = config['license_plate_image_file_col'] # Updated name

    corrected_container_col = config['corrected_container_col']
    corrected_plate_number_col = config['corrected_plate_number_col']
    corrected_plate_province_col = config['corrected_plate_province_col']
    thai_provinces_list = config['thai_provinces_list']

    # Initialize results for this row
    # Must match the keys used when updating the DataFrame later
    row_results = {
        'index': index,
        corrected_container_col: '',
        corrected_plate_number_col: '',
        corrected_plate_province_col: ''
    }

    # 1. Container Number Verification (NEW MULTI-IMAGE LOGIC)
    excel_container_num_raw = str(row_data.get(config['container_number_col'], '')).strip()

    # These are the actual column names from the Excel header, e.g., "left_camera_image_file"
    container_image_cols_in_order = [
        config['left_camera_image_file_col'],
        config['right_camera_image_file_col'],
        config['top_camera_image_file_col']
    ]

    ocr_container_text_found = None
    any_image_exists = False
    all_found_images_unreadable = True # Assume initially true if images are found

    actual_image_paths_to_check = []
    for col_data_key in container_image_cols_in_order:
        path = str(row_data.get(col_data_key, '')).strip()
        if path: # Only consider non-empty paths from Excel
            actual_image_paths_to_check.append(path)

    if not actual_image_paths_to_check: # No paths provided in any of the designated columns
        row_results[config['corrected_container_col']] = '--'
    else:
        for image_path in actual_image_paths_to_check:
            if image_path and os.path.exists(image_path):
                any_image_exists = True # At least one listed path points to an existing file
                ocr_text = perform_ocr(image_path, lang='eng')
                if ocr_text: # Check if ocr_text is not None and not empty
                    ocr_container_text_found = ocr_text
                    all_found_images_unreadable = False # We found a readable one
                    break # Found a readable image, use this one
                # If ocr_text is None or empty, this image was unreadable. Loop continues.
            # If path is empty or file doesn't exist, it's skipped here.

        if not any_image_exists: # None of the provided paths (even if non-empty) led to an actual file
            row_results[config['corrected_container_col']] = '--'
        elif all_found_images_unreadable: # Images existed, but none were readable by OCR
            row_results[config['corrected_container_col']] = '-'
        elif ocr_container_text_found is not None: # A readable image was found and OCR text extracted
            cleaned_excel_container = clean_text(excel_container_num_raw)
            cleaned_ocr_container = clean_text(ocr_container_text_found)
            if cleaned_excel_container != cleaned_ocr_container:
                row_results[config['corrected_container_col']] = cleaned_ocr_container
            else:
                row_results[config['corrected_container_col']] = '' # Match, leave blank
        else:
            # This case implies any_image_exists was true, but all_found_images_unreadable was false,
            # yet ocr_container_text_found is None. This can happen if an image path exists,
            # but perform_ocr returns None (FileNotFound inside perform_ocr, though pre-checked here)
            # or returns "" (empty string for other OCR errors).
            # If an image existed but OCR yielded no usable text from any image.
            row_results[config['corrected_container_col']] = '-'
            # Add a print for debugging this unexpected state, if it occurs.
            # Using row_data.name (if available, typically DataFrame index) or a placeholder for row identification.
            row_identifier = row_data.name if hasattr(row_data, 'name') else f"Index_{index}"
            print(f"Warning: Row {row_identifier} entered unexpected state in container processing. Check image readability or paths.")

    # 2. License Plate Number and Province Verification
    plate_img_path = str(row_data.get(license_plate_image_file_col, '')).strip() # Use new key
    excel_lp_num = str(row_data.get(license_plate_number_col, '')).strip()
    excel_lp_prov = str(row_data.get(license_plate_province_col, '')).strip()

    if not plate_img_path or not os.path.exists(plate_img_path):
        row_results[corrected_plate_number_col] = '--'
        row_results[corrected_plate_province_col] = '--'
    else:
        ocr_plate_text = perform_ocr(plate_img_path, lang='tha+eng')
        if ocr_plate_text is None or ocr_plate_text == "":
            row_results[corrected_plate_number_col] = '-'
            row_results[corrected_plate_province_col] = '-'
        else:
            # License Plate Number
            excel_lp_num_raw = str(row_data.get(config['license_plate_number_col'], '')).strip()
            # For comparison, remove all separators from Excel data and convert to uppercase
            comp_excel_lp = re.sub(r'[^A-Z0-9]', '', excel_lp_num_raw.upper())

            # Assuming ocr_plate_text contains the text for the license plate.
            # This might need refinement if ocr_plate_text also contains province and needs splitting first.
            # For now, assume ocr_plate_text is primarily the license plate number or can be processed as such.
            raw_ocr_lp_text_from_image = ocr_plate_text # This is the text from perform_ocr for the plate image

            # For comparison, remove all separators from raw OCR data and convert to uppercase
            comp_ocr_lp = re.sub(r'[^A-Z0-9]', '', raw_ocr_lp_text_from_image.upper())

            # Format the OCR output according to the new rule (hyphen to comma, etc.) for storing if different
            formatted_ocr_lp_for_output = normalize_license_plate_number(raw_ocr_lp_text_from_image)

            if comp_excel_lp != comp_ocr_lp:
                # If they don't match after stripping all separators, store the comma-formatted OCR version
                row_results[config['corrected_plate_number_col']] = formatted_ocr_lp_for_output
            else:
                # If they match after stripping all separators, leave blank
                row_results[config['corrected_plate_number_col']] = ''

            # License Plate Province
            cleaned_excel_lp_prov = clean_text(excel_lp_prov)
            extracted_ocr_lp_prov = extract_license_plate_province(ocr_plate_text, thai_provinces_list)
            if cleaned_excel_lp_prov != extracted_ocr_lp_prov:
                row_results[corrected_plate_province_col] = extracted_ocr_lp_prov
            # else: stays blank

    return row_results

def process_data(excel_file_path: str, output_excel_path: str) -> None:
    """
    Main function to process the Excel data, verify against images, and save the output.
    Uses multiprocessing for faster OCR processing.
    """

    # --- Configuration: Column Names (Update these with actual column names from the Excel file) ---
    config = {
        'container_number_col': 'container_number',
        'license_plate_number_col': 'license_plate_number',
        'license_plate_province_col': 'license_plate_province',

        # New image column names
        'left_camera_image_file_col': 'left_camera_image_file',
        'right_camera_image_file_col': 'right_camera_image_file',
        'top_camera_image_file_col': 'top_camera_image_file',
        'license_plate_image_file_col': 'license_plate_image_file', # Renamed

        'corrected_container_col': 'corrected_container_number',
        'corrected_plate_number_col': 'corrected_license_plate_number',
        'corrected_plate_province_col': 'corrected_license_plate_province',
        'thai_provinces_list': None
    }
    # --- End Configuration ---

    df = load_excel_data(excel_file_path)
    if df is None:
        return

    # Initialize corrected columns if they don't exist
    for col_key in ['corrected_container_col', 'corrected_plate_number_col', 'corrected_plate_province_col']:
        col_name = config[col_key]
        if col_name not in df.columns:
            df[col_name] = ''

    # Prepare arguments for each row
    # We pass a copy of the row data to avoid potential issues with shared state if Series are mutable in some contexts across processes
    tasks_args = [(index, row.copy(), config) for index, row in df.iterrows()]

    # Determine number of workers
    # Use one less than total CPUs to leave resources for other system tasks, or os.cpu_count()
    num_workers = max(1, multiprocessing.cpu_count() - 1 if multiprocessing.cpu_count() > 1 else 1)
    print(f"Using {num_workers} worker processes for OCR.")

    results = []
    # Using ProcessPoolExecutor for CPU-bound tasks like OCR
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Use executor.map to process tasks, wrapped with tqdm for progress
        # map processes in order and returns results in order
        future_to_row = {executor.submit(process_row_wrapper, arg_set): arg_set[0] for arg_set in tasks_args}

        for future in tqdm(concurrent.futures.as_completed(future_to_row), total=len(tasks_args), desc="Processing records"):
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                row_index = future_to_row[future]
                print(f"WARNING: Processing failed for row index {row_index} due to an error: '{exc}'. This row's corrected fields may be incomplete. Please check console output for details if errors persist.")
                # Optionally, mark these rows with an error status in the DataFrame
                # For now, we just print the error and the row might not get its values updated correctly or at all
                # depending on where the error occurred in process_row_wrapper.

    # Update DataFrame with results
    # It's important to update by index to ensure correctness, especially if results are out of order
    # (though ProcessPoolExecutor.map returns them in order, as_completed does not)
    print("Updating DataFrame with processed results...")
    for res_item in tqdm(results, desc="Updating DataFrame"):
        idx = res_item['index']
        for col_key in ['corrected_container_col', 'corrected_plate_number_col', 'corrected_plate_province_col']:
            col_name = config[col_key]
            # Ensure the column exists, though it should have been initialized
            if col_name not in df.columns:
                df[col_name] = pd.NA # Or some default
            df.loc[idx, col_name] = res_item[col_name]

    # Save the updated DataFrame
    try:
        df.to_excel(output_excel_path, index=False)
        print(f"Processing complete. Output saved to: {output_excel_path}")
    except Exception as e:
        print(f"Error saving Excel file {output_excel_path}: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Automated Data Verification Tool")
    parser.add_argument("input_excel",
                        help="Path to the input Excel file containing data to verify.")
    parser.add_argument("-o", "--output_excel",
                        default="corrected_output.xlsx",
                        help="Path to save the corrected output Excel file (default: corrected_output.xlsx).")
    # Optional: Add argument for Tesseract path if needed frequently
    # parser.add_argument("--tesseract_path",
    #                     help="Path to the Tesseract OCR executable, if not in system PATH.")

    args = parser.parse_args()

    # Optional: Configure Tesseract path if provided
    # if args.tesseract_path:
    #     pytesseract.pytesseract.tesseract_cmd = args.tesseract_path
    #     print(f"Using Tesseract OCR from: {args.tesseract_path}")


    print("Starting Data Verification Process...")

    input_file_path = args.input_excel
    output_file_path = args.output_excel

    # Example: Check if a dummy input file exists, if not, create one for basic testing
    # This behavior might be revised: typically a script expects the input file to exist.
    # For this project, creating a dummy if not found can help first-time users.
    if not os.path.exists(input_file_path):
        print(f"Warning: Input file '{input_file_path}' not found.")
        print(f"Creating a dummy '{input_file_path}' for testing purposes with expected column headers.")
        print(f"Please replace '{input_file_path}' with your actual data file and ensure image paths are correct.")

        # --- Configuration: Column Names (Must match those in process_data and process_row_wrapper) ---
        # This needs to be consistent with how process_data expects them or pass them around.
        # For simplicity, let's use the same default names here for the dummy file.
        # These should ideally align with the main config keys if used beyond dummy creation.
        container_number_col_name = 'container_number' # Or fetch from a global config if defined
        license_plate_number_col_name = 'license_plate_number'
        license_plate_province_col_name = 'license_plate_province'

        # New image path columns for dummy data
        left_camera_col_name = 'left_camera_image_file'
        right_camera_col_name = 'right_camera_image_file'
        top_camera_col_name = 'top_camera_image_file'
        license_plate_image_col_name = 'license_plate_image_file'
        # --- End Configuration ---

        dummy_data = {
            container_number_col_name: ["CN123", "CN456"],
            license_plate_number_col_name: ["AB1234", "CD5678"], # Will be updated later for new format
            license_plate_province_col_name: ["ProvinceA", "ProvinceB"],
            left_camera_col_name: ["path/to/left_container1.jpg", "path/to/nonexistent_left.jpg"],
            right_camera_col_name: ["path/to/right_container1.jpg", "path/to/nonexistent_right.jpg"],
            top_camera_col_name: ["path/to/top_container1.jpg", "path/to/nonexistent_top.jpg"],
            license_plate_image_col_name: ["path/to/plate1.jpg", "path/to/nonexistent_plate.jpg"]
        }
        dummy_df = pd.DataFrame(dummy_data)
        try:
            dummy_df.to_excel(input_file_path, index=False)
            print(f"Dummy '{input_file_path}' created. Please populate it with actual data and image paths.")
        except Exception as e:
            print(f"Could not create dummy input file: {e}")

    # Check for Tesseract installation before starting full processing
    try:
        tesseract_version = pytesseract.get_tesseract_version()
        print(f"Found Tesseract OCR version: {tesseract_version}")
    except pytesseract.TesseractNotFoundError:
        print("CRITICAL: Tesseract OCR is not installed or not found in your PATH.")
        print("The program cannot proceed without Tesseract. Please install it and try again.")
        print("If Tesseract is installed but not in PATH, you might need to set the path explicitly in the script ")
        print("near the top, where `pytesseract.pytesseract.tesseract_cmd` is mentioned.")
        exit()
    except Exception as e:
        print(f"An error occurred while checking Tesseract version: {e}")
        # Decide if to exit or continue if version check fails for other reasons

    process_data(input_file_path, output_file_path)
    print("Data Verification Process Finished.")
