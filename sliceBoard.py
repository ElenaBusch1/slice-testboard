import sys, argparse

parser = argparse.ArgumentParser(description="Application for controlling FEB2 Slice Testboard")
parser.add_argument('-d', '--debug', action='store_true', help='Enter debug mode.')
parser.add_argument('-n', '--no-connect', action='store_true', help='For testing without a board.')
parser.add_argument('--configure_lpgbt', dest='configure_lpgbt', required=False, default=None, help='Configure lpGBT, i.e. lpgbt12')
parser.add_argument('--configure_coluta', dest='configure_coluta', required=False, default=None, help='Configure lpGBT, i.e. coluta16')
parser.add_argument('--configure_lauroc', dest='configure_lauroc', required=False, default=None, help='Configure LAUROC, i.e. lauroc15')
parser.add_argument('--configure_all', dest='configure_all', action='store_true', help='Configure all')
args = parser.parse_args()

if (__name__ == "__main__") and (args.configure_lpgbt is None) and (args.configure_coluta is None) and (args.configure_lauroc is None) and (not args.configure_all):
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
    result = True
    if args.configure_lpgbt is not None:
        result &= slice_board.sendFullLPGBTConfigs(args.configure_lpgbt)
    if args.configure_coluta is not None:
        result &= slice_board.sendFullCOLUTAConfig(args.configure_coluta)
    if args.configure_lauroc is not None:
        result &= slice_board.sendFullLAUROCConfigs(args.configure_lauroc)
    if args.configure_all:
        result &= slice_board.configureAll()
    if not result:
        sys.exit(1)

