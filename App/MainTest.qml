pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt.labs.qmlmodels
import App.Backend

ApplicationWindow {
    id: root
    visible: true
    width: 900
    height: 600
    title: "TableView Debug Test"
    color: "#ecf0f1"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 5

        Label {
            text: "Debug Test — TableView with hardcoded data"
            font.bold: true
            font.pixelSize: 16
            Layout.fillWidth: true
        }

        TableView {
            id: tableView
            anchors.fill: parent
            columnSpacing: 1
            rowSpacing: 1
            clip: true

            model: TableModel {
                TableModelColumn {
                    display: "name"
                }
                TableModelColumn {
                    display: "color"
                }

                rows: [
                    {
                        "name": "cat",
                        "color": "black"
                    },
                    {
                        "name": "dog",
                        "color": "brown"
                    },
                    {
                        "name": "bird",
                        "color": "white"
                    }
                ]
            }

            Text {
                id: header
                text: "A table header"
            }

            delegate: Rectangle {
                implicitWidth: 100
                implicitHeight: 50
                border.width: 1

                Text {
                    text: tableView.model.display
                    anchors.centerIn: parent
                }
            }
        }
    }
}
