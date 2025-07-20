import pandas as pd
from collections import Counter
import tkinter as tk

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
