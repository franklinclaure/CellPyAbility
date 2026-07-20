"""Windows GUI wrapper for simple analysis using shared CLI backend logic."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import CellPyAbility_toolbox_app as tb_gui
from cellpyability import simple_analysis
from cellpyability.toolbox import logger


def run():
    def simple_gui():
        root = tk.Tk()
        root.title('Simple input')

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

        ttk.Button(root, text='Upload a Plate Map', command=select_plate_map).pack()
        plate_map_label = ttk.Label(root, text='No plate map selected')
        plate_map_label.pack()

        ttk.Label(root, text='Experiment title:').pack()
        title_entry = ttk.Entry(root)
        title_entry.pack()

        image_dir = ''

        def select_dir():
            nonlocal image_dir
            selected = filedialog.askdirectory()
            if selected:
                image_dir = selected
                image_dir_label.config(text=Path(selected).name)

        ttk.Button(root, text='Select images…', command=select_dir).pack()
        image_dir_label = ttk.Label(root, text='No image directory selected')
        image_dir_label.pack()

        inputs = {}

        def on_submit():
            inputs['title'] = title_entry.get().strip()
            inputs['image_dir'] = image_dir
            inputs['plate_map_file'] = plate_map_file
            root.destroy()

        ttk.Button(root, text='Submit', command=on_submit).pack()
        root.mainloop()
        return inputs

    gui = simple_gui()
    required_fields = ['title', 'image_dir']
    missing_fields = [field for field in required_fields if not gui.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required input(s): {', '.join(missing_fields)}")

    output_base = tb_gui.configure_cli_backend()
    logger.debug('Configured shared CLI backend for simple GUI run.')

    simple_analysis.run_simple(
        title=gui['title'],
        image_dir=gui['image_dir'],
        output_dir=str(output_base)
    )


if __name__ == '__main__':
    run()
