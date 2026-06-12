"""Windows GUI wrapper for batch analysis using shared CLI backend logic."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import CellPyAbility_toolbox_app as tb_gui
from cellpyability import cli
from cellpyability.toolbox import logger


def run():
    def batch_gui():
        # Hide the main root window for now
        root = tk.Tk()
        root.withdraw()

        # Ask the user to select the batch configuration CSV
        csv_file = filedialog.askopenfilename(
            title="Select Batch Configuration CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        root.destroy()
        return csv_file

    config_csv = batch_gui()
    if not config_csv:
        # User cancelled
        return

    output_base = tb_gui.configure_cli_backend()
    logger.debug('Configured shared CLI backend for Batch GUI run.')

    try:
        # Re-use the existing batch logic from cli.py
        # show_plot=True to match the user's preference for popups
        cli.run_batch(config_csv, show_plot=True, output_dir=str(output_base))
        messagebox.showinfo("Batch Complete", "All experiments in the batch have been processed.")
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        messagebox.showerror("Batch Error", f"Batch analysis failed: {e}")


if __name__ == '__main__':
    run()
