import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    visible: true
    width: 1024
    height: 680
    minimumWidth: 800
    minimumHeight: 600
    title: "Gessofer"
    color: Constants.contentBg

    property string selectedItem: "Bem-vindo"
    property string selectedGroup: ""
    WelcomeScreen {}
}
