from controllers.main_controller import MainController
from microscope_configs.klamath.controllers.galvo_controller import GalvoController

class MainController(MainController):
    def __init__(self):
        super().__init__()
        self._galvo_controller = GalvoController()
        self._main_window.galvo_button.clicked.connect(self._galvo_button_clicked)

    def _galvo_button_clicked(self):
        self._galvo_controller.galvo_dialog.show()
        self._galvo_controller.galvo_dialog.activateWindow()