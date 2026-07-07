import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

pragma ComponentBehavior: Bound

MenuBar {
    id: root

    objectName: "navbar"

    // ── Signals ───────────────────────────────────────
    signal itemClicked(string label, string groupTitle)

    // ── Menu: "Notas" ─────────────────────────────────
    Menu {
        id: notasMenu
        objectName: "nav-menu-orders"
        title: Constants.navGroups[0].title

        Repeater {
            model: Constants.navGroups[0].items

           delegate: MenuItem {
                            required property var modelData
                text: modelData.label
                objectName: {
                    if (modelData.label === "Pedidos") return "nav-link-orders-list"
                    if (modelData.label === "Cadastrar") return "nav-link-orders-create"
                    return ""
                }
                onTriggered: root.itemClicked(modelData.label, modelData.group)
            }
        }
    }

    // ── Menu: "Despesas" ──────────────────────────────
    Menu {
        id: despesasMenu
        objectName: "nav-menu-expenses"
        title: Constants.navGroups[1].title

        Repeater {
            model: Constants.navGroups[1].items

            delegate: MenuItem {
                            required property var modelData
                text: modelData.label
                objectName: {
                    if (modelData.label === "Lista") return "nav-link-expenses-list"
                    if (modelData.label === "Cadastrar") return "nav-link-expenses-create"
                    return ""
                }
                onTriggered: root.itemClicked(modelData.label, modelData.group)
            }
        }
    }
}
