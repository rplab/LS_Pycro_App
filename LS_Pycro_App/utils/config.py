import ast
import configparser
import logging
import os

from LS_Pycro_App.controllers.select_controller import microscope, MICROSCOPE_CONFIG_SECTION, MICROSCOPE_CONFIG_OPTION

class Config(configparser.ConfigParser):
    """
    Class that extends configparser. Used to write and read configuration file,
    which are then used to initialize values in class instances.

    Future Changes:

    - _config_section_read() only reads in attributes that are already part of the class.
    Could maybe add a way to dynamically add attributes to class. Only problem is it 
    currently determines the type by the type of the attribute initialized in the class,
    so would need to look into type evaluating.

    - get rid of this and use JSON instead
    """

    COMMENTS_SECTION = "COMMENTS"
    FILE_NAME = "config.cfg"

    def __init__(self, filename: str = None, dir: str = None):
        super().__init__()
        self.FILE_NAME = filename or Config.FILE_NAME
        self.dir = dir or os.curdir
        self.file_path = f"{self.dir}/{self.FILE_NAME}"
        self._logger = logging.getLogger(__name__)
        self.init_from_config_file()
        self._write_comments_section()
        self._write_microscope_section()
    
    def write_config_file(self, file_path: str = None):
        """
        Writes current sections in Config to file at given path. 
        """
        file_path = file_path or self.file_path
        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))
        with open(file_path, "w") as configfile:
            self.write(configfile)
    
    def init_from_config_file(self, file_path: str = None):
        """
        Initializes Config from file located at file_path. 
        """
        file_path = file_path or self.file_path
        if os.path.exists(file_path):
            self.read(file_path)
            self._logger.info("Config file read")
    
    def write_class(self, class_instance: object, section: str = None):
        """
        Writes section to Config with instance attributes of class_instance.
        If section = None, section name is assumed to be the name taken from
        class_instance.__class__.__name__ (this is recommended).
        """
        section = section or class_instance.__class__.__name__
        if not self.has_section(section):
            self.add_section(section)
        #Iterates through all class attributes that aren't dunders
        for attr in [attr for attr in dir(class_instance) if "__" not in attr]:
            value = None
            class_has_attr = hasattr(class_instance.__class__, attr)
            if class_has_attr:
                #first checks if attr is property and grabs value if it is
                if isinstance(getattr(class_instance.__class__, attr), property):
                    value = str(getattr(class_instance, attr))
            #if attr not a property, then we check for class or instance attributes. Current assumption is that
            #an attribute that isn't callable (ie not a function) is a class or instance attribute.
            elif not callable(getattr(class_instance, attr)):
                value = str(getattr(class_instance, attr))
            #value should only be set if it was set to something other than None.
            if value is not None:
                #NOT_CONFIG_PROPS is a list that holds names of instance attributes that shouldn't be 
                #written to config.
                try:
                    if not attr in class_instance.NOT_CONFIG_PROPS:
                        self.set(section, attr.strip("_"), value)
                except AttributeError:
                    self.set(section, attr.strip("_"), value)
        self.write_config_file(self.file_path)
    
    def init_class(self, class_instance, section: str = None):
        """
        Initializes instance attributes of class_instance from values in section, if it exists.
        If section = None, section name is assumed to be the name taken from class_instance.__class__.__name__ 
        (this is recommended for classes with only one instance). 
        
        If section exists in config, returns True. Else, returns False.
        """
        if not section:
            section = class_instance.__class__.__name__
        has_section = self.has_section(section)
        if has_section:
            self._read_config_section(class_instance, section)
            self.write_class(class_instance, section)
        return has_section

    def _read_config_section(self, class_instance: object, section: str):
        """
        Sets class_instance attributes to key-value pairs in section.

        Currently supports int, float, bool, str, and lists and dicts of these types.
        Could add more if it's necessary in the future.
        """
        class_dict = vars(class_instance)
        for key in class_dict.keys():
            #attributes are stripped when written to config, so must be stripped when reading.
            option = key.strip("_")
            if hasattr(class_instance, "NOT_CONFIG_PROPS"):
                if option in class_instance.NOT_CONFIG_PROPS:
                    continue
            try:
                attr_type = type(class_dict[key])
                if attr_type == int:
                    class_dict[key] = self.getint(section, option)
                elif attr_type == float:
                    class_dict[key] = self.getfloat(section, option)
                elif attr_type == bool:
                    class_dict[key] = self.getboolean(section, option)
                elif attr_type == str:
                    class_dict[key] = self.get(section, option)
                else:
                    class_dict[key] = ast.literal_eval(self.get(section, option))
            except:
                exception = f"{section} {key} invalid data type for config initialization"
                self._logger.exception(exception)
            else:
                info = f"{section} {key} read"
                self._logger.info(info)

    def _write_comments_section(self):
        """
        Adds in comments section to config if it doesn't exist.
        """
        section = self.COMMENTS_SECTION
        if not self.has_section(section):
            self.add_section(section)
        self.set(section, "COMMENTS", "PLEASE DO NOT EDIT UNLESS YOU KNOW WHAT YOU ARE DOING")
        self.set(section, "unit_comments", 'All "exposure" attributes are in units of ms and all "pos" attributes are in um.')
        self.write_config_file(self.file_path)

    def _write_microscope_section(self):
        """
        Adds in comments section to config if it doesn't exist.
        """
        if not self.has_section(MICROSCOPE_CONFIG_SECTION):
            self.add_section(MICROSCOPE_CONFIG_SECTION)
        self.set(MICROSCOPE_CONFIG_SECTION, MICROSCOPE_CONFIG_OPTION, microscope.name)
        self.write_config_file(self.file_path)
