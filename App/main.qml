import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

pragma ComponentBehavior: Bound

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

    // ── Top Navbar ────────────────────────────────────
    Item {
        id: menuBarContainer
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 28

        TopNavbar {
            anchors.fill: parent
            onItemClicked: function(label, groupTitle) {
                root.selectedItem = label
                root.selectedGroup = groupTitle
            }
        }
    }

    // ── Main Content Area ─────────────────────────────
    RowLayout {
        anchors.top: menuBarContainer.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: 0

        WelcomeScreen {}
    }
}
