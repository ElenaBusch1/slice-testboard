import sys, argparse
from PyQt5 import QtWidgets, QtGui
import sliceBoardGUI

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GUI for controlling FEB2 Slice Testboard")
    parser.add_argument('-d', '--debug', action='store_true', help='Enter debug mode.')
    parser.add_argument('-n', '--no-connect', action='store_true', help='For testing without a board.')
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)

    window = sliceBoardGUI.sliceBoardGUI(app, args)
    app.setWindowIcon(QtGui.QIcon('./images/cern.png'))
    window.show()

    sys.exit(app.exec_())