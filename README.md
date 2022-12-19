# Biomarker Study Visualizations

*PROJECT SUMMARY*

This repository is home to data visualizations of anonymized patient data created using R and RStudio for several niomarker studies run jointly by the Wurfel, Morrel, and Bhatraju research groups. The visualizations are created using raw biomarker concentration data collected using a MSD Biomarker Assay Instrument with the biomarkers of interest being Ang-2, sfas, IL-18, and NGAL. This raw data is found in the raw_data folder of the repository. The code for the visualizations is found in the various .rmd files in the main folder outputting files to the visualizations subfolder.

The code for the visualizations is fairly straight forward with documentation in the rmd files detailing any specifics. Broadly, however, a 2x2 grid of box plots and scatter plots are outputted by the various rmd files into the visualizations subfolder. These look at a subset of the patient population based on various clinical factors, such as COVID-19 status, presence of acute kidney injury, and use of dialysis, and then compares their various biomarker concentrations to look for any correlations for future investigation. 

The datasets from the various MSD plates initially had to be joined with each other as well as with clinical patient data, the latter of which had to undergo signifcant data cleaning by transforming variable types and accounting for string inconsistencies. 

*HOW TO USE* 

1. Clone the repo to your local machine
2. To generate the processed data, open the plate_iteration.rmd file
3. Change the path in the read_excel function to the desired raw data set and change the path in the write_xlsx to your desired extension

