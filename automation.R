# tidyverse allows us to do our data processing
library("tidyverse")
# readxl allows us to read excel files
library("readxl")
# writexl allows us to write to excel files
library("writexl")
# tidyr lets us reshape our long data into wide data
library("tidyr")
# qpcR lets us merge data frames side by side
library("qpcR")

automation <- function(raw_data) {

#-----------------------------------------------------LONG DATA------------------------------------------------------
# stores a subset of columns from raw_data as long_data
long_data <- raw_data[,c("Plate Name",
                         "Sample",
                         "Assay",
                         "Dilution",
                         "Concentration",
                         "% Recovery Mean",
                         "Calc. Concentration",
                         "Calc. Conc. Mean",
                         "Calc. Conc. CV",
                         "Detection Range",
                         "Detection Limits: Calc. High",
                         "Detection Limits: Calc. Low")]

# separates the sample column into visit and sample number
long_data <- raw_data %>% 
  separate(col = Sample,
           into = c("Sample", "Visit"),
           sep = "_")
#-------------------------------------------------------WIDE DATA-----------------------------------------------------


# selects the "Sample" and "Calc. Conc. Mean columns of the wide_data dataframe
wide_data <- raw_data[,c("Sample",
                         "Assay",
                         "Sample Group",
                         "Calc. Conc. Mean")]
# removes the blank sample
wide_data <- wide_data %>%
  filter(`Sample Group` != "Blanks")

#----------------------------------------------------WIDE SAMPLES----------------------------------------------------
# creates the initial dataframe
wide_sample <- wide_data %>%
  # concatenates columns in order to find and filter for unique observations and then separates into three new columns
  unite("Sample",
        Sample:Assay,
        sep = "_") %>%
  distinct(Sample,
           .keep_all = TRUE) %>%
  separate("Sample",
           into = c("Sample", "Visit", "Assay"),
           sep = "_")

# makes the sample column a numeric data type
wide_sample$Sample <- as.numeric(as.character(wide_sample$Sample))

# drops all rows in sample that are NA
wide_sample <- wide_sample %>%
  drop_na(Sample)

# orders the column by sample
wide_sample <- wide_sample[order(
  wide_sample$Sample),]

# pivots the long format of the original data into a wide format
wide_sample <- wide_sample %>%
  pivot_wider(names_from = c(`Sample Group`,`Assay`, `Visit`), 
              values_from = `Calc. Conc. Mean`,
              names_sep = "_")

#------------------------------------------------------WIDE STANDARDS------------------------------------------------
# filters the wide_data to just the standard samples
wide_std <- wide_data %>%
  filter(grepl("S", wide_data$Sample))

# removes the replicate measurements of the standard 
wide_std <- wide_std %>%
  unite("Sample",
        Sample:Assay,
        sep = "_") %>%
  distinct(Sample,
           .keep_all = TRUE) %>%
  separate(Sample,
           into = c("Sample", "Assay"),
           sep = "_")

# pivots the std data into a wide format
wide_std <- wide_std %>%
  pivot_wider(names_from = Assay,
              values_from = `Calc. Conc. Mean`,
              names_sep = "_")

# adds a separator denoting the type of sample this is (sample/QC)
colnames(wide_std) <- paste(colnames(wide_std),
                            "std",
                            sep = "_")

#-------------------------------------------------------WIDE QC------------------------------------------------------
# establishes the inital wide_qc dataframe
wide_qc <- long_data[,c("Sample",
                        "Assay",
                        "Calc. Conc. Mean")] %>%
  filter(grepl("QC", long_data$Sample))

# converts the concentration column into a numeric value
wide_qc$`Calc. Conc. Mean` <- as.numeric(as.character(wide_qc$`Calc. Conc. Mean`))

# takes the mean of the qc samples by assay and then pivots the table into wide format
wide_qc <- wide_qc %>%
  unite("Sample",
        Sample:Assay,
        sep = "_") %>%
  group_by(Sample) %>%
  summarise("Calc. Conc. Mean" = mean(`Calc. Conc. Mean`),
            .groups = "drop") %>%
  separate(col = Sample,
           into = c("Sample", "Assay"),
           sep = "_") %>%
  pivot_wider(names_from = Assay,
              values_from = `Calc. Conc. Mean`)

colnames(wide_qc) <- paste(colnames(wide_qc),
                            "qc",
                            sep = "_")

# df merging that places the above data frames side by side
wide_data_group <- qpcR:::cbind.na(wide_sample, wide_std, wide_qc)

#----------------------------------------------------LLOD------------------------------------------------------------
# creates a new data frame looking at lowest limit of detection (LLOD)
llod <- raw_data[,c("Sample",
                    "Well",
                    "Signal",
                    "Assay",
                    "Calc. Concentration",
                    "Detection Range")] %>%
  separate(col = Sample,
           into = c("Sample", "Visit"),
           sep = "_")

#----------------------------------------------------LLOD SAMPLES----------------------------------------------------
llod_sample <- llod 
llod_sample$Sample <- as.numeric(as.character(llod_sample$Sample))
llod_sample <- llod_sample %>%
  drop_na(Sample)
llod_sample <- llod_sample[order(
  llod_sample$Sample),]

#--------------------------------------------------------LLOD STANDARDS----------------------------------------------
llod_std <- llod %>%
  filter(grepl("S", llod$Sample))
colnames(llod_std) <- paste(colnames(llod_std), 
                            "std", 
                            sep = "_")
colnames(llod_std)[1] = "Standard"

#---------------------------------------------------------LLOD QC----------------------------------------------------
llod_qc <- llod %>%
  filter(grepl("QC", llod$Sample))
colnames(llod_qc) <- paste(colnames(llod_qc), 
                           "qc", 
                           sep = "_")
colnames(llod_qc)[1] = "QC"

#---------------------------------------------------------LLOD COUNT-------------------------------------------------
# creates a data frame that tallies the number of samples with a detection range at or below the detection/fit curve
llod_count <- llod_sample %>%
  group_by(`Detection Range`) %>%
  tally()

# converts the long data into wide format
llod_count <- pivot_wider(llod_count,
                          names_from = `Detection Range`,
                          values_from = `n`)

# merges the various llod dataframes side by side
llod_group <- qpcR:::cbind.na(llod_sample, 
                              llod_std, 
                              llod_qc, 
                              llod_count)

#------------------------------------------------------INTRAPLATE CVs------------------------------------------------
# takes the Sample ID and Calc. Conc. CV from the long data set
intraplate_cvs <-raw_data[,c("Sample",
                             "Sample Group",
                             "Assay", 
                             "Calc. Conc. CV",
                             "Plate Name")] %>%
  unite(Sample,
        Sample:Assay,
        sep = "_")%>%
  add_count(Sample)

intraplate_cvs <- intraplate_cvs %>%
  filter(`Sample` != "Blanks")


#---------------------------------------------------INTRA SAMPLES----------------------------------------------------
intraplate_cvs_sample <- intraplate_cvs
intraplate_cvs_sample <- distinct(intraplate_cvs_sample,
                                  Sample,
                                  .keep_all = TRUE) %>%
  separate(col = Sample,
           into = c("Sample","Visit","Assay"),
           sep = "_") %>%
  subset(select = -c(`Plate Name`))
intraplate_cvs_sample$Sample <- as.numeric(as.character(intraplate_cvs_sample$Sample))
intraplate_cvs_sample <- intraplate_cvs_sample %>%
  drop_na(Sample)
intraplate_cvs_sample <- intraplate_cvs_sample[order(
  intraplate_cvs_sample$Sample),]


#---------------------------------------------------INTRA STANDARDS--------------------------------------------------
intraplate_cvs_std <- intraplate_cvs %>%
  filter(grepl("S", intraplate_cvs$Sample))
intraplate_cvs_std <- distinct(intraplate_cvs_std,
                               Sample,
                               .keep_all = TRUE) %>%
  subset(select = -c(`Plate Name`))
colnames(intraplate_cvs_std) <- paste(colnames(intraplate_cvs_std),
                                      "std",
                                      sep = "_")
colnames(intraplate_cvs_std)[1] = "Standard"


#------------------------------------------------------INTRA QC------------------------------------------------------
intraplate_cvs_qc <- intraplate_cvs %>%
  filter(grepl("QC", intraplate_cvs$Sample)) %>%
  unite(Sample,
        Sample, `Plate Name`,
        sep = "_") %>%
  group_by(Sample) %>%
  mutate('Intraplate CV' = mean(as.numeric(`Calc. Conc. CV`))) %>%
  ungroup

intraplate_cvs_qc <- distinct(intraplate_cvs_qc,
                              Sample,
                              .keep_all = TRUE)
colnames(intraplate_cvs_qc) <- paste(colnames(intraplate_cvs_qc),
                                     "QC",
                                     sep = "_")
colnames(intraplate_cvs_qc)[1] = "QC"


intracvs_group <- qpcR:::cbind.na(intraplate_cvs_sample, 
                                  intraplate_cvs_std, 
                                  intraplate_cvs_qc)

#--------------------------------------------------------------------------------------------------------------------
README <- read_excel("ReadME_Template.xlsx")

output <-  list(RawData = raw_data, 
                LongData = long_data,
                WideData = wide_data_group,
                WideSampleData = wide_sample,
                LLODs = llod_group,
                IntraplateCVs = intracvs_group,
                README = README) 
}