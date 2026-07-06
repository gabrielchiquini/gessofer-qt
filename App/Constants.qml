pragma Singleton
import QtQuick

QtObject {
    id: constants

    // ── Dimensions ──────────────────────────────────────
    readonly property int sidebarWidth: 200
    readonly property int sidebarHeaderHeight: 56
    readonly property int navItemHeight: 40
    readonly property int contentMargins: 40

    // ── Colors ──────────────────────────────────────────
    readonly property string sidebarBg: "#2c3e50"
    readonly property string sidebarText: "#ecf0f1"
    readonly property string sidebarHover: "#34495e"
    readonly property string sidebarActive: "#3498db"
    readonly property string sidebarHeaderBg: "#1a252f"
    readonly property string contentBg: "#ecf0f1"
    readonly property string accentColor: "#3498db"
    readonly property string indicatorColor: "#ffffff"
    readonly property string separatorColor: "#bdc3c7"
    readonly property string metaTextColor: "#95a5a6"
    readonly property string hintTextColor: "#bdc3c7"

    // ── Navigation ──────────────────────────────────────
    readonly property var navGroups: [
        {
            title: "Notas",
            items: [
                { label: "Pedidos", group: "Notas" },
                { label: "Cadastrar", group: "Notas" }
            ]
        },
        {
            title: "Despesas",
            items: [
                { label: "Lista", group: "Despesas" },
                { label: "Cadastrar", group: "Despesas" }
            ]
        }
    ]

    // ── Welcome text ────────────────────────────────────
    readonly property string welcomeTitle: "Bem-vindo ao Gessofer"
    readonly property string welcomeSubtitle: "Sistema de Gest\u00e3o de Pedidos e Despesas"
    readonly property string welcomeHint: "Selecione uma op\u00e7\u00e3o no menu lateral para come\u00e7ar"
    readonly property string welcomeLetter: "G"
}
