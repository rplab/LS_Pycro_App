## Prerequisites
1. OS: Windows (Tested on 10 and 11)

1. Install [Python](https://www.python.org/downloads) >=3.9. Note: Set environment variable to True in the installation options.

2. Install latest version of [Git](https://git-scm.com/download/win).

## Installing and Setting up Micromanager

1. Install or update [Java](https://www.java.com/en/)

2. Install [Micromanager](https://micro-manager.org/Download_Micro-Manager_Latest_Release). Following versions are known to work:
- Willamette: 2.0.3 20231027
- Klamath: 2.0.3 20230328

## Instructions for Windows PC

1. Create a folder named `Microscope Software` on Desktop

Open command prompt and go to the right directory using `cd`: 
`cd "C:\Users\<your-user-name>\Desktop\Microscope Software"`

e.g. create a folder "Microscope Software" on desktop, and go to it using 
`cd "C:\Users\Will LSM\Desktop\Microscope Software"`

2. Clone git repo: 
`git clone https://github.com/rplab/LS_Pycro_App`

3. This will create a folder "LS_Pycro_App" inside "Microscope Software". Go to this folder: 
`cd LS_Pycro_App`

4. Creating Virtual Environment

   a. Create venv in the folder 'venv':
   `python -m venv venv`

   b. Activate the venv:
   `venv\Scripts\activate`

optional: check if correctly activated using: `where python`, this should give the location inside the venv folder as one of its options.

5. With venv activated (seen by the text `(venv)` before the command prompt), Install dependencies from requirements.txt file:
   `pip install -r requirements.txt`

## Creating shortcuts
Create two shortcuts in Desktop/Microscope Software for ease of launching microscope software:
1. Create Micromanager shortcut and call it: "FIRST_Micro-Manager"
2. Making Pycromanager shortcut:
   
   a. Create a text file "app_start.bat" in LS_Pycro_app with content:
   `"C:\Users\<your-user-name>\Desktop\Microscope Software\LS_Pycro_App\venv\Scripts\python.exe" "C:\Users\<your-user-name>\Desktop\Microscope Software\LS_Pycro_App\app_start.py"`

   e.g. `"C:\Users\Will LSM\Desktop\Microscope Software\LS_Pycro_App\venv\Scripts\python.exe" "C:\Users\Will LSM\Desktop\Microscope Software\LS_Pycro_App\app_start.py"`

   b. Right-click app_start.bat file -> create shortcut. Move this and rename it: "THEN THIS_Sokolight"

## Setting up Micromanager for the first time

- Open Micro-Manager: Go to Tools > Options, and set the same options as in the screenshot here [mmanager_options.png](https://github.com/rplab/LS_Pycro_App/blob/master/LS_Pycro_App/setup_from_scratch/preference_screenshots/mmanager_options.png). 

- ImageJ window (that opens alongwith Micro-manager): Go to Edit > Options > Memory & Threads, and and set the same options as in the screenshot here [imagej_options.png](https://github.com/rplab/LS_Pycro_App/blob/master/LS_Pycro_App/setup_from_scratch/preference_screenshots/imagej_options.png).

### Additional setting for KLA LSM
- Devices > Load Hardware Configuration > Go to "<your-downloaded-LS_Pycro_App-location> -> mmanager_config_files -> KLA_LSM_config", and select all the files > Open. Note: there should be at least two config files: CLS.cfg and HTLS.cfg

### Additional setting for WIL LSM
- Devices > Load Hardware Configuration > Go to "<your-downloaded-LS_Pycro_App-location> -> mmanager_config_files -> WIL_LSM_config", and select all the files > Open.

- Plugins > On-The-Fly Image Processing > Image Flipper > Select "Rotate 90 degrees". This should open the "On-The-Fly Image Processing Pipeline" window, check "Enabled" box.


## Normal usage
Open Microscope Software folder on desktop. Run the First, then Second shortcut to launch the microscope control software.

