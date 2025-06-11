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
    Example: Keeps alphanumeric characters, potentially formats to XX-XXXX.
    This is a basic version and might need enhancement based on actual OCR output.
    """
    if not isinstance(text, str):
        return ""

    # Remove spaces and hyphens first
    cleaned_text = re.sub(r'[\s\-]', '', text)

    # Further specific cleaning for license plates if needed (e.g., remove special chars not part of plates)
    # For now, just return the cleaned alphanumeric string in uppercase
    # This function will primarily be used for the license_plate_number part
    return cleaned_text.upper()

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
    container_image_path_col = config['container_image_path_col']
    plate_image_path_col = config['plate_image_path_col']
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

    # 1. Container Number Verification
    container_img_path = str(row_data.get(container_image_path_col, '')).strip()
    excel_container_num = str(row_data.get(container_number_col, '')).strip()

    if not container_img_path or not os.path.exists(container_img_path):
        row_results[corrected_container_col] = '--'
    else:
        ocr_container_text = perform_ocr(container_img_path, lang='eng')
        if ocr_container_text is None or ocr_container_text == "":
            row_results[corrected_container_col] = '-'
        else:
            cleaned_excel_container = clean_text(excel_container_num)
            cleaned_ocr_container = clean_text(ocr_container_text)
            if cleaned_excel_container != cleaned_ocr_container:
                row_results[corrected_container_col] = cleaned_ocr_container
            # else: stays blank (already initialized)

    # 2. License Plate Number and Province Verification
    plate_img_path = str(row_data.get(plate_image_path_col, '')).strip()
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
            normalized_excel_lp_num = normalize_license_plate_number(excel_lp_num)
            normalized_ocr_lp_num = normalize_license_plate_number(ocr_plate_text) # Simplified
            if normalized_excel_lp_num != normalized_ocr_lp_num:
                row_results[corrected_plate_number_col] = normalized_ocr_lp_num
            # else: stays blank

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
        'container_image_path_col': 'container_image_path',
        'plate_image_path_col': 'plate_image_path',
        'corrected_container_col': 'corrected_container_number',
        'corrected_plate_number_col': 'corrected_license_plate_number',
        'corrected_plate_province_col': 'corrected_license_plate_province',
        # Optional: Predefined list of Thai provinces for more accurate province extraction
        # 'thai_provinces_list': ["กรุงเทพมหานคร", "ชลบุรี", "เชียงใหม่", ...]
        'thai_provinces_list': None # Set to None if not used or provide a list
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
                print(f'Row {row_index} generated an exception: {exc}')
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
        container_number_col = 'container_number'
        license_plate_number_col = 'license_plate_number'
        license_plate_province_col = 'license_plate_province'
        container_image_path_col = 'container_image_path'
        plate_image_path_col = 'plate_image_path'
        # --- End Configuration ---

        dummy_data = {
            container_number_col: ["CN123", "CN456"],
            license_plate_number_col: ["AB1234", "CD5678"],
            license_plate_province_col: ["ProvinceA", "ProvinceB"],
            container_image_path_col: ["path/to/container1.jpg", "path/to/nonexistent_container.jpg"],
            plate_image_path_col: ["path/to/plate1.jpg", "path/to/nonexistent_plate.jpg"]
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
