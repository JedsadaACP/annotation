# Automated Data Verification Tool

## Objective
This Python tool automates the manual verification and correction of data extracted by an AI system. It compares data in an Excel file against corresponding source images, aiming for 100% accuracy in the final dataset by applying a set of predefined correction rules.

## Features
*   **Excel Processing:** Reads data from `.xlsx` files using `pandas`.
*   **OCR Integration:** Uses `pytesseract` (with Tesseract OCR engine) to extract text from images.
    *   Supports English (`eng`) for general text (e.g., container numbers).
    *   Supports Thai and English (`tha+eng`) for license plates.
*   **Rule-Based Verification:** Automatically applies specific rules for data correction (see "Output Rules" and "Special Handling & Business Logic" below).
*   **Intelligent Comparison:** Cleans and normalizes text before comparison (e.g., removing spaces, standardizing case, specific transformations for license plates).
*   **Multiprocessing:** Utilizes multiple CPU cores to significantly speed up the OCR process for large datasets.
*   **Command-Line Interface:** Allows specifying input and output files via CLI arguments using `argparse`.
*   **Output Generation:** Saves results to a new Excel file with original data and added "corrected" columns.

## Requirements

### 1. Python
*   Python 3.7 or higher.

### 2. Tesseract OCR Engine
This is crucial for the script to function.
*   **Installation:** Tesseract OCR must be installed on your system and accessible via your system's PATH environment variable.
    *   **Windows:** Download installer from [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). During installation, **make sure to select additional language data (Thai)**.
    *   **macOS:** `brew install tesseract tesseract-lang` (this should include common languages; verify Thai is included or install separately).
    *   **Linux (Debian/Ubuntu):** `sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-tha`
*   **Language Packs:** Ensure you have installed the language packs for English (`eng`) and Thai (`tha`).
*   **Verification:** After installation, try running `tesseract --version` in your terminal. If this command is not found, Tesseract is not correctly installed or not in your PATH.

### 3. Python Libraries
Install these using pip:
```bash
pip install -r requirements.txt
```
The `requirements.txt` file includes:
*   `pandas`
*   `pytesseract`
*   `Pillow`
*   `tqdm`

## Expected Input Excel Structure
The script expects your input Excel file (e.g., `input.xlsx`) to have specific column names. The default column names used by the script are:

*   **Data to Verify:**
    *   `container_number`
    *   `license_plate_number`
    *   `license_plate_province`
*   **Image File Paths:**
    *   `left_camera_image_file`: Path to the left camera image for container verification.
    *   `right_camera_image_file`: Path to the right camera image for container verification.
    *   `top_camera_image_file`: Path to the top camera image for container verification.
    *   `license_plate_image_file`: Path to the image for license plate verification.
*   **Corrected Data Columns (Output - these will be created by the script):**
    *   `corrected_container_number`
    *   `corrected_license_plate_number`
    *   `corrected_license_plate_province`

**Note on Input File Naming:** The input Excel file is often named based on the date, e.g., `9-6-2025.xlsx`. The script accepts any valid file name provided as a command-line argument.

**Note on Configuration:** If your input Excel file is not found when you first run the script, a dummy file with these headers and some sample data will be created. You can use this as a template. The column names can be changed directly in the `config` dictionary within the `main.py` script if needed.

## Image Requirements
*   Image paths in the Excel file must be absolute or relative paths accessible from where the script is run.
*   Supported image formats include common types like PNG, JPEG, TIFF, etc. (those supported by Pillow and Tesseract).
*   Image quality is key for accurate OCR. Blurry or low-resolution images may result in poor text extraction.

## How to Run
1.  Ensure all requirements (Python, Tesseract, Python libraries) are installed.
2.  Open your terminal or command prompt.
3.  Navigate to the directory where `main.py` is located.
4.  Run the script using the following command structure:

    ```bash
    python main.py <your_input_excel.xlsx> -o <your_output_excel.xlsx>
    ```
    *   **`<your_input_excel.xlsx>`:** (Required) Replace with the path to your input Excel file.
    *   **`-o <your_output_excel.xlsx>`:** (Optional) Replace with your desired output file name. If omitted, it defaults to `corrected_output.xlsx`.

    **Example:**
    ```bash
    python main.py 9-6-2025.xlsx -o verified_data.xlsx
    ```

### Tesseract Path Configuration (If Needed)
If Tesseract is installed but `pytesseract` cannot find it (e.g., it's not in your system PATH), you can explicitly set the path to the Tesseract executable within the `main.py` script. Near the top of the file, uncomment and modify the following line:
```python
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # Example for Windows
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract' # Example for Linux
```

## Output Rules
The script generates a new Excel file (e.g., `corrected_output.xlsx`) containing all original data plus the new "corrected" columns. The "corrected" columns are populated based on these rules:

1.  **Perfect Match:** If the Excel record matches the image information (after applying relevant normalizations), the corrected column is left **blank**.
2.  **Mismatch:** If the Excel record does not match the image, the correct information (read from the image via OCR and appropriately formatted) is entered into the corrected column.
3.  **Unreadable Image:** If image(s) exist but OCR cannot read usable text from any of them, a single hyphen (`-`) is entered.
4.  **Missing Image:** If a record has no corresponding image file (path invalid or missing for all relevant image columns), two hyphens (`--`) are entered.

## Special Handling & Business Logic

### License Plate Number Transformation
A key transformation is applied to license plate numbers extracted from images:
- Hyphens (`-`) are converted to commas (`,`). For example, if OCR reads `740-699`, it's treated as `740,699`. Similarly, `74-699` becomes `74,699`.
- For comparison accuracy, the script normalizes both the Excel value and the OCR value by removing all non-alphanumeric characters before deciding if a correction is needed. If they differ, the comma-formatted OCR version is stored.

### Container Number - Multi-Image Strategy
For container number verification, the script processes images from up to three columns in a specific order: `left_camera_image_file`, then `right_camera_image_file`, then `top_camera_image_file`.
- The OCR result from the *first* image in this sequence that exists and provides readable text is used.
- If all specified image paths for a record are empty or invalid (file not found), `'--'` is written to the `corrected_container_number` column.
- If image(s) exist but all are unreadable by OCR, `'-'` is written to the `corrected_container_number` column.

## Performance
The script uses Python's `multiprocessing` module to process multiple images concurrently, significantly reducing processing time for large datasets. The number of CPU cores used is typically one less than the total available, to maintain system responsiveness.

## Troubleshooting
*   **`pytesseract.TesseractNotFoundError: tesseract is not installed or not found in your PATH`**:
    *   Ensure Tesseract OCR is installed correctly (see Requirements).
    *   Verify that the Tesseract installation directory is added to your system's PATH environment variable.
    *   If issues persist, try setting the `pytesseract.tesseract_cmd` path directly in the `main.py` script as described above.
*   **OCR Accuracy Issues**:
    *   OCR quality heavily depends on the input image quality. Ensure images are clear, well-lit, and text is reasonably large.
    *   The script uses various text cleaning and normalization techniques. For very noisy images or complex layouts, OCR results might vary.
    *   The current logic for separating license plate numbers and provinces from a single OCR string is basic. If OCR merges them without clear separators, extraction might be imperfect. This area may require further refinement based on specific image characteristics.
*   **Incorrect Language Data:** If OCR results for Thai are poor, ensure the Thai language pack (`tha.traineddata`) for Tesseract is correctly installed and accessible.
