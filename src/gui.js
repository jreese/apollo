var app = require('app')
var dialog = require('dialog')
var menu = require('menu')

/*
Build the application menu for the current platform.
*/
exports.application_menu = function(window) {
    var file = {
        label: 'File',
        submenu: [
            {
                label: 'Quit',
                accelerator: 'CmdOrCtrl+Q',
                click: function() {
                    app.quit()
                }
            },
        ]
    }

    var help = {
        label: 'Help',
        submenu: []
    }

    var about = {
        label: 'About Apollo',
        click: function() {
            dialog.showMessageBox(window, {
                title: 'About Apollo',
                message: 'Apollo v' + app.getVersion(),
                buttons: ['ok'],
            })
        }
    }

    if (process.platform == 'darwin') {
        file.submenu.push(about)
    } else {
        help.submenu.push(about)
    }

    return menu.buildFromTemplate([
        file,
        help,
    ])
}
