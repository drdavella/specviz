# The import wizard is implemented in a way that is not specific to any given
# file format, but instead has the concept that a file can include one or more
# datasets, and a dataset can include one or more components. In the case of
# a FITS file, the datasets are HDUs, and components can be columns, standalone
# components (in the case of a Primary or ImageHDU), or spectral WCS for
# example.

import os
import sys
import tempfile
import uuid
from collections import OrderedDict


import yaml
from qtpy import compat
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication, QDialog
from ...core.plugin import plugin
from specutils.io.registers import _load_user_io

from .base_import_wizard import BaseImportWizard
from .parse_fits import simplify_arrays, parse_fits
from .parse_ecsv import parse_ecsv, parse_ascii


def represent_dict_order(self, data):
    return self.represent_mapping('tag:yaml.org,2002:map', data.items())


yaml.add_representer(OrderedDict, represent_dict_order)

class FITSImportWizard(BaseImportWizard):
    dataset_label = 'HDU'

    def as_new_loader_dict(self, name=None):
        """
        Convert the current configuration to a dictionary that can then be
        serialized to a python loader template
        """

        self.new_loader_dict['name'] = name or self.ui.loader_name.text()
        self.new_loader_dict['extension'] = ['fits']

        if self.helper_disp.component_name.startswith('WCS::'):
            self.new_loader_dict['wcs_hdu'] = self.helper_disp.hdu_index

        else:
            self.new_loader_dispersion()
            self.new_loader_dict['wcs_hdu'] = self.helper_disp.hdu_index

        self.new_loader_data()

        self.new_loader_uncertainty()

        if self.ui.bool_mask.isChecked():
            # if going to use this, might need to change this to single
            # dict items
            self.new_loader_dict['mask'] = OrderedDict()
            self.new_loader_dict['mask']['hdu'] = self.helper_mask.hdu_index
            self.new_loader_dict['mask']['col'] = self.helper_mask.component_name
            definition = self.ui.combo_bit_mask_definition.currentData()
            if definition != 'custom':
                self.new_loader_dict['mask']['definition'] = definition

        self.new_loader_dict['meta_author'] = 'Wizard'

    def get_template(self):
        if "uncertainty_hdu" in self.new_loader_dict.keys():
            if self.new_loader_dict['uncertainty_type'] == 'std':
                template = "new_loader_fits_uncer_stddev_py.tmpl"

            else:
                template = "new_loader_fits_uncer_ivar_py.tmpl"

        else:
            template = "new_loader_fits_py.tmpl"

        template_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".", template))

        return template_path


class ASCIIImportWizard(BaseImportWizard):
    dataset_label = 'Table'

    def as_new_loader_dict(self, name=None):
        """
        Convert the current configuration to a dictionary
        that can then be serialized to YAML
        """
        self.new_loader_dict['name'] = name or self.ui.loader_name.text()

        self.new_loader_dispersion()

        self.new_loader_data()

        self.new_loader_uncertainty()

        self.new_loader_dict['meta_author'] = 'Wizard'

        self.add_extension()


    def add_extension(self):
        self.new_loader_dict['extension'] = ['dat']


class ECSVImportWizard(ASCIIImportWizard):

    def add_extension(self):
        self.new_loader_dict['extension'] = ['ecsv']


@plugin("Loader Wizard")
class LoaderWizard(QDialog):
    @plugin.tool_bar("Loader Wizard", icon=QIcon(":/icons/012-file.svg"), location=0)
    def open_wizard(self):

        filters = ["FITS, ECSV, text (*.fits *.ecsv *.dat *.txt)"]
        filename, file_filter = compat.getopenfilename(filters=";;".join(filters))

        if filename == '':
            return

        if filename.lower().endswith('fits'):
            dialog = FITSImportWizard(simplify_arrays(parse_fits(filename)))

        elif filename.lower().endswith('ecsv'):
            dialog = ECSVImportWizard(simplify_arrays(parse_ecsv(filename)))

        elif filename.lower().endswith('dat') or filename.lower().endswith('txt'):
            dialog = ASCIIImportWizard(simplify_arrays(parse_ascii(filename)))

        else:
            raise NotImplementedError(file_filter)

        val = dialog.exec_()

        if val == 0:
            return

        # Make temporary YAML file
        yaml_file = tempfile.mktemp()
        with open(yaml_file, 'w') as f:
            f.write(dialog.as_new_loader(name=str(uuid.uuid4())))

        # Temporarily load YAML file
        # yaml_filter = load_yaml_reader(yaml_file)

        def remove_yaml_filter(data):

            # Just some checking in the edge case where a user is simultaneously loading another file...
            if data.name != os.path.basename(filename).split('.')[0]:
                return

            # io_registry._readers.pop((yaml_filter, Spectrum1DRef))
            # io_registry._identifiers.pop((yaml_filter, Spectrum1DRef))

            # dispatch.unregister_listener("on_added_data", remove_yaml_filter)

        # dispatch.register_listener("on_added_data", remove_yaml_filter)
        #
        # # Emit signal to indicate that file should be read
        # dispatch.on_file_read.emit(file_name=filename,
        #                            file_filter=yaml_filter)


if __name__ == "__main__":

    app = QApplication([])
    dialog = FITSImportWizard(simplify_arrays(parse_fits(sys.argv[1])))
    dialog.exec_()
