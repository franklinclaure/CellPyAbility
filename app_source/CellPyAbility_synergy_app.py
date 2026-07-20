"""Windows GUI wrapper for synergy analysis using shared CLI backend logic."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import CellPyAbility_toolbox_app as tb_gui
from cellpyability import synergy_analysis
from cellpyability.toolbox import logger


def run():
    def synergy_gui():
        image_dir = ''
        plate_map_file = ''

        def select_image_dir():
            nonlocal image_dir
            selected = filedialog.askdirectory()
            if selected:
                image_dir = selected
                image_dir_label.config(text=Path(selected).name)

        def select_plate_map():
            nonlocal plate_map_file
            selected = filedialog.askopenfilename(
                title="Select Plate Map CSV",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if selected:
                plate_map_file = selected
                plate_map_label.config(text=Path(selected).name)

        root = tk.Tk()
        root.title('synergy input')

        ttk.Button(root, text='Upload a Plate Map', command=select_plate_map).pack()
        plate_map_label = ttk.Label(root, text='No plate map selected')
        plate_map_label.pack()

        entries = {}
        fields = [
            ('title_name', 'Enter the title of the experiment:'),
            ('x_drug', 'Enter the drug name for the horizontal gradient:'),
            ('x_top_conc', 'Enter the horizontal top concentration (M):'),
            ('x_dilution', 'Enter the horizontal dilution factor (x-fold):'),
            ('y_drug', 'Enter the drug name for the vertical gradient:'),
            ('y_top_conc', 'Enter the vertical top concentration (M):'),
            ('y_dilution', 'Enter the vertical dilution factor (x-fold):'),
        ]
        for key, text in fields:
            ttk.Label(root, text=text).pack()
            entry = ttk.Entry(root)
            entry.pack()
            entries[key] = entry

        ttk.Button(root, text='Select Image Directory', command=select_image_dir).pack()
        image_dir_label = ttk.Label(root, text='No image directory selected')
        image_dir_label.pack()

        gui_inputs = {}

        def submit():
            for key, entry in entries.items():
                gui_inputs[key] = entry.get().strip()
            gui_inputs['image_dir'] = image_dir
            gui_inputs['plate_map_file'] = plate_map_file
            root.destroy()

        ttk.Button(root, text='Submit', command=submit).pack()
        root.mainloop()
        return gui_inputs

    gui_inputs = synergy_gui()
    required_fields = [
        'title_name', 'x_drug', 'x_top_conc', 'x_dilution',
        'y_drug', 'y_top_conc', 'y_dilution', 'image_dir'
    ]
    missing_fields = [field for field in required_fields if not gui_inputs.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required input(s): {', '.join(missing_fields)}")

    output_base = tb_gui.configure_cli_backend()
    logger.debug('Configured shared CLI backend for synergy GUI run.')

    synergy_analysis.run_synergy(
        title_name=gui_inputs['title_name'],
        x_drug=gui_inputs['x_drug'],
        x_top_conc=float(gui_inputs['x_top_conc']),
        x_dilution=float(gui_inputs['x_dilution']),
        y_drug=gui_inputs['y_drug'],
        y_top_conc=float(gui_inputs['y_top_conc']),
        y_dilution=float(gui_inputs['y_dilution']),
        image_dir=gui_inputs['image_dir'],
        show_plot=True,
        output_dir=str(output_base),
        plate_map_file=gui_inputs.get('plate_map_file') or None
    )


if __name__ == '__main__':
    run()
