import QtQuick
import QtQuick.Layouts

Rectangle {
    Layout.preferredWidth: 80
    Layout.preferredHeight: 80
    Layout.alignment: Qt.AlignHCenter
    radius: 40
    color: Constants.accentColor

    Text {
        anchors.centerIn: parent
        text: Constants.welcomeLetter
        font.bold: true
        font.pixelSize: 36
        color: Constants.indicatorColor
    }
}
