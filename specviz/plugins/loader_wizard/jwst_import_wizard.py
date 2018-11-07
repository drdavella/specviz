from qtpy.QtWidgets import QDialog


class JWSTImportWizard(QDialog):

    def __init__(self, filename, parent=None):
        super().__init__(parent=parent)


if __name__ == "__main__":

    import sys
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    dialog = JWSTImportWizard(sys.argv[1])
    dialog.exec_()
