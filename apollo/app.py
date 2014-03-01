# Copyright 2014 John Reese
# Licensed under the MIT license

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import platform
import webbrowser

from argparse import ArgumentParser
from os import path

from PySide import QtCore, QtGui
from PySide.QtCore import Qt, Slot, QUrl, QSettings
from PySide.QtGui import (QApplication, QWidget, QLabel, QMenuBar, QStatusBar,
                          QHBoxLayout, QVBoxLayout, QMessageBox, QDialog,
                          QPushButton, QAction)
from PySide.QtWebKit import QWebView, QWebSettings

from apollo import VERSION
from .log import logger, enable_debug
from .irc import ServerConnection

# global reference to
app = None


class ApolloApp(QApplication):

    log = None
    root = None

    def __init__(self, options, argv):
        QApplication.__init__(self, argv)

        self.log = logger('apollo')
        self.options = options

        self.log.debug('__file__: %s', __file__)
        if path.exists(__file__):
            self.root = path.realpath(path.dirname(__file__))
        else:
            # we're running from a bundle
            self.root = path.realpath(path.dirname(path.dirname(__file__)))
        self.log.debug('running from %s', self.root)

        icon = QtGui.QIcon(path.join(self.root, 'images/logomed.png'))
        self.setWindowIcon(icon)

    @Slot(str)
    def open_url(self, url):
        webbrowser.open(url)

    @Slot(str, result=str)
    def foo(self, word):
        self.log.debug(word)
        return 'foo'


class ApolloWindow(QWidget):

    def __init__(self):
        QWidget.__init__(self)

        self.conn = None
        self.settings = QSettings('noswap.com', 'apollo')

        self.setWindowTitle('apollo')
        self.setMinimumSize(800, 600)
        self.restoreGeometry(self.settings.value('geometry'))

        self.init_menu()
        self.init_status()
        self.init_layout()

    def init_menu(self):
        self.menubar = QMenuBar(self)
        filemenu = self.menubar.addMenu('&File')
        helpmenu = self.menubar.addMenu('&Help')

        quit = QAction('&Quit', self)
        quit.setShortcut(Qt.Modifier.CTRL + Qt.Key_Q)
        quit.triggered.connect(self.close)
        filemenu.addAction(quit)

        about = QAction('&About', self)
        about.triggered.connect(self.about)
        helpmenu.addAction(about)

        about = QAction('About &Qt', self)
        about.triggered.connect(self.about_qt)
        helpmenu.addAction(about)

    def init_status(self):
        self.statusbar = QStatusBar(self)
        self.statusbar.showMessage('apollo ready.')

    def init_layout(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.setMenuBar(self.menubar)

        self.webview = ApolloWebView(self)
        self.webview.loadFile('index.html')
        layout.addWidget(self.webview, 1)

        button = QPushButton("Hello")
        button.setSizePolicy(QtGui.QSizePolicy.Maximum,
                             QtGui.QSizePolicy.Maximum)
        button.clicked.connect(self.connect)
        layout.addWidget(button, 0)
        layout.setAlignment(button, Qt.AlignHCenter)

        layout.addWidget(self.statusbar, 0)

        self.setLayout(layout)

    @Slot()
    def about(self):
        dialog = ApolloAbout(self)
        dialog.show()

    @Slot()
    def about_qt(self):
        QMessageBox.aboutQt(self)

    @Slot()
    def close(self):
        self.settings.setValue('geometry', self.saveGeometry())
        #self.settings.setValue('windowState', self.saveState())
        if self.conn:
            self.conn.quit()
            self.conn.wait()
        QWidget.close(self)

    @Slot()
    def connect(self):
        if not self.conn:
            self.conn = ServerConnection()
            self.conn.event.connect(self.status_update)
            self.conn.start()
            self.statusbar.showMessage('ready...')
        else:
            self.conn.connect_irc()

    @Slot()
    def status_update(self, message):
        self.statusbar.showMessage(message)


class ApolloAbout(QDialog):
    '''\
apollo v{0}<br/>
Python {1}<br/>
Qt {2}<br/>
<br/>
<a href="http://github.com/jreese/apollo">
http://github.com/jreese/apollo</a><br/>
<br/>
Copyright 2014 John Reese.<br/>
Licensed under the MIT license.<br/>
<br/>
'''

    def __init__(self, parent):
        QDialog.__init__(self, parent, 0)

        self.setModal(True)
        self.setWindowTitle('About apollo')
        self.setSizePolicy(QtGui.QSizePolicy.Maximum,
                           QtGui.QSizePolicy.Maximum)

        layout = QHBoxLayout()
        sublayout = QVBoxLayout()
        btnlayout = QHBoxLayout()

        image = QtGui.QPixmap(path.join(app.root, 'images/logobig.png'))
        label = QLabel()
        label.setPixmap(image)
        label.setSizePolicy(QtGui.QSizePolicy.Maximum,
                            QtGui.QSizePolicy.Maximum)
        layout.addWidget(label)
        layout.setAlignment(label, Qt.AlignVCenter)

        about_text = self.__doc__.format(VERSION,
                                         platform.python_version(),
                                         QtCore.__version__)

        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setText(about_text)
        label.linkActivated.connect(app.open_url)
        sublayout.addWidget(label)

        button = QPushButton('Ok')
        button.setSizePolicy(QtGui.QSizePolicy.Maximum,
                             QtGui.QSizePolicy.Maximum)
        button.clicked.connect(self.accept)
        btnlayout.addWidget(button)
        btnlayout.setAlignment(button, Qt.AlignRight)

        sublayout.addLayout(btnlayout)
        layout.addLayout(sublayout)
        self.setLayout(layout)


class ApolloWebView(QWebView):

    def __init__(self, parent=None):
        QWebView.__init__(self, parent)

        settings = {
            QWebSettings.WebAttribute.JavaEnabled: False,
            QWebSettings.WebAttribute.PluginsEnabled: False,
        }

        if app.options.debug:
            settings[QWebSettings.WebAttribute.DeveloperExtrasEnabled] = True

        for key, value in settings.items():
            self.settings().setAttribute(key, value)

        self.frame = self.page().mainFrame()
        self.frame.javaScriptWindowObjectCleared.connect(self.setupDOM)

    def loadFile(self, filename):
        if not path.isabs(filename):
            filename = path.join(app.root, 'html', filename)

        app.log.debug('loading local file %s', filename)
        url = QUrl.fromLocalFile(filename)
        self.load(url)

    def setupDOM(self):
        app.log.debug('setupDOM()')
        self.page().mainFrame().addToJavaScriptWindowObject("apollo", app)


def main(argv):
    '''Main entry point for the apollo application.'''
    global app
    assert(app is None)

    log = logger()

    parser = ArgumentParser(prog='apollo', description='IRC client')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='enable debug output')
    parser.add_argument('-V', '--version', action='version',
                        version='%(prog)s ' + VERSION)

    options = parser.parse_args()

    if options.debug:
        enable_debug()

    log.debug('starting application')

    app = ApolloApp(options, argv)
    window = ApolloWindow()
    window.show()
    app.exec_()
