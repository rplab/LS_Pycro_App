How to run tests:

1. open command prompt

2. set current directory to LS_Pycro_App source folder

i.e.

cd "C:/Users/Raghu/Desktop/Microscope Software/LS_Pycro_App"

3a. To run all tests, enter the following into cmd:

{path_to_python_interpreter} -m unittest discover

i.e.

"C:\Users\Raghu\Desktop\Microscope Software\LS_Pycro_App\venv\Scripts\python.exe" -m unittest discover

3b. To run a specific test, enter the following into cmd

{path_to_python_interpreter} -m unittest discover {relative_import_path}

i.e.

"C:\Users\Raghu\Desktop\Microscope Software\LS_Pycro_App\venv\Scripts\python.exe" -m unittest discover -s LS_Pycro_App.tests.test_htls_offset.TestHTLSOffset

Note that the final part of the relative import can be a module, class, or function name.

i.e. to run the function test_offset in the module test_htls_offset, the following will run only this function:

"C:\Users\Raghu\Desktop\Microscope Software\LS_Pycro_App\venv\Scripts\python.exe" -m unittest discover -s LS_Pycro_App.tests.test_htls_offset.test_offset

