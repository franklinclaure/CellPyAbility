"""Windows GUI wrapper for GDA analysis using shared CLI backend logic."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import CellPyAbility_toolbox_app as tb_gui
from cellpyability import GDA_interactive_map, gda_analysis
from cellpyability.toolbox import logger


def run():
    def gda_gui():
        image_dir = ''
        plate_map_file = ''
        number_of_drugs = 1
        genotype_codes = []
        entries = {}

        def get_number_of_drugs(selected_plate_map):
            plate_map = GDA_interactive_map.load_plate_map(selected_plate_map)
            gradient_rows = plate_map[
                plate_map['treatment_type'].astype(str).eq('drug_gradient')
            ]
            drugs = gradient_rows['drug'].astype(str).str.strip()
            drugs = drugs[drugs.str.len().gt(0)]
            return drugs.nunique()

        def get_genotype_codes(selected_plate_map):
            plate_map = GDA_interactive_map.load_plate_map(selected_plate_map)
            genotypes = plate_map['genotype'].astype(str).str.strip()
            genotypes = genotypes[genotypes.isin(['g1', 'g2'])]
            return sorted(genotypes.unique())

        def render_fields():
            entries.clear()
            for widget in fields_frame.winfo_children():
                widget.destroy()

            if plate_map_file:
                fields = [
                    ('title_name', 'Enter the title of the experiment:'),
                ]
                if 'g1' in genotype_codes:
                    fields.append(('genotype_1_name', 'Cell condition 1 (genotype):'))
                if 'g2' in genotype_codes:
                    fields.append(('genotype_2_name', 'Cell condition 2 (genotype):'))
                for drug_number in range(1, number_of_drugs + 1): #Makes prompts accord for every drug based on number_of_drugs
                    fields.extend([
                        (f'drug_name{drug_number}', f'Enter the name of drug {drug_number}:'),
                        (f'top_conc{drug_number}', f'Enter the top concentration of drug {drug_number} used:'),
                        (f'dilution{drug_number}', f'Enter a dilution factor for drug {drug_number} (x-fold):'),
                    ])
            else:#If no plate map is provided it defaults to the original GDA layout
                fields = [
                    ('title_name', 'Enter the title of the experiment:'),
                    ('upper_name', 'Enter the name for the upper cell condition (rows B-D):'),
                    ('lower_name', 'Enter the name for the lower cell condition (rows E-G):'),
                    ('top_conc1', 'Enter the top concentration of drug used (column 11):'),
                    ('dilution1', 'Enter the drug dilution factor (x-fold):'),
                ]

            for key, text in fields:#Makes prompts visible on GUI
                ttk.Label(fields_frame, text=text).pack()
                entry = ttk.Entry(fields_frame)
                entry.pack()
                entries[key] = entry

        def select_image_dir():
            nonlocal image_dir
            selected = filedialog.askdirectory()
            if selected:
                image_dir = selected
                image_dir_label.config(text=Path(selected).name)

        def select_plate_map():
            nonlocal plate_map_file, number_of_drugs, genotype_codes
            selected = filedialog.askopenfilename(
                title="Select Plate Map CSV",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            if selected:
                plate_map_file = selected
                number_of_drugs = get_number_of_drugs(selected)
                genotype_codes = get_genotype_codes(selected)
                plate_map_label.config(text=Path(selected).name)
                render_fields()

        #Makes a window and assigns title
        root = tk.Tk()
        root.title('GDA input')

        #Button for uploading Plate Map
        ttk.Button(root, text='Upload a Plate Map', command=select_plate_map).pack()
        plate_map_label = ttk.Label(root, text='No plate map selected')
        plate_map_label.pack()

        #Creates the label that later updates to show the selected plate map filename
        fields_frame = ttk.Frame(root)
        fields_frame.pack()
        render_fields()

        #Button for uploading images
        ttk.Button(root, text='Select Image Directory', command=select_image_dir).pack()
        image_dir_label = ttk.Label(root, text='No image directory selected')
        image_dir_label.pack()

        gui_inputs = {} #Dictionary that drug_params will gather information from for instances in drug objects in gda_analysis

        def submit():#Sotres the information in dictionary when user clicks 'submit' on the GUI
            for key, entry in entries.items():#Adds prompts from GUI as keys and inputs as values to gui_inputs dictionary
                gui_inputs[key] = entry.get().strip()
            gui_inputs['image_dir'] = image_dir
            gui_inputs['plate_map_file'] = plate_map_file
            gui_inputs['number_of_drugs'] = number_of_drugs
            root.destroy()

        ttk.Button(root, text='Submit', command=submit).pack()
        root.mainloop()
        return gui_inputs

    gui_inputs = gda_gui()
    number_of_drugs = int(gui_inputs.get('number_of_drugs', 1))
    required_fields = ['title_name', 'top_conc1', 'dilution1', 'image_dir']
    if gui_inputs.get('plate_map_file'):
        required_fields.insert(1, 'drug_name1')
        if 'genotype_1_name' in gui_inputs:
            required_fields.insert(1, 'genotype_1_name')
        if 'genotype_2_name' in gui_inputs:
            required_fields.insert(1, 'genotype_2_name')
        for drug_number in range(2, number_of_drugs + 1):
            required_fields.extend([f'drug_name{drug_number}', f'top_conc{drug_number}', f'dilution{drug_number}'])
    else:
        required_fields.extend(['upper_name', 'lower_name'])
    missing_fields = [field for field in required_fields if not gui_inputs.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required input(s): {', '.join(missing_fields)}")

    output_base = tb_gui.configure_cli_backend()
    logger.debug('Configured shared CLI backend for GDA GUI run.')


    #stores information from inputs for each drug gradient in a list of dictionries so that class Drug's objects can take values as instances.
    drug_params = None
    genotype_names = None
    if gui_inputs.get('plate_map_file'):
        plate_map = GDA_interactive_map.load_plate_map(gui_inputs['plate_map_file'])
        gradient_rows = plate_map[
            plate_map['treatment_type'].astype(str).eq('drug_gradient')
        ]
        #Example output: Cisplatin: drug_name1
        drug_params = [
            {
                'drug_number': drug_number,
                'drug_name': gui_inputs[f'drug_name{drug_number}'],
                'top_conc': float(gui_inputs[f'top_conc{drug_number}']),
                'dilution': float(gui_inputs[f'dilution{drug_number}']),
                'max_index': int(
                    gradient_rows[
                        gradient_rows['drug'].astype(str).str.strip() == f'd{drug_number}'
                    ]['concentration_index'].astype(int).max()
                ),
            }
            for drug_number in range(1, number_of_drugs + 1)#Makes a dictionary for every drug.
        ]#Makes a list composed of dictionaries that hold relevant information for dose calculations.
        genotype_names = {
            genotype_code: genotype_name
            for genotype_code, genotype_name in (
                ('g1', gui_inputs.get('genotype_1_name')),
                ('g2', gui_inputs.get('genotype_2_name')),
            )
            if genotype_name
        }
    #Runs the GDA analysis using the shared CLI backend logic with the inputs from the GUI.
    gda_analysis.run_gda(
        title_name=gui_inputs['title_name'],
        upper_name=gui_inputs.get('upper_name', ''),
        lower_name=gui_inputs.get('lower_name', ''),
        top_conc=float(gui_inputs['top_conc1']),
        dilution=float(gui_inputs['dilution1']),
        image_dir=gui_inputs['image_dir'],
        show_plot=True,
        output_dir=str(output_base),
        plate_map_file=gui_inputs.get('plate_map_file') or None,
        drug_params=drug_params,
        genotype_names=genotype_names,
    )

if __name__ == '__main__': #run when the file is executed as the main script
    run()
