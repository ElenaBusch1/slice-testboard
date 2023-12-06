import sys, argparse

parser = argparse.ArgumentParser(description="Application for controlling FEB2 Slice Testboard")
parser.add_argument('-d', '--debug', action='store_true', help='Enter debug mode.')
parser.add_argument('-n', '--no-connect', action='store_true', help='For testing without a board.')
parser.add_argument('-c', '--command', dest='command', action='store_true', help='Use command line, i.e. no GUI')
parser.add_argument('--configure_lpgbt', dest='configure_lpgbt', required=False, default=None, help='Configure lpGBT, i.e. lpgbt12')
args = parser.parse_args()

if (__name__ == "__main__") and (not args.command):
    from PyQt5 import QtWidgets, QtGui
    import sliceBoardGUI

    app = QtWidgets.QApplication(sys.argv)

    window = sliceBoardGUI.sliceBoardGUI(app, args)
    app.setWindowIcon(QtGui.QIcon('./images/cern.png'))
    window.show()

    sys.exit(app.exec_())

else:
    import sliceBoardGUI
    slice_board = sliceBoardGUI.sliceBoardGUI(None, args)
    if args.configure_lpgbt is not None:
        slice_board.sendFullLPGBTConfigs(args.configure_lpgbt)

