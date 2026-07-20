"""Windows GUI wrapper for batch analysis using shared backend logic."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import CellPyAbility_toolbox_app as tb_gui
from cellpyability import batch_analysis
from cellpyability.toolbox import logger


def run():
    def batch_gui():
        root = tk.Tk()
        root.title('Batch input')
        config_csv = ''

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
    logger.debug('Configured shared batch backend for Batch GUI run.')

    try:
        batch_analysis.run_batch(
            input_file=config_csv,
            show_plot=True,
            output_dir=str(output_base),
        )
        messagebox.showinfo("Batch Complete", "All experiments in the batch have been processed.")
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        messagebox.showerror("Batch Error", f"Batch analysis failed: {e}")


if __name__ == '__main__':
    run()
