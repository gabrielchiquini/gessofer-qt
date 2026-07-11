import QtQuick
import QtQuick.Layouts

Rectangle {
    id: contentArea
    color: Constants.contentBg

    Layout.maximumWidth: 1024
    Layout.alignment: Qt.AlignRight

    ColumnLayout {
        Layout.fillHeight: true
        Layout.fillWidth: true

        spacing: 16

        WelcomeIcon {}

        Text {
            text: Constants.welcomeTitle
            font.bold: true
            font.pixelSize: 28
            color: Constants.sidebarBg
        }

        Text {
            text: Constants.welcomeSubtitle
            font.pixelSize: 16
            color: Constants.metaTextColor
        }

        Rectangle {
            Layout.preferredWidth: 120
            Layout.preferredHeight: 2
            color: Constants.separatorColor
        }

        Text {
            text: Qt.formatDateTime(new Date(), "dddd, dd 'de' MMMM 'de' yyyy ' \u00e0s' HH:mm")
            font.pixelSize: 14
            color: Constants.metaTextColor
        }

        Item {
            Layout.fillHeight: true
        }

        Text {
            text: Constants.welcomeHint
            font.pixelSize: 13
            color: Constants.hintTextColor
        }
        Text {
            text: "AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA AAAAAAAAAAAAAAAAAAAAAA "
            font.pixelSize: 13
            color: Constants.hintTextColor
        }
    }
}
