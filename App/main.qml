pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    visible: true
    minimumWidth: 800
    minimumHeight: 600
    title: "Gessofer"
    color: Constants.contentBg

    property string selectedItem: "Bem-vindo"
    property string selectedGroup: ""

    // ── Top Navbar ────────────────────────────────────
    Rectangle {

        color: Constants.contentBg
        anchors.fill: parent

        ColumnLayout {
            Item {
                id: menuBarContainer
                height: 28

                TopNavbar {
                    anchors.fill: parent
                    onItemClicked: function (label, groupTitle) {
                        root.selectedItem = label;
                        root.selectedGroup = groupTitle;
                    }
                }
            }

            // ── Main Content Area ─────────────────────────────
            ColumnLayout {
                Layout.fillHeight: true
                Layout.fillWidth: true

                spacing: 0

                ProductList {
                    visible: root.selectedItem === "Pedidos" && root.selectedGroup === "Notas"
                }

                WelcomeScreen {
                    visible: !(root.selectedItem === "Pedidos" && root.selectedGroup === "Notas")
                }
            }
        }
    }
}
