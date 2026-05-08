"""
stat_utils.py - Statistical Skills for Clinical AI Agents
This module provides a Python interface to R-based pharmaverse tools 
and gsDesign, specifically formatted for Agentic tool-calling.
"""

import os
import pandas as pd
from typing import Dict, Any, Optional
try:
    import rpy2.robjects as robjects
    from rpy2.robjects import pandas2ri, packages
    from rpy2.robjects.packages import importr
    pandas2ri.activate()
except ImportError:
    print("Warning: rpy2 not installed. R-based tools will be unavailable.")

class ClinicalStatTools:
    def __init__(self):
        """Initializes the R environment and loads essential libraries."""
        try:
            self.base = importr('base')
            self.stats = importr('stats')
            self.gsDesign = importr('gsDesign')
            self.admiral = importr('admiral')  # pharmaverse: ADaM 
            self.tplyr = importr('Tplyr')      # pharmaverse: Tables
        except Exception as e:
            print(f"Error loading R packages: {e}")

    def calculate_gsd_boundaries(self, k: int, test_type: int, alpha: float, beta: float) -> Dict[str, Any]:
        """
        Calculates Group Sequential Design boundaries using the gsDesign R package.
        
        Args:
            k: Number of analyses (interims + final).
            test_type: 1=one-sided, 2=two-sided symmetric, etc.
            alpha: Type I error.
            beta: Type II error (1 - Power).
            
        Returns:
            A dictionary containing efficacy and futility boundaries.
        """
        # Call R function gsDesign::gsDesign()
        design = self.gsDesign.gsDesign(k=k, test_type=test_type, alpha=alpha, beta=beta)
        
        # Convert R object to a readable dictionary/JSON for the Agent
        return {
            "upper_bounds": list(design.rx2('upper').rx2('bound')),
            "lower_bounds": list(design.rx2('lower').rx2('bound')),
            "en": list(design.rx2('en')),  # Expected sample size
            "n_final": design.rx2('n_Sp')[0]
        }

    def derive_adam_columns(self, df_sdtm: pd.DataFrame, dataset_type: str = "ADSL") -> pd.DataFrame:
        """
        Wraps pharmaverse/admiral to derive standard ADaM columns from SDTM data.
        
        Args:
            df_sdtm: A pandas DataFrame containing SDTM data.
            dataset_type: The target ADaM dataset (e.g., 'ADSL', 'ADAE').
            
        Returns:
            A pandas DataFrame with derived ADaM variables.
        """
        # Convert Python DataFrame to R
        r_sdtm = pandas2ri.py2rpy(df_sdtm)
        
        # Conceptual admiral logic:
        # In a real tool, the Agent would provide the specific admiral derivation function
        # Here we provide a high-level wrapper.
        if dataset_type == "ADSL":
            # Example: deriving TRTSDT (Treatment Start Date)
            r_adam = self.admiral.derive_vars_merged(r_sdtm, dataset_add=r_sdtm, by_vars="USUBJID")
        
        return pandas2ri.rpy2py(r_adam)

    def generate_tplyr_table(self, df_adam: pd.DataFrame, target_var: str) -> str:
        """
        Uses Tplyr to generate a summary table (TLF) in ASCII or RTF format.
        """
        r_adam = pandas2ri.py2rpy(df_adam)
        t = self.tplyr.tplyr_table(r_adam, "ARM")
        self.tplyr.add_layer(t, self.tplyr.group_count(target_var))
        
        # Build and capture output
        built_table = self.tplyr.build(t)
        return str(built_table)

# Instance for agent tool-binding
tools = ClinicalStatTools()
