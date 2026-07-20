"""Batch analysis backend shared by the CLI and GUI."""

import csv

from cellpyability.toolbox import CellPyAbilityError, build_gda_drug_params


def run_batch(input_file, show_plot=True, output_dir=None):
    """Run batch processing from a CSV configuration file."""
    from cellpyability import gda_analysis, synergy_analysis

    try:
        with open(input_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                module = row.get('module', '').strip().lower()
                title = row.get('title')
                image_dir = row.get('dir') or row.get('image_dir')

                if not module:
                    print(f"Skipping row with no module specified: {row}")
                    continue

                if module == 'gda':
                    print(f"\n--- Running GDA: {title} ---")
                    plate_map_file = row.get('plate_map') or row.get('plate_map_file') or None
                    top_conc = row.get('top_conc1') or row.get('top_conc') or row.get('conc')
                    dilution = row.get('dilution1') or row.get('dilution') or row.get('dil')
                    drug_params = None
                    genotype_names = None

                    if plate_map_file:
                        from cellpyability import GDA_interactive_map

                        plate_map = GDA_interactive_map.load_plate_map(plate_map_file)
                        gradient_rows = plate_map[
                            plate_map['treatment_type'].astype(str).eq('drug_gradient')
                        ]
                        drug_codes = gradient_rows['drug'].astype(str).str.strip()
                        number_of_drugs = drug_codes[drug_codes.str.len().gt(0)].nunique()
                        if number_of_drugs > 5:
                            raise ValueError(f"Plate map contains {number_of_drugs} drugs, but batch GDA supports up to 5.")

                        def row_float(key, *fallbacks):
                            value = row.get(key)
                            for fallback in fallbacks:
                                value = value or row.get(fallback)
                            return float(value) if value else None

                        drug_params = build_gda_drug_params(
                            plate_map_file,
                            number_of_drugs,
                            lambda drug_number: row.get(f'drug_name{drug_number}'),
                            lambda drug_number: row_float(f'top_conc{drug_number}', *(['top_conc', 'conc'] if drug_number == 1 else [])),
                            lambda drug_number: row_float(f'dilution{drug_number}', *(['dilution', 'dil'] if drug_number == 1 else [])),
                        )
                        genotype_names = {
                            genotype_code: genotype_name
                            for genotype_code, genotype_name in (
                                ('g1', row.get('genotype_1_name')),
                                ('g2', row.get('genotype_2_name')),
                            )
                            if genotype_name
                        }

                    gda_analysis.run_gda(
                        title_name=title,
                        upper_name=row.get('upper') or row.get('upper_name'),
                        lower_name=row.get('lower') or row.get('lower_name'),
                        top_conc=float(top_conc),
                        dilution=float(dilution),
                        image_dir=image_dir,
                        show_plot=show_plot,
                        output_dir=output_dir,
                        plate_map_file=plate_map_file,
                        drug_params=drug_params,
                        genotype_names=genotype_names,
                    )
                elif module == 'synergy':
                    print(f"\n--- Running Synergy: {title} ---")
                    synergy_analysis.run_synergy(
                        title_name=title,
                        x_drug=row.get('xdrug') or row.get('x_drug'),
                        x_top_conc=float(row.get('xconc') or row.get('x_top_conc')),
                        x_dilution=float(row.get('xdil') or row.get('x_dilution')),
                        y_drug=row.get('ydrug') or row.get('y_drug'),
                        y_top_conc=float(row.get('yconc') or row.get('y_top_conc')),
                        y_dilution=float(row.get('ydil') or row.get('y_dilution')),
                        image_dir=image_dir,
                        show_plot=show_plot,
                        output_dir=output_dir
                    )
                else:
                    print(f"Unknown module '{module}' in row: {row}")

    except FileNotFoundError:
        raise CellPyAbilityError(f"Batch input file not found: {input_file}")
    except Exception as e:
        raise CellPyAbilityError(f"Error during batch processing: {e}")
