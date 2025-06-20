# SAPOS Tagging Toolkit

> **Important third-party software & services**  
> - **REDtoolbox** (proprietary): used as an intermediary for geotagging.  
>   [Purchase/licensing information →](https://www.redcatch.at/redtoolbox/#buy)  
> - **DJI Terra** (proprietary but **free** for geotagging & Zenmuse L2 processing):  
>   [Download DJI Terra →](https://www.dji.com/de/downloads/products/dji-terra#other_software)  
> - **SAPOS® service** (account and data downloads typically fee-based): requires registration and incurs usage fees per data request or via subscriptions; pricing varies by region.  
>   [Learn more →](https://www.sapos.de/)

**Automate geotagging and PPK preparation for UAV drone imagery using SAPOS and REDToolbox/DJI Terra.**

---

## Features

### 1. General SAPOS Query Generation
- **Supported Models**: DJI Phantom 4 Multispectral, Phantom 4 RTK, Zenmuse L2, Mavic 3 Enterprise, Wingtra
- Auto-generate SAPOS query files for download from [sapos.bayern.de](https://sapos.bayern.de/shop.php)  
- Rename `.25o` files to `.obs` for compatibility with DJI Terra processing
- Notebook: general_SAPOS_query.ipynb


### 2. WZE-UAV (Phantom 4 Multispectral) → Agisoft Metashape Workflow
- Auto-generate SAPOS query files for download from [sapos.bayern.de](https://sapos.bayern.de/shop.php)
- Copy VRS files into `FPLAN` folders by TNR (plot ID code)
- Generate Windows batch script for REDToolbox CLI commands (for geotagging) for Post-Processed Kinematic (PPK)
- Organize outputs and PPK-ready images
- Notebook: wze-uav_SAPOS_REDToolBox_pipeline.ipynb

---

## Installation
This package was developed and tested on Windows Server 2016 running python=3.9.

We use conda to create a new environment:

user@userpc: /sapos_tagging$ conda create -n py3.9
user@userpc: /sapos_tagging$ conda activate py3.9
(py3.9) user@userpc: /sapos_tagging$ conda install python=3.9 

Then we use pip to install all other packages specified in the requirements.txt:

(py3.9) user@userpc: /sapos_tagging$ pip install --file requirements.txt
