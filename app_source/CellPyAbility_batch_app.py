"""Windows GUI wrapper for batch analysis using shared CLI backend logic."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import CellPyAbility_toolbox_app as tb_gui
from cellpyability import cli
from cellpyability.toolbox import logger


def run():
    def batch_gui():
        root = tk.Tk()
        root.title('Batch input')
        config_csv = ''
        plate_map_file = ''

        def select_plate_map():
            nonlocal plate_map_file
            selected = filedialog.askopenfilename(
                title="Select Plate Map CSV",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if selected:
                plate_map_file = selected
                plate_map_label.config(text=Path(selected).name)

        def select_config_csv():
            nonlocal config_csv
            selected = filedialog.askopenfilename(
                title="Select Batch Configuration CSV",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if selected:
                config_csv = selected
                config_label.config(text=Path(selected).name)

        def submit():
            root.destroy()

        ttk.Button(root, text='Upload a Plate Map', command=select_plate_map).pack()
        plate_map_label = ttk.Label(root, text='No plate map selected')
        plate_map_label.pack()

        ttk.Button(root, text='Select Batch Configuration CSV', command=select_config_csv).pack()
        config_label = ttk.Label(root, text='No batch CSV selected')
        config_label.pack()

        ttk.Button(root, text='Submit', command=submit).pack()
        root.mainloop()
        return config_csv

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
