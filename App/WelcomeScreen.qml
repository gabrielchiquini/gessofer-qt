import QtQuick
import QtQuick.Layouts

Rectangle {
    id: contentArea
    color: Constants.contentBg
    anchors.fill: parent

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Constants.contentMargins
        spacing: 16

        WelcomeIcon {}

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Constants.welcomeTitle
            font.bold: true
            font.pixelSize: 28
            color: Constants.sidebarBg
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Constants.welcomeSubtitle
            font.pixelSize: 16
            color: Constants.metaTextColor
        }

        Rectangle {
            Layout.preferredWidth: 120
            Layout.preferredHeight: 2
            Layout.alignment: Qt.AlignHCenter
            color: Constants.separatorColor
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatDateTime(new Date(), "dddd, dd 'de' MMMM 'de' yyyy ' \u00e0s' HH:mm")
            font.pixelSize: 14
            color: Constants.metaTextColor
        }

        Item { Layout.fillHeight: true }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Constants.welcomeHint
            font.pixelSize: 13
            color: Constants.hintTextColor
        }
    }
}
