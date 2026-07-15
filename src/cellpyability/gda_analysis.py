"""
GDA analysis module receives user input from CLI or CellPyAbility GUI, then runs statistical and graphical analysis
of the nuclei counts from CellProfiler.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import toolbox as tb

# Initialize toolbox
logger, base_dir = tb.logger, tb.base_dir




def run_gda(title_name, upper_name, lower_name, top_conc, dilution, image_dir, show_plot=True, counts_file=None, output_dir=None, plate_map_file=None, drug_params=None, genotype_names=None):
    """
    Run GDA (Growth Delay Assay) analysis for two cell lines (B-D, E-G) and one drug gradient (2-11).
    
    Parameters:
    -----------
    title_name : str
        Title of the experiment
    upper_name : str
        Name for upper cell condition (rows B-D)
    lower_name : str
        Name for lower cell condition (rows E-G)
    top_conc : float
        Top concentration in molar
    dilution : float
        Dilution factor between columns
    image_dir : str
        Directory containing the 60 well images
    show_plot : bool
        Whether to display the plot (default: True)
    counts_file : str, optional
        Path to pre-existing counts CSV file (for testing)
    output_dir : str, optional
        Custom output directory. If None, uses current working directory.
    plate_map_file : str, optional
        Path to a CellPyAbility plate map CSV. If provided, genotype, vehicle,
        gradient, and technical replicate metadata are read from the map instead
        of using the historical rows B-D / E-G and columns 2-11 assumptions.
    drug_params : list of dict, optional
        Plate-map-only drug parameters collected by the GUI. Each item contains
        drug_number, top_conc, and dilution.
    genotype_names : dict, optional
        Plate-map-only display names for genotype codes, e.g. {"g1": "Cell A"}.
    """
    
    # Create a concentration range array
    doses = tb.gen_dose_range(top_conc, dilution, 9) # 9 because 9 doses, excluding vehicle (columns 3-11)
    
    # Run CellProfiler headless and return a DataFrame with the raw nuclei counts and the .csv path
    df_cp, cp_csv = tb.run_cellprofiler(image_dir, counts_file=counts_file, output_dir=output_dir)
    
    # Standardize CellProfiler counts columns
    df_cp = tb.standardize_counts_dataframe(df_cp)
    
    # Rename rows from the TIFF file names to the corresponding well names
    df_cp['well'] = df_cp['well'].apply(lambda x: tb.rename_wells(x))
    logger.debug('CellProfiler output rows renamed to well names.')
    
    # Extract full 96-well row/column designators for pivoting
    df_cp[['Row','Column']] = df_cp['well'].str.extract(r'^([A-H])([1-9]|1[0-2])$')
    if df_cp[['Row', 'Column']].isnull().any().any():
        raise tb.DataValidationError(
            "Could not extract expected 96-well coordinates (A-H, 1-12) from one or more filenames."
        )
    logger.debug('Extracted Row and Column from well names.')

    #If the user provides a plate map, disregard the rows and columns asssignments with B-G and 2-11 and use the plate map instead to run the GDA analysis
    #***This currently uses same top_conc and dilution for every drug gradient. Code needs to be updated to allow for different top_conc and dilution for each drug gradient.***
    if plate_map_file is not None:
        return _run_gda_from_plate_map(
            title_name=title_name,
            top_conc=top_conc,
            dilution=dilution,
            drug_params=drug_params,
            df_cp=df_cp,
            cp_csv=cp_csv,
            plate_map_file=plate_map_file,
            show_plot=show_plot,
            output_dir=output_dir,
            genotype_names=genotype_names,
        )
    
    # Pivot nuclei counts into a matrix for fast group stats
    #* Takes outputed CellProfiler counts and puts into a matrix that matches plate format
    count_matrix = df_cp.pivot(index='Row', columns='Column', values='nuclei')
    logger.debug('Pivoted df_cp into count_matrix.')
    
    # Define upper and lower rows
    upper_rows = ['B', 'C', 'D']
    lower_rows = ['E', 'F', 'G']
    
    # Compute mean nuclei per column for upper and lower groups
    upper_counts = count_matrix.loc[upper_rows]
    lower_counts = count_matrix.loc[lower_rows]
    
    upper_means = upper_counts.mean(axis=0)
    lower_means = lower_counts.mean(axis=0)
    
    # Normalize means to vehicle control (column '2')
    upper_vehicle = upper_means['2']
    lower_vehicle = lower_means['2']
    upper_normalized_means = (upper_means / upper_vehicle).loc[[str(i) for i in range(2,12)]].tolist()
    lower_normalized_means = (lower_means / lower_vehicle).loc[[str(i) for i in range(2,12)]].tolist()
    logger.debug('Upper and lower mean nuclei counts normalized to vehicle.')
    
    # Compute standard deviations of normalized counts per condition
    upper_sd = (upper_counts.div(upper_vehicle)).std(axis=0).loc[[str(i) for i in range(2,12)]].tolist()
    lower_sd = (lower_counts.div(lower_vehicle)).std(axis=0).loc[[str(i) for i in range(2,12)]].tolist()
    logger.debug('Computed standard deviations for normalized counts.')
    
    # Pair column number with drug dose
    column_labels = [str(i) for i in range(2,12)]
    
    all_doses = np.insert(doses, 0, 0) # add zero to start of NumPy array for vehicle
    column_concentrations = dict(zip(column_labels, all_doses))
    
    # Define file path to or create gda_output/ subfolder in output directory
    output_base = tb.get_output_base_dir(output_dir)
    gda_output_dir = output_base / 'gda_output'
    gda_output_dir.mkdir(exist_ok=True)
    logger.debug(f'gda_output/ directory created at {gda_output_dir}')
    
    # Consolidate analytics into a new .csv file
    df_stats = pd.DataFrame(columns=column_labels)
    df_stats.index.name = '96-Well Column'
    df_stats.loc['Drug Concentration'] = list(column_concentrations.values())
    df_stats.loc[f'Relative Cell Viability {upper_name}'] = upper_normalized_means
    df_stats.loc[f'Relative Cell Viability {lower_name}'] = lower_normalized_means
    df_stats.loc[f'Relative Standard Deviation {upper_name}'] = upper_sd
    df_stats.loc[f'Relative Standard Deviation {lower_name}'] = lower_sd
    df_stats.to_csv(gda_output_dir / f'{title_name}_gda_Stats.csv')
    logger.info(f'{title_name}_gda_Stats saved to {gda_output_dir}.')

    
    # Normalize nuclei counts for each well individually so that you can make a viability matrix.
    vehicle_map = {r: upper_vehicle for r in upper_rows}
    vehicle_map.update({r: lower_vehicle for r in lower_rows})
    df_cp['normalized_nuclei'] = df_cp['nuclei'] / df_cp['Row'].map(vehicle_map)
    logger.debug('Each well normalized to its condition vehicle (Vectorized).')
    
    # Create viability matrix via pivot on normalized values
    viability_matrix = df_cp.pivot(index='Row', columns='Column', values='normalized_nuclei')
    
    # Reindex to maintain plate order and replace column labels with doses
    viability_matrix = viability_matrix.reindex(index=upper_rows+lower_rows, columns=column_labels)
    viability_matrix.columns = [column_concentrations[col] for col in viability_matrix.columns]
    
    # Rename rows to replicates
    viability_matrix.index = [f'{upper_name} rep {i}' for i in [1,2,3]] + [f'{lower_name} rep {i}' for i in [1,2,3]]
    logger.debug('Created viability matrix via vectorized pivot.')
    
    # Save the viability matrix as a .csv
    viability_matrix.to_csv(gda_output_dir / f'{title_name}_gda_ViabilityMatrix.csv')
    logger.info(f'{title_name} viability matrix saved to {gda_output_dir}.')
    
    # Assign doses to the x-axis
    x = np.array(doses)
    
    # Assign average normalized nuclei counts to the y-axis for each condition
    # skip the vehicle at index 0
    y1 = np.array(upper_normalized_means[1:])
    y2 = np.array(lower_normalized_means[1:])
    logger.debug('Assigned doses and normalized means to x and y values via NumPy, respectively.')
    
    # Fit each condition and keep the full selected-fit model output.
    fit_results = []
    for label, y_values in ((upper_name, y1), (lower_name, y2)):
        try:
            comparison = tb.fit_response_models(x, y_values, label)
            if comparison is None:
                raise ValueError("Neither 4PL nor 5PL could be fit.")
            selected_fit = comparison['selected_fit']
            fit_results.append(
                (
                    label,
                    selected_fit['x_fit'],
                    selected_fit['y_fit'],
                    selected_fit['params']['IC50'],
                    comparison,
                )
            )
            logger.debug(f'{label} condition curve fitting complete.')
        except Exception as exc:
            logger.warning(f'Could not fit {label}: {exc}')
            fit_results.append((label, x, y_values, np.nan, None))

    _, x_plot_fit_y1, y_plot_fit_y1, IC50_val_y1, _ = fit_results[0]
    _, x_plot_fit_y2, y_plot_fit_y2, IC50_val_y2, _ = fit_results[1]
    
    # Calculate ratio (Handling potential NaNs safely)
    if np.isnan(IC50_val_y1) or np.isnan(IC50_val_y2):
        IC50_ratio = np.nan
    else:
        IC50_ratio = IC50_val_y1 / IC50_val_y2
        
    logger.info(f'{upper_name} IC50 / {lower_name} IC50 = {IC50_ratio}')
    
    # Plot the curves using the variables defined above
    plt.plot(x_plot_fit_y1, y_plot_fit_y1, 'b-')
    plt.plot(x_plot_fit_y2, y_plot_fit_y2, 'r-')
    logger.debug('Plotted data.')
    
    # Create scatter plot
    # Create basic structure
    plt.style.use('default')
    plt.xscale('log')
    plt.scatter(x, y1, color='blue', label=str(upper_name))
    plt.scatter(x, y2, color='red', label=str(lower_name))
    plt.errorbar(x, y1, yerr=upper_sd[1:], fmt='o', color='blue', capsize=3)
    plt.errorbar(x, y2, yerr=lower_sd[1:], fmt='o', color='red', capsize=3)
    
    # Annotate the plot
    plt.xlabel('Concentration (M)')
    plt.ylabel('Relative Cell Survival')
    plt.title(str(title_name))
    plt.text(0.05, 0.09, f'IC50 = {IC50_val_y1:.2e}',
        color='blue',
        fontsize=10,
        transform=plt.gca().transAxes
    )
    plt.text(
        0.05, 0.05, f'IC50 = {IC50_val_y2:.2e}',
        color='red',
        fontsize=10,
        transform=plt.gca().transAxes
    )
    plt.text(
        0.05, 0.01, f'IC50 ratio = {IC50_ratio:.1f}',
        color='black',
        fontsize=10,
        transform=plt.gca().transAxes
    )
    plt.legend()
    plt.savefig(gda_output_dir / f'{title_name}_gda_plot.png', dpi=200, bbox_inches='tight')
    logger.info(f'{title_name} GDA plot saved to {gda_output_dir}.')

    fitted_params_table = tb.fitted_params_table(
        [(label, comparison) for label, _, _, _, comparison in fit_results]
    )
    for stale_name in (
        f'{title_name}_gda_4pl_params.csv',
        f'{title_name}_gda_5pl_params.csv',
    ):
        stale_path = gda_output_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()
    fitted_params_table.to_csv(gda_output_dir / f'{title_name}_gda_fitted_params.csv')

    if show_plot:
        plt.show()
    else:
        plt.close()
    
    # Rename the CellProfiler output using the provided title name
    counts_csv = gda_output_dir / f'{title_name}_gda_counts.csv'
    
    tb.rename_counts(cp_csv, counts_csv)
    logger.info(f'{title_name} raw counts saved to {gda_output_dir}.')


def _run_gda_from_plate_map(title_name, top_conc, dilution, df_cp, cp_csv, plate_map_file, drug_params=None, show_plot=True, output_dir=None, genotype_names=None):
    """Run GDA analysis using an explicit plate map CSV."""
    from . import GDA_interactive_map

    #import the plate map csv and assign columns to specific data types for analysis
    plate_map = GDA_interactive_map.load_plate_map(plate_map_file)
    plate_map['well'] = plate_map['well'].astype(str)
    plate_map['column'] = plate_map['column'].astype(int)
    plate_map['is_vehicle'] = plate_map['is_vehicle'].astype(bool)

    #Merges the plate map with CellProfiler nuclei counts and checks if plate map has a well that is not present in the CellProfiler counts
    df = df_cp.merge(plate_map, on='well', how='left', validate='many_to_one')
    if df['row'].isna().any():
        missing_wells = df.loc[df['row'].isna(), 'well'].tolist()
        raise ValueError(f'Counts contain wells not present in plate map: {missing_wells}')

    # Blank compact-map cells are allowed and ignored by the analysis.
    df = df[
        df['genotype'].astype(str).str.len().gt(0)
        & df['treatment_type'].astype(str).str.len().gt(0)
    ].copy()

    # Check that the plate map has at least one vehicle and one drug_gradient well for GDA analysis
    if df.empty:
        raise ValueError('Plate map does not assign any wells for GDA analysis.')

    if not (df['treatment_type'] == 'vehicle').any():
        raise ValueError('Plate map must include at least one vehicle well.')

    gradient_rows = df[df['treatment_type'] == 'drug_gradient'].copy()
    if gradient_rows.empty:
        raise ValueError('Plate map must include at least one drug_gradient well for GDA analysis.')

    genotype_names = genotype_names or {}

    def genotype_label(genotype):
        genotype = str(genotype)
        name = str(genotype_names.get(genotype, '')).strip()
        return f'{genotype} ({name})' if name else genotype

    #Creating a class so that each drugs speecific parameters can be stored as separate objects.
    #Organizing the drug parametrs in order to streamline the concentration calculations.
    class Drug:
        def __init__(self, drug_number=None, drug_name=None, top_conc=None, dilution=None, max_index=None):
            self.drug_number = drug_number
            self.drug_name = drug_name
            self.top_conc = top_conc
            self.dilution = dilution
            self.max_index = max_index


    drugs = [] #empty list that will hold the Drug objects for each drug gradient in the plate map.

    #Assigns values to the Drug class objects. Makes a list of objects = to # of drug gradients

    if drug_params is None:
        drug_params = [
            {
                'drug_number': int(str(drug).removeprefix('d')),
                'drug_name': str(drug),
                'top_conc': top_conc,
                'dilution': dilution,
                'max_index': int(group['concentration_index'].max()),
            }
            for drug, group in gradient_rows.groupby('drug')
        ]

    for drug_param in drug_params:
        drugs.append(
            Drug(
                drug_number = drug_param['drug_number'],
                drug_name = drug_param['drug_name'],
                top_conc = drug_param['top_conc'],
                dilution = drug_param['dilution'],
                max_index = drug_param['max_index']
            )
        )


    df['concentration_index'] = (
        pd.to_numeric(df['concentration_index'].replace('', np.nan), errors='coerce')
        .fillna(0)
        .astype(int)
    )#assigns blank/non numeric indices to 0 and converts all other values to integers.
    df['Drug Concentration'] = np.nan #Creates an empty column in the dataframe

    #Loops through each class object in drugs list and makes a dictionary of concentration index and dose for each d
    for drug in drugs:
        doses = tb.gen_dose_range(drug.top_conc, drug.dilution, drug.max_index)#Makes list of doses for each concentration index position.
        dose_lookup = {0: 0.0} #making a dictionary that currently only stores the vehicle concentrationindex and dose.
        dose_lookup.update({idx: dose for idx, dose in enumerate(doses, start=1)})#updates the dictionary with the index and dose.
        drug_mask = df['drug'].astype(str).str.strip() == f'd{drug.drug_number}' #stores rows where 'drug' matches drug_number as boolean mask.
        df.loc[drug_mask, 'Drug Concentration'] = (
            df.loc[drug_mask, 'concentration_index'].map(dose_lookup)
        )#Finds the rows in the mask where True and assigns the corresponding dose to the 'Drug Concentration' column.



    #Calculate the mean nuclei count for vehicle rows of the same genotype.
    vehicle_means = (
        df[df['treatment_type'] == 'vehicle']
        .groupby('genotype')['nuclei']
        .mean()
    )
    missing_vehicle = sorted(set(gradient_rows['genotype']) - set(vehicle_means.index))
    if missing_vehicle:
        raise ValueError(f'Each genotype needs a vehicle control. Missing: {", ".join(missing_vehicle)}')

    df['normalized_nuclei'] = df['nuclei'] / df['genotype'].map(vehicle_means) #normalized nuclei counts.

    # Create output directory for GDA results
    output_base = tb.get_output_base_dir(output_dir)
    gda_output_dir = output_base / 'gda_output'
    gda_output_dir.mkdir(exist_ok=True)

    #Calculates statistics for each genotype and drug combination and makes csv
    grouped = (
        df.groupby(['genotype', 'drug', 'concentration_index', 'Drug Concentration'], dropna=False)
        .agg(
            Mean=('nuclei', 'mean'),
            Standard_Deviation=('nuclei', 'std'),
            Normalized_Mean=('normalized_nuclei', 'mean'),
            Relative_Standard_Deviation=('normalized_nuclei', 'std'),
            Wells=('well', lambda wells: ';'.join(sorted(wells))),
            N=('well', 'count'),
            Map_Codes=('notes', lambda codes: ';'.join(sorted({str(code) for code in codes if str(code)}))),
        )
        .reset_index()
        .sort_values(['genotype', 'drug', 'concentration_index'])
    )
    grouped = grouped.rename(columns={
        'genotype': 'Genotype',
        'drug': 'Drug',
        'concentration_index': 'Concentration Index',
        'Standard_Deviation': 'Standard Deviation',
        'Normalized_Mean': 'Normalized Mean',
        'Relative_Standard_Deviation': 'Relative Standard Deviation',
        'Map_Codes': 'Map Codes',
    })
    grouped['Genotype'] = grouped['Genotype'].map(genotype_label)
    grouped.to_csv(gda_output_dir / f'{title_name}_gda_Stats.csv', index=False)

#Makes a table based on information from platemap and CP counts
    viability_matrix = df[
        [
            'well',
            'row',
            'column',
            'genotype',
            'treatment_type',
            'drug',
            'gradient_id',
            'gradient_axis',
            'concentration_index',
            'Drug Concentration',
            'replicate_group',
            'replicate_index',
            'notes',
            'nuclei',
            'normalized_nuclei',
        ]
    ].sort_values(['row', 'column'])
    viability_matrix = viability_matrix.rename(columns={'notes': 'map_code'})
    viability_matrix['genotype'] = viability_matrix['genotype'].map(genotype_label)
    viability_matrix.to_csv(gda_output_dir / f'{title_name}_gda_bywell.csv', index=False)


    plt.style.use('default')
    fig = plt.figure()
    plotted_any = False
    fitted_param_rows = []
    selected_models = set()
    plot_colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    #Loops through each Genotype and drug combination and fits a curve to the data. Uses Toolbox function to determine if 4PL or 5PL is the best fit. Then plots the data and fitted curve.
    for curve_index, ((genotype, drug), curve_stats) in enumerate(grouped.groupby(['Genotype', 'Drug'])):
        curve_stats = curve_stats[curve_stats['Concentration Index'] > 0].sort_values('Concentration Index')
        if curve_stats.empty:
            continue
        x = curve_stats['Drug Concentration'].astype(float).to_numpy()
        y = curve_stats['Normalized Mean'].astype(float).to_numpy()
        yerr = curve_stats['Relative Standard Deviation'].astype(float).to_numpy()
        label = f'{genotype} {drug}'
        color = plot_colors[curve_index % len(plot_colors)]
        try:
            comparison = tb.fit_response_models(x, y, label)
            if comparison is None:
                raise ValueError("Neither 4PL nor 5PL could be fit.")
            selected_fit = comparison['selected_fit']
            selected_model = comparison['selected_model']
            selected_models.add(selected_model)
            x_fit = selected_fit['x_fit']
            y_fit = selected_fit['y_fit']
            ic50 = selected_fit['params']['IC50']
            plt.plot(x_fit, y_fit, color=color, label='_nolegend_')
            plt.text(
                0.05,
                0.08 + (0.04 * len(plt.gca().texts)),
                f'{label} {selected_model} IC50 = {ic50:.2e}',
                color=color,
                transform=plt.gca().transAxes,
            )
            fitted_param_rows.append((label, comparison))
        except Exception as exc:
            logger.warning(f'Could not fit {label}: {exc}')
        plt.scatter(x, y, color=color, label=label)
        plt.errorbar(x, y, yerr=yerr, fmt='none', color=color, capsize=3)
        plotted_any = True

    plt.xscale('log')
    plt.xlabel('Concentration (M)')
    plt.ylabel('Relative Cell Survival')
    plt.title(str(title_name))
    if selected_models:
        model_title = " + ".join(sorted(selected_models, key=lambda model: int(model[0])))
        fig.canvas.manager.set_window_title(f"{model_title} Plot")
    if plotted_any:
        plt.legend()
    plt.savefig(gda_output_dir / f'{title_name}_gda_plot.png', dpi=200, bbox_inches='tight')

    fitted_params_table = tb.fitted_params_table(fitted_param_rows)
    for stale_name in (
        f'{title_name}_gda_4pl_params.csv',
        f'{title_name}_gda_5pl_params.csv',
    ):
        stale_path = gda_output_dir / stale_name
        if stale_path.exists():
            stale_path.unlink()
    fitted_params_table.to_csv(gda_output_dir / f'{title_name}_gda_fitted_params.csv')

    if show_plot:
        plt.show()
    else:
        plt.close()

    counts_csv = gda_output_dir / f'{title_name}_gda_counts.csv'
    tb.rename_counts(cp_csv, counts_csv)
    logger.info(f'{title_name} plate-map GDA outputs saved to {gda_output_dir}.')
